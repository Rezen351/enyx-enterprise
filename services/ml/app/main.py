"""FastAPI application factory for the ML / Vision API."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import get_settings
from app.database import init_db
from app.routes_detect import router as detect_router
from app.routes_models import router as models_router
from app.routes_system import router as system_router
from app.routes_results import router as results_router
from app.responses import EnvelopeJSONResponse, install_response_wrapper
from app.vision_engine import registry

settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("ml-api")


def create_app() -> FastAPI:
    app = FastAPI(
        title="ML Service",
        description=(
            "YOLO-based computer vision service. Manages a registry of models "
            "(each with a stable model_id), accepts images, runs inference, and "
            "returns detections with annotated images stored in MinIO + events "
            "published to NATS."
        ),
        version="1.0.0",
        default_response_class=EnvelopeJSONResponse,
    )

    install_response_wrapper(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(system_router)
    app.include_router(models_router)
    app.include_router(detect_router)
    app.include_router(results_router)

    @app.get("/metrics", include_in_schema=False)
    def metrics():
        from fastapi import Response

        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    Instrumentator().instrument(app).expose(app, endpoint="/metrics-internal")

    @app.on_event("startup")
    def _startup() -> None:
        logger.info("Initializing database schema...")
        init_db()
        # Make the bundled aeroponic vision model available out of the box.
        registry.ensure_seeded_model(
            weights_filename="vision-aeroponik-model-root.pt",
            model_id="vision-aeroponik",
            slug="vision-aeroponik",
            name="Vision Aeroponik",
            description="YOLO model for aeroponic plant/crop detection (user-triggered snapshots).",
        )
        logger.info("Warming up model registry...")
        registry.warmup()

    return app


app = create_app()
