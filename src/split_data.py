"""Split a dataset into N files of exactly 10 rows each, stored in the raw_data folder.

Usage:
    python src/split_data.py <dataset_path> <raw_data_folder> <number_of_files>
    python src/split_data.py data/production.csv data/raw_data 40
"""

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

ROWS_PER_FILE = 10


def split_dataset(df: pd.DataFrame, output_dir: Path, number_of_files: int, seed=None) -> list[Path]:
    needed = number_of_files * ROWS_PER_FILE
    if number_of_files <= 0:
        raise ValueError("number_of_files must be > 0")
    if needed > len(df):
        raise ValueError(
            f"{number_of_files} files x {ROWS_PER_FILE} rows = {needed} rows, "
            f"but the dataset only has {len(df)} rows"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    sample = df.sample(n=needed, random_state=seed).reset_index(drop=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    paths = []
    for i in range(number_of_files):
        chunk = sample.iloc[i * ROWS_PER_FILE : (i + 1) * ROWS_PER_FILE]
        path = output_dir / f"batch_{stamp}_{i + 1:04d}.csv"
        chunk.to_csv(path, index=False)
        paths.append(path)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("dataset_path")
    parser.add_argument("raw_data_folder")
    parser.add_argument("number_of_files", type=int)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    # read as text so values are written back exactly as they were
    df = pd.read_csv(args.dataset_path, dtype=str, keep_default_na=False)
    paths = split_dataset(df, Path(args.raw_data_folder), args.number_of_files, args.seed)
    print(f"Created {len(paths)} files of {ROWS_PER_FILE} rows in {args.raw_data_folder}")


if __name__ == "__main__":
    main()
