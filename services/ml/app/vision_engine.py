"""YOLO model registry and inference engine.

The registry persists model metadata in MariaDB and caches loaded ``YOLO``
instances in memory keyed by ``model_id``. API consumers select a model by
its id; the engine lazily loads the corresponding weights (e.g. your trained
``best.pt``) and runs inference, returning detections + annotated images.
"""
from __future__ import annotations

import io
import logging
import os
import threading
import time
import uuid
import concurrent.futures
from typing import Optional

import cv2
import numpy as np
from PIL import Image
from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal, VisionDetection, VisionModel
from app.metrics import (
    DETECTIONS_TOTAL,
    INFERENCE_LATENCY,
    INFERENCE_TOTAL,
    MODELS_LOADED,
)
from app.schemas import BoundingBox, DetectResult, Detection, ModelCreate
from app import storage

logger = logging.getLogger(__name__)
settings = get_settings()

# Dedicated pool for inference so a long-running predict can be time-boxed in a
# separate thread without blocking the event loop / other requests.
_INFER_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
    max_workers=2, thread_name_prefix="ml-infer"
)


class InferenceTimeout(Exception):
    """Raised when model.predict exceeds the configured wall-clock limit."""


class ModelRegistry:
    def __init__(self) -> None:
        self._loaded: dict[str, object] = {}
        self._lock = threading.Lock()

    # ─── Persistence helpers ──────────────────────────────────────────────
    @staticmethod
    def _row_to_dict(m: VisionModel) -> dict:
        return {
            "id": m.id,
            "name": m.name,
            "slug": m.slug,
            "description": m.description,
            "model_type": m.model_type,
            "framework": m.framework,
            "version": m.version,
            "file_path": m.file_path,
            "class_names": m.class_names,
            "input_size": m.input_size,
            "confidence_threshold": m.confidence_threshold,
            "iou_threshold": m.iou_threshold,
            "status": m.status,
            "is_default": m.is_default,
            "metadata": m.metadata_,
            "created_at": m.created_at,
            "updated_at": m.updated_at,
        }

    def list_models(self, status: Optional[str] = None) -> list[dict]:
        with SessionLocal() as session:
            stmt = select(VisionModel)
            if status:
                stmt = stmt.where(VisionModel.status == status)
            stmt = stmt.order_by(VisionModel.created_at.desc())
            rows = session.execute(stmt).scalars().all()
            return [self._row_to_dict(m) for m in rows]

    def get_model(self, model_id: str) -> Optional[dict]:
        with SessionLocal() as session:
            m = session.get(VisionModel, model_id)
            return self._row_to_dict(m) if m else None

    def get_model_by_slug(self, slug: str) -> Optional[dict]:
        with SessionLocal() as session:
            m = session.execute(
                select(VisionModel).where(VisionModel.slug == slug)
            ).scalars().first()
            return self._row_to_dict(m) if m else None

    def create_model(self, data) -> dict:
        model_id = str(uuid.uuid4())
        with SessionLocal() as session:
            # Ensure a unique slug if provided.
            if data.slug:
                existing = session.execute(
                    select(VisionModel).where(VisionModel.slug == data.slug)
                ).scalars().first()
                if existing:
                    raise ValueError(f"Slug '{data.slug}' already in use")
            row = VisionModel(
                id=model_id,
                name=data.name,
                slug=data.slug,
                description=data.description,
                model_type=data.model_type,
                framework=data.framework,
                version=data.version,
                file_path=data.file_path,
                class_names=data.class_names,
                input_size=data.input_size,
                confidence_threshold=data.confidence_threshold,
                iou_threshold=data.iou_threshold,
                is_default=data.is_default,
                metadata_=data.metadata,
                status="active" if data.is_default else "registered",
            )
            session.add(row)
            session.commit()
            if data.is_default:
                self._clear_other_defaults(session, model_id)
                row.status = "active"
                session.commit()
            return self._row_to_dict(row)

    def update_model(self, model_id: str, data) -> Optional[dict]:
        with SessionLocal() as session:
            m = session.get(VisionModel, model_id)
            if not m:
                return None
            for field, value in data.model_dump(exclude_unset=True).items():
                if field == "metadata":
                    field = "metadata_"
                if value is not None:
                    setattr(m, field, value)
            if data.is_default is True:
                self._clear_other_defaults(session, model_id)
                m.status = "active"
            session.commit()
            # Drop the cached instance so next inference reloads with new config.
            self._loaded.pop(model_id, None)
            return self._row_to_dict(m)

    def delete_model(self, model_id: str) -> bool:
        with SessionLocal() as session:
            m = session.get(VisionModel, model_id)
            if not m:
                return False
            session.delete(m)
            session.commit()
        self._loaded.pop(model_id, None)
        return True

    def set_active(self, model_id: str) -> Optional[dict]:
        with SessionLocal() as session:
            m = session.get(VisionModel, model_id)
            if not m:
                return None
            self._clear_other_defaults(session, model_id)
            m.is_default = True
            m.status = "active" if m.status != "failed" else "active"
            session.commit()
            self._loaded.pop(model_id, None)
            return self._row_to_dict(m)

    def _clear_other_defaults(self, session, keep_id: str) -> None:
        rows = session.execute(
            select(VisionModel).where(VisionModel.is_default.is_(True))
        ).scalars().all()
        for r in rows:
            if r.id != keep_id:
                r.is_default = False

    def default_model(self) -> Optional[dict]:
        with SessionLocal() as session:
            m = session.execute(
                select(VisionModel).where(VisionModel.is_default.is_(True))
            ).scalars().first()
            if m:
                return self._row_to_dict(m)
            if settings.auto_activate_first_model:
                m = session.execute(
                    select(VisionModel)
                    .where(VisionModel.status != "disabled")
                    .order_by(VisionModel.created_at.asc())
                ).scalars().first()
                if m:
                    m.is_default = True
                    m.status = "active" if m.status != "failed" else "active"
                    session.commit()
                    return self._row_to_dict(m)
        return None

    # ─── Weights resolution & loading ────────────────────────────────────
    def _within_models_dir(self, path: str) -> bool:
        """True only if `path` resolves to a location inside settings.models_dir.
        Prevents loading (pickle-deserializing) arbitrary filesystem paths."""
        try:
            base = os.path.realpath(settings.models_dir)
            target = os.path.realpath(path)
            return target == base or target.startswith(base + os.sep)
        except OSError:
            return False

    def _find_weights(self, meta: dict) -> Optional[str]:
        candidates: list[str] = []
        if meta.get("file_path"):
            # User-supplied path must stay within the models directory to avoid
            # loading untrusted weights from arbitrary locations.
            fp = meta["file_path"]
            if self._within_models_dir(fp):
                candidates.append(fp)
            else:
                logger.warning(
                    "Ignoring file_path outside models_dir for model %s: %s",
                    meta.get("id"), fp,
                )
        candidates.append(os.path.join(settings.models_dir, f"{meta['id']}.pt"))
        if meta.get("slug"):
            candidates.append(os.path.join(settings.models_dir, f"{meta['slug']}.pt"))
        candidates.append(
            os.path.join(settings.models_dir, settings.default_weights_filename)
        )
        for c in candidates:
            if c and os.path.exists(c) and self._within_models_dir(c):
                return c
        return None

    def load(self, model_id: str, meta: Optional[dict] = None) -> object:
        """Load (and cache) a YOLO model by id. Raises if not resolvable."""
        with self._lock:
            if model_id in self._loaded:
                return self._loaded[model_id]
        if meta is None:
            meta = self.get_model(model_id)
            if not meta:
                raise FileNotFoundError(f"Model '{model_id}' not found in registry")
        path = self._find_weights(meta)
        if not path:
            raise FileNotFoundError(
                f"No weights found for model '{model_id}'. Register weights via "
                f"POST /ml/models/{model_id}/weights or set file_path."
            )
        from ultralytics import YOLO

        logger.info("Loading YOLO weights for model %s from %s", model_id, path)
        model = YOLO(path)
        # If class names were not captured at registration, persist them.
        try:
            names = list(model.names.values())
            if not meta.get("class_names") and names:
                with SessionLocal() as session:
                    row = session.get(VisionModel, model_id)
                    if row:
                        row.class_names = names
                        session.commit()
                meta["class_names"] = names
        except Exception as exc:  # pragma: no cover
            logger.warning("Could not read class names: %s", exc)
        with self._lock:
            self._loaded[model_id] = model
            MODELS_LOADED.set(len(self._loaded))
        return model

    def resolve(self, model_id: Optional[str]) -> tuple[dict, object]:
        """Resolve (meta, loaded_model). Picks default when id is None."""
        if model_id:
            meta = self.get_model(model_id) or self.get_model_by_slug(model_id)
            if not meta:
                raise FileNotFoundError(f"Model '{model_id}' not found in registry")
            if meta["status"] == "disabled":
                raise ValueError(f"Model '{model_id}' is disabled")
        else:
            meta = self.default_model()
            if not meta:
                raise FileNotFoundError(
                    "No active model. Register a model and mark it default, or "
                    "pass model_id explicitly."
                )
        model = self.load(meta["id"], meta)
        return meta, model

    def upload_weights(self, model_id: str, filename: str, data: bytes) -> dict:
        """Persist uploaded weights into the models volume and link them."""
        os.makedirs(settings.models_dir, exist_ok=True)
        dest = os.path.join(settings.models_dir, f"{model_id}.pt")
        with open(dest, "wb") as f:
            f.write(data)
        with SessionLocal() as session:
            m = session.get(VisionModel, model_id)
            if not m:
                raise FileNotFoundError(f"Model '{model_id}' not found")
            m.file_path = dest
            if m.status in ("registered", "failed"):
                m.status = "active"
            session.commit()
            meta = self._row_to_dict(m)
        # Reload on next inference.
        self._loaded.pop(model_id, None)
        return meta

    def warmup(self) -> None:
        """Best-effort: load the default model at startup."""
        try:
            meta = self.default_model()
            if meta:
                self.load(meta["id"], meta)
                logger.info("Warmed up default model: %s", meta["id"])
        except Exception as exc:  # pragma: no cover
            logger.warning("Model warmup skipped: %s", exc)

    def ensure_seeded_model(
        self,
        weights_filename: str,
        model_id: str,
        slug: str,
        name: str,
        description: str,
    ) -> Optional[dict]:
        """Idempotently register a bundled weights file in the registry.

        Used to make a trained model (e.g. ``vision-aeroponik-model-root.pt``)
        available out of the box. If a model with the same id already exists it
        is left untouched unless the bundled weights file has changed (e.g.
        after a model update), in which case the file_path is refreshed. The
        seed only claims the default slot when no model is currently default,
        so it never clobbers an operator's choice.
        """
        existing = self.get_model(model_id)
        if existing:
            path = os.path.join(settings.models_dir, weights_filename)
            if os.path.exists(path) and self._within_models_dir(path):
                if existing.get("file_path") != path:
                    try:
                        with SessionLocal() as session:
                            row = session.get(VisionModel, model_id)
                            if row:
                                row.file_path = path
                                session.commit()
                                self._loaded.pop(model_id, None)
                                existing["file_path"] = path
                                logger.info("updated seeded model %s weights to %s", model_id, path)
                    except Exception as exc:
                        logger.warning("failed to update seeded model weights: %s", exc)
            return existing
        path = os.path.join(settings.models_dir, weights_filename)
        if not os.path.exists(path) or not self._within_models_dir(path):
            logger.warning("seed model weights not found: %s", path)
            return None
        is_default = self.default_model() is None
        data = ModelCreate(
            name=name,
            slug=slug,
            description=description,
            model_type="yolov8",
            framework="ultralytics",
            file_path=path,
            is_default=is_default,
        )
        try:
            meta = self.create_model(data)
            logger.info("seeded model %s (default=%s)", model_id, is_default)
            return meta
        except ValueError as exc:
            logger.warning("seed model registration skipped: %s", exc)
            return None

    def loaded_count(self) -> int:
        return len(self._loaded)


# Instantiate the singleton registry after the class is defined.
registry = ModelRegistry()


# ─── Inference ───────────────────────────────────────────────────────────────
def run_inference(
    image_bytes: bytes,
    model_id: Optional[str],
    source_type: str = "upload",
    source_ref: Optional[str] = None,
    conf: Optional[float] = None,
    iou: Optional[float] = None,
    imgsz: Optional[int] = None,
) -> DetectResult:
    """Run YOLO on a single image and persist + publish the result."""
    start = time.time()
    meta, model = registry.resolve(model_id)
    mid = meta["id"]

    conf = conf if conf is not None else meta["confidence_threshold"]
    iou = iou if iou is not None else meta["iou_threshold"]
    imgsz = imgsz if imgsz is not None else meta["input_size"]

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    def _predict():
        return model.predict(image, conf=conf, iou=iou, imgsz=imgsz, verbose=False)

    try:
        future = _INFER_EXECUTOR.submit(_predict)
        results = future.result(timeout=settings.inference_timeout_seconds)
    except concurrent.futures.TimeoutError as exc:
        logger.error("Inference timed out after %ss", settings.inference_timeout_seconds)
        raise InferenceTimeout(
            f"Inference exceeded the {settings.inference_timeout_seconds}s limit"
        ) from exc
    except InferenceTimeout:
        raise

    detections: list[Detection] = []
    names = model.names
    for r in results:
        for box in r.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            confidence = float(box.conf[0])
            cls = int(box.cls[0])
            name = names[cls] if isinstance(names, dict) else str(cls)
            detections.append(
                Detection(
                    class_id=cls,
                    class_name=str(name),
                    confidence=round(confidence, 4),
                    bbox=BoundingBox(
                        x1=int(x1), y1=int(y1), x2=int(x2), y2=int(y2)
                    ),
                )
            )

    # Annotated image.
    annotated_np = results[0].plot()
    annotated_rgb = cv2.cvtColor(annotated_np, cv2.COLOR_BGR2RGB)
    annotated_buf = io.BytesIO()
    Image.fromarray(annotated_rgb).save(annotated_buf, format="JPEG")
    annotated_bytes = annotated_buf.getvalue()

    classes = sorted({d.class_name for d in detections})
    confs = [d.confidence for d in detections]
    conf_min = min(confs) if confs else None
    conf_max = max(confs) if confs else None
    conf_avg = round(sum(confs) / len(confs), 4) if confs else None
    elapsed_ms = round((time.time() - start) * 1000, 2)

    root_lengths_cm: list[float] = []
    tuber_sizes_cm: list[float] = []
    for det in detections:
        name_lower = det.class_name.lower()
        width_px = det.bbox.x2 - det.bbox.x1
        height_px = det.bbox.y2 - det.bbox.y1
        if "akar" in name_lower or "root" in name_lower:
            root_lengths_cm.append(round(max(width_px, height_px) / settings.pixels_per_cm, 2))
        elif "umbi" in name_lower or "tuber" in name_lower:
            tuber_sizes_cm.append(round(min(width_px, height_px) / settings.pixels_per_cm, 2))
    root_length_cm = max(root_lengths_cm) if root_lengths_cm else None
    tuber_size_cm = max(tuber_sizes_cm) if tuber_sizes_cm else None

    original_url = annotated_url = None
    try:
        original_key = storage.safe_object_key(
            settings.minio_original_prefix, source_ref or "image.jpg"
        )
        original_url = storage.upload_image(
            settings.minio_ml_bucket, original_key, image_bytes
        )
        annotated_key = storage.safe_object_key(
            settings.minio_annotated_prefix, source_ref or "image.jpg"
        )
        annotated_metadata = {
            "root_length_cm": str(root_length_cm) if root_length_cm is not None else "",
            "tuber_size_cm": str(tuber_size_cm) if tuber_size_cm is not None else "",
            "condition": str(round(conf_avg, 4)) if conf_avg is not None else "",
            "confidence": str(round(conf_avg, 4)) if conf_avg is not None else "",
            "num_detections": str(len(detections)),
        }
        annotated_url = storage.upload_image_with_metadata(
            settings.minio_ml_bucket,
            annotated_key,
            annotated_bytes,
            annotated_metadata,
        )
    except Exception as exc:  # pragma: no cover - depends on live MinIO
        logger.warning("MinIO upload failed: %s", exc)

    result = DetectResult(
        detection_uid=str(uuid.uuid4()),
        model_id=mid,
        model_name=meta["name"],
        source_type=source_type,
        source_ref=source_ref,
        original_url=original_url,
        annotated_url=annotated_url,
        num_detections=len(detections),
        classes=classes,
        detections=detections,
        confidence_min=conf_min,
        confidence_max=conf_max,
        confidence_avg=conf_avg,
        root_length_cm=root_length_cm,
        tuber_size_cm=tuber_size_cm,
        condition=conf_avg,
        execution_time_ms=elapsed_ms,
        status="success",
    )

    _persist_and_publish(result, source_type, source_ref)
    INFERENCE_TOTAL.labels(model_id=mid, source_type=source_type, status="success").inc()
    DETECTIONS_TOTAL.labels(model_id=mid).inc(len(detections))
    INFERENCE_LATENCY.labels(model_id=mid).observe(elapsed_ms / 1000.0)
    return result


def _persist_and_publish(result: DetectResult, source_type: str, source_ref: Optional[str]) -> None:
    try:
        with SessionLocal() as session:
            row = VisionDetection(
                detection_uid=result.detection_uid,
                model_id=result.model_id,
                model_name=result.model_name,
                source_type=source_type,
                source_ref=source_ref,
                original_url=result.original_url,
                annotated_url=result.annotated_url,
                num_detections=result.num_detections,
                classes=result.classes,
                detections=[d.model_dump() for d in result.detections],
                confidence_min=result.confidence_min,
                confidence_max=result.confidence_max,
                confidence_avg=result.confidence_avg,
                execution_time_ms=result.execution_time_ms,
                status=result.status,
            )
            session.add(row)
            session.commit()
    except Exception as exc:  # pragma: no cover - depends on live DB
        logger.warning("Failed to persist detection: %s", exc)

    try:
        from app import messaging

        messaging.publish_detection_sync(result.model_dump())
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to publish detection event: %s", exc)
