"""Background PPO prediction loop."""

from __future__ import annotations

import datetime as dt
import json
import logging
import threading
import time
from typing import Any

from .config import settings
from .control_client import ControlClient
from .minio_client import MinIOClient
from .ppo_client import PPOControllerClient
from .telemetry_cache import get_cache

logger = logging.getLogger("ppo-control")
logging.basicConfig(level=logging.INFO)


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _sunlight_index() -> float:
    now = dt.datetime.now()
    hour = now.hour + now.minute / 60.0
    if 6 <= hour <= 18:
        return (hour - 6) / 12.0
    return 0.0


def _condition_to_u_status(condition: float | None) -> float:
    if condition is None:
        return settings.DEFAULT_U_STATUS
    if condition >= settings.CONDITION_SCORE_HEALTHY:
        return 1.0
    if condition >= settings.CONDITION_SCORE_MODERATE:
        return 0.75
    if condition >= settings.CONDITION_SCORE_POOR:
        return 0.5
    return 0.25


def assemble_state() -> list[float]:
    cache = get_cache()
    node_id = settings.NODE_ID

    meta = MinIOClient().get_latest_metadata(settings.MODULE_ID)
    try:
        L_root = float(meta.get("root_length_cm", settings.DEFAULT_L_ROOT))
    except (TypeError, ValueError):
        L_root = settings.DEFAULT_L_ROOT

    try:
        condition = float(meta.get("condition", settings.DEFAULT_U_STATUS))
    except (TypeError, ValueError):
        condition = settings.DEFAULT_U_STATUS
    U_status = _condition_to_u_status(condition)

    T_in = cache.get_metric(node_id, "telemetry.modbus.cwt2.temp") or settings.DEFAULT_T_IN
    H_in = cache.get_metric(node_id, "telemetry.modbus.cwt2.hum") or settings.DEFAULT_H_IN
    T_out = cache.get_metric(node_id, "telemetry.modbus.cwt1.temp") or settings.DEFAULT_T_OUT
    H_out = cache.get_metric(node_id, "telemetry.modbus.cwt1.hum") or  settings.DEFAULT_H_OUT
    EC = cache.get_metric(node_id, "telemetry.modbus.npk.ec_nutrisi") or settings.DEFAULT_EC
    pH = cache.get_metric(node_id, "telemetry.modbus.npk.ph_nutrisi") or settings.DEFAULT_PH
    T_nut = cache.get_metric(node_id, "telemetry.modbus.npk.temp_nutrisi") or settings.DEFAULT_T_NUT
    I_day = _sunlight_index()

    cache_debug = {
        "T_in": {"value": T_in, "age_s": round(cache.age(node_id, "telemetry.modbus.cwt2.temp"), 1)},
        "H_in": {"value": H_in, "age_s": round(cache.age(node_id, "telemetry.modbus.cwt2.hum"), 1)},
        "T_out": {"value": T_out, "age_s": round(cache.age(node_id, "telemetry.modbus.cwt1.temp"), 1)},
        "H_out": {"value": H_out, "age_s": round(cache.age(node_id, "telemetry.modbus.cwt1.hum"), 1)},
        "EC": {"value": EC, "age_s": round(cache.age(node_id, "telemetry.modbus.npk.ec_nutrisi"), 1)},
        "pH": {"value": pH, "age_s": round(cache.age(node_id, "telemetry.modbus.npk.ph_nutrisi"), 1)},
        "T_nut": {"value": T_nut, "age_s": round(cache.age(node_id, "telemetry.modbus.npk.temp_nutrisi"), 1)},
    }
    logger.debug("cache metrics: %s", json.dumps(cache_debug, default=str))

    return [
        _clamp(L_root, 0.0, 300.0),
        _clamp(U_status, 0.0, 1.0),
        _clamp(T_in, 15.0, 30.0),
        _clamp(H_in, 20.0, 100.0),
        _clamp(T_out, 15.0, 30.0),
        _clamp(H_out, 20.0, 100.0),
        _clamp(EC, 0.5, 3.5),
        _clamp(pH, 4.0, 9.0),
        _clamp(T_nut, 18.0, 25.0),
        _clamp(I_day, 0.0, 1.0),
    ]


class PPOLoop:
    def __init__(self) -> None:
        self.running = False
        self._thread: threading.Thread | None = None
        self.ppo = PPOControllerClient()
        self.ctrl = ControlClient()
        self.last_schedule_update: float = 0.0
        self.current_D_mist: int = 60
        self.current_interval: int = 540
        self.pending_action: dict[str, float] | None = None

    def start(self) -> None:
        self.running = True
        self._thread = threading.Thread(target=self._run, daemon=False)
        self._thread.start()
        logger.info("PPO loop started interval=%ss", settings.PREDICTION_INTERVAL_SEC)

    def stop(self) -> None:
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self) -> None:
        while self.running:
            try:
                self._tick()
            except Exception as exc:
                logger.exception("PPO loop tick failed: %s", exc)
            time.sleep(settings.PREDICTION_INTERVAL_SEC)

    def _tick(self) -> None:
        state = assemble_state()
        logger.info("state=%s", json.dumps(state, default=str))

        action = self.ppo.predict(state)
        if action:
            self.pending_action = action

        cycle_done = False
        if self.last_schedule_update == 0.0:
            cycle_done = True
        else:
            elapsed = time.time() - self.last_schedule_update
            cycle_done = elapsed >= (self.current_D_mist + self.current_interval)

        if not cycle_done or not self.pending_action:
            logger.debug(
                "tick skipped cycle_done=%s pending=%s elapsed=%.1fs cycle=%ds",
                cycle_done,
                bool(self.pending_action),
                time.time() - self.last_schedule_update if self.last_schedule_update else 0.0,
                self.current_D_mist + self.current_interval,
            )
            return

        D_mist = int(_clamp(round(float(self.pending_action.get("D_mist", 0))), 10, 240))
        interval_sec = int(_clamp(round(float(self.pending_action.get("interval_sec", 0))), 60, 540))
        A_valve = 1 if float(self.pending_action.get("A_valve", 0)) >= 0 else 0

        ok = self.ctrl.update_schedule(
            settings.PUMP_SCHEDULE_ID,
            on_sec=D_mist,
            off_sec=interval_sec,
        )
        logger.info("schedule update ok=%s D_mist=%d interval=%d", ok, D_mist, interval_sec)

        valve_ok = self.ctrl.send_valve_command(settings.NODE_ID, A_valve)
        logger.info("valve command ok=%s A_valve=%d", valve_ok, A_valve)

        if ok:
            self.last_schedule_update = time.time()
            self.current_D_mist = D_mist
            self.current_interval = interval_sec
            self.pending_action = None
