"""Scheduled prediction DAG (every 2 minutes).

check_for_new_data -> make_predictions

Files are NOT moved or deleted from good_data (the Defense 2 training DAG archives them).
New files are found by remembering the modification time of the newest file already
predicted (Airflow Variable). When nothing is new, check_for_new_data raises
AirflowSkipException, so BOTH tasks (the whole run) show as skipped.
"""

import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from airflow.exceptions import AirflowSkipException
from airflow.sdk import Variable, dag, task

DATA_DIR = Path(os.getenv("DATA_DIR", "/opt/airflow/data"))
GOOD_DATA = DATA_DIR / "good_data"
API_URL = os.getenv("API_URL", "http://api:8000")
LAST_PROCESSED_VARIABLE = "prediction_last_processed_mtime_ns"

FEATURES = ["Time"] + [f"V{i}" for i in range(1, 29)] + ["Amount", "time_period"]


@dag(
    dag_id="scheduled_prediction",
    description="Batch predictions on newly ingested good data",
    schedule="*/2 * * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["dsp", "prediction"],
)
def scheduled_prediction():
    @task
    def check_for_new_data() -> dict:
        last_processed = int(Variable.get(LAST_PROCESSED_VARIABLE, default="0"))
        new_files = []
        for path in GOOD_DATA.glob("*.csv"):
            mtime = path.stat().st_mtime_ns
            if mtime > last_processed:
                new_files.append((str(path), mtime))

        if not new_files:
            raise AirflowSkipException("No new file in good_data")

        print(f"{len(new_files)} new file(s): {[Path(p).name for p, _ in new_files]}")
        return {
            "files": [p for p, _ in new_files],
            "max_mtime_ns": max(m for _, m in new_files),
        }

    @task
    def make_predictions(batch: dict) -> None:
        frames = [pd.read_csv(path) for path in batch["files"] if Path(path).exists()]
        if not frames:
            raise AirflowSkipException("Files disappeared before prediction")
        data = pd.concat(frames, ignore_index=True)

        columns = (["transaction_id"] if "transaction_id" in data.columns else []) + FEATURES
        transactions = data[columns].to_dict(orient="records")

        # ONE API call for all the new files (batch prediction)
        response = requests.post(
            f"{API_URL}/predict",
            json={"transactions": transactions, "source": "scheduled"},
            timeout=120,
        )
        if response.status_code != 200:
            raise RuntimeError(f"API error {response.status_code}: {response.text[:500]}")
        result = response.json()
        frauds = sum(p["prediction"] for p in result["predictions"])
        print(f"{result['count']} predictions (model {result['model_version']}), {frauds} fraud")

        # only mark files as processed after a successful prediction
        Variable.set(LAST_PROCESSED_VARIABLE, str(batch["max_mtime_ns"]))

    make_predictions(check_for_new_data())


scheduled_prediction()
