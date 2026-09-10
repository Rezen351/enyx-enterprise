"""HTTP client to Control Service."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from .config import settings

logger = logging.getLogger("model-control")


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

    def _request(
        self, method: str, url: str, payload: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Send an authenticated request, re-authenticating once on 401.

        The JWT is cached after the first login; if it becomes invalid
        (expired, clock skew, auth/control restart) the control service
        answers 401. We drop the cached token, log in again, and retry a
        single time instead of forever replaying a dead token.
        """
        if not self._token and not self.login():
            return None

        def _send() -> httpx.Response:
            return httpx.request(
                method,
                url,
                json=payload,
                headers=self._auth_headers(),
                timeout=httpx.Timeout(10.0, connect=5.0),
            )

        try:
            resp = _send()
            if resp.status_code == 401:
                self._token = None
                if not self.login():
                    return None
                resp = _send()
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            logger.error("%s %s failed: %s", method, url, exc)
            return None

    def update_schedule(self, schedule_id: str, on_sec: int, off_sec: int) -> bool:
        payload = {
            "params": {
                "on_sec": on_sec,
                "off_sec": off_sec,
                "value_on": 1,
                "value_off": 0,
            }
        }
        data = self._request(
            "PUT",
            f"{self.base_url}/control/schedules/{schedule_id}",
            payload,
        )
        return bool(data.get("success")) if data else False

    def send_valve_command(self, node_id: str, value: int) -> bool:
        payload = {
            "node_id": node_id,
            "type": "set_state",
            "output": settings.VALVE_OUTPUT_NAME,
            "value": value,
            "bypass": True,
        }
        data = self._request(
            "POST",
            f"{self.base_url}/control/command",
            payload,
        )
        return bool(data.get("success")) if data else False
