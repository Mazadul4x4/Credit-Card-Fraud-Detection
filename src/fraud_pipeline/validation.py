"""Great Expectations setup and validation-result parsing used by the ingestion DAG."""

import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

import great_expectations as gx
import pandas as pd
from great_expectations.checkpoint import UpdateDataDocsAction
from great_expectations.core.run_identifier import RunIdentifier

import fraud_pipeline.gx_custom  # noqa: F401  (registers the custom expectation)
from fraud_pipeline.gx_suite import SUITE_NAME, build_expectations, build_suite
from fraud_pipeline.schema import ERROR_CATEGORIES, REQUIRED_COLUMNS

GX_PROJECT_ROOT = os.getenv("GX_PROJECT_ROOT", "/opt/airflow/gx_project")
DATASOURCE_NAME = "pandas_runtime"
ASSET_NAME = "ingested_file"
BATCH_DEFINITION_NAME = "whole_file"
VALIDATION_DEFINITION_NAME = "creditcard_validation"
CHECKPOINT_NAME = "creditcard_checkpoint"
DATA_DOCS_SITE = "local_site"


# --------------------------------------------------------------------------- setup
def get_context(project_root: str = GX_PROJECT_ROOT):
    return gx.get_context(mode="file", project_root_dir=project_root)


def setup_context(context) -> None:
    """Create (or update) datasource, asset, batch definition, suite, validation
    definition and checkpoint. Safe to run many times."""
    try:
        datasource = context.data_sources.get(DATASOURCE_NAME)
    except (KeyError, ValueError):
        datasource = context.data_sources.add_pandas(name=DATASOURCE_NAME)

    try:
        asset = datasource.get_asset(ASSET_NAME)
    except LookupError:
        asset = datasource.add_dataframe_asset(name=ASSET_NAME)

    try:
        batch_definition = asset.get_batch_definition(BATCH_DEFINITION_NAME)
    except (KeyError, ValueError):
        batch_definition = asset.add_batch_definition_whole_dataframe(BATCH_DEFINITION_NAME)

    # The suite is defined in code (gx_suite.py). Only rewrite it when the rules changed,
    # so the JSON committed in the repo stays stable.
    try:
        suite = context.suites.get(SUITE_NAME)
    except Exception:
        suite = None
    if suite is None:
        suite = context.suites.add(build_suite())
    elif _signature(suite.expectations) != _signature(build_expectations()):
        for expectation in list(suite.expectations):
            suite.delete_expectation(expectation)
        for expectation in build_expectations():
            suite.add_expectation(expectation)

    try:
        validation_definition = context.validation_definitions.get(VALIDATION_DEFINITION_NAME)
    except Exception:
        validation_definition = context.validation_definitions.add(
            gx.ValidationDefinition(
                name=VALIDATION_DEFINITION_NAME, data=batch_definition, suite=suite
            )
        )

    checkpoint = gx.Checkpoint(
        name=CHECKPOINT_NAME,
        validation_definitions=[validation_definition],
        actions=[UpdateDataDocsAction(name="update_data_docs", site_names=[DATA_DOCS_SITE])],
        result_format={"result_format": "COMPLETE"},
    )
    context.checkpoints.add_or_update(checkpoint)


def _signature(expectations) -> list:
    return [(e.expectation_type, dict(e.configuration.kwargs), e.meta) for e in expectations]


# ------------------------------------------------------------------ run + parse
def run_checkpoint(df: pd.DataFrame, file_name: str, context=None) -> dict:
    """Validate one ingested file and return a JSON-serialisable summary."""
    context = context or get_context()
    checkpoint = context.checkpoints.get(CHECKPOINT_NAME)
    run_name = f"{Path(file_name).stem}_{datetime.now(timezone.utc):%Y%m%dT%H%M%S}"
    result = checkpoint.run(
        batch_parameters={"dataframe": df}, run_id=RunIdentifier(run_name=run_name)
    )
    result_id, validation_result = next(iter(result.run_results.items()))
    report_path = _report_path(result_id, context)
    summary = summarize_results(validation_result.results, total_rows=len(df))
    summary["report_path"] = report_path
    summary["validation_success"] = bool(validation_result.success)
    return summary


def _report_path(result_id, context) -> str:
    """Path of this run's Data Docs HTML page, relative to the Data Docs site root
    (gx_project/gx/uncommitted/data_docs/local_site/)."""
    try:
        urls = context.get_docs_sites_urls(resource_identifier=result_id, site_names=[DATA_DOCS_SITE])
        path = Path(unquote(urlparse(urls[0]["site_url"]).path)).resolve()
        site_root = (Path(context.root_directory) / "uncommitted" / "data_docs" / DATA_DOCS_SITE).resolve()
        return path.relative_to(site_root).as_posix()
    except Exception:
        return ""


def summarize_results(results, total_rows: int) -> dict:
    """Turn GX expectation results into per-category row counts and the set of bad rows."""
    rows_by_category: dict[str, set] = {category: set() for category in ERROR_CATEGORIES}
    failed_expectations = []
    missing_columns: list[str] = []

    for res in results:
        config = res.expectation_config
        category = (config.meta or {}).get("category", "validity")
        if res.success:
            continue

        details = res.result or {}
        if config.type == "expect_table_columns_to_match_set":
            observed = set(details.get("observed_value") or [])
            missing_columns = sorted(set(REQUIRED_COLUMNS) - observed)
            if not missing_columns:  # extra columns only: not an error for us
                continue
        elif res.exception_info and _raised(res.exception_info):
            # Expectation could not run, usually because the column is missing.
            # That is already reported by the schema expectation.
            continue
        else:
            indexes = details.get("unexpected_index_list") or []
            rows_by_category[category].update(int(i) for i in indexes)

        failed_expectations.append(
            {
                "expectation": config.type,
                "column": config.kwargs.get("column"),
                "category": category,
                "unexpected_count": details.get("unexpected_count", len(missing_columns)),
            }
        )

    if missing_columns:
        # A missing required column makes every row of the file unusable.
        rows_by_category["schema"] = set(range(total_rows))

    invalid_rows = set().union(*rows_by_category.values())
    invalid_count = len(invalid_rows)
    invalid_ratio = invalid_count / total_rows if total_rows else 0.0

    return {
        "total_rows": total_rows,
        "invalid_rows": invalid_count,
        "valid_rows": total_rows - invalid_count,
        "invalid_ratio": round(invalid_ratio, 4),
        "invalid_row_indexes": sorted(invalid_rows),
        "missing_columns": missing_columns,
        "error_counts": {k: len(v) for k, v in rows_by_category.items()},
        "failed_expectations": failed_expectations,
        "criticality": criticality(invalid_ratio, missing_columns),
    }


def _raised(exception_info) -> bool:
    if isinstance(exception_info, dict):
        if "raised_exception" in exception_info:
            return bool(exception_info["raised_exception"])
        return any(
            isinstance(v, dict) and v.get("raised_exception") for v in exception_info.values()
        )
    return False


def criticality(invalid_ratio: float, missing_columns: list) -> str:
    """HIGH: missing column or >50% invalid | MEDIUM: 10-50% | LOW: >0 and <10% | NONE."""
    if missing_columns or invalid_ratio > 0.5:
        return "HIGH"
    if invalid_ratio >= 0.1:
        return "MEDIUM"
    if invalid_ratio > 0:
        return "LOW"
    return "NONE"
