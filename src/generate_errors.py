"""Generate synthetic errors for data quality testing and GX validation.

Supports 8 distinct error types:
1. missing_amount: NaN values in Amount
2. negative_amount: Amount < 0
3. missing_time: NaN values in Time
4. negative_time: Time < 0
5. invalid_class: Class values not in [0, 1]
6. extreme_amount: Amount > 50,000 (extreme outlier)
7. missing_columns: Required columns dropped
8. duplicate_rows: Duplicate transaction rows
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

ERROR_TYPES = [
    "missing_amount",
    "negative_amount",
    "missing_time",
    "negative_time",
    "invalid_class",
    "extreme_amount",
    "missing_columns",
    "duplicate_rows",
]


def inject_error(df: pd.DataFrame, error_type: str, fraction: float = 0.3) -> pd.DataFrame:
    """Inject a specific error type into a copy of the dataframe."""
    bad_df = df.copy()
    n_rows = len(bad_df)
    n_corrupt = max(1, int(n_rows * fraction))
    indices = np.random.choice(n_rows, size=min(n_corrupt, n_rows), replace=False)

    if error_type == "missing_amount":
        bad_df.loc[indices, "Amount"] = np.nan

    elif error_type == "negative_amount":
        bad_df.loc[indices, "Amount"] = -abs(bad_df.loc[indices, "Amount"]) - 10.0

    elif error_type == "missing_time":
        bad_df.loc[indices, "Time"] = np.nan

    elif error_type == "negative_time":
        bad_df.loc[indices, "Time"] = -abs(bad_df.loc[indices, "Time"]) - 100.0

    elif error_type == "invalid_class":
        bad_df.loc[indices, "Class"] = 99

    elif error_type == "extreme_amount":
        bad_df.loc[indices, "Amount"] = 999999.0

    elif error_type == "missing_columns":
        # Drop Amount or Class
        cols_to_drop = [c for c in ["Amount", "Class"] if c in bad_df.columns]
        if cols_to_drop:
            bad_df = bad_df.drop(columns=[cols_to_drop[0]])

    elif error_type == "duplicate_rows":
        dups = bad_df.iloc[:n_corrupt]
        bad_df = pd.concat([bad_df, dups], ignore_index=True)

    else:
        raise ValueError(
            f"Unknown error_type: {error_type}. Supported: {ERROR_TYPES}"
        )

    return bad_df


def generate_error_datasets(
    input_path: str | Path = "data/raw_data/creditcard.csv",
    output_dir: str | Path = "data/bad_data",
    sample_rows: int = 50,
) -> dict[str, Path]:
    in_file = Path(input_path)
    if not in_file.exists():
        alt = Path("data/raw_data/train.csv")
        if alt.exists():
            in_file = alt
        else:
            raise FileNotFoundError(f"Input dataset not found at {in_file}")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Loading {sample_rows} sample rows from {in_file}...")
    df = pd.read_csv(in_file, nrows=sample_rows)

    generated = {}

    for idx, err in enumerate(ERROR_TYPES, 1):
        corrupted = inject_error(df, err, fraction=0.3)
        file_path = out_dir / f"error_{idx}_{err}.csv"
        corrupted.to_csv(file_path, index=False)
        generated[err] = file_path
        logger.info(f"Generated {file_path} for error: {err}")

    # Also generate a mixed error file containing multiple errors
    mixed_df = df.copy()
    if len(mixed_df) >= 8:
        mixed_df.loc[0, "Amount"] = np.nan
        mixed_df.loc[1, "Amount"] = -25.0
        mixed_df.loc[2, "Time"] = np.nan
        mixed_df.loc[3, "Time"] = -500.0
        mixed_df.loc[4, "Class"] = 42
        mixed_df.loc[5, "Amount"] = 888888.0
        # Duplicate row 6
        dup_row = mixed_df.iloc[[6]]
        mixed_df = pd.concat([mixed_df, dup_row], ignore_index=True)

    mixed_path = out_dir / "error_mixed_all.csv"
    mixed_df.to_csv(mixed_path, index=False)
    generated["mixed"] = mixed_path
    logger.info(f"Generated combined multi-error dataset: {mixed_path}")

    return generated


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate data quality error files")
    parser.add_argument("--input", default="data/raw_data/creditcard.csv", help="Input dataset path")
    parser.add_argument("--output-dir", default="data/bad_data", help="Output directory")
    parser.add_argument("--sample-rows", type=int, default=50, help="Rows per file")
    args = parser.parse_args()

    generate_error_datasets(
        input_path=args.input,
        output_dir=args.output_dir,
        sample_rows=args.sample_rows,
    )
