"""Data error injection used by generate_errors.py and make_demo_files.py.

All dataframes are handled as text (dtype=str) so injected values are written exactly
as intended and clean columns keep their original formatting.
"""

import numpy as np
import pandas as pd

from fraud_pipeline.schema import (
    CATEGORICAL_FEATURE,
    FEATURE_COLUMNS,
    ID_COLUMN,
    MAX_TIME_SECONDS,
    NUMERIC_FEATURES,
    REQUIRED_COLUMNS,
)

ROW_ERROR_TYPES = ["completeness", "validity", "consistency", "type", "duplicate", "outlier", "format"]

DEFAULT_ROW_PROBABILITIES = {
    "completeness": 0.04,  # null value in a required column
    "validity": 0.04,  # Amount < 0 or Time out of range
    "consistency": 0.03,  # unknown time_period category
    "type": 0.03,  # text in a numeric column
    "duplicate": 0.02,  # duplicated transaction_id
    "outlier": 0.02,  # unrealistic Amount
    "format": 0.02,  # malformed transaction_id
}
DEFAULT_SCHEMA_PROBABILITY = 0.05  # per file: drop a required column


def _set(df: pd.DataFrame, row: int, column: str, value: str) -> None:
    df.iat[row, df.columns.get_loc(column)] = value


def inject_row_error(df: pd.DataFrame, row: int, error_type: str, rng: np.random.Generator) -> None:
    if error_type == "completeness":
        _set(df, row, rng.choice([ID_COLUMN] + FEATURE_COLUMNS), "")
    elif error_type == "validity":
        if rng.random() < 0.5:
            _set(df, row, "Amount", f"-{rng.uniform(1, 500):.2f}")
        else:
            bad_time = rng.choice([-rng.integers(1, 10_000), MAX_TIME_SECONDS + rng.integers(1, 10_000)])
            _set(df, row, "Time", str(bad_time))
    elif error_type == "consistency":
        _set(df, row, CATEGORICAL_FEATURE, str(rng.choice(["midnight", "XYZ", "unknown", "Weekend"])))
    elif error_type == "type":
        _set(df, row, rng.choice(NUMERIC_FEATURES), str(rng.choice(["abc", "xyz", "twelve", "1,5", "$12"])))
    elif error_type == "duplicate":
        if len(df) > 1:
            other = int(rng.choice([i for i in range(len(df)) if i != row]))
            _set(df, row, ID_COLUMN, df.iat[other, df.columns.get_loc(ID_COLUMN)])
    elif error_type == "outlier":
        _set(df, row, "Amount", f"{rng.uniform(50_000, 999_999):.2f}")
    elif error_type == "format":
        _set(df, row, ID_COLUMN, str(rng.choice(["TX-1234", "tx0000123", "ABC123", "TX12"])))
    else:
        raise ValueError(f"unknown error type: {error_type}")


def drop_random_column(df: pd.DataFrame, rng: np.random.Generator) -> tuple[pd.DataFrame, str]:
    column = str(rng.choice([c for c in REQUIRED_COLUMNS if c in df.columns]))
    return df.drop(columns=[column]), column


def corrupt(
    df: pd.DataFrame,
    rng: np.random.Generator,
    row_probabilities: dict | None = None,
    schema_probability: float = DEFAULT_SCHEMA_PROBABILITY,
) -> tuple[pd.DataFrame, dict]:
    """Randomly inject errors. Returns the corrupted copy and a count per error type."""
    probabilities = {**DEFAULT_ROW_PROBABILITIES, **(row_probabilities or {})}
    df = df.copy()
    counts = {error_type: 0 for error_type in ROW_ERROR_TYPES + ["schema"]}

    for row in range(len(df)):
        for error_type in ROW_ERROR_TYPES:
            if rng.random() < probabilities[error_type]:
                inject_row_error(df, row, error_type, rng)
                counts[error_type] += 1

    if rng.random() < schema_probability:
        df, _ = drop_random_column(df, rng)
        counts["schema"] += 1
    return df, counts
