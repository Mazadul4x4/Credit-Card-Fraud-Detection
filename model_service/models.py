from sqlalchemy import Column, Integer, Float, String, DateTime
from datetime import datetime

from model_service.database import Base

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    predicted_class = Column(Integer)
    probability = Column(Float)
    source = Column(String)
    model_version = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)