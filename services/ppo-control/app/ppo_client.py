"""HTTP client to ppo-controller inference service."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from .config import settings

logger = logging.getLogger("ppo-control")


class PPOControllerClient:
    def __init__(self) -> None:
        self.base_url = settings.PPO_CONTROLLER_URL.rstrip("/")

    def predict(self, state: list[float]) -> dict[str, float] | None:
        payload = {"state": state}
        try:
            resp = httpx.post(
                f"{self.base_url}/predict",
                json=payload,
                timeout=httpx.Timeout(10.0, connect=5.0),
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("success") and "data" in data:
                return data["data"]
            return None
        except Exception as exc:
            logger.error("ppo-controller predict failed: %s", exc)
            return None
