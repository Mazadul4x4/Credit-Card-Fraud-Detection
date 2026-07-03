from sqlalchemy.orm import Session

from model_service import models


def create_prediction(
    db: Session,
    predicted_class: int,
    probability: float,
    source: str,
    model_version: str,
):
    prediction = models.Prediction(
        predicted_class=predicted_class,
        probability=probability,
        source=source,
        model_version=model_version,
    )

    db.add(prediction)
    db.commit()
    db.refresh(prediction)

    return prediction


def get_predictions(db: Session):
    return (
        db.query(models.Prediction)
        .order_by(models.Prediction.id.desc())
        .all()
    )
    