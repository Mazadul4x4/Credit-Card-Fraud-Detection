"""Randomly inject data quality errors, with a configurable probability per error type.

Works on a single dataset file OR on a folder of files (e.g. raw_data). Folder mode is
what you want for the ingestion job: every file gets its own random mix of errors, and
the file-level "missing column" error can only be applied per file.

Error types (8): completeness, validity, consistency, schema, type,
                 duplicate, outlier, format

Usage:
    # whole dataset -> corrupted dataset
    python src/generate_errors.py data/production.csv data/production_corrupted.csv

    # every file in raw_data, in place (recommended, after split_data.py)
    python src/generate_errors.py data/raw_data data/raw_data --clean-file-ratio 0.3

    # tune probabilities
    python src/generate_errors.py data/raw_data data/raw_data --p-type 0.1 --p-schema 0.2
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from fraud_pipeline.errors import DEFAULT_ROW_PROBABILITIES, DEFAULT_SCHEMA_PROBABILITY, corrupt


def read_text_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("input", help="CSV file or folder of CSV files")
    parser.add_argument("output", help="output CSV file or folder (can be the same as input)")
    for error_type, default in DEFAULT_ROW_PROBABILITIES.items():
        parser.add_argument(f"--p-{error_type}", type=float, default=default,
                            help=f"probability per row (default {default})")
    parser.add_argument("--p-schema", type=float, default=DEFAULT_SCHEMA_PROBABILITY,
                        help="probability per file of dropping a required column")
    parser.add_argument("--clean-file-ratio", type=float, default=0.0,
                        help="folder mode: share of files left untouched (default 0)")
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    probabilities = {k: getattr(args, f"p_{k}") for k in DEFAULT_ROW_PROBABILITIES}
    source, target = Path(args.input), Path(args.output)

    if source.is_dir():
        target.mkdir(parents=True, exist_ok=True)
        files = sorted(source.glob("*.csv"))
        totals: dict[str, int] = {}
        untouched = 0
        for path in files:
            df = read_text_csv(path)
            if rng.random() < args.clean_file_ratio:
                untouched += 1
                corrupted, counts = df, {}
            else:
                corrupted, counts = corrupt(df, rng, probabilities, args.p_schema)
            corrupted.to_csv(target / path.name, index=False)
            for k, v in counts.items():
                totals[k] = totals.get(k, 0) + v
        print(f"Processed {len(files)} files ({untouched} left clean) -> {target}")
        print("Injected:", totals)
    else:
        df = read_text_csv(source)
        # schema errors only make sense per file; use folder mode for them
        corrupted, counts = corrupt(df, rng, probabilities, schema_probability=0.0)
        target.parent.mkdir(parents=True, exist_ok=True)
        corrupted.to_csv(target, index=False)
        print(f"Wrote {len(corrupted)} rows -> {target}")
        print("Injected:", counts)


if __name__ == "__main__":
    main()
