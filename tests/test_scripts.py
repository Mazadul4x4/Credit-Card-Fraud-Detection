from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd

from src.generate_errors import ERROR_TYPES, inject_error
from src.split_data import split_data


def test_split_data_n_files_10_rows():
    # Create temporary dataset
    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = Path(tmpdir) / "test_input.csv"
        rows = []
        for i in range(35):
            r = {"Time": float(i), "Amount": 10.0 + i, "Class": i % 2}
            for v in range(1, 29):
                r[f"V{v}"] = 0.01 * v
            rows.append(r)
        pd.DataFrame(rows).to_csv(input_file, index=False)

        out_dir = Path(tmpdir) / "batches"
        files = split_data(
            input_path=input_file,
            output_dir=out_dir,
            num_files=3,
            rows_per_file=10,
            prefix="test_chunk",
            ensure_fraud_in_first=False,
        )

        assert len(files) == 3
        for f in files:
            df = pd.read_csv(f)
            assert len(df) == 10


def test_generate_errors_all_8_types():
    base_rows = []
    for i in range(20):
        r = {"Time": 100.0 + i, "Amount": 50.0 + i, "Class": 0}
        for v in range(1, 29):
            r[f"V{v}"] = 0.1
        base_rows.append(r)
    df = pd.DataFrame(base_rows)

    assert len(ERROR_TYPES) == 8

    # Test each error injection
    for err in ERROR_TYPES:
        corrupted = inject_error(df, err, fraction=0.5)
        if err == "missing_amount":
            assert corrupted["Amount"].isna().sum() > 0
        elif err == "negative_amount":
            assert (corrupted["Amount"] < 0).sum() > 0
        elif err == "missing_time":
            assert corrupted["Time"].isna().sum() > 0
        elif err == "negative_time":
            assert (corrupted["Time"] < 0).sum() > 0
        elif err == "invalid_class":
            assert (~corrupted["Class"].isin([0, 1])).sum() > 0
        elif err == "extreme_amount":
            assert (corrupted["Amount"] > 50000.0).sum() > 0
        elif err == "missing_columns":
            assert "Amount" not in corrupted.columns or "Class" not in corrupted.columns
        elif err == "duplicate_rows":
            assert corrupted.duplicated().sum() > 0
