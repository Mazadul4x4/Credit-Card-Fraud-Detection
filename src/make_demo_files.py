"""Create the 5 demo files required for the defense (+1 bonus file).

    1_all_errors.csv        every row has an error  -> HIGH alert, all rows to bad_data
    2_clean.csv, 3_clean.csv, 4_clean.csv            -> good_data, then predictions
    5_mixed.csv             4 of 10 rows have errors -> MEDIUM alert, file split in two
    6_missing_column.csv    `Amount` column removed   -> HIGH alert (schema error)

Keep them OUTSIDE raw_data and copy them into raw_data during the demo.

Usage:
    python src/make_demo_files.py data/production.csv data/demo_files
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from fraud_pipeline.errors import ROW_ERROR_TYPES, inject_row_error

ROWS = 10


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("dataset_path")
    parser.add_argument("output_folder")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    df = pd.read_csv(args.dataset_path, dtype=str, keep_default_na=False)
    sample = df.sample(n=ROWS * 6, random_state=args.seed).reset_index(drop=True)
    chunks = [sample.iloc[i * ROWS : (i + 1) * ROWS].reset_index(drop=True).copy() for i in range(6)]
    out = Path(args.output_folder)
    out.mkdir(parents=True, exist_ok=True)

    # 1. only errors: one error per row, cycling through every row-level type
    all_errors = chunks[0]
    for row in range(ROWS):
        error_type = ROW_ERROR_TYPES[row % len(ROW_ERROR_TYPES)]
        if error_type == "duplicate":
            error_type = "format"  # a duplicate also flags the other row; keep it simple
        inject_row_error(all_errors, row, error_type, rng)
    all_errors.to_csv(out / "1_all_errors.csv", index=False)

    # 2-4. clean files
    for i, name in enumerate(["2_clean.csv", "3_clean.csv", "4_clean.csv"], start=1):
        chunks[i].to_csv(out / name, index=False)

    # 5. mixed: rows 0-3 bad, rows 4-9 good
    mixed = chunks[4]
    for row, error_type in enumerate(["completeness", "validity", "consistency", "type"]):
        inject_row_error(mixed, row, error_type, rng)
    mixed.to_csv(out / "5_mixed.csv", index=False)

    # 6. bonus: schema error
    chunks[5].drop(columns=["Amount"]).to_csv(out / "6_missing_column.csv", index=False)

    print(f"Demo files written to {out}:")
    for path in sorted(out.glob("*.csv")):
        print("  ", path.name)


if __name__ == "__main__":
    main()
