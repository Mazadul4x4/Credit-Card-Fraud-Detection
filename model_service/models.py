from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String

from model_service.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Prediction(Base):
    """One row per predicted transaction: input features + prediction.
    Features are stored so the drift dashboard (Defense 2) can compare serving data
    with the training data; model_version distinguishes before/after retraining."""

    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    source = Column(String(20), nullable=False, index=True)  # "webapp" or "scheduled"
    model_version = Column(String(100), nullable=False)
    transaction_id = Column(String(50), nullable=True)
    prediction = Column(Integer, nullable=False)  # 1 = fraud, 0 = legit
    fraud_probability = Column(Float, nullable=False)

    # input features
    txn_time = Column(Float, nullable=False)
    v1 = Column(Float, nullable=False)
    v2 = Column(Float, nullable=False)
    v3 = Column(Float, nullable=False)
    v4 = Column(Float, nullable=False)
    v5 = Column(Float, nullable=False)
    v6 = Column(Float, nullable=False)
    v7 = Column(Float, nullable=False)
    v8 = Column(Float, nullable=False)
    v9 = Column(Float, nullable=False)
    v10 = Column(Float, nullable=False)
    v11 = Column(Float, nullable=False)
    v12 = Column(Float, nullable=False)
    v13 = Column(Float, nullable=False)
    v14 = Column(Float, nullable=False)
    v15 = Column(Float, nullable=False)
    v16 = Column(Float, nullable=False)
    v17 = Column(Float, nullable=False)
    v18 = Column(Float, nullable=False)
    v19 = Column(Float, nullable=False)
    v20 = Column(Float, nullable=False)
    v21 = Column(Float, nullable=False)
    v22 = Column(Float, nullable=False)
    v23 = Column(Float, nullable=False)
    v24 = Column(Float, nullable=False)
    v25 = Column(Float, nullable=False)
    v26 = Column(Float, nullable=False)
    v27 = Column(Float, nullable=False)
    v28 = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)
    time_period = Column(String(20), nullable=False)


class IngestionStats(Base):
    """One row per ingested file, written by the ingestion DAG (save_statistics task).
    Error columns = number of rows affected by each error category, which is what the
    data quality dashboard (Defense 2) plots over time."""

    __tablename__ = "ingestion_stats"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    total_rows = Column(Integer, nullable=False)
    valid_rows = Column(Integer, nullable=False)
    invalid_rows = Column(Integer, nullable=False)
    invalid_ratio = Column(Float, nullable=False)
    criticality = Column(String(10), nullable=False)  # NONE / LOW / MEDIUM / HIGH
    missing_columns = Column(String(500), nullable=True)
    completeness_errors = Column(Integer, nullable=False, default=0)
    validity_errors = Column(Integer, nullable=False, default=0)
    consistency_errors = Column(Integer, nullable=False, default=0)
    schema_errors = Column(Integer, nullable=False, default=0)
    type_errors = Column(Integer, nullable=False, default=0)
    duplicate_errors = Column(Integer, nullable=False, default=0)
    outlier_errors = Column(Integer, nullable=False, default=0)
    format_errors = Column(Integer, nullable=False, default=0)
    report_path = Column(String(500), nullable=True)
