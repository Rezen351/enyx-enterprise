"""Inference routes — run YOLO on images and return analysis output.

Clients select the model via ``model_id`` (or omit it to use the active
default). Images may be uploaded, supplied as base64, or pulled from a frame
already stored in the ``stream`` MinIO bucket.
"""
from __future__ import annotations

import base64
import binascii
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select

from app.database import SessionLocal, VisionDetection
from app.schemas import (
    DetectResponse,
    DetectResult,
    DetectionHistory,
    DetectionHistoryItem,
)
from app.security import require_read, require_write
from app.vision_engine import run_inference, InferenceTimeout
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ml", tags=["Inference"])


class DetectBase64(BaseModel):
    image_base64: str
    model_id: str | None = None
    conf: float | None = Field(None, ge=0.0, le=1.0)
    iou: float | None = Field(None, ge=0.0, le=1.0)
    imgsz: int | None = Field(None, gt=0)


class DetectFromStream(BaseModel):
    object_key: str
    model_id: str | None = None
    conf: float | None = Field(None, ge=0.0, le=1.0)
    iou: float | None = Field(None, ge=0.0, le=1.0)
    imgsz: int | None = Field(None, gt=0)


@router.post("/detect", response_model=DetectResponse, dependencies=[Depends(require_write)])
def detect_images(
    files: list[UploadFile] = File(...),
    model_id: str | None = Form(None),
    conf: float | None = Form(None),
    iou: float | None = Form(None),
    imgsz: int | None = Form(None),
):
    """Run detection on one or more uploaded images.

    Returns detections (class, confidence, bounding box) plus annotated image
    URLs in the ``ml`` MinIO bucket.
    """
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files provided")
    max_bytes = get_settings().max_upload_bytes
    results: list[DetectResult] = []
    for f in files:
        raw = f.file.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds max upload size of {get_settings().max_upload_mb} MB",
            )
        if not raw:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Empty file: {f.filename}",
            )
        try:
            result = run_inference(
                raw, model_id, source_type="upload",
                source_ref=f.filename, conf=conf, iou=iou, imgsz=imgsz,
            )
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        results.append(result)
    return DetectResponse(count=len(results), results=results)


@router.post("/detect/base64", response_model=DetectResponse,
             dependencies=[Depends(require_write)])
def detect_base64(payload: DetectBase64):
    """Run detection on a base64-encoded image (JSON body)."""
    try:
        raw = base64.b64decode(payload.image_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid base64 image"
        ) from exc
    if len(raw) > get_settings().max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image exceeds max upload size of {get_settings().max_upload_mb} MB",
        )
    try:
        result = run_inference(
            raw, payload.model_id, source_type="base64",
            source_ref="base64", conf=payload.conf, iou=payload.iou, imgsz=payload.imgsz,
        )
    except InferenceTimeout as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(exc)
        ) from exc
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return DetectResponse(count=1, results=[result])


@router.post("/detect/from-stream", response_model=DetectResponse,
             dependencies=[Depends(require_write)])
def detect_from_stream(payload: DetectFromStream):
    """Run detection on a frame already stored in the ``stream`` MinIO bucket."""
    from app import storage

    if not get_settings().minio_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MinIO is disabled (external mode); upload the image via "
            "/ml/detect or /ml/detect/base64 instead of referencing a stream key.",
        )

    try:
        raw = storage.download_object(storage_settings_stream_bucket(), payload.object_key)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Frame not found in stream bucket: {exc}",
        ) from exc
    try:
        result = run_inference(
            raw, payload.model_id, source_type="stream",
            source_ref=payload.object_key, conf=payload.conf, iou=payload.iou, imgsz=payload.imgsz,
        )
    except InferenceTimeout as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(exc)
        ) from exc
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return DetectResponse(count=1, results=[result])


def storage_settings_stream_bucket() -> str:
    from app.config import get_settings

    return get_settings().minio_stream_bucket


@router.get("/detections", response_model=DetectionHistory, dependencies=[Depends(require_read)])
def list_detections(
    model_id: str | None = None,
    source_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """Paginated history of inference runs."""
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    with SessionLocal() as session:
        stmt = select(VisionDetection)
        if model_id:
            stmt = stmt.where(VisionDetection.model_id == model_id)
        if source_type:
            stmt = stmt.where(VisionDetection.source_type == source_type)
        total = session.execute(
            select(func.count()).select_from(stmt.subquery())
        ).scalar_one()
        rows = session.execute(
            stmt.order_by(desc(VisionDetection.created_at)).limit(limit).offset(offset)
        ).scalars().all()
    items = [
        DetectionHistoryItem(
            id=r.id,
            detection_uid=r.detection_uid,
            model_id=r.model_id,
            model_name=r.model_name,
            source_type=r.source_type,
            source_ref=r.source_ref,
            original_url=r.original_url,
            annotated_url=r.annotated_url,
            num_detections=r.num_detections,
            classes=r.classes,
            confidence_min=r.confidence_min,
            confidence_max=r.confidence_max,
            confidence_avg=r.confidence_avg,
            execution_time_ms=r.execution_time_ms,
            status=r.status,
            created_at=r.created_at,
        )
        for r in rows
    ]
    return DetectionHistory(total=total, limit=limit, offset=offset, items=items)


@router.get("/detections/{detection_id}", response_model=DetectionHistoryItem, dependencies=[Depends(require_read)])
def get_detection(detection_id: int):
    with SessionLocal() as session:
        r = session.get(VisionDetection, detection_id)
        if not r:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
        return DetectionHistoryItem(
            id=r.id,
            detection_uid=r.detection_uid,
            model_id=r.model_id,
            model_name=r.model_name,
            source_type=r.source_type,
            source_ref=r.source_ref,
            original_url=r.original_url,
            annotated_url=r.annotated_url,
            num_detections=r.num_detections,
            classes=r.classes,
            confidence_min=r.confidence_min,
            confidence_max=r.confidence_max,
            confidence_avg=r.confidence_avg,
            execution_time_ms=r.execution_time_ms,
            status=r.status,
            created_at=r.created_at,
        )
