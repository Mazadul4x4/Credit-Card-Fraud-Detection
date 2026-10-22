from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy.orm import Session

from model_service import crud, schemas
from model_service.config import DEFAULT_MODEL_PATH, MODEL_VERSION
from model_service.database import get_db, init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

FEATURE_COLUMNS = ["Time"] + [f"V{i}" for i in range(1, 29)] + ["Amount"]


def resolve_model_file() -> Path:
    candidates = [
        Path(os.getenv("MODEL_PATH", "")),
        Path(DEFAULT_MODEL_PATH),
        Path("/app/models/fraud_model.joblib"),
        Path("/opt/airflow/models/fraud_model.joblib"),
        Path("models/fraud_model.joblib"),
        Path(__file__).resolve().parent.parent / "models" / "fraud_model.joblib",
    ]
    for c in candidates:
        if str(c) and c.exists() and c.is_file():
            return c

    # If no model found, raise with instructions
    raise FileNotFoundError(
        "Model file not found. Checked: " + ", ".join(str(c) for c in candidates if str(c))
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables and schema
    try:
        init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.warning(f"Database initialization warning: {e}")

    # Load machine learning model
    try:
        model_file = resolve_model_file()
        app.state.model = joblib.load(model_file)
        app.state.model_loaded = True
        logger.info(f"Model loaded successfully from {model_file}")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        app.state.model = None
        app.state.model_loaded = False

    yield

    logger.info("Application shutting down.")


app = FastAPI(
    title="Credit Card Fraud Detection API",
    version=MODEL_VERSION,
    lifespan=lifespan,
)


@app.get("/", status_code=status.HTTP_200_OK)
def home():
    return {
        "service": "Credit Card Fraud Detection API",
        "version": MODEL_VERSION,
        "docs_url": "/docs",
    }


@app.get("/health", status_code=status.HTTP_200_OK, response_model=schemas.HealthResponse)
def health():
    return schemas.HealthResponse(
        status="healthy" if app.state.model_loaded else "degraded",
        model_loaded=bool(app.state.model_loaded),
        model_version=MODEL_VERSION,
    )


@app.post(
    "/predict",
    status_code=status.HTTP_200_OK,
    response_model=schemas.BatchPredictionResponse,
)
def predict_batch(
    request: schemas.BatchPredictionRequest,
    db: Session = Depends(get_db),
):
    if not getattr(app.state, "model_loaded", False) or app.state.model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model is not loaded. Train and save model to models/fraud_model.joblib first.",
        )

    model = app.state.model
    transactions = request.transactions
    source = request.source

    # Convert request to pandas DataFrame
    dict_records = [t.model_dump() for t in transactions]
    df = pd.DataFrame(dict_records)

    # Ensure all feature columns exist in DataFrame
    for col in FEATURE_COLUMNS:
        if col not in df.columns:
            df[col] = 0.0
    df = df[FEATURE_COLUMNS]

    try:
        predicted_classes = model.predict(df)
        probabilities = model.predict_proba(df)[:, 1]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Inference error: {e}",
        )

    # Prepare database records
    records_to_create = []
    for pred_class, prob, feat_dict in zip(predicted_classes, probabilities, dict_records):
        records_to_create.append({
            "predicted_class": int(pred_class),
            "probability": float(prob),
            "source": source,
            "model_version": MODEL_VERSION,
            "features": feat_dict,
        })

    saved_instances = crud.create_batch_predictions(db=db, records=records_to_create)

    results = [
        schemas.PredictionResult(
            id=inst.id,
            predicted_class=inst.predicted_class,
            probability=inst.probability,
            source=inst.source,
            model_version=inst.model_version,
            features=inst.features,
            created_at=inst.created_at,
        )
        for inst in saved_instances
    ]

    return schemas.BatchPredictionResponse(
        predictions=results,
        total_predictions=len(results),
        model_version=MODEL_VERSION,
    )


@app.post(
    "/predict/single",
    status_code=status.HTTP_200_OK,
    response_model=schemas.PredictionResult,
)
def predict_single(
    request: schemas.SinglePredictionRequest,
    db: Session = Depends(get_db),
):
    batch_req = schemas.BatchPredictionRequest(
        transactions=[request.transaction],
        source=request.source,
    )
    batch_res = predict_batch(request=batch_req, db=db)
    return batch_res.predictions[0]


@app.get(
    "/predictions",
    status_code=status.HTTP_200_OK,
    response_model=list[schemas.PredictionResult],
)
def get_predictions(
    start_date: datetime | None = Query(default=None, description="Filter starting from UTC datetime"),
    end_date: datetime | None = Query(default=None, description="Filter up to UTC datetime"),
    source: str | None = Query(default=None, description="Filter by source name"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return crud.get_predictions(
        db=db,
        start_date=start_date,
        end_date=end_date,
        source=source,
        limit=limit,
        offset=offset,
    )


@app.get(
    "/stats",
    status_code=status.HTTP_200_OK,
    response_model=list[schemas.IngestionStatsResponse],
)
def get_stats(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return crud.get_ingestion_stats(db=db, limit=limit)
