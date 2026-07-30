import os

from pydantic_settings import BaseSettings


SERVICE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Settings(BaseSettings):
    APP_NAME: str = "model-controller"
    PORT: int = 8080

    # Model paths (absolute paths derived from service dir)
    MODEL_PATH: str = os.path.join(SERVICE_DIR, "models", "aeroponic_td3.zip")
    VEC_NORM_PATH: str = os.path.join(SERVICE_DIR, "models", "vec_normalize_td3.pkl")

    # NATS
    NATS_URL: str = "nats://nats:4222"
    NATS_SUBJECT_TELEMETRY: str = "telemetry.ingest"
    NATS_SUBJECT_ACTION: str = "model.action"

    # Inference
    DEVICE: str = "cpu"
    DETERMINISTIC: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
