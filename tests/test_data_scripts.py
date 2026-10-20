import numpy as np
import pandas as pd
import pytest

from fraud_pipeline.errors import corrupt, inject_row_error
from fraud_pipeline.schema import REQUIRED_COLUMNS, TIME_PERIODS, time_period_from_seconds
from split_data import ROWS_PER_FILE, split_dataset


def test_prepare_adds_id_and_categorical(prepared_df):
    assert list(prepared_df.columns) == REQUIRED_COLUMNS
    assert prepared_df["transaction_id"].is_unique
    assert set(prepared_df["time_period"]) <= set(TIME_PERIODS)


@pytest.mark.parametrize(
    "seconds, expected",
    [(0, "night"), (7 * 3600, "morning"), (13 * 3600, "afternoon"), (20 * 3600, "evening"),
     (86_400 + 3600, "night")],
)
def test_time_period(seconds, expected):
    assert time_period_from_seconds(seconds) == expected


def test_split_creates_n_files_of_exactly_10_rows(prepared_df, tmp_path):
    paths = split_dataset(prepared_df, tmp_path, number_of_files=25, seed=1)
    assert len(paths) == 25
    assert all(len(pd.read_csv(p)) == ROWS_PER_FILE for p in paths)


def test_split_refuses_too_many_files(prepared_df, tmp_path):
    with pytest.raises(ValueError):
        split_dataset(prepared_df, tmp_path, number_of_files=10_000)


def test_corrupt_probability_one_hits_every_row(clean_file):
    rng = np.random.default_rng(0)
    probabilities = {k: 0.0 for k in ["completeness", "validity", "consistency", "type",
                                      "duplicate", "outlier", "format"]}
    probabilities["consistency"] = 1.0
    corrupted, counts = corrupt(clean_file, rng, probabilities, schema_probability=0.0)
    assert counts["consistency"] == 10
    assert not corrupted["time_period"].isin(TIME_PERIODS).any()


def test_schema_error_drops_a_column(clean_file):
    rng = np.random.default_rng(0)
    zero = {k: 0.0 for k in ["completeness", "validity", "consistency", "type",
                             "duplicate", "outlier", "format"]}
    corrupted, counts = corrupt(clean_file, rng, zero, schema_probability=1.0)
    assert counts["schema"] == 1
    assert len(corrupted.columns) == len(REQUIRED_COLUMNS) - 1


def test_type_error_injects_text(clean_file):
    df = clean_file.copy()
    inject_row_error(df, 0, "type", np.random.default_rng(1))
    assert pd.to_numeric(df.iloc[0][1:31], errors="coerce").isna().sum() == 1
