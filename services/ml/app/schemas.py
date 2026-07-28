"""Request / response schemas for the ML / Vision API."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator


# ─── Model registry ─────────────────────────────────────────────────────────
class ModelCreate(BaseModel):
    """Register a new model in the registry.

    Provide either an explicit ``file_path`` (weights already present in the
    mounted models volume, e.g. ``/app/models/best.pt``) or upload the weights
    separately via ``POST /ml/models/{id}/weights``.
    """

    name: str = Field(..., min_length=1, max_length=255)
    slug: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    model_type: str = "yolov8"
    framework: str = "ultralytics"
    version: Optional[str] = None
    file_path: Optional[str] = None
    class_names: Optional[list[str]] = None
    input_size: int = 640
    confidence_threshold: float = 0.25
    iou_threshold: float = 0.45
    is_default: bool = False
    metadata: Optional[dict[str, Any]] = None


class ModelUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    model_type: Optional[str] = None
    framework: Optional[str] = None
    version: Optional[str] = None
    file_path: Optional[str] = None
    class_names: Optional[list[str]] = None
    input_size: Optional[int] = None
    confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    iou_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    is_default: Optional[bool] = None
    metadata: Optional[dict[str, Any]] = None
    status: Optional[str] = Field(
        None, description="registered | active | failed | disabled"
    )

    @model_validator(mode="after")
    def _non_empty(self) -> "ModelUpdate":
        # Allow partial updates; pydantic handles missing fields.
        return self


class ModelOut(BaseModel):
    id: str
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    model_type: str = "yolov8"
    framework: str = "ultralytics"
    version: Optional[str] = None
    file_path: Optional[str] = None
    class_names: Optional[list[str]] = None
    input_size: int = 640
    confidence_threshold: float = 0.25
    iou_threshold: float = 0.45
    status: str = "registered"
    is_default: bool = False
    metadata: Optional[dict[str, Any]] = None
    loaded: bool = False
    num_classes: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ModelList(BaseModel):
    total: int
    items: list[ModelOut]


# ─── Detection (inference) ──────────────────────────────────────────────────
class BoundingBox(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int


class Detection(BaseModel):
    class_id: int
    class_name: str
    confidence: float
    bbox: BoundingBox


class DetectResult(BaseModel):
    detection_uid: str
    model_id: str
    model_name: str
    source_type: str
    source_ref: Optional[str] = None
    original_url: Optional[str] = None
    annotated_url: Optional[str] = None
    num_detections: int
    classes: list[str] = []
    detections: list[Detection] = []
    confidence_min: Optional[float] = None
    confidence_max: Optional[float] = None
    confidence_avg: Optional[float] = None
    root_length_cm: Optional[float] = None
    tuber_size_cm: Optional[float] = None
    condition: Optional[float] = None
    execution_time_ms: float
    status: str = "success"


class DetectResponse(BaseModel):
    count: int
    results: list[DetectResult]


class DetectionHistoryItem(BaseModel):
    id: int
    detection_uid: Optional[str] = None
    model_id: Optional[str] = None
    model_name: Optional[str] = None
    source_type: str
    source_ref: Optional[str] = None
    original_url: Optional[str] = None
    annotated_url: Optional[str] = None
    num_detections: int
    classes: Optional[list[str]] = None
    confidence_min: Optional[float] = None
    confidence_max: Optional[float] = None
    confidence_avg: Optional[float] = None
    execution_time_ms: Optional[float] = None
    status: str
    created_at: Optional[datetime] = None


class DetectionHistory(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[DetectionHistoryItem]


# ─── Generic ────────────────────────────────────────────────────────────────
class Message(BaseModel):
    message: str
    detail: Optional[Any] = None


class HealthStatus(BaseModel):
    status: str
    service: str
    version: str
    models_loaded: int
    default_model: Optional[str] = None
