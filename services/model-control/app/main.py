from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse

import json
import logging
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.config import settings
from app.telemetry_cache import NATSTelemetrySubscriber, get_cache
from app.ppo_loop import PPOLoop

app = FastAPI(title=settings.APP_NAME)

_logger = logging.getLogger("model-control")
_logger.setLevel(logging.DEBUG)
if not _logger.handlers:
    import sys
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(_handler)
    _logger.propagate = False


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "error": {"code": code, "message": message}},
    )


@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/health")
def health():
    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "node_id": settings.NODE_ID,
            "schedule_id": settings.PUMP_SCHEDULE_ID,
            "valve_output": settings.VALVE_OUTPUT_NAME,
            "interval_sec": settings.PREDICTION_INTERVAL_SEC,
        },
    )


@app.post("/trigger-predict")
def trigger_predict():
    loop: PPOLoop = app.state.loop
    if not loop:
        return _error_response(503, "SERVICE_UNAVAILABLE", "prediction loop is not running; please wait for initialization or restart the service")
    try:
        loop._tick()
        return JSONResponse(status_code=200, content={"success": True, "data": {"status": "tick executed"}})
    except Exception as exc:
        _logger.exception("prediction tick failed")
        return _error_response(500, "INTERNAL_ERROR", "prediction tick failed")


@app.on_event("startup")
def startup_event():
    cache = get_cache()
    sub = NATSTelemetrySubscriber(cache)

    import asyncio
    import threading

    async_loop = asyncio.new_event_loop()

    def run_async():
        asyncio.set_event_loop(async_loop)
        async_loop.run_until_complete(sub.start())

    t = threading.Thread(target=run_async, daemon=False, name="nats-thread")
    t.start()

    app.state.nats_sub = sub
    app.state.nats_thread = t
    app.state.async_loop = async_loop

    ppo = PPOLoop()
    ppo.start()
    app.state.loop = ppo


@app.on_event("shutdown")
def shutdown_event():
    ppo = getattr(app.state, "loop", None)
    if ppo:
        ppo.stop()
    sub = getattr(app.state, "nats_sub", None)
    if sub:
        import asyncio

        loop = app.state.async_loop
        if loop and not loop.is_closed():
            loop.run_until_complete(sub.stop())
            loop.close()
