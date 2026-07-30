from pydantic import BaseModel, Field
from typing import Optional, List


class PredictRequest(BaseModel):
    state: List[float] = Field(..., min_length=10, max_length=10, description="10D observation vector")


class PredictResponse(BaseModel):
    D_mist: float
    interval_sec: float
    A_valve: float


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    vec_norm_loaded: bool


class TelemetryMessage(BaseModel):
    node_id: str
    timestamp: str
    state: List[float]
