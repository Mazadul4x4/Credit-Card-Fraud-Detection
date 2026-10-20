FROM apache/airflow:3.0.2-python3.12

ARG AIRFLOW_VERSION=3.0.2
ARG PYTHON_VERSION=3.12

COPY airflow/requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"
