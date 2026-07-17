from datetime import datetime

from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator

with DAG(
    dag_id="credit_card_ingestion",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["credit-card", "ingestion"],
) as dag:

   split_data = BashOperator(
    task_id="split_data",
    cwd="/opt/airflow",
    bash_command="/home/airflow/.local/bin/python /opt/airflow/src/split_data.py",
)

generate_bad_data = BashOperator(
    task_id="generate_bad_data",
    cwd="/opt/airflow",
    bash_command="/home/airflow/.local/bin/python /opt/airflow/src/generate_errors.py",
)

split_data >> generate_bad_data