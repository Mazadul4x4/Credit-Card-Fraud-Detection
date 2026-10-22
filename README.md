# DSP | Credit Card Fraud Detection

End-to-end ML pipeline on the Kaggle [Credit Card Fraud](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud)
dataset: continuous data ingestion with Great Expectations validation, Teams alerts, scheduled
predictions with Airflow 3, a FastAPI model service and a Streamlit web app.

| Service | URL | Notes |
|---|---|---|
| Streamlit web app | http://localhost:8501 | Prediction + Past predictions pages |
| FastAPI model service | http://localhost:8000/docs | Swagger UI |
| Airflow 3 | http://localhost:8080 | login `admin` / `admin@123` |
| PostgreSQL | localhost:5432 | app DB `dsp_app` + Airflow DB `airflow` |

## Prerequisites

- Docker Desktop (or Docker Engine + Compose v2), ~6 GB free RAM for Docker
- The dataset: download `creditcard.csv` from Kaggle and put it at `data/creditcard.csv`
- Optional: a Teams webhook URL for the **Data Quality Alerts** channel

## Setup (first time)

```bash
# 1. configuration
cp .env.example .env          # then edit it (Linux: set AIRFLOW_UID to the output of `id -u`)

# 2. build the images
docker compose build

# 3. prepare the dataset: adds transaction_id + time_period, splits train/test/production
docker compose run --rm tools python src/prepare_dataset.py data/creditcard.csv

# 4. train the model (writes models/fraud_model.joblib + models/model_metadata.json)
docker compose run --rm tools python src/train.py

# 5. start everything
docker compose up -d

# 6. create files for the ingestion job: N files of exactly 10 rows, then inject errors
docker compose run --rm tools python src/split_data.py data/production.csv data/raw_data 100
docker compose run --rm tools python src/generate_errors.py data/raw_data data/raw_data --clean-file-ratio 0.3

# 7. the 5 demo files for the defense (kept OUTSIDE raw_data)
docker compose run --rm tools python src/make_demo_files.py data/production.csv data/demo_files
```

Both DAGs are active as soon as Airflow starts: `data_ingestion` (every minute) and
`scheduled_prediction` (every 2 minutes).

> **Upgrading from the old version of this repo?** The database tables changed. Run
> `docker compose down -v` once (this deletes the old Postgres volume) before `docker compose up`.

Why the scripts run inside Docker (`tools` service): the model must be trained with the same
scikit-learn version as the API that loads it. Running them on your machine also works
(`pip install -r requirements-dev.txt`, then `python src/<script>.py ...`) but train the model in Docker.

## How it works

```
data/raw_data ──► data_ingestion DAG (every minute)
                   read_data ─► validate_data ─┬─► save_statistics ─► ingestion_stats table
                                               ├─► send_alerts ─────► Teams (MEDIUM / HIGH only)
                                               └─► split_and_save_data ─► good_data / bad_data

data/good_data ──► scheduled_prediction DAG (every 2 minutes)
                   check_for_new_data ─► make_predictions ─► POST /predict (1 call) ─► predictions table
```

### Ingestion DAG
- **read_data**: picks one random file in `raw_data`, returns its content + path through XCom and deletes the file.
- **validate_data**: runs the Great Expectations **checkpoint** (`creditcard_checkpoint`) on the file.
  The checkpoint pairs the **validation definition** (dataframe batch) with the **expectation suite**
  (`creditcard_suite`, 71 expectations) and its `UpdateDataDocsAction` builds the **Data Docs** report.
  The results are parsed into the bad rows per error category and the criticality.
- **save_statistics**: one row per file in `ingestion_stats` with `PostgresHook` and the Airflow
  connection `dsp_postgres` (created by `airflow-init`).
- **send_alerts**: Teams Adaptive Card with criticality, error summary and report path.
- **split_and_save_data**: clean file → `good_data`, all rows bad → `bad_data`, otherwise split into both.

### Validation rules (8 error types)

| Category | Level | Rule | Example injected error |
|---|---|---|---|
| completeness | row | required column not null | empty `Amount` |
| validity | row | `Time` in [0, 172800], `Amount` ≥ 0 | `Amount = -42.10` |
| consistency | row | `time_period` in {night, morning, afternoon, evening}, `Class` in {0, 1} | `time_period = "XYZ"` |
| schema | file | all required columns present | `Amount` column missing |
| type | row | numeric columns contain numbers | `V7 = "abc"` |
| duplicate | row | `transaction_id` unique | same id twice |
| outlier | row | `Amount` ≤ 30,000 | `Amount = 999999` |
| format | row | `transaction_id` matches `TX` + 8 digits | `TX-1234` |

Files are validated **as text**, so a value like `"abc"` is reported on its own row (type error)
instead of breaking the whole column. Range checks use a small custom expectation
(`src/fraud_pipeline/gx_custom.py`) that converts values to numbers first.

**Criticality**: HIGH = a column is missing or > 50% invalid rows | MEDIUM = 10 to 50% |
LOW = above 0% and below 10% | NONE = no error. Teams alerts are sent for MEDIUM and HIGH only.

**Data Docs**: open `gx_project/gx/uncommitted/data_docs/local_site/index.html` in a browser.
Each alert and each `ingestion_stats.report_path` gives the page of that run (relative to `local_site/`).

### Prediction DAG
`check_for_new_data` lists files in `good_data` modified after the last processed file
(Airflow Variable `prediction_last_processed_mtime_ns`). If none, it raises `AirflowSkipException`,
so the whole run shows as skipped. `make_predictions` sends **one** batch request to the API.
Files are never moved or deleted by this DAG.

### API (FastAPI)
- `POST /predict` (`source`: `webapp` or `scheduled`), `GET /past-predictions?start_date&end_date&source`,
  `GET /past-predictions/{id}`, `GET /health`
- Pydantic request/response models, 400 (bad date range), 404 (unknown id), 422 (invalid input),
  503 (no model), model loaded once at startup with `lifespan`, DB session with `Depends(get_db)`
- Tables are SQLAlchemy ORM classes (`model_service/models.py`), created at startup.
  `predictions` stores the input features + `model_version` (needed for the Defense 2 dashboards).

### Model
`src/fraud_pipeline/model.py`: one scikit-learn `Pipeline` (StandardScaler + OneHotEncoder +
RandomForest with balanced class weights). Train 70% / test 10% (fixed hold-out) / production 20%
(fed to the ingestion job).

## Defense demo checklist

1. Empty `data/good_data` and `data/bad_data`.
2. Copy demo files from `data/demo_files` into `data/raw_data` one by one:
   `1_all_errors.csv` (HIGH alert, all rows to bad_data), `2_clean.csv`, `3_clean.csv`, `4_clean.csv`
   (good_data, then predictions), `5_mixed.csv` (MEDIUM alert, split), `6_missing_column.csv` (bonus: schema error).
3. Show the Teams alert, the Data Docs report, the `ingestion_stats` rows, the scheduled predictions in the web app.

## Development

```bash
pip install -r requirements-dev.txt
ruff check .
pytest
```

CI (GitHub Actions, `.github/workflows/ci.yml`) runs ruff, pytest and a Docker build on every push
and pull request to `main` and `develop`.

## Project structure

```
dags/                   ingestion_dag.py, prediction_dag.py
src/
  fraud_pipeline/       shared code: schema, GX suite + custom expectation, validation, errors, model, alerts
  prepare_dataset.py    add transaction_id + time_period, train/test/production split
  split_data.py         dataset -> N files of exactly 10 rows in raw_data
  generate_errors.py    random error injection, probability per error type
  make_demo_files.py    the 5 defense demo files
  train.py              train the model -> models/
  setup_gx.py           create/update the GX project (run by airflow-init)
gx_project/gx/          GX config: suite, validation definition, checkpoint (Data Docs in uncommitted/)
model_service/          FastAPI app
webapp/                 Streamlit app
airflow/                Airflow image (Dockerfile + requirements)
scripts/                ensure_airflow_db.py (creates the Airflow DB)
tests/                  pytest
```
