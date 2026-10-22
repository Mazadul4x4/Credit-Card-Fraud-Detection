from datetime import date, datetime, time, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from model_service import models
from model_service.features import DB_COLUMN, FEATURE_COLUMNS


def save_predictions(
    db: Session,
    transactions: list[dict],
    predictions: list[int],
    probabilities: list[float],
    source: str,
    model_version: str,
) -> list[models.Prediction]:
    """Save all predictions of one request in a single transaction."""
    rows = []
    for features, prediction, probability in zip(transactions, predictions, probabilities, strict=True):
        row = models.Prediction(
            source=source,
            model_version=model_version,
            transaction_id=features.get("transaction_id"),
            prediction=int(prediction),
            fraud_probability=float(probability),
            **{DB_COLUMN[name]: features[name] for name in FEATURE_COLUMNS},
        )
        rows.append(row)
    db.add_all(rows)
    db.commit()
    for row in rows:
        db.refresh(row)
    return rows


def get_past_predictions(
    db: Session,
    start_date: Optional[date],
    end_date: Optional[date],
    source: str,
    limit: int,
) -> list[models.Prediction]:
    query = db.query(models.Prediction)
    if start_date:
        query = query.filter(
            models.Prediction.created_at >= datetime.combine(start_date, time.min, timezone.utc)
        )
    if end_date:
        next_day = datetime.combine(end_date + timedelta(days=1), time.min, timezone.utc)
        query = query.filter(models.Prediction.created_at < next_day)
    if source != "all":
        query = query.filter(models.Prediction.source == source)
    return query.order_by(models.Prediction.id.desc()).limit(limit).all()


def get_prediction(db: Session, prediction_id: int) -> Optional[models.Prediction]:
    return db.get(models.Prediction, prediction_id)


def features_of(row: models.Prediction) -> dict:
    return {name: getattr(row, DB_COLUMN[name]) for name in FEATURE_COLUMNS}
