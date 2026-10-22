import numpy as np
import pytest

from fraud_pipeline.errors import inject_row_error
from fraud_pipeline.validation import criticality, get_context, run_checkpoint, setup_context


@pytest.fixture(scope="module")
def gx_context(tmp_path_factory):
    context = get_context(str(tmp_path_factory.mktemp("gx")))
    setup_context(context)
    return context


def validate(df, context):
    return run_checkpoint(df.replace({"": None}), "test.csv", context=context)


def test_clean_file_has_no_errors(clean_file, gx_context):
    summary = validate(clean_file, gx_context)
    assert summary["invalid_rows"] == 0
    assert summary["criticality"] == "NONE"
    assert summary["report_path"].endswith(".html")


@pytest.mark.parametrize(
    "error_type, category",
    [
        ("completeness", "completeness"),
        ("validity", "validity"),
        ("consistency", "consistency"),
        ("type", "type"),
        ("outlier", "outlier"),
        ("format", "format"),
    ],
)
def test_each_error_type_is_detected_in_its_category(clean_file, gx_context, error_type, category):
    df = clean_file.copy()
    inject_row_error(df, 3, error_type, np.random.default_rng(0))
    summary = validate(df, gx_context)
    assert summary["error_counts"][category] == 1
    assert summary["invalid_row_indexes"] == [3]
    assert summary["criticality"] == "MEDIUM"  # 1 of 10 rows = 10%


def test_duplicate_ids_are_detected(clean_file, gx_context):
    df = clean_file.copy()
    df.loc[1, "transaction_id"] = df.loc[0, "transaction_id"]
    summary = validate(df, gx_context)
    assert summary["error_counts"]["duplicate"] == 2


def test_missing_column_is_high_and_all_rows_invalid(clean_file, gx_context):
    summary = validate(clean_file.drop(columns=["Amount"]), gx_context)
    assert summary["missing_columns"] == ["Amount"]
    assert summary["invalid_rows"] == 10
    assert summary["criticality"] == "HIGH"


@pytest.mark.parametrize(
    "ratio, missing, expected",
    [(0, [], "NONE"), (0.05, [], "LOW"), (0.1, [], "MEDIUM"), (0.5, [], "MEDIUM"),
     (0.6, [], "HIGH"), (0, ["Amount"], "HIGH")],
)
def test_criticality_rules(ratio, missing, expected):
    assert criticality(ratio, missing) == expected
