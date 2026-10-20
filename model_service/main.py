import logging
from contextlib import asynccontextmanager
from datetime import date
from typing import Literal, Optional

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from model_service import crud, schemas
from model_service.config import MODEL_METADATA_PATH, MODEL_PATH
from model_service.database import Base, engine, get_db
from model_service.features import FEATURE_COLUMNS
from model_service.ml import load_model_from_file

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs ONCE at startup: create tables and load the model (not on every request)
    Base.metadata.create_all(bind=engine)
    app.state.model, app.state.model_version = load_model_from_file(MODEL_PATH, MODEL_METADATA_PATH)
    yield


app = FastAPI(
    title="Credit Card Fraud Detection API",
    version="1.0.0",
    lifespan=lifespan,
)


def get_model(request: Request):
    """Dependency: the loaded model, or 503 if no model is available."""
    if request.app.state.model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No model loaded. Train one with src/train.py and restart the API.",
        )
    return request.app.state.model


@app.get("/health", response_model=schemas.HealthResponse)
def health(request: Request):
    return schemas.HealthResponse(
        status="ok",
        model_loaded=request.app.state.model is not None,
        model_version=request.app.state.model_version,
    )


@app.post("/predict", response_model=schemas.PredictionResponse)
def predict(
    body: schemas.PredictionRequest,
    request: Request,
    db: Session = Depends(get_db),
    model=Depends(get_model),
):
    """Batch prediction: one call for one or many transactions (webapp and Airflow)."""
    transactions = [t.model_dump() for t in body.transactions]
    features = pd.DataFrame(transactions)[FEATURE_COLUMNS]

    try:
        predictions = model.predict(features).tolist()
        probabilities = model.predict_proba(features)[:, 1].tolist()
    except Exception as exc:
        logger.exception("Prediction failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {exc}",
        ) from exc

    version = request.app.state.model_version
    rows = crud.save_predictions(db, transactions, predictions, probabilities, body.source, version)
    return schemas.PredictionResponse(
        model_version=version,
        source=body.source,
        count=len(rows),
        predictions=[
            schemas.PredictionItem(
                id=row.id,
                transaction_id=row.transaction_id,
                prediction=row.prediction,
                label="fraud" if row.prediction == 1 else "legit",
                fraud_probability=round(row.fraud_probability, 4),
            )
            for row in rows
        ],
    )


@app.get("/past-predictions", response_model=schemas.PastPredictionsResponse)
def past_predictions(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    source: Literal["all", "webapp", "scheduled"] = "all",
    limit: int = Query(default=1000, ge=1, le=10_000),
    db: Session = Depends(get_db),
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before or equal to end_date",
        )
    rows = crud.get_past_predictions(db, start_date, end_date, source, limit)
    return schemas.PastPredictionsResponse(count=len(rows), predictions=[_to_past(r) for r in rows])


@app.get("/past-predictions/{prediction_id}", response_model=schemas.PastPrediction)
def past_prediction(prediction_id: int, db: Session = Depends(get_db)):
    row = crud.get_prediction(db, prediction_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prediction not found")
    return _to_past(row)


def _to_past(row) -> schemas.PastPrediction:
    return schemas.PastPrediction(
        id=row.id,
        created_at=row.created_at,
        source=row.source,
        model_version=row.model_version,
        transaction_id=row.transaction_id,
        prediction=row.prediction,
        fraud_probability=row.fraud_probability,
        features=crud.features_of(row),
    )
