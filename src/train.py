"""Train credit card fraud detection model.

Produces a scikit-learn pipeline saved to models/fraud_model.joblib along with
training metadata in models/model_metadata.json.
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

FEATURE_COLUMNS = ["Time"] + [f"V{i}" for i in range(1, 29)] + ["Amount"]
MODEL_VERSION = "1.0.0"


def train_model(
    data_path: str | Path = "data/raw_data/creditcard.csv",
    output_dir: str | Path = "models",
    model_version: str = MODEL_VERSION,
) -> Path:
    data_file = Path(data_path)
    if not data_file.exists():
        # Fallback to train.csv
        alt = Path("data/raw_data/train.csv")
        if alt.exists():
            data_file = alt
        else:
            raise FileNotFoundError(f"Cannot find training data at {data_file} or {alt}")

    logger.info(f"Loading data from {data_file}...")
    df = pd.read_csv(data_file)
    logger.info(f"Loaded {len(df)} rows. Fraud count: {(df['Class'] == 1).sum()}")

    # Ensure required columns
    missing = set(FEATURE_COLUMNS + ["Class"]) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in dataset: {missing}")

    X = df[FEATURE_COLUMNS]
    y = df["Class"]

    # Stratified split
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    # Build preprocessing + classification pipeline
    preprocessor = ColumnTransformer(
        transformers=[
            ("scaler", StandardScaler(), ["Amount", "Time"]),
        ],
        remainder="passthrough",
    )

    pipeline = Pipeline([
        ("preprocessor", preprocessor),
        (
            "classifier",
            RandomForestClassifier(
                n_estimators=100,
                max_depth=12,
                class_weight="balanced",
                random_state=42,
                n_jobs=-1,
            ),
        ),
    ])

    logger.info("Training model pipeline...")
    pipeline.fit(X_train, y_train)

    # Evaluation
    logger.info("Evaluating model on test split...")
    y_pred = pipeline.predict(X_test)
    y_prob = pipeline.predict_proba(X_test)[:, 1]

    roc_auc = float(roc_auc_score(y_test, y_prob))
    report = classification_report(y_test, y_pred, output_dict=True)

    logger.info(f"Model ROC-AUC Score: {roc_auc:.4f}")
    logger.info(
        f"Fraud Precision: {report['1']['precision']:.4f}, Recall: {report['1']['recall']:.4f}"
    )

    # Save artifact
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    model_path = out_dir / "fraud_model.joblib"
    joblib.dump(pipeline, model_path)
    logger.info(f"Saved model artifact to {model_path}")

    metadata = {
        "model_version": model_version,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "roc_auc": roc_auc,
        "classification_report": report,
        "feature_columns": FEATURE_COLUMNS,
    }

    metadata_path = out_dir / "model_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"Saved model metadata to {metadata_path}")

    return model_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train credit card fraud model")
    parser.add_argument("--data", default="data/raw_data/creditcard.csv", help="Dataset path")
    parser.add_argument("--output-dir", default="models", help="Output directory for model")
    parser.add_argument("--version", default=MODEL_VERSION, help="Model version")
    args = parser.parse_args()

    train_model(data_path=args.data, output_dir=args.output_dir, model_version=args.version)
