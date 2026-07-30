from fastapi import FastAPI
from pydantic import BaseModel


class PredictRequest(BaseModel):
    state: list[float]


class PredictResponse(BaseModel):
    D_mist: float
    interval_sec: float
    A_valve: float


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    vec_norm_loaded: bool
