"""Model definition, training and evaluation (reused by train.py and, in Defense 2,
by the training DAG)."""

import time

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from fraud_pipeline.schema import (
    CATEGORICAL_FEATURE,
    FEATURE_COLUMNS,
    NUMERIC_FEATURES,
    TARGET_COLUMN,
    TIME_PERIODS,
)


def build_pipeline(random_state: int = 42) -> Pipeline:
    """Preprocessing + classifier in ONE object, so the API never needs a separate scaler."""
    preprocessing = ColumnTransformer(
        [
            ("numeric", StandardScaler(), NUMERIC_FEATURES),
            (
                "categorical",
                OneHotEncoder(categories=[TIME_PERIODS], handle_unknown="ignore"),
                [CATEGORICAL_FEATURE],
            ),
        ]
    )
    classifier = RandomForestClassifier(
        n_estimators=100,
        max_depth=12,
        min_samples_leaf=2,
        class_weight="balanced_subsample",  # the dataset is very imbalanced (~0.17% fraud)
        n_jobs=-1,
        random_state=random_state,
    )
    return Pipeline([("preprocessing", preprocessing), ("classifier", classifier)])


def split_xy(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    return df[FEATURE_COLUMNS], df[TARGET_COLUMN].astype(int)


def evaluate(model: Pipeline, df: pd.DataFrame) -> dict:
    X, y = split_xy(df)
    start = time.perf_counter()
    predictions = model.predict(X)
    inference_ms = (time.perf_counter() - start) * 1000
    probabilities = model.predict_proba(X)[:, 1]
    return {
        "f1": round(float(f1_score(y, predictions, zero_division=0)), 4),
        "precision": round(float(precision_score(y, predictions, zero_division=0)), 4),
        "recall": round(float(recall_score(y, predictions, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y, probabilities)), 4) if y.nunique() > 1 else None,
        "inference_ms_per_1000_rows": round(inference_ms / max(len(X), 1) * 1000, 3),
        "test_rows": int(len(X)),
    }
