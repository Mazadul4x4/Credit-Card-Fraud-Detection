"""Prepare the baseline credit card dataset.

Combines train and test datasets into data/raw_data/creditcard.csv if not already present.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def prepare_dataset(
    output_path: str | Path = "data/raw_data/creditcard.csv",
    train_path: str | Path = "data/raw_data/train.csv",
    test_path: str | Path = "data/good_data/test.csv",
) -> Path:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    train_p = Path(train_path)
    test_p = Path(test_path)

    if out.exists() and out.stat().st_size > 0:
        logger.info(f"Dataset already exists at {out} ({out.stat().st_size} bytes)")
        return out

    if train_p.exists() and test_p.exists():
        logger.info(f"Combining {train_p} and {test_p} into {out}...")
        df_train = pd.read_csv(train_p)
        df_test = pd.read_csv(test_p)
        df_combined = pd.concat([df_train, df_test], ignore_index=True)
        df_combined.to_csv(out, index=False)
        logger.info(f"Created {out} with {len(df_combined)} rows.")
        return out

    if train_p.exists():
        logger.info(f"Copying {train_p} to {out}...")
        df_train = pd.read_csv(train_p)
        df_train.to_csv(out, index=False)
        logger.info(f"Created {out} with {len(df_train)} rows.")
        return out

    raise FileNotFoundError(f"Neither {train_p} nor {out} could be found to prepare dataset.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare credit card dataset")
    parser.add_argument("--output", default="data/raw_data/creditcard.csv", help="Output path")
    parser.add_argument("--train", default="data/raw_data/train.csv", help="Train CSV path")
    parser.add_argument("--test", default="data/good_data/test.csv", help="Test CSV path")
    args = parser.parse_args()

    prepare_dataset(output_path=args.output, train_path=args.train, test_path=args.test)
