# src/schemas/anomaly.py

from pydantic import BaseModel
from datetime import datetime


class AnomalyResponse(BaseModel):
    id: int
    line_id: str
    timestamp: datetime
    status: str
    score: float

    model_config = {"from_attributes": True}


class AnomalyStatusUpdate(BaseModel):
    status: str
