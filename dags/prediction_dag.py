from __future__ import annotations

import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from airflow.decorators import dag, task
from airflow.exceptions import AirflowSkipException

logger = logging.getLogger(__name__)

GOOD_DATA_DIR = Path(os.getenv("GOOD_DATA_DIR", "/opt/airflow/data/good_data"))
ARCHIVE_DATA_DIR = Path(os.getenv("ARCHIVE_DATA_DIR", "/opt/airflow/data/archived_data"))
API_URL = os.getenv("API_URL", "http://api:8000")


@dag(
    dag_id="credit_card_prediction",
    start_date=datetime(2026, 1, 1),
    schedule="*/2 * * * *",  # Runs every 2 minutes
    catchup=False,
    tags=["credit-card", "prediction", "batch-inference"],
)
def credit_card_prediction():

    @task
    def detect_new_data() -> list[str]:
        """Detect unpredicted CSV files in good_data directory.

        Skips downstream tasks and the entire run if no files are found.
        """
        data_dir = GOOD_DATA_DIR
        if not data_dir.exists():
            data_dir = Path("data/good_data")

        files = sorted(
            str(f)
            for f in data_dir.glob("*.csv")
            if not f.name.startswith(".") and f.stat().st_size > 0
        )

        if not files:
            logger.info("No new files detected in good_data directory. Skipping run.")
            raise AirflowSkipException("No new data found. Whole prediction run skipped.")

        logger.info(f"Detected {len(files)} new file(s) for prediction: {files}")
        return files

    @task
    def batch_predict_and_archive(file_paths: list[str]) -> dict:
        """Score all transactions across detected files in ONE batch API call, then archive files."""
        if not file_paths:
            raise AirflowSkipException("No files passed to batch prediction.")

        dfs = []
        for fp in file_paths:
            df = pd.read_csv(fp)
            # Remove Class if present in ingested demo files
            if "Class" in df.columns:
                df = df.drop(columns=["Class"])
            dfs.append(df)

        combined_df = pd.concat(dfs, ignore_index=True)
        total_rows = len(combined_df)
        logger.info(f"Total transactions to predict across {len(file_paths)} files: {total_rows}")

        # Construct single batch payload
        records = combined_df.to_dict(orient="records")
        payload = {
            "transactions": records,
            "source": "Prediction DAG",
        }

        # Make ONE batch API call
        predict_endpoint = f"{API_URL}/predict"
        logger.info(f"Dispatching single batch API call to {predict_endpoint} for {total_rows} items...")
        response = requests.post(predict_endpoint, json=payload, timeout=90)

        if response.status_code != 200:
            logger.error(f"Prediction API error ({response.status_code}): {response.text}")
            response.raise_for_status()

        result_data = response.json()
        predictions = result_data.get("predictions", [])
        fraud_count = sum(1 for p in predictions if p.get("predicted_class") == 1)
        model_version = result_data.get("model_version", "1.0.0")

        logger.info(
            f"Batch prediction completed: {len(predictions)} scored, "
            f"{fraud_count} flagged as fraud, model_version={model_version}"
        )

        # Archive processed files so they are not scored again
        archive_dir = ARCHIVE_DATA_DIR
        if not archive_dir.exists():
            archive_dir = Path("data/archived_data")
        archive_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        for fp in file_paths:
            src = Path(fp)
            if src.exists():
                dst = archive_dir / f"scored_{src.stem}_{timestamp}.csv"
                shutil.move(src, dst)
                logger.info(f"Archived {src} -> {dst}")

        return {
            "total_scored": total_rows,
            "fraud_flagged": fraud_count,
            "model_version": model_version,
            "files_processed": len(file_paths),
        }

    detected_files = detect_new_data()
    batch_predict_and_archive(detected_files)


credit_card_prediction()
