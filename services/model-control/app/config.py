"""ppo-control service configuration."""

from __future__ import annotations

import os
from typing import Optional


class Settings:
    APP_NAME: str = "model-control"
    PORT: int = int(os.getenv("PORT", "8081"))

    # Target device
    NODE_ID: str = os.getenv("NODE_ID", "node-00")
    OUTPUT_NAME: str = os.getenv("OUTPUT_NAME", "load1")
    VALVE_OUTPUT_NAME: str = os.getenv("VALVE_OUTPUT_NAME", "load2")
    MODULE_ID: str = os.getenv("MODULE_ID", "ee8831ff-c2dd-45c9-abb6-fb3def8fd513")

    # Schedule
    PUMP_SCHEDULE_ID: str = os.getenv("PUMP_SCHEDULE_ID", "35461f5f-d6ef-4c30-abfc-9eb680b5dfe7")
    PREDICTION_INTERVAL_SEC: int = int(os.getenv("PREDICTION_INTERVAL_SEC", "3600"))

    # URLs
    CONTROL_URL: str = os.getenv("CONTROL_URL", "http://control:8080")
    AUTH_URL: str = os.getenv("AUTH_URL", "http://auth:8080")
    MODEL_CONTROLLER_URL: str = os.getenv("MODEL_CONTROLLER_URL", os.getenv("PPO_CONTROLLER_URL", "http://model-controller:8080"))
    PPO_CONTROLLER_URL: str = MODEL_CONTROLLER_URL
    NATS_URL: str = os.getenv("NATS_URL", "nats://nats:4222")

    # MinIO
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "minio:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
    MINIO_USE_SSL: bool = os.getenv("MINIO_USE_SSL", "false").lower() == "true"
    MINIO_BUCKET: str = os.getenv("MINIO_BUCKET", "ml")
    MINIO_PREFIX: str = os.getenv("MINIO_PREFIX", "results")

    # Auth
    CONTROL_USER: str = os.getenv("CONTROL_USER", "admin")
    CONTROL_PASS: str = os.getenv("CONTROL_PASS", "admin1234")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "super-secret-key")

    # Fallback defaults
    DEFAULT_L_ROOT: float = 10.0
    DEFAULT_U_STATUS: float = 0.5
    DEFAULT_T_IN: float = 25.0
    DEFAULT_H_IN: float = 70.0
    DEFAULT_T_OUT: float = 28.0
    DEFAULT_H_OUT: float = 65.0
    DEFAULT_EC: float = 1.5
    DEFAULT_PH: float = 6.5
    DEFAULT_T_NUT: float = 25.0
    DEFAULT_I_DAY: float = 0.5

    # Condition score mapping
    CONDITION_SCORE_HEALTHY: float = 0.95
    CONDITION_SCORE_MODERATE: float = 0.75
    CONDITION_SCORE_POOR: float = 0.5

    # Valve command timeout
    VALVE_CMD_TIMEOUT_SEC: int = 5


settings = Settings()
