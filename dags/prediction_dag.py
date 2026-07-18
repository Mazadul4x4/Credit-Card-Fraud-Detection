from datetime import datetime
import os
import pandas as pd
import requests

from airflow import DAG
from airflow.decorators import task
from airflow.exceptions import AirflowSkipException

default_args = {
    "owner": "airflow",
}

with DAG(
    dag_id="credit_card_prediction",
    default_args=default_args,
    start_date=datetime(2026, 7, 1),
    schedule="*/2 * * * *",      # every 2 minutes
    catchup=False,
    tags=["prediction"],
) as dag:

    @task
    def check_for_new_data():
      good_data_dir = "/opt/airflow/data/good_data"

      files = [
        os.path.join(good_data_dir, f)
        for f in os.listdir(good_data_dir)
        if f.endswith(".csv")
      ]

      if not files:
        raise AirflowSkipException("No new data found.")

      print(f"Found {len(files)} file(s).")
      return files
   

    @task
    def make_predictions(files):

      dfs = [pd.read_csv(file) for file in files]

      data = pd.concat(dfs, ignore_index=True)

      print(f"Total rows to predict: {len(data)}")

      payload = {
        "transactions": data.to_dict(orient="records")
      }

      response = requests.post(
        "http://api:8000/predict",
        json=payload,
        timeout=60,
      )

      response.raise_for_status()

      print(response.json())