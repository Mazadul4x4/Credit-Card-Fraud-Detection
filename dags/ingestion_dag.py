from __future__ import annotations
import os
import requests
import random
import shutil
from datetime import datetime
from pathlib import Path
from airflow.providers.postgres.hooks.postgres import PostgresHook

import pandas as pd
import great_expectations as gx
from airflow.decorators import dag, task
from airflow.exceptions import AirflowSkipException

RAW_DATA_DIR = Path("/opt/airflow/data/raw_data")
GX_PROJECT_ROOT = "/opt/airflow/src/gx"


@dag(
    dag_id="credit_card_ingestion",
    start_date=datetime(2026, 1, 1),
    schedule="* * * * *",  # every minute
    catchup=False,
    tags=["credit-card", "ingestion"],
)
def credit_card_ingestion():

    @task
    def read_data() -> dict:
        files = sorted(RAW_DATA_DIR.glob("*.csv"))

        if not files:
            raise AirflowSkipException("No raw_data files found.")

        file_path = random.choice(files)

        return {
            "file_path": str(file_path)
        }

    @task
    def validate_data(payload: dict) -> dict:
        file_path = payload["file_path"]

        # Load GX context
        context = gx.get_context(
            mode="file",
            project_root_dir=GX_PROJECT_ROOT,
        )

        # Load checkpoint
        checkpoint = context.checkpoints.get("creditcard_checkpoint")

        # Run validation
        result = checkpoint.run()

        # Build Data Docs
        context.build_data_docs()

        # Read the file again to compute summary counts for the alert
        df = pd.read_csv(file_path)
        total_rows = int(len(df))

        required_columns = {"Time", "Amount", "Class"}
        missing_columns = sorted(required_columns - set(df.columns))

        if missing_columns:
            invalid_rows = total_rows
        else:
            invalid_mask = (
                df["Class"].isna()
                | ~df["Class"].isin([0, 1])
                | df["Amount"].isna()
                | (df["Amount"] < 0)
                | df["Time"].isna()
                | (df["Time"] < 0)
            )
            invalid_rows = int(invalid_mask.sum())

        return {
            "file_path": file_path,
            "validation_success": bool(result.success),
            "total_rows": total_rows,
            "invalid_rows": invalid_rows,
            "missing_columns": missing_columns,
            "report_file": "pandas-creditcard_csv.html",
        }

    @task
    def save_statistics(validation_result: dict) -> dict: 
        file_path = validation_result["file_path"]
        df = pd.read_csv(file_path)

        hook = PostgresHook(postgres_conn_id="postgres_default")

        filename = Path(file_path).name
        records_processed = len(df)
        records_loaded = len(df) if validation_result["validation_success"] else 0
        status = "SUCCESS" if validation_result["validation_success"] else "FAILED"

        hook.run(
          """
          INSERT INTO ingestion_stats
          (filename, records_processed, records_loaded, status, created_at)
          VALUES (%s, %s, %s, %s, NOW())
          """,
          parameters=(
            filename,
            records_processed,
            records_loaded,
           status,
          ),
        )

        print(f"Saved statistics for {filename}")

        return {
          "filename": filename,
          "records_processed": records_processed,
          "records_loaded": records_loaded,
          "status": status,
        }
    
    @task
    def send_alerts(validation_result: dict):
        total_rows = validation_result["total_rows"]
        invalid_rows = validation_result["invalid_rows"]
        missing_columns = validation_result["missing_columns"]
        report_file = validation_result["report_file"]
        file_name = Path(validation_result["file_path"]).name

        if total_rows == 0:
            print("No alert: empty file.")
            return {"alert_sent": False, "criticality": "NONE"}

        invalid_pct = (invalid_rows / total_rows) * 100

        if missing_columns or invalid_pct > 50:
            criticality = "HIGH"
        elif invalid_pct >= 10:
            criticality = "MEDIUM"
        elif invalid_pct > 0:
            criticality = "LOW"
        else:
            print("No alert: no data quality issues detected.")
            return {
                "alert_sent": False,
                "criticality": "NONE",
                "report_file": report_file,
            }

        alert_text = (
            f"Data Quality Alert\n"
            f"File: {file_name}\n"
            f"Criticality: {criticality}\n"
            f"Total rows: {total_rows}\n"
            f"Invalid rows: {invalid_rows}\n"
            f"Invalid %: {invalid_pct:.2f}\n"
            f"Missing columns: {', '.join(missing_columns) if missing_columns else 'None'}\n"
            f"Report file: {report_file}"
        )

        # Only notify for medium/high
        if criticality in {"MEDIUM", "HIGH"}:
            webhook_url = os.getenv("TEAMS_WEBHOOK_URL")
            if webhook_url:
                response = requests.post(webhook_url, json={"text": alert_text}, timeout=15)
                response.raise_for_status()
                print("Teams alert sent.")
            else:
                print("TEAMS_WEBHOOK_URL not set. Alert preview:")
                print(alert_text)

        return {
            "alert_sent": criticality in {"MEDIUM", "HIGH"},
            "criticality": criticality,
            "invalid_rows": invalid_rows,
            "total_rows": total_rows,
            "invalid_pct": round(invalid_pct, 2),
            "report_file": report_file,
        }
    @task
    def split_and_save_data(validation_result: dict):

      file_path = Path(validation_result["file_path"])

      if not file_path.exists():
        print(f"{file_path} does not exist.")
        return validation_result

      if validation_result["validation_success"]:
        destination = Path("/opt/airflow/data/archived_data") / file_path.name
      else:
        destination = Path("/opt/airflow/data/bad_data") / file_path.name

      shutil.copy2(file_path, destination)

      print(f"Moved {file_path.name} to {destination}")

      return {
        **validation_result,
        "destination": str(destination),
    }

    raw_data = read_data()
    validated = validate_data(raw_data)

    save_statistics(validated)
    send_alerts(validated)
    split_and_save_data(validated)
    
credit_card_ingestion()