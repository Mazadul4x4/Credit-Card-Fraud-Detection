# Defense 1 fixes

What was changed compared to the previous version, and why.

## Broken before

| Area | Problem | Fix |
|---|---|---|
| Prediction DAG | tasks defined but never called: the DAG had no tasks | rewritten, tasks wired `check_for_new_data >> make_predictions` |
| Ingestion routing | valid files went to `archived_data` with `copy2`; raw files never deleted | `read_data` deletes the file; valid rows → `good_data`, bad rows → `bad_data`, mixed files split |
| Great Expectations | asset hardcoded to one `train.csv`; suite had 0 expectations; checkpoint had no actions; two different GX contexts | runtime dataframe asset validates the file that was read; 71 expectations built in code; checkpoint with `UpdateDataDocsAction`; one GX project (`gx_project/`) set up automatically by `airflow-init` |
| Error counting | invalid rows computed by hand in pandas | computed from the GX validation results (`unexpected_index_list` per expectation) |
| API | crashed at startup (no model mounted, wrong file name); scaler not applied; no `/predictions` endpoint | model = one sklearn Pipeline (preprocessing included), mounted from `./models`; 503 if missing; `/past-predictions` with filters |
| Web app | sent `predicted_class`/`probability` instead of features; one page; not in Docker; `localhost` URL | 2 pages (prediction: form + CSV; past predictions: dates + source), containerized, `API_URL` env |
| Airflow | `airflow` DB never created; password hardcoded and different from `.env`; no Airflow connection; webhook not passed | `ensure_airflow_db.py`; everything from `.env`; connection `dsp_postgres` created at init; env vars passed |
| Training | Windows path; `imblearn` not installed; saved under a different name | `src/train.py` with relative paths, no extra dependency, `models/fraud_model.joblib` + metadata |

## Missing before

- **CI**: GitHub Actions with ruff, pytest (32 tests) and Docker build.
- **split_data.py**: now creates N files of exactly 10 rows (was a train/test split).
- **generate_errors.py**: 8 error types (5 required + duplicate, outlier, format), random with
  configurable probability per type; folder mode for per-file schema errors.
- **Categorical feature**: the dataset has none, so `time_period` (derived from `Time`) was added.
  Needed for the consistency rule now and the drift dashboard in Defense 2.
- **Primary key** `transaction_id` (needed for the duplicate and format rules).
- **Database**: `predictions` stores features + `model_version`; `ingestion_stats` stores one
  counter column per error category (ready for the Defense 2 data quality dashboard).
- **Demo files**: `make_demo_files.py` creates the 5 required files (+ a missing-column file).
- **Single docker-compose.yml** for all services, pinned versions, README with setup steps.

## Removed

`explore_data.py`, `preprocessing.py`, `add_expectations.py`, `create_*.py`, `run_checkpoint.py`,
`docker-compose.airflow.yml`, `src/gx/`: replaced by the files above.

## Ready for Defense 2

- `model_service/ml.py` is where `/reload-model` and MLflow loading go.
- `src/fraud_pipeline/model.py` (`build_pipeline`, `evaluate`) can be reused by the training DAG.
- `data/training/test.csv` is a fixed hold-out set for a fair champion vs candidate comparison.
- `DATA_DOCS_BASE_URL` in `.env` turns the report path in alerts into a clickable nginx link.
