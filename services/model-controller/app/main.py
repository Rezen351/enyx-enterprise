import logging
import time

from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse

from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.config import settings
from app.model_loader import ModelLoader
from app.responses import predict_success, health_success, error
from app.schemas import PredictRequest

app = FastAPI(title=settings.APP_NAME)
logger = logging.getLogger("model-controller")
logging.basicConfig(level=logging.INFO)


@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


model_loader = ModelLoader(
    model_path=settings.MODEL_PATH,
    vec_norm_path=settings.VEC_NORM_PATH,
    device=settings.DEVICE,
)

model_loaded = False
vec_norm_loaded = False


@app.on_event("startup")
def startup_event():
    global model_loaded, vec_norm_loaded
    try:
        model_loader.load()
        model_loaded = True
        vec_norm_loaded = True
        logger.info("Model and vec_norm loaded successfully")
    except Exception as exc:
        logger.error("Failed to load model: %s", exc)
        raise


@app.get("/health")
def health():
    status = "ok" if model_loaded else "degraded"
    logger.debug("health check: status=%s model_loaded=%s vec_norm_loaded=%s", status, model_loaded, vec_norm_loaded)
    return JSONResponse(
        status_code=200,
        content=health_success(
            status=status,
            model_loaded=model_loaded,
            vec_norm_loaded=vec_norm_loaded,
        ),
    )


@app.post("/predict")
def predict(req: PredictRequest):
    start = time.perf_counter()
    if not model_loaded:
        logger.warning("predict rejected: model not loaded")
        return JSONResponse(
            status_code=503,
            content=error(503, "SERVICE_UNAVAILABLE", "Model not loaded"),
        )
    try:
        action = model_loader.predict(req.state)
        latency = time.perf_counter() - start
        logger.info(
            "predict state=%s action=%s latency=%.4fs",
            req.state,
            action.tolist(),
            latency,
        )
        return JSONResponse(status_code=200, content=predict_success(action))
    except Exception as exc:
        latency = time.perf_counter() - start
        logger.error("predict failed state=%s latency=%.4fs error=%s", req.state, latency, exc)
        return JSONResponse(
            status_code=500,
            content=error(500, "INTERNAL_ERROR", str(exc)),
        )
