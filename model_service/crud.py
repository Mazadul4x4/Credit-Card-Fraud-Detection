from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from model_service import models


def create_prediction(
    db: Session,
    predicted_class: int,
    probability: float,
    source: str,
    model_version: str,
    features: dict[str, Any] | None = None,
) -> models.Prediction:
    prediction = models.Prediction(
        predicted_class=predicted_class,
        probability=probability,
        source=source,
        model_version=model_version,
        features=features,
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    return prediction


def create_batch_predictions(
    db: Session,
    records: list[dict[str, Any]],
) -> list[models.Prediction]:
    instances = [
        models.Prediction(
            predicted_class=rec["predicted_class"],
            probability=rec["probability"],
            source=rec["source"],
            model_version=rec["model_version"],
            features=rec.get("features"),
        )
        for rec in records
    ]
    db.add_all(instances)
    db.commit()
    for inst in instances:
        db.refresh(inst)
    return instances


def get_predictions(
    db: Session,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    source: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[models.Prediction]:
    query = db.query(models.Prediction)

    if start_date is not None:
        query = query.filter(models.Prediction.created_at >= start_date)
    if end_date is not None:
        query = query.filter(models.Prediction.created_at <= end_date)
    if source is not None and source.strip() != "":
        query = query.filter(models.Prediction.source == source.strip())

    return query.order_by(models.Prediction.id.desc()).offset(offset).limit(limit).all()


def create_ingestion_stats(
    db: Session,
    filename: str,
    records_processed: int,
    records_loaded: int,
    records_failed: int,
    criticality: str,
    status: str,
    error_summary: dict[str, Any] | None = None,
) -> models.IngestionStats:
    stats = models.IngestionStats(
        filename=filename,
        records_processed=records_processed,
        records_loaded=records_loaded,
        records_failed=records_failed,
        criticality=criticality,
        status=status,
        error_summary=error_summary,
    )
    db.add(stats)
    db.commit()
    db.refresh(stats)
    return stats


def get_ingestion_stats(
    db: Session,
    limit: int = 50,
) -> list[models.IngestionStats]:
    return (
        db.query(models.IngestionStats)
        .order_by(models.IngestionStats.id.desc())
        .limit(limit)
        .all()
    )
