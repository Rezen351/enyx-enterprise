from app.schemas import PredictResponse, HealthResponse


def success(data):
    return {"success": True, "data": data}


def predict_success(action):
    return success(PredictResponse(
        D_mist=float(action[0]),
        interval_sec=float(action[1]),
        A_valve=float(action[2]),
    ).dict())


def health_success(status, model_loaded, vec_norm_loaded):
    return success(HealthResponse(
        status=status,
        model_loaded=model_loaded,
        vec_norm_loaded=vec_norm_loaded,
    ).dict())


def error(status_code: int, code: str, message: str):
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
        },
    }
