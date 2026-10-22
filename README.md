# 🛡️ Credit Card Fraud Detection — Defense 1 End-to-End Pipeline

[![CI Pipeline](https://github.com/Mazadul4x4/Credit-Card-Fraud-Detection/actions/workflows/ci.yml/badge.svg)](https://github.com/Mazadul4x4/Credit-Card-Fraud-Detection/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Airflow](https://img.shields.io/badge/Apache%20Airflow-3.0.2-017CEE.svg)](https://airflow.apache.org/)
[![Great Expectations](https://img.shields.io/badge/Great%20Expectations-1.x-orange.svg)](https://greatexpectations.io/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.42+-FF4B4B.svg)](https://streamlit.io/)

A production-grade, end-to-end Machine Learning data platform for credit card fraud detection. Features automated data quality validation with **Great Expectations**, scheduled orchestration with **Apache Airflow**, high-performance inference with **FastAPI**, audit logging to **PostgreSQL**, and an interactive **Streamlit** dashboard.

---

## 🏛️ Architecture Overview

```mermaid
flowchart TD
    subgraph Data Generation & Preparation
        RAW[data/raw_data/*.csv]
        SCRIPTS[Helper Scripts: split_data, generate_errors, make_demo_files]
        SCRIPTS --> RAW
    end

    subgraph Airflow Ingestion DAG [credit_card_ingestion]
        READ[read_data: Detect Next Raw File]
        GX[validate_data: Dynamic GX Checkpoint & 8 Error Checks]
        STATS[save_statistics: Log to Postgres ingestion_stats]
        ALERTS[send_alerts: MS Teams Alert & Data Docs Link]
        SPLIT[split_and_save_data: Good / Bad Split]

        READ --> GX
        GX --> STATS
        GX --> ALERTS
        GX --> SPLIT
    end

    RAW --> READ
    SPLIT -->|Valid Records| GOOD[data/good_data/*.csv]
    SPLIT -->|Invalid Records| BAD[data/bad_data/*.csv]
    SPLIT -->|Processed File| ARCHIVE[data/archived_data/*.csv]

    subgraph Airflow Prediction DAG [credit_card_prediction]
        DETECT[detect_new_data: Scan good_data]
        BATCH_PRED[batch_predict_and_archive: 1 Batch API Call]

        DETECT -->|Files Found| BATCH_PRED
        DETECT -->|No New Data| SKIP[Skip Entire Run]
    end

    GOOD --> DETECT

    subgraph FastAPI Model Service [Port 8000]
        API_PRED[/predict endpoint: Batch & Single]
        LIFESPAN[Lifespan: Loads Random Forest Pipeline]
        DB_INJECT[Depends(get_db)]

        LIFESPAN -.-> API_PRED
        API_PRED --> DB_INJECT
    end

    BATCH_PRED -->|Single Batch POST| API_PRED

    subgraph PostgreSQL Database [Port 5432]
        DB_PRED[(predictions: features + model_version)]
        DB_STATS[(ingestion_stats: error breakdown)]

        DB_INJECT --> DB_PRED
        STATS --> DB_STATS
    end

    subgraph Streamlit WebApp [Port 8501]
        PAGE1[Prediction Page: Form + CSV Upload]
        PAGE2[Past Predictions Page: Dates + Source Filter]
    end

    PAGE1 --> API_PRED
    PAGE2 -->|Query with Filters| API_PRED
    API_PRED --> DB_PRED
```

---

## 📦 Services Summary & Ports

| Service | Port | Description |
| :--- | :--- | :--- |
| **Streamlit WebApp** | `8501` | Interactive dashboard for single and batch fraud scoring and historical audits |
| **FastAPI Backend** | `8000` | REST API with Pydantic validation, lifespan model loading, and database persistence |
| **Airflow Webserver** | `8080` | Airflow UI and API server (`admin:admin`) |
| **PostgreSQL** | `5432` | Dual database host: `dsp_app` (predictions & ingestion stats) and `airflow` |

---

## 🚀 Quickstart: Single Docker Compose

### 1. Environment Setup
Create a `.env` file from the example:
```bash
cp .env.example .env
```
Ensure `.env` contains:
```env
POSTGRES_USER=dsp
POSTGRES_PASSWORD=yourRealPassword123
POSTGRES_DB=dsp_app
DATABASE_URL=postgresql://dsp:yourRealPassword123@db:5432/dsp_app
AIRFLOW_DB=airflow
```

### 2. Generate Demo Files & Train Model
Prepare the dataset, train the machine learning pipeline, and generate clean 10-row batch files:
```bash
python3 src/make_demo_files.py
```

### 3. Launch All Services
Start the entire stack using the unified single `docker-compose.yml`:
```bash
docker compose up --build
```
Once launched:
- **Streamlit WebApp:** [http://localhost:8501](http://localhost:8501)
- **FastAPI Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Airflow Webserver:** [http://localhost:8080](http://localhost:8080) (User: `admin`, Password: `admin`)
- **PostgreSQL:** `localhost:5432` (Database: `dsp_app`)

---

## 🔍 Defense 1 Features Breakdown

### 1. Ingestion DAG (`credit_card_ingestion`)
- **Dynamic Great Expectations Checkpoint:** Runs a validation checkpoint against the exact ingested file using the dynamic pandas batch definition and updates Data Docs.
- **8 Data Quality Error Types:**
  1. `missing_amount`: Null or NaN transaction amounts.
  2. `negative_amount`: Strictly negative transaction amounts (`Amount < 0`).
  3. `missing_time`: Null or NaN timestamp values.
  4. `negative_time`: Negative timestamp values (`Time < 0`).
  5. `invalid_class`: Target class corrupted outside `{0, 1}` (e.g. `99`, `2`, `-1`).
  6. `extreme_amount`: Outlier transaction amounts exceeding threshold (`Amount > 50,000`).
  7. `missing_columns`: Critical columns missing from the schema.
  8. `duplicate_rows`: Exact duplicate transaction rows in the batch.
- **Criticality Classification:** Categorizes files into `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, or `NONE` based on error severity and corrupted record rates.
- **Category Statistics in PostgreSQL:** Stores exact counts for each error category as JSON in `ingestion_stats.error_summary`.
- **Microsoft Teams Alerts:** Formats an adaptive alert card with file details, error breakdown, and Data Docs link. Dispatched via `TEAMS_WEBHOOK_URL` if configured (logged to task output otherwise).
- **Good / Bad Data Split:**
  - Valid rows that pass validation are written to `data/good_data/<stem>_good.csv`.
  - Corrupted rows are written to `data/bad_data/<stem>_bad.csv`.
  - The source raw file is moved to `data/archived_data/` to prevent redundant ingestion.

### 2. Prediction DAG (`credit_card_prediction`)
- **New-File Detection:** Scans `data/good_data/*.csv` for newly validated files.
- **Run Skipping:** If no files exist in `good_data`, raises `AirflowSkipException`, cleanly marking the entire run as **SKIPPED**.
- **One Batch API Call:** Combines all records across detected files and dispatches **one single batch HTTP POST** to `/predict`.
- **Automatic Archival:** After successful prediction, moves files from `data/good_data/` to `data/archived_data/`.

### 3. FastAPI Service (`model_service`)
- **Pydantic Validation:** Type-safe models with `ConfigDict(extra="ignore")` for transaction features.
- **Explicit Status Codes:** Returns HTTP 200, 400, 422, 503 with standardized REST error responses.
- **Lifespan Model Loading:** Modern `@asynccontextmanager async def lifespan(app: FastAPI)` pattern to load Scikit-Learn pipeline without deprecated startup event handlers.
- **Dependency Injection:** Database sessions safely managed with `Depends(get_db)`.
- **Feature & Version Persistence:** Every prediction record stores the exact transaction feature dictionary (JSON) alongside `model_version`, `source`, `probability`, and `predicted_class`.

### 4. Streamlit Application (`webapp`)
- **Prediction Page:**
  - **Single Transaction Form:** Manual feature inputs with pre-configured presets ("Normal Transaction" and "High-Risk Profile"), probability progress bar, and visual alert badges.
  - **Batch CSV Upload:** Drag-and-drop CSV scoring, executive summary metric cards, interactive preview, and CSV download.
- **Past Predictions Page:**
  - Date range filtering (`start_date` and `end_date`).
  - Source filtering (`Prediction DAG`, `streamlit_form`, `streamlit_csv`, etc.).
  - Metric summary cards (Total Records, Fraud Count, Fraud Rate %).
  - Expandable feature payload viewer for full auditability.

---

## 🛠️ Helper Scripts Reference

All helper scripts are located in `src/`:

```bash
# 1. Prepare baseline credit card dataset
python3 src/prepare_dataset.py

# 2. Train the Random Forest pipeline with StandardScaler and export metadata
python3 src/train.py

# 3. Split dataset into N files of 10 rows each
python3 src/split_data.py --input data/raw_data/creditcard.csv -n 10 --rows-per-file 10 --output-dir data/raw_data

# 4. Generate datasets demonstrating all 8 error types
python3 src/generate_errors.py --output-dir data/bad_data

# 5. One-stop demo files generator
python3 src/make_demo_files.py --clean-batches 5 --rows-per-batch 10

# 6. Execute GX checkpoint and build Data Docs locally
python3 src/run_checkpoint.py --file data/raw_data/demo_batch_001.csv
```

---

## 🧪 Testing & CI

Continuous Integration is automated via GitHub Actions on every push and PR:
- **Linting:** `ruff check .`
- **Testing:** `pytest` (unit & integration tests for API, models, scripts, and GX validation)
- **Container Build:** Validates `model_service/Dockerfile`, `webapp/Dockerfile`, and `airflow/Dockerfile`.

### Running Tests Locally
```bash
# Run linter
ruff check .

# Run test suite
pytest -v
```

---

## 📊 Great Expectations Data Docs
Data Docs provide interactive HTML reports detailing validation results:
- Local report location: `src/gx/gx/uncommitted/data_docs/local_site/index.html`
- To regenerate docs manually:
  ```bash
  python3 src/run_checkpoint.py
  ```
  Open `src/gx/gx/uncommitted/data_docs/local_site/index.html` in any browser.
