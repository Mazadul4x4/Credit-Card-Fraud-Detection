"""Prepare the Kaggle creditcard.csv for the project.

1. Adds a `transaction_id` primary key (TX00000001, ...).
2. Adds the categorical feature `time_period` derived from `Time`.
3. Splits the data (stratified on Class) into:
     data/training/train.csv   70%  -> initial model training
     data/training/test.csv    10%  -> fixed hold-out test set (fair model comparison in Defense 2)
     data/production.csv       20%  -> "new" data that feeds the ingestion job

Usage:
    python src/prepare_dataset.py data/creditcard.csv
"""

import argparse
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from fraud_pipeline.schema import (
    CATEGORICAL_FEATURE,
    ID_COLUMN,
    REQUIRED_COLUMNS,
    TARGET_COLUMN,
    time_period_from_seconds,
)


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop_duplicates().reset_index(drop=True)
    df.insert(0, ID_COLUMN, [f"TX{i:08d}" for i in range(1, len(df) + 1)])
    df[CATEGORICAL_FEATURE] = df["Time"].apply(time_period_from_seconds)
    df[TARGET_COLUMN] = df[TARGET_COLUMN].astype(int)
    return df[REQUIRED_COLUMNS]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("dataset", help="path to the original creditcard.csv")
    parser.add_argument("--output-dir", default="data")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    df = prepare(pd.read_csv(args.dataset))

    rest, production = train_test_split(
        df, test_size=0.2, stratify=df[TARGET_COLUMN], random_state=args.seed
    )
    train, test = train_test_split(
        rest, test_size=0.125, stratify=rest[TARGET_COLUMN], random_state=args.seed
    )  # 0.125 * 80% = 10% of the full dataset

    out = Path(args.output_dir)
    (out / "training").mkdir(parents=True, exist_ok=True)
    train.to_csv(out / "training" / "train.csv", index=False)
    test.to_csv(out / "training" / "test.csv", index=False)
    production.to_csv(out / "production.csv", index=False)

    for name, part in [("train", train), ("test", test), ("production", production)]:
        print(f"{name:<11} {len(part):>7} rows  fraud={part[TARGET_COLUMN].sum()}")


if __name__ == "__main__":
    main()
