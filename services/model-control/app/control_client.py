"""HTTP client to Control Service."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from .config import settings

logger = logging.getLogger("ppo-control")


class ControlClient:
    def __init__(self) -> None:
        self.base_url = settings.CONTROL_URL.rstrip("/")
        self.auth_url = settings.AUTH_URL.rstrip("/")
        self._token: str | None = None

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"} if self._token else {}

    def login(self) -> bool:
        try:
            resp = httpx.post(
                f"{self.auth_url}/auth/login",
                json={
                    "username": settings.CONTROL_USER,
                    "password": settings.CONTROL_PASS,
                },
                timeout=httpx.Timeout(10.0, connect=5.0),
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("success") and "data" in data:
                self._token = data["data"].get("access_token")
                return bool(self._token)
            return False
        except Exception as exc:
            logger.error("auth login failed: %s", exc)
            return False

    def update_schedule(self, schedule_id: str, on_sec: int, off_sec: int) -> bool:
        if not self._token and not self.login():
            return False
        payload = {
            "params": {
                "on_sec": on_sec,
                "off_sec": off_sec,
                "value_on": 1,
                "value_off": 0,
            }
        }
        try:
            resp = httpx.put(
                f"{self.base_url}/control/schedules/{schedule_id}",
                json=payload,
                headers=self._auth_headers(),
                timeout=httpx.Timeout(10.0, connect=5.0),
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("success", False)
        except Exception as exc:
            logger.error("update schedule %s failed: %s", schedule_id, exc)
            return False

    def send_valve_command(self, node_id: str, value: int) -> bool:
        if not self._token and not self.login():
            return False
        payload = {
            "node_id": node_id,
            "type": "set_state",
            "output": settings.VALVE_OUTPUT_NAME,
            "value": value,
            "bypass": True,
        }
        try:
            resp = httpx.post(
                f"{self.base_url}/control/command",
                json=payload,
                headers=self._auth_headers(),
                timeout=httpx.Timeout(10.0, connect=5.0),
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("success", False)
        except Exception as exc:
            logger.error("valve command failed: %s", exc)
            return False
