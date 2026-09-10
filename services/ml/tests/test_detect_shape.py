"""Tests for the ``/ml/detect`` response *shape* (``run_inference``).

These run WITHOUT torch/ultralytics: the heavy model load is stubbed so the
real ``run_inference`` flow (resolve -> predict -> annotate -> persist ->
publish) executes against a fake model that returns a deterministic result.
The test asserts the produced ``DetectResult`` matches the documented schema
(Analytics/Stream consumers rely on this shape).
"""
from __future__ import annotations

import sys
import types

import pytest


def _fake_settings():
    s = types.SimpleNamespace()
    s.models_dir = "/tmp/fake_models"
    s.default_weights_filename = "best.pt"
    s.auto_activate_first_model = True
    s.inference_timeout_seconds = 30
    s.minio_original_prefix = "original"
    s.minio_annotated_prefix = "detected"
    s.minio_ml_bucket = "mlbucket"
    s.minio_public_url = "http://minio"
    s.pixels_per_cm = 10.0
    s.minio_enabled = True
    return s


sys.path.insert(0, __file__.rsplit("/", 1)[0])
from _fakes import install, reset_store  # noqa: E402

_storage, _ve = install(_fake_settings)
run_inference = _ve.run_inference


class _FakeBox:
    def __init__(self, x1, y1, x2, y2, conf, cls):
        import numpy as np
        self.xyxy = [np.array([x1, y1, x2, y2])]
        self.conf = [conf]
        self.cls = [cls]


class _FakeResult:
    def __init__(self):
        self.boxes = [
            _FakeBox(10, 20, 30, 40, 0.9, 0),
            _FakeBox(50, 60, 70, 80, 0.5, 1),
        ]
        self.names = {0: "leaf", 1: "fruit"}

    def plot(self):
        import numpy as np
        return np.zeros((100, 100, 3), dtype="uint8")


class _FakeModel:
    names = {0: "leaf", 1: "fruit"}

    def predict(self, image, **kwargs):
        return [_FakeResult()]


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    reset_store()
    _ve.registry._loaded.clear()

    fake_meta = {
        "id": "test-model",
        "name": "TestModel",
        "confidence_threshold": 0.25,
        "iou_threshold": 0.45,
        "input_size": 640,
    }
    monkeypatch.setattr(_ve.registry, "resolve", lambda model_id: (fake_meta, _FakeModel()))
    # Stub the two MinIO writers so run_inference completes offline. ML Service
    # is REST-only (no NATS/messaging dependency); in default (minio_enabled)
    # mode the annotated image is uploaded, not inlined, so annotated_base64
    # stays None and the URLs are populated by these stubs.
    monkeypatch.setattr(_storage, "upload_image", lambda *a, **k: "http://minio/fake")
    monkeypatch.setattr(_storage, "upload_image_with_metadata", lambda *a, **k: "http://minio/fake")
    yield
    reset_store()


def _valid_jpeg() -> bytes:
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (120, 80, 40)).save(buf, format="JPEG")
    return buf.getvalue()


def test_run_inference_shape():
    result = run_inference(_valid_jpeg(), None, source_type="upload", source_ref="x.jpg")
    # Top-level envelope fields.
    assert result.detection_uid
    assert result.model_id == "test-model"
    assert result.model_name == "TestModel"
    assert result.source_type == "upload"
    assert result.status == "success"
    assert result.num_detections == 2
    # URLs populated by the stubbed upload_image.
    assert result.original_url == "http://minio/fake"
    assert result.annotated_url == "http://minio/fake"
    # Default (minio_enabled=True) mode uploads the annotated image, so it is
    # NOT inlined as base64.
    assert result.annotated_base64 is None


def test_run_inference_external_mode_inlines_base64(monkeypatch):
    """When MINIO_ENABLED=false the annotated image is returned inline."""
    import app.vision_engine as _ve

    monkeypatch.setattr(_ve.registry, "resolve", lambda model_id: ({"id": "m", "name": "M", "confidence_threshold": 0.25, "iou_threshold": 0.45, "input_size": 640}, _FakeModel()))
    monkeypatch.setattr(_storage, "upload_image", lambda *a, **k: "http://minio/fake")
    monkeypatch.setattr(_storage, "upload_image_with_metadata", lambda *a, **k: "http://minio/fake")
    monkeypatch.setattr(_ve.settings, "minio_enabled", False)
    result = run_inference(_valid_jpeg(), None, source_type="upload", source_ref="x.jpg")
    assert result.original_url is None
    assert result.annotated_url is None
    assert isinstance(result.annotated_base64, str) and result.annotated_base64
    # Confidence stats derived from the two fake boxes.
    assert result.confidence_min == 0.5
    assert result.confidence_max == 0.9
    assert result.confidence_avg == pytest.approx(0.7, rel=1e-3)
    # Classes sorted & unique.
    assert result.classes == ["fruit", "leaf"]
    # Detections carry the documented bbox shape.
    det = result.detections[0]
    assert det.bbox.x1 == 10 and det.bbox.x2 == 30
    assert det.class_name in ("leaf", "fruit")
    assert 0.0 <= det.confidence <= 1.0


def test_run_inference_no_detections_empty_image():
    # A fake model with zero boxes -> empty detections, None confidences.
    class _EmptyModel:
        names = {}

        def predict(self, image, **kwargs):
            class _R:
                boxes = []
                names = {}
                def plot(self):
                    import numpy as np
                    return np.zeros((10, 10, 3), dtype="uint8")
            return [_R()]

    _ve.registry.resolve = lambda model_id: ({"id": "m", "name": "M", "confidence_threshold": 0.25, "iou_threshold": 0.45, "input_size": 640}, _EmptyModel())
    result = run_inference(_valid_jpeg(), None)
    assert result.num_detections == 0
    assert result.confidence_min is None
    assert result.confidence_max is None
    assert result.confidence_avg is None
    assert result.detections == []
