import numpy as np
import pandas as pd
import pytest

from fraud_pipeline.schema import NUMERIC_FEATURES
from prepare_dataset import prepare


@pytest.fixture(scope="session")
def prepared_df() -> pd.DataFrame:
    """Small synthetic dataset with the same columns as the Kaggle creditcard.csv."""
    rng = np.random.default_rng(0)
    n = 2_000
    raw = pd.DataFrame({"Time": rng.uniform(0, 172_000, n).round(0)})
    fraud = rng.random(n) < 0.05
    for i in range(1, 29):
        values = rng.normal(0, 1, n)
        values[fraud] += 3
        raw[f"V{i}"] = values
    raw["Amount"] = rng.lognormal(3, 1, n).round(2)
    raw["Class"] = fraud.astype(int)
    return prepare(raw)


@pytest.fixture()
def clean_file(prepared_df) -> pd.DataFrame:
    """10 clean rows, read as text like the ingestion DAG does."""
    return prepared_df.head(10).astype(str).reset_index(drop=True)


@pytest.fixture(scope="session")
def trained_model_dir(prepared_df, tmp_path_factory):
    import joblib

    from fraud_pipeline.model import build_pipeline, split_xy

    model = build_pipeline()
    model.set_params(classifier__n_estimators=10)
    model.fit(*split_xy(prepared_df))
    model_dir = tmp_path_factory.mktemp("models")
    joblib.dump(model, model_dir / "fraud_model.joblib")
    (model_dir / "model_metadata.json").write_text('{"model_version": "test-model"}')
    return model_dir


def feature_records(df: pd.DataFrame) -> list[dict]:
    return df[["transaction_id"] + NUMERIC_FEATURES + ["time_period"]].to_dict(orient="records")
