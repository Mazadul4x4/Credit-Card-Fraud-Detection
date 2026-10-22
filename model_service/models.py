from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String

from model_service.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    predicted_class = Column(Integer, nullable=False)
    probability = Column(Float, nullable=False)
    source = Column(String, default="api")
    model_version = Column(String, default="1.0.0")
    features = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utcnow)


class IngestionStats(Base):
    __tablename__ = "ingestion_stats"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    records_processed = Column(Integer, default=0)
    records_loaded = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    criticality = Column(String, default="NONE")
    error_summary = Column(JSON, nullable=True)
    status = Column(String, default="SUCCESS")
    created_at = Column(DateTime, default=utcnow)
