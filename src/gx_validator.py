"""Great Expectations validation module for credit card fraud pipeline.

Handles GX context initialization, expectation suites covering 8 error types,
checkpoint execution on ingested files, error statistics, criticality, Data Docs,
and good/bad data splitting.
"""

from __future__ import annotations

import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import great_expectations as gx
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = ["Time"] + [f"V{i}" for i in range(1, 29)] + ["Amount", "Class"]
SUITE_NAME = "creditcard_suite"
CHECKPOINT_NAME = "creditcard_checkpoint"


def resolve_gx_root(custom_path: str | Path | None = None) -> Path:
    """Resolve the GX project root directory across Docker and local environments."""
    if custom_path:
        p = Path(custom_path)
        if p.exists():
            return p

    env_root = os.getenv("GX_PROJECT_ROOT")
    if env_root and Path(env_root).exists():
        return Path(env_root)

    candidates = [
        Path("/opt/airflow/src/gx"),
        Path(__file__).resolve().parent / "gx",
        Path("src/gx"),
    ]
    for c in candidates:
        if c.exists() and (c / "gx" / "great_expectations.yml").exists():
            return c
        if c.exists() and (c / "great_expectations.yml").exists():
            return c.parent

    # Fallback to local src/gx
    local_gx = Path("src/gx")
    local_gx.mkdir(parents=True, exist_ok=True)
    return local_gx


def get_gx_context(project_root: str | Path | None = None) -> gx.DataContext:
    """Get or initialize Great Expectations context."""
    root = resolve_gx_root(project_root)
    try:
        context = gx.get_context(mode="file", project_root_dir=str(root))
        logger.info(f"Loaded GX file context from {root}")
    except Exception as e:
        logger.warning(f"Could not load GX file context from {root} ({e}). Falling back to ephemeral.")
        context = gx.get_context(mode="ephemeral")
    return context


def configure_suite(context: gx.DataContext) -> Any:
    """Create or update the creditcard expectation suite covering the 8 error types."""
    try:
        suite = context.suites.get(SUITE_NAME)
        suite.expectations = []
    except Exception:
        suite = gx.ExpectationSuite(name=SUITE_NAME)
        context.suites.add(suite)

    # 1 & 2. Amount: not null, non-negative, and within realistic limits (< 50,000)
    suite.add_expectation(gx.expectations.ExpectColumnToExist(column="Amount"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="Amount"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeBetween(column="Amount", min_value=0.0, max_value=50000.0))

    # 3 & 4. Time: not null and non-negative
    suite.add_expectation(gx.expectations.ExpectColumnToExist(column="Time"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="Time"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeBetween(column="Time", min_value=0.0))

    # 5. Class: in set [0, 1]
    suite.add_expectation(gx.expectations.ExpectColumnToExist(column="Class"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeInSet(column="Class", value_set=[0, 1]))

    # 6. Duplicate detection (compound unique columns)
    suite.add_expectation(gx.expectations.ExpectCompoundColumnsToBeUnique(column_list=["Time", "Amount", "V1", "V2"]))

    # 7. Check critical feature columns exist
    for col in ["V1", "V2", "V3", "V4"]:
        suite.add_expectation(gx.expectations.ExpectColumnToExist(column=col))

    context.suites.add_or_update(suite)
    logger.info(f"Configured expectation suite '{SUITE_NAME}' with {len(suite.expectations)} expectations.")
    return suite


def setup_checkpoint_for_dataframe(context: gx.DataContext, suite: Any) -> Any:
    """Set up a dynamic pandas dataframe asset and checkpoint."""
    try:
        ds = context.data_sources.get("pandas_datasource")
    except KeyError:
        ds = context.data_sources.add_pandas("pandas_datasource")

    try:
        asset = ds.get_asset("transaction_dataframe")
    except (LookupError, KeyError):
        asset = ds.add_dataframe_asset("transaction_dataframe")

    try:
        batch_def = asset.get_batch_definition("default_batch")
    except (LookupError, KeyError):
        batch_def = asset.add_batch_definition_whole_dataframe("default_batch")

    try:
        val_def = context.validation_definitions.get("transaction_validation")
        val_def.data = batch_def
        val_def.suite = suite
        context.validation_definitions.add_or_update(val_def)
    except Exception:
        val_def = context.validation_definitions.add(
            gx.ValidationDefinition(name="transaction_validation", data=batch_def, suite=suite)
        )

    try:
        checkpoint = context.checkpoints.get(CHECKPOINT_NAME)
        checkpoint.validation_definitions = [val_def]
        context.checkpoints.add_or_update(checkpoint)
    except Exception:
        checkpoint = context.checkpoints.add(
            gx.Checkpoint(name=CHECKPOINT_NAME, validation_definitions=[val_def])
        )

    return checkpoint


def evaluate_error_categories(df: pd.DataFrame) -> dict[str, Any]:
    """Inspect dataframe rows and compute exact counts and boolean masks for 8 error categories."""
    total_rows = len(df)
    missing_cols = sorted(set(REQUIRED_COLUMNS) - set(df.columns))

    if missing_cols:
        # If critical columns missing, all rows considered invalid for missing_columns
        invalid_mask = np.ones(total_rows, dtype=bool)
        stats = {
            "missing_amount": 0,
            "negative_amount": 0,
            "missing_time": 0,
            "negative_time": 0,
            "invalid_class": 0,
            "extreme_amount": 0,
            "missing_columns": total_rows,
            "duplicate_rows": 0,
        }
        return {
            "stats": stats,
            "missing_columns_list": missing_cols,
            "invalid_mask": invalid_mask,
            "invalid_rows": total_rows,
            "valid_rows": 0,
        }

    # 1. Missing amount
    missing_amount_mask = df["Amount"].isna()

    # 2. Negative amount
    negative_amount_mask = (~missing_amount_mask) & (df["Amount"] < 0)

    # 3. Missing time
    missing_time_mask = df["Time"].isna()

    # 4. Negative time
    negative_time_mask = (~missing_time_mask) & (df["Time"] < 0)

    # 5. Invalid class
    invalid_class_mask = df["Class"].isna() | (~df["Class"].isin([0, 1]))

    # 6. Extreme amount (> 50000.0)
    extreme_amount_mask = (~missing_amount_mask) & (df["Amount"] > 50000.0)

    # 7. Missing columns
    np.zeros(total_rows, dtype=bool)

    # 8. Duplicate rows
    duplicate_rows_mask = df.duplicated(keep="first")

    # Combine into overall invalid mask
    invalid_mask = (
        missing_amount_mask
        | negative_amount_mask
        | missing_time_mask
        | negative_time_mask
        | invalid_class_mask
        | extreme_amount_mask
        | duplicate_rows_mask
    )

    stats = {
        "missing_amount": int(missing_amount_mask.sum()),
        "negative_amount": int(negative_amount_mask.sum()),
        "missing_time": int(missing_time_mask.sum()),
        "negative_time": int(negative_time_mask.sum()),
        "invalid_class": int(invalid_class_mask.sum()),
        "extreme_amount": int(extreme_amount_mask.sum()),
        "missing_columns": 0,
        "duplicate_rows": int(duplicate_rows_mask.sum()),
    }

    invalid_rows = int(invalid_mask.sum())
    valid_rows = total_rows - invalid_rows

    return {
        "stats": stats,
        "missing_columns_list": [],
        "invalid_mask": invalid_mask,
        "invalid_rows": invalid_rows,
        "valid_rows": valid_rows,
    }


def determine_criticality(
    invalid_rows: int,
    total_rows: int,
    missing_columns: list[str],
    stats: dict[str, int],
) -> str:
    """Calculate error criticality: CRITICAL, HIGH, MEDIUM, LOW, or NONE."""
    if total_rows == 0:
        return "NONE"

    if missing_columns:
        return "CRITICAL"

    invalid_pct = (invalid_rows / total_rows) * 100

    if invalid_pct >= 50 or stats.get("invalid_class", 0) > 0:
        return "CRITICAL"
    elif invalid_pct >= 20:
        return "HIGH"
    elif invalid_pct >= 5 or stats.get("negative_amount", 0) > 0 or stats.get("missing_amount", 0) > 0:
        return "MEDIUM"
    elif invalid_rows > 0:
        return "LOW"
    return "NONE"


def validate_file(
    file_path: str | Path,
    project_root: str | Path | None = None,
) -> dict[str, Any]:
    """Validate an ingested file with Great Expectations checkpoint and compute comprehensive stats."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File to validate does not exist: {path}")

    df = pd.read_csv(path)
    total_rows = len(df)

    # 1. GX context & suite
    context = get_gx_context(project_root)
    suite = configure_suite(context)
    checkpoint = setup_checkpoint_for_dataframe(context, suite)

    # 2. Run GX checkpoint on the ingested file dataframe
    try:
        gx_res = checkpoint.run(batch_parameters={"dataframe": df})
        gx_success = bool(gx_res.success)
    except Exception as e:
        logger.warning(f"GX checkpoint run raised error: {e}")
        gx_success = False

    # 3. Build Data Docs
    try:
        docs = context.build_data_docs()
        report_url = docs.get("local_site", "pandas-creditcard_csv.html")
    except Exception as e:
        logger.warning(f"Failed to build Data Docs: {e}")
        report_url = "pandas-creditcard_csv.html"

    # 4. Error category statistics & masks
    eval_res = evaluate_error_categories(df)
    stats = eval_res["stats"]
    missing_cols = eval_res["missing_columns_list"]
    invalid_mask = eval_res["invalid_mask"]
    invalid_rows = eval_res["invalid_rows"]
    valid_rows = eval_res["valid_rows"]

    # 5. Criticality
    criticality = determine_criticality(invalid_rows, total_rows, missing_cols, stats)
    validation_success = gx_success and (invalid_rows == 0)

    return {
        "file_path": str(path),
        "filename": path.name,
        "validation_success": validation_success,
        "total_rows": total_rows,
        "valid_rows": valid_rows,
        "invalid_rows": invalid_rows,
        "invalid_pct": round((invalid_rows / total_rows * 100) if total_rows > 0 else 0.0, 2),
        "criticality": criticality,
        "missing_columns": missing_cols,
        "stats_per_category": stats,
        "report_file": str(report_url),
        "invalid_mask": invalid_mask,
    }


def split_good_bad(
    file_path: str | Path,
    validation_result: dict[str, Any],
    good_dir: str | Path = "data/good_data",
    bad_dir: str | Path = "data/bad_data",
    archive_dir: str | Path = "data/archived_data",
) -> dict[str, Any]:
    """Split ingested file into good_data and bad_data, and archive original raw file."""
    src = Path(file_path)
    if not src.exists():
        logger.warning(f"Source file {src} does not exist.")
        return {"good_path": None, "bad_path": None, "archived_path": None}

    good_d = Path(good_dir)
    bad_d = Path(bad_dir)
    arch_d = Path(archive_dir)

    for d in [good_d, bad_d, arch_d]:
        d.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(src)
    invalid_mask = validation_result.get("invalid_mask")
    if invalid_mask is None or len(invalid_mask) != len(df):
        eval_res = evaluate_error_categories(df)
        invalid_mask = eval_res["invalid_mask"]

    good_df = df[~invalid_mask]
    bad_df = df[invalid_mask]

    stem = src.stem
    good_path = None
    bad_path = None

    if len(good_df) > 0:
        good_path = good_d / f"{stem}_good.csv"
        good_df.to_csv(good_path, index=False)
        logger.info(f"Saved {len(good_df)} valid rows to {good_path}")

    if len(bad_df) > 0:
        bad_path = bad_d / f"{stem}_bad.csv"
        bad_df.to_csv(bad_path, index=False)
        logger.info(f"Saved {len(bad_df)} invalid rows to {bad_path}")

    # Move raw source file to archive
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archived_path = arch_d / f"{stem}_{timestamp}.csv"
    shutil.move(src, archived_path)
    logger.info(f"Archived {src} to {archived_path}")

    return {
        "good_path": str(good_path) if good_path else None,
        "bad_path": str(bad_path) if bad_path else None,
        "archived_path": str(archived_path),
        "good_count": len(good_df),
        "bad_count": len(bad_df),
    }
