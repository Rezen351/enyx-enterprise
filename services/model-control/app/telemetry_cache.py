"""In-memory telemetry cache backed by NATS telemetry.ingest and telemetry.batch."""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from typing import Any

import nats
from nats.errors import ConnectionClosedError, TimeoutError

from .config import settings

logger = logging.getLogger("ppo-control")

TELEMETRY_SUBJECTS = ["telemetry.ingest", "telemetry.batch"]


class TelemetryCache:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._latest: dict[str, dict[str, Any]] = {}
        self._metrics: dict[str, dict[str, float]] = {}
        self._ts: dict[str, dict[str, float]] = {}

    def ingest(self, node_id: str, metric: str, value: float, ts: float) -> None:
        with self._lock:
            if node_id not in self._latest:
                self._latest[node_id] = {}
                self._metrics[node_id] = {}
                self._ts[node_id] = {}
            self._latest[node_id][metric] = {"value": value, "ts": ts}
            self._metrics[node_id][metric] = value
            self._ts[node_id][metric] = ts / 1000.0

    def get(self, node_id: str) -> dict[str, Any]:
        with self._lock:
            return dict(self._latest.get(node_id, {}))

    def get_metric(self, node_id: str, metric: str, fallback: float = 0.0) -> float:
        with self._lock:
            metrics = self._metrics.get(node_id, {})
            return metrics.get(metric, fallback)

    def age(self, node_id: str, metric: str) -> float:
        with self._lock:
            ts_map = self._ts.get(node_id, {})
            last = ts_map.get(metric)
            if last is None:
                return float("inf")
            return time.time() - last


_cache = TelemetryCache()


def get_cache() -> TelemetryCache:
    return _cache


class NATSTelemetrySubscriber:
    def __init__(self, cache: TelemetryCache) -> None:
        self.cache = cache
        self.nc: nats.NATS | None = None
        self._subs: list[nats.Subscription] = []

    async def start(self) -> None:
        try:
            self.nc = await nats.connect(
                servers=[settings.NATS_URL],
                connect_timeout=5,
                max_reconnect_attempts=0,
            )
        except Exception as exc:
            logger.error("NATS connect failed: %s", exc)
            return

        for subject in TELEMETRY_SUBJECTS:
            sub = await self.nc.subscribe(subject)
            self._subs.append(sub)
            logger.info("NATS subscribed to %s", subject)

        # Process messages in a loop so subscription callbacks keep firing.
        _msg_count = 0
        try:
            while True:
                try:
                    # Wait for messages from any subscription concurrently.
                    pending = [
                        asyncio.create_task(sub.next_msg(timeout=1.0))
                        for sub in self._subs
                    ]
                    done, pending = await asyncio.wait(
                        pending, timeout=1.0, return_when=asyncio.FIRST_COMPLETED
                    )
                    for task in pending:
                        task.cancel()
                    if not done:
                        if _msg_count == 0:
                            logger.debug("NATS no telemetry messages received yet")
                        continue
                    msg = done.pop().result()
                    _msg_count += 1
                    try:
                        data = json.loads(msg.data)
                        self._handle_message(data, msg.subject)
                    except Exception:
                        pass
                except nats.errors.TimeoutError:
                    continue
                except Exception as exc:
                    logger.debug("NATS receive error: %s", exc)
                    break
        except asyncio.CancelledError:
            pass

    def _handle_message(self, data: dict[str, Any], subject: str) -> None:
        if subject == "telemetry.ingest":
            node_id = data.get("node_id")
            metric = data.get("metric")
            value = data.get("value")
            ts = data.get("ts")
            if not node_id or metric is None or value is None or ts is None:
                return
            self.cache.ingest(node_id, metric, float(value), float(ts))
        elif subject == "telemetry.batch":
            rows = data.get("rows", [])
            if not isinstance(rows, list):
                return
            for row in rows:
                if not isinstance(row, dict):
                    continue
                node_id = row.get("node_id")
                metric = row.get("metric")
                last = row.get("last")
                last_ts = row.get("last_ts")
                if not node_id or metric is None or last is None or last_ts is None:
                    continue
                self.cache.ingest(node_id, metric, float(last), float(last_ts))

    async def stop(self) -> None:
        for sub in self._subs:
            try:
                await sub.unsubscribe()
            except Exception:
                pass
        if self.nc:
            try:
                await self.nc.close()
            except Exception:
                pass
