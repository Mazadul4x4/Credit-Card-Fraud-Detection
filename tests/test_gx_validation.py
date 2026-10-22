from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd

from src.gx_validator import split_good_bad, validate_file


def test_gx_validation_on_clean_data():
    with tempfile.TemporaryDirectory() as tmpdir:
        clean_file = Path(tmpdir) / "clean.csv"
        rows = []
        for i in range(10):
            r = {"Time": float(100 + i), "Amount": 25.0 + i, "Class": 0}
            for v in range(1, 29):
                r[f"V{v}"] = 0.05
            rows.append(r)
        pd.DataFrame(rows).to_csv(clean_file, index=False)

        res = validate_file(clean_file)
        assert res["validation_success"] is True
        assert res["invalid_rows"] == 0
        assert res["valid_rows"] == 10
        assert res["criticality"] == "NONE"


def test_gx_validation_on_negative_amount_and_split():
    with tempfile.TemporaryDirectory() as tmpdir:
        dirty_file = Path(tmpdir) / "dirty.csv"
        rows = []
        for i in range(10):
            amt = -50.0 if i < 3 else 50.0
            r = {"Time": float(100 + i), "Amount": amt, "Class": 0}
            for v in range(1, 29):
                r[f"V{v}"] = 0.05
            rows.append(r)
        pd.DataFrame(rows).to_csv(dirty_file, index=False)

        res = validate_file(dirty_file)
        assert res["validation_success"] is False
        assert res["invalid_rows"] == 3
        assert res["valid_rows"] == 7
        assert res["stats_per_category"]["negative_amount"] == 3
        assert res["criticality"] in ["MEDIUM", "HIGH", "CRITICAL"]

        # Test good/bad split
        good_dir = Path(tmpdir) / "good"
        bad_dir = Path(tmpdir) / "bad"
        arch_dir = Path(tmpdir) / "arch"

        split_info = split_good_bad(
            file_path=dirty_file,
            validation_result=res,
            good_dir=good_dir,
            bad_dir=bad_dir,
            archive_dir=arch_dir,
        )

        assert split_info["good_count"] == 7
        assert split_info["bad_count"] == 3
        assert Path(split_info["good_path"]).exists()
        assert Path(split_info["bad_path"]).exists()
