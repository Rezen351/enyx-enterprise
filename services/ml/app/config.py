"""Application configuration for the ML Service.

All values are sourced from environment variables (set by docker-compose)
with sensible development defaults so the service can also run standalone.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ─── Service ──────────────────────────────────────────────────────────
    app_name: str = "ml-api"
    environment: str = "development"
    host: str = "0.0.0.0"
    port: int = 8080
    log_level: str = "INFO"

    # ─── Database (MariaDB) ───────────────────────────────────────────────
    # SQLAlchemy URL, e.g. mysql+pymysql://app:app1234@mariadb-ml:3306/ml_db
    database_url: str = "mysql+pymysql://app:app1234@mariadb-ml:3306/ml_db"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_recycle: int = 1800

    # ─── Auth (shared JWT secret with Auth Service) ───────────────────────
    # No default: must be provided via environment. When empty, auth is only
    # bypassed in an explicit development environment (see security.py).
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    # Roles allowed to mutate (write) model registry & trigger inference config.
    write_roles: list[str] = ["admin", "operator"]
    # Roles allowed to read detections / models.
    read_roles: list[str] = ["admin", "operator", "viewer"]
    # Allowed CORS origins (browser). Wildcard with credentials is unsafe.
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    # ─── Model registry ───────────────────────────────────────────────────
    # Directory where uploaded / registered weights (.pt) live inside the container.
    models_dir: str = "/app/models"
    # Filename searched when a model is registered without an explicit file_path
    # (classic "best.pt" produced by YOLO training).
    default_weights_filename: str = "best.pt"
    # Auto-load & mark active the first registered model at startup if none active.
    auto_activate_first_model: bool = True

    # ─── Inference defaults ───────────────────────────────────────────────
    default_conf_threshold: float = 0.25
    default_iou_threshold: float = 0.45
    default_input_size: int = 640
    max_upload_mb: int = 16
    allowed_image_extensions: list[str] = ["jpg", "jpeg", "png", "bmp", "webp"]
    # Hard wall-clock cap on a single inference call so a malicious/heavy
    # payload cannot hang the worker indefinitely (security checklist).
    inference_timeout_seconds: int = 30

    # ─── MinIO (shared instance, bucket ml) ───────────────────────────────
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin123"
    minio_use_ssl: bool = False
    minio_ml_bucket: str = "mlbucket"
    minio_stream_bucket: str = "stream"
    minio_result_bucket: str = "mlbucket"
    # Prefix layout inside the ml bucket.
    minio_original_prefix: str = "original"
    minio_annotated_prefix: str = "detected"
    # Public base URL used to build shareable links (Kong / MinIO console).
    minio_public_url: str = "http://localhost:9000"

    # ─── Vision calibration ────────────────────────────────────────────────
    # Simple pixels-to-centimetres factor. 1.0 means 1 px == 1 cm.
    pixels_per_cm: float = 10.0

    # ─── NATS (events) ────────────────────────────────────────────────────
    nats_url: str = "nats://nats:4222"
    nats_user: Optional[str] = None
    nats_password: Optional[str] = None
    nats_subject_detection: str = "detection.result"
    nats_enabled: bool = True

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
