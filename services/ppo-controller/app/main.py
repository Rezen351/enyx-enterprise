from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.config import settings
from app.model_loader import PPOModelLoader
from app.responses import predict_success, health_success, error
from app.schemas import PredictRequest

app = FastAPI(title=settings.APP_NAME)

model_loader = PPOModelLoader(
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
    except Exception as exc:
        print(f"Failed to load PPO model: {exc}")


@app.get("/health")
def health():
    return JSONResponse(
        status_code=200,
        content=health_success(
            status="ok" if model_loaded else "degraded",
            model_loaded=model_loaded,
            vec_norm_loaded=vec_norm_loaded,
        ),
    )


@app.post("/predict")
def predict(req: PredictRequest):
    if not model_loaded:
        return JSONResponse(
            status_code=503,
            content=error(503, "SERVICE_UNAVAILABLE", "PPO model not loaded"),
        )
    try:
        action = model_loader.predict(req.state)
        return JSONResponse(status_code=200, content=predict_success(action))
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error(500, "INTERNAL_ERROR", str(exc)),
        )
