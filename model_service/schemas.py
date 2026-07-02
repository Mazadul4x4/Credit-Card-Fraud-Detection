from pydantic import BaseModel

class PredictionRequest(BaseModel):
    predicted_class: int
    probability: float
    source: str


class PredictionResponse(BaseModel):
    id: int
    predicted_class: int
    probability: float
    source: str
    model_version: str

    class Config:
        from_attributes = True