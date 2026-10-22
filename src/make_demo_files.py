"""Generate demo files for testing end-to-end Airflow pipelines and FastAPI.

Prepares:
1. Baseline dataset (data/raw_data/creditcard.csv)
2. Trained model if missing (models/fraud_model.joblib)
3. Clean micro-batches of 10 rows in data/raw_data/ for Ingestion DAG
4. Test files with data errors in data/bad_data/ and data/raw_data/
"""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from pathlib import Path

# Ensure root directory is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.generate_errors import generate_error_datasets
from src.prepare_dataset import prepare_dataset
from src.split_data import split_data
from src.train import train_model

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def make_demo_files(
    num_clean_batches: int = 5,
    rows_per_batch: int = 10,
    include_error_in_raw: bool = True,
) -> None:
    # 1. Ensure required directories
    for d in ["data/raw_data", "data/good_data", "data/bad_data", "data/archived_data", "models"]:
        Path(d).mkdir(parents=True, exist_ok=True)

    # 2. Ensure baseline creditcard.csv
    dataset_path = prepare_dataset()

    # 3. Ensure model is trained
    model_path = Path("models/fraud_model.joblib")
    if not model_path.exists():
        logger.info("Model not found. Training demo model...")
        train_model(data_path=dataset_path, output_dir="models")
    else:
        logger.info(f"Using existing model at {model_path}")

    # 4. Generate clean micro-batch files in data/raw_data
    logger.info(f"Generating {num_clean_batches} clean files of {rows_per_batch} rows...")
    clean_files = split_data(
        input_path=dataset_path,
        output_dir="data/raw_data",
        num_files=num_clean_batches,
        rows_per_file=rows_per_batch,
        prefix="demo_batch",
    )
    logger.info(f"Generated clean batches: {[f.name for f in clean_files]}")

    # 5. Generate error files in data/bad_data
    logger.info("Generating error datasets for all 8 error types...")
    error_files = generate_error_datasets(
        input_path=dataset_path,
        output_dir="data/bad_data",
        sample_rows=20,
    )

    # 6. Optionally copy an error file into data/raw_data to test error ingestion
    if include_error_in_raw and "mixed" in error_files:
        dest = Path("data/raw_data/demo_error_batch.csv")
        shutil.copy2(error_files["mixed"], dest)
        logger.info(f"Copied error batch to {dest} for ingestion testing.")

    logger.info("Demo files preparation complete!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create demo files for pipeline testing")
    parser.add_argument("--clean-batches", type=int, default=5, help="Number of clean batches")
    parser.add_argument("--rows-per-batch", type=int, default=10, help="Rows per batch")
    parser.add_argument(
        "--no-error-in-raw",
        action="store_true",
        help="Do not place an error file in raw_data",
    )
    args = parser.parse_args()

    make_demo_files(
        num_clean_batches=args.clean_batches,
        rows_per_batch=args.rows_per_batch,
        include_error_in_raw=not args.no_error_in_raw,
    )
