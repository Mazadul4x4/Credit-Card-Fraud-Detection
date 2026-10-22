"""Split dataset into N files of 10 rows each.

Useful for simulating continuous micro-batch ingestion and streaming files.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def split_data(
    input_path: str | Path = "data/raw_data/creditcard.csv",
    output_dir: str | Path = "data/raw_data",
    num_files: int = 10,
    rows_per_file: int = 10,
    prefix: str = "batch",
    ensure_fraud_in_first: bool = True,
) -> list[Path]:
    in_file = Path(input_path)
    if not in_file.exists():
        alt = Path("data/raw_data/train.csv")
        if alt.exists():
            in_file = alt
        else:
            raise FileNotFoundError(f"Input file not found at {in_file} or {alt}")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Reading dataset from {in_file}...")
    df = pd.read_csv(in_file)

    # If requested, sample rows such that some batches contain fraud cases
    if ensure_fraud_in_first and "Class" in df.columns:
        fraud_df = df[df["Class"] == 1]
        normal_df = df[df["Class"] == 0]
        # Interleave fraud and normal to ensure interesting demo batches
        sample_rows = []
        f_idx = 0
        n_idx = 0
        total_needed = num_files * rows_per_file
        while len(sample_rows) < total_needed and (
            f_idx < len(fraud_df) or n_idx < len(normal_df)
        ):
            # 1 fraud every 10 rows if available
            if len(sample_rows) % rows_per_file == (rows_per_file - 1) and f_idx < len(
                fraud_df
            ):
                sample_rows.append(fraud_df.iloc[f_idx])
                f_idx += 1
            elif n_idx < len(normal_df):
                sample_rows.append(normal_df.iloc[n_idx])
                n_idx += 1
            elif f_idx < len(fraud_df):
                sample_rows.append(fraud_df.iloc[f_idx])
                f_idx += 1
        subset = pd.DataFrame(sample_rows)
    else:
        subset = df.iloc[: num_files * rows_per_file].copy()

    created_files = []
    for i in range(num_files):
        start_idx = i * rows_per_file
        end_idx = start_idx + rows_per_file
        chunk = subset.iloc[start_idx:end_idx]
        if len(chunk) == 0:
            break

        file_name = f"{prefix}_{i + 1:03d}.csv"
        file_path = out_dir / file_name
        chunk.to_csv(file_path, index=False)
        created_files.append(file_path)
        logger.info(f"Wrote {file_path} ({len(chunk)} rows)")

    logger.info(
        f"Successfully created {len(created_files)} files of {rows_per_file} rows in {out_dir}"
    )
    return created_files


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Split dataset into N files of 10 rows")
    parser.add_argument("--input", default="data/raw_data/creditcard.csv", help="Input dataset path")
    parser.add_argument("--output-dir", default="data/raw_data", help="Output directory")
    parser.add_argument("-n", "--num-files", type=int, default=10, help="Number of files to create")
    parser.add_argument("--rows-per-file", type=int, default=10, help="Rows per file")
    parser.add_argument("--prefix", default="batch", help="Filename prefix")
    args = parser.parse_args()

    split_data(
        input_path=args.input,
        output_dir=args.output_dir,
        num_files=args.num_files,
        rows_per_file=args.rows_per_file,
        prefix=args.prefix,
    )
