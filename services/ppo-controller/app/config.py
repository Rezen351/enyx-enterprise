import os

from pydantic_settings import BaseSettings


SERVICE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Settings(BaseSettings):
    APP_NAME: str = "ppo-controller"
    PORT: int = 8080

    # Model paths (absolute paths derived from service dir)
    MODEL_PATH: str = os.path.join(SERVICE_DIR, "models", "aeroponic_ppo.zip")
    VEC_NORM_PATH: str = os.path.join(SERVICE_DIR, "models", "vec_normalize.pkl")

    # NATS
    NATS_URL: str = "nats://nats:4222"
    NATS_SUBJECT_TELEMETRY: str = "telemetry.ingest"
    NATS_SUBJECT_ACTION: str = "ppo.action"

    # Inference
    DEVICE: str = "cpu"
    DETERMINISTIC: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
