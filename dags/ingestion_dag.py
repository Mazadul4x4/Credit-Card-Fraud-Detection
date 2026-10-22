"""Data ingestion DAG (every minute).

read_data -> validate_data -> [save_statistics, send_alerts, split_and_save_data]
"""

import os
import random
from datetime import datetime
from pathlib import Path

import pandas as pd
from airflow.exceptions import AirflowSkipException
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.sdk import dag, task

DATA_DIR = Path(os.getenv("DATA_DIR", "/opt/airflow/data"))
RAW_DATA = DATA_DIR / "raw_data"
GOOD_DATA = DATA_DIR / "good_data"
BAD_DATA = DATA_DIR / "bad_data"
POSTGRES_CONN_ID = "dsp_postgres"  # Airflow Connection created by the airflow-init container


def content_to_dataframe(content: dict) -> pd.DataFrame:
    """Rebuild the file from the XCom content. Values stay text; empty cells become null."""
    df = pd.DataFrame(content["rows"], columns=content["columns"], dtype=object)
    return df.replace({"": None})


@dag(
    dag_id="data_ingestion",
    description="Ingest one raw file per minute, validate it with Great Expectations",
    schedule="* * * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,  # one validation at a time (shared GX project folder)
    tags=["dsp", "ingestion"],
)
def data_ingestion():
    @task
    def read_data() -> dict:
        """Pick ONE random file from raw_data, return its content + path, delete it."""
        files = list(RAW_DATA.glob("*.csv"))
        if not files:
            raise AirflowSkipException("No file in raw_data")

        path = random.choice(files)
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        path.unlink()  # avoid re-processing the same file
        print(f"Read {path.name}: {len(df)} rows, {len(df.columns)} columns")
        return {
            "file_name": path.name,
            "file_path": str(path),
            "content": {"columns": list(df.columns), "rows": df.values.tolist()},
        }

    @task
    def validate_data(payload: dict) -> dict:
        """Run the Great Expectations checkpoint and compute the criticality."""
        from fraud_pipeline.validation import run_checkpoint

        df = content_to_dataframe(payload["content"])
        summary = run_checkpoint(df, payload["file_name"])
        summary["file_name"] = payload["file_name"]
        print(
            f"{payload['file_name']}: criticality={summary['criticality']} "
            f"invalid={summary['invalid_rows']}/{summary['total_rows']} "
            f"errors={summary['error_counts']} report={summary['report_path']}"
        )
        return summary

    @task
    def save_statistics(summary: dict) -> None:
        """Save summary statistics (not raw rows) to the database."""
        counts = summary["error_counts"]
        hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
        hook.run(
            """
            INSERT INTO ingestion_stats (
                created_at, file_name, total_rows, valid_rows, invalid_rows, invalid_ratio,
                criticality, missing_columns,
                completeness_errors, validity_errors, consistency_errors, schema_errors,
                type_errors, duplicate_errors, outlier_errors, format_errors, report_path
            ) VALUES (NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            parameters=(
                summary["file_name"],
                summary["total_rows"],
                summary["valid_rows"],
                summary["invalid_rows"],
                summary["invalid_ratio"],
                summary["criticality"],
                ",".join(summary["missing_columns"]) or None,
                counts["completeness"],
                counts["validity"],
                counts["consistency"],
                counts["schema"],
                counts["type"],
                counts["duplicate"],
                counts["outlier"],
                counts["format"],
                summary["report_path"] or None,
            ),
        )
        print(f"Statistics saved for {summary['file_name']}")

    @task
    def send_alerts(summary: dict) -> None:
        """Teams alert to 'Data Quality Alerts' for MEDIUM and HIGH criticality only."""
        from fraud_pipeline.alerts import build_data_quality_card, report_link, send_teams

        criticality = summary["criticality"]
        if criticality not in ("MEDIUM", "HIGH"):
            print(f"No alert (criticality {criticality})")
            return

        report = report_link(summary["report_path"], os.getenv("DATA_DOCS_BASE_URL", ""))
        card = build_data_quality_card(summary["file_name"], summary, report)
        sent = send_teams(os.getenv("TEAMS_WEBHOOK_DATA_QUALITY", ""), card)
        print(f"{criticality} alert {'sent to Teams' if sent else 'NOT sent (no webhook configured)'}")

    @task
    def split_and_save_data(payload: dict, summary: dict) -> None:
        """No issue -> good_data | all rows bad -> bad_data | otherwise split into both."""
        df = pd.DataFrame(payload["content"]["rows"], columns=payload["content"]["columns"])
        name = payload["file_name"]
        bad_index = summary["invalid_row_indexes"]
        bad = df.iloc[bad_index]
        good = df.drop(index=bad_index)

        GOOD_DATA.mkdir(parents=True, exist_ok=True)
        BAD_DATA.mkdir(parents=True, exist_ok=True)
        if len(good):
            good.to_csv(GOOD_DATA / name, index=False)
        if len(bad):
            bad.to_csv(BAD_DATA / name, index=False)
        print(f"{name}: {len(good)} rows -> good_data, {len(bad)} rows -> bad_data")

    payload = read_data()
    summary = validate_data(payload)
    save_statistics(summary)
    send_alerts(summary)
    split_and_save_data(payload, summary)


data_ingestion()
