import pandas as pd
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
import joblib

from model_service.database import Base, engine, get_db
from model_service import models, schemas, crud
from model_service.config import MODEL_VERSION

Base.metadata.create_all(bind=engine)

MODEL_PATH = Path("/opt/airflow/models/fraud_model.joblib")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model file not found: {MODEL_PATH}")

    app.state.model = joblib.load(MODEL_PATH)
    print(f"Model loaded from {MODEL_PATH}")
    yield


app = FastAPI(
    title="Credit Card Fraud Detection API",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
def home():
    return {"message": "Credit Card Fraud Detection API is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/predict")
def predict(
    request: schemas.BatchPredictionRequest,
    db: Session = Depends(get_db),
):
    model = app.state.model

    # Convert request to DataFrame
    transactions = request.transactions
    df = pd.DataFrame(
        [transaction.model_dump() for transaction in transactions]
    )

    print(f"Received {len(df)} transactions")

    # Make predictions
    predicted_classes = model.predict(df)
    probabilities = model.predict_proba(df)[:, 1]

    results = []

    # Save predictions to database
    for predicted_class, probability in zip(predicted_classes, probabilities):
        prediction = crud.create_prediction(
            db=db,
            predicted_class=int(predicted_class),
            probability=float(probability),
            source="Prediction DAG",
            model_version=MODEL_VERSION,
        )

        results.append(
            {
                "id": prediction.id,
                "predicted_class": prediction.predicted_class,
                "probability": prediction.probability,
                "source": prediction.source,
                "model_version": prediction.model_version,
            }
        )

    return {
        "predictions": results,
        "total_predictions": len(results),
    }