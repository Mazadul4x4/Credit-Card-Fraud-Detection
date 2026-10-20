"""Create the Airflow metadata database inside the project's Postgres if it does not exist.
Run by the airflow-init container before `airflow db migrate`."""

import os
import time

import psycopg2

user = os.environ["POSTGRES_USER"]
password = os.environ["POSTGRES_PASSWORD"]
app_db = os.environ["POSTGRES_DB"]
airflow_db = os.environ.get("AIRFLOW_DB", "airflow")

for _attempt in range(30):
    try:
        conn = psycopg2.connect(host="db", port=5432, user=user, password=password, dbname=app_db)
        break
    except psycopg2.OperationalError:
        print("Waiting for Postgres...")
        time.sleep(2)
else:
    raise SystemExit("Postgres not reachable")

conn.autocommit = True
with conn.cursor() as cur:
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (airflow_db,))
    if cur.fetchone():
        print(f"Database '{airflow_db}' already exists")
    else:
        cur.execute(f'CREATE DATABASE "{airflow_db}"')
        print(f"Database '{airflow_db}' created")
conn.close()
