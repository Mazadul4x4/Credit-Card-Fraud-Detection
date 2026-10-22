from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import requests
from airflow.decorators import dag, task
from airflow.exceptions import AirflowSkipException
from airflow.providers.postgres.hooks.postgres import PostgresHook

# Ensure airflow root and src are on sys.path
for p in ["/opt/airflow", "/opt/airflow/src", str(Path(__file__).resolve().parent.parent), str(Path(__file__).resolve().parent.parent / "src")]:
    if Path(p).exists() and p not in sys.path:
        sys.path.insert(0, p)

from src.gx_validator import split_good_bad, validate_file

logger = logging.getLogger(__name__)

RAW_DATA_DIR = Path(os.getenv("RAW_DATA_DIR", "/opt/airflow/data/raw_data"))
GX_PROJECT_ROOT = os.getenv("GX_PROJECT_ROOT", "/opt/airflow/src/gx")


@dag(
    dag_id="credit_card_ingestion",
    start_date=datetime(2026, 1, 1),
    schedule="* * * * *",  # Runs every minute
    catchup=False,
    tags=["credit-card", "ingestion", "great-expectations"],
)
def credit_card_ingestion():

    @task
    def read_data() -> dict:
        """Scan raw_data directory for un-ingested CSV files."""
        raw_dir = RAW_DATA_DIR
        if not raw_dir.exists():
            raw_dir = Path("data/raw_data")

        files = sorted(f for f in raw_dir.glob("*.csv") if not f.name.startswith("."))

        if not files:
            raise AirflowSkipException("No new raw_data files found to ingest.")

        # Process the first available file deterministically
        file_path = files[0]
        logger.info(f"Ingesting file: {file_path}")

        return {
            "file_path": str(file_path),
            "filename": file_path.name,
        }

    @task
    def validate_data(payload: dict) -> dict:
        """Run Great Expectations checkpoint on the ingested file and compute error stats."""
        file_path = payload["file_path"]
        logger.info(f"Validating {file_path} with Great Expectations...")

        results = validate_file(file_path=file_path, project_root=GX_PROJECT_ROOT)

        # Remove numpy arrays before XCom serialization
        invalid_mask = results.pop("invalid_mask", None)
        invalid_indices = [int(i) for i, bad in enumerate(invalid_mask) if bad] if invalid_mask is not None else []
        results["invalid_indices"] = invalid_indices

        logger.info(
            f"Validation complete for {results['filename']}: "
            f"Success={results['validation_success']}, Criticality={results['criticality']}, "
            f"Valid={results['valid_rows']}, Invalid={results['invalid_rows']}"
        )
        return results

    @task
    def save_statistics(validation_result: dict) -> dict:
        """Save ingestion and error category statistics into PostgreSQL."""
        filename = validation_result["filename"]
        records_processed = int(validation_result["total_rows"])
        records_loaded = int(validation_result["valid_rows"])
        records_failed = int(validation_result["invalid_rows"])
        criticality = str(validation_result["criticality"])
        status = "SUCCESS" if validation_result["validation_success"] else "FAILED"
        error_summary_json = json.dumps(validation_result.get("stats_per_category", {}))

        try:
            hook = PostgresHook(postgres_conn_id="postgres_default")
            hook.run(
                """
                INSERT INTO ingestion_stats
                (filename, records_processed, records_loaded, records_failed, criticality, error_summary, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                """,
                parameters=(
                    filename,
                    records_processed,
                    records_loaded,
                    records_failed,
                    criticality,
                    error_summary_json,
                    status,
                ),
            )
            logger.info(f"Recorded ingestion stats for {filename} into database.")
        except Exception as e:
            logger.error(f"Failed to write stats to Postgres: {e}")

        return {
            "filename": filename,
            "records_processed": records_processed,
            "records_loaded": records_loaded,
            "records_failed": records_failed,
            "criticality": criticality,
            "status": status,
        }

    @task
    def send_alerts(validation_result: dict) -> dict:
        """Send Microsoft Teams data quality alert if configured, or log alert details."""
        filename = validation_result["filename"]
        criticality = validation_result["criticality"]
        total_rows = validation_result["total_rows"]
        valid_rows = validation_result["valid_rows"]
        invalid_rows = validation_result["invalid_rows"]
        invalid_pct = validation_result["invalid_pct"]
        stats = validation_result.get("stats_per_category", {})
        report_file = validation_result.get("report_file", "")

        status_emoji = "✅" if validation_result["validation_success"] else "⚠️"
        crit_color = {
            "CRITICAL": "FF0000",
            "HIGH": "FF6600",
            "MEDIUM": "FFCC00",
            "LOW": "3399FF",
            "NONE": "00CC66",
        }.get(criticality, "CCCCCC")

        alert_title = f"{status_emoji} Data Quality Alert: {filename}"
        alert_body = (
            f"**File:** {filename}\n\n"
            f"**Criticality:** {criticality}\n\n"
            f"**Total Records:** {total_rows} | **Valid:** {valid_rows} | **Invalid:** {invalid_rows} ({invalid_pct}%)\n\n"
            f"**Error Breakdown:**\n"
            f"- Missing Amount: {stats.get('missing_amount', 0)}\n"
            f"- Negative Amount: {stats.get('negative_amount', 0)}\n"
            f"- Missing Time: {stats.get('missing_time', 0)}\n"
            f"- Negative Time: {stats.get('negative_time', 0)}\n"
            f"- Invalid Class: {stats.get('invalid_class', 0)}\n"
            f"- Extreme Amount: {stats.get('extreme_amount', 0)}\n"
            f"- Missing Columns: {stats.get('missing_columns', 0)}\n"
            f"- Duplicate Rows: {stats.get('duplicate_rows', 0)}\n\n"
            f"**Data Docs Report:** {report_file}"
        )

        webhook_url = os.getenv("TEAMS_WEBHOOK_URL")
        alert_sent = False

        if webhook_url and criticality in ["MEDIUM", "HIGH", "CRITICAL"]:
            teams_payload = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": crit_color,
                "summary": alert_title,
                "sections": [
                    {
                        "activityTitle": alert_title,
                        "text": alert_body,
                    }
                ],
            }
            try:
                resp = requests.post(webhook_url, json=teams_payload, timeout=10)
                resp.raise_for_status()
                alert_sent = True
                logger.info(f"Teams alert sent successfully for {filename}")
            except Exception as e:
                logger.warning(f"Failed to dispatch Teams alert: {e}")
        else:
            logger.info("Teams webhook not triggered (either unconfigured or low criticality). Alert preview:")
            logger.info("\n" + alert_body)

        return {
            "alert_sent": alert_sent,
            "criticality": criticality,
            "filename": filename,
        }

    @task
    def split_and_save_data(validation_result: dict) -> dict:
        """Split clean rows to good_data, bad rows to bad_data, and archive original raw file."""
        file_path = validation_result["file_path"]
        good_dir = Path(os.getenv("GOOD_DATA_DIR", "/opt/airflow/data/good_data"))
        bad_dir = Path(os.getenv("BAD_DATA_DIR", "/opt/airflow/data/bad_data"))
        archive_dir = Path(os.getenv("ARCHIVE_DATA_DIR", "/opt/airflow/data/archived_data"))

        split_info = split_good_bad(
            file_path=file_path,
            validation_result=validation_result,
            good_dir=good_dir,
            bad_dir=bad_dir,
            archive_dir=archive_dir,
        )
        logger.info(
            f"Split completed for {validation_result['filename']}: "
            f"{split_info['good_count']} good rows, {split_info['bad_count']} bad rows. "
            f"Archived to {split_info['archived_path']}"
        )
        return split_info

    # DAG Dependency Pipeline
    raw_payload = read_data()
    validated = validate_data(raw_payload)

    stats = save_statistics(validated)
    alerts = send_alerts(validated)
    split_res = split_and_save_data(validated)

    # Order constraints
    validated >> [stats, alerts, split_res]


credit_card_ingestion()
