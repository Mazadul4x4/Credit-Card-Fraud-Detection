from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TransactionFeatures(BaseModel):
    model_config = ConfigDict(extra="ignore")

    Time: float = Field(default=0.0, description="Time in seconds elapsed since first transaction")
    V1: float = 0.0
    V2: float = 0.0
    V3: float = 0.0
    V4: float = 0.0
    V5: float = 0.0
    V6: float = 0.0
    V7: float = 0.0
    V8: float = 0.0
    V9: float = 0.0
    V10: float = 0.0
    V11: float = 0.0
    V12: float = 0.0
    V13: float = 0.0
    V14: float = 0.0
    V15: float = 0.0
    V16: float = 0.0
    V17: float = 0.0
    V18: float = 0.0
    V19: float = 0.0
    V20: float = 0.0
    V21: float = 0.0
    V22: float = 0.0
    V23: float = 0.0
    V24: float = 0.0
    V25: float = 0.0
    V26: float = 0.0
    V27: float = 0.0
    V28: float = 0.0
    Amount: float = Field(default=0.0, description="Transaction amount")


class SinglePredictionRequest(BaseModel):
    transaction: TransactionFeatures
    source: str = Field(default="streamlit_form", description="Prediction trigger source")


class BatchPredictionRequest(BaseModel):
    transactions: list[TransactionFeatures] = Field(..., min_length=1)
    source: str = Field(default="Prediction DAG", description="Prediction trigger source")


class PredictionResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    predicted_class: int
    probability: float
    source: str
    model_version: str
    features: dict[str, Any] | None = None
    created_at: datetime


class BatchPredictionResponse(BaseModel):
    predictions: list[PredictionResult]
    total_predictions: int
    model_version: str


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_version: str


class IngestionStatsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    records_processed: int
    records_loaded: int
    records_failed: int
    criticality: str
    status: str
    created_at: datetime
