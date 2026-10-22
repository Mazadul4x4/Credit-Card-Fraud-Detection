from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd


def test_model_artifact_exists_and_predicts():
    model_path = Path("models/fraud_model.joblib")
    assert model_path.exists(), "Model file models/fraud_model.joblib must exist"

    pipeline = joblib.load(model_path)
    assert hasattr(pipeline, "predict")
    assert hasattr(pipeline, "predict_proba")

    # Construct test sample dataframe
    sample = {"Time": [100.0, 200.0], "Amount": [50.0, 999.0]}
    for i in range(1, 29):
        sample[f"V{i}"] = [0.1, -0.2]
    df = pd.DataFrame(sample)

    preds = pipeline.predict(df)
    probs = pipeline.predict_proba(df)[:, 1]

    assert len(preds) == 2
    assert all(p in [0, 1] for p in preds)
    assert len(probs) == 2
    assert all(0.0 <= pr <= 1.0 for pr in probs)
