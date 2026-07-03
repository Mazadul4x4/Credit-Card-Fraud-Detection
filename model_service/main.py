from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from model_service.database import Base, engine, get_db
from model_service import models, schemas, crud
from model_service.config import MODEL_VERSION

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Credit Card Fraud Detection API",
    version="1.0.0"
)


@app.get("/")
def home():
    return {"message": "Credit Card Fraud Detection API is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/predict", response_model=schemas.PredictionResponse)
def predict(
    request: schemas.PredictionRequest,
    db: Session = Depends(get_db),
):
    prediction = crud.create_prediction(
        db=db,
        predicted_class=request.predicted_class,
        probability=request.probability,
        source=request.source,
        model_version=MODEL_VERSION,
    )

    return prediction

@app.get("/predictions", response_model=list[schemas.PredictionResponse])
def get_predictions(
    db: Session = Depends(get_db),
):
    return crud.get_predictions(db)