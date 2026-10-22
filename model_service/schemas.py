from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

TimePeriod = Literal["night", "morning", "afternoon", "evening"]
Source = Literal["webapp", "scheduled"]


class Transaction(BaseModel):
    """Input features of one transaction. Pydantic rejects bad input with a 422."""

    model_config = ConfigDict(extra="ignore")  # e.g. the Class label in ingested files

    transaction_id: Optional[str] = Field(default=None, max_length=50)
    Time: float = Field(ge=0, description="seconds since the first transaction")
    V1: float
    V2: float
    V3: float
    V4: float
    V5: float
    V6: float
    V7: float
    V8: float
    V9: float
    V10: float
    V11: float
    V12: float
    V13: float
    V14: float
    V15: float
    V16: float
    V17: float
    V18: float
    V19: float
    V20: float
    V21: float
    V22: float
    V23: float
    V24: float
    V25: float
    V26: float
    V27: float
    V28: float
    Amount: float = Field(ge=0)
    time_period: TimePeriod


class PredictionRequest(BaseModel):
    transactions: list[Transaction] = Field(min_length=1, max_length=50_000)
    source: Source = "webapp"


class PredictionItem(BaseModel):
    id: int
    transaction_id: Optional[str]
    prediction: int
    label: Literal["fraud", "legit"]
    fraud_probability: float


class PredictionResponse(BaseModel):
    model_version: str
    source: Source
    count: int
    predictions: list[PredictionItem]


class PastPrediction(BaseModel):
    id: int
    created_at: datetime
    source: str
    model_version: str
    transaction_id: Optional[str]
    prediction: int
    fraud_probability: float
    features: dict[str, float | str]


class PastPredictionsResponse(BaseModel):
    count: int
    predictions: list[PastPrediction]


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_version: Optional[str]
