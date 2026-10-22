"""Train the initial fraud detection model (Defense 1: the API loads it from a file).

Writes:
    models/fraud_model.joblib    sklearn Pipeline (preprocessing + RandomForest)
    models/model_metadata.json   model version + test metrics (shown by the API)

Usage (run inside Docker so the scikit-learn version matches the API):
    docker compose run --rm tools python src/train.py
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
import sklearn

from fraud_pipeline.model import build_pipeline, evaluate, split_xy


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--train", default="data/training/train.csv")
    parser.add_argument("--test", default="data/training/test.csv")
    parser.add_argument("--model-dir", default="models")
    args = parser.parse_args()

    train_df = pd.read_csv(args.train)
    test_df = pd.read_csv(args.test)
    print(f"Training on {len(train_df)} rows ({int(train_df['Class'].sum())} fraud)")

    model = build_pipeline()
    model.fit(*split_xy(train_df))
    metrics = evaluate(model, test_df)

    version = "file-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    model_dir = Path(args.model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_dir / "fraud_model.joblib")
    metadata = {
        "model_version": version,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "sklearn_version": sklearn.__version__,
        "train_rows": len(train_df),
        "metrics": metrics,
    }
    (model_dir / "model_metadata.json").write_text(json.dumps(metadata, indent=2))
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
