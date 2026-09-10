#!/usr/bin/env python3
"""MQTT telemetry traffic monitor.

Subscribes to a wildcard topic (default: smartfarm/+/telemetry) and counts
messages, throughput, and per-node traffic. Useful for manual ingest validation
when observing Grafana / broker metrics directly.

Usage:
    python3 mqtt_monitor.py --topic "smartfarm/+/telemetry"
    python3 mqtt_monitor.py --broker tcp://localhost:1883 --port 1883 --duration 60
"""

from __future__ import annotations

import argparse
import json
import signal
import sys
import time
from collections import defaultdict
from typing import Dict, Optional

try:
    import paho.mqtt.client as mqtt
    _MQTT_V2 = hasattr(mqtt, "CallbackAPIVersion")
except ImportError:
    print("Missing dependency: paho-mqtt")
    print("  python3 -m pip install paho-mqtt")
    sys.exit(1)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="MQTT telemetry traffic counter")
    p.add_argument("--broker", default="tcp://localhost:1883", help="MQTT broker address, e.g. tcp://192.168.1.103:1883")
    p.add_argument("--port", type=int, default=1883, help="MQTT broker port (ignored if port is embedded in --broker)")
    p.add_argument("--topic", default="smartfarm/+/telemetry", help="Wildcard topic to subscribe")
    p.add_argument("--user", default=None, help="MQTT username")
    p.add_argument("--password", default=None, help="MQTT password")
    p.add_argument("--duration", type=float, default=None, help="Run duration in seconds (default: infinite until Ctrl+C)")
    p.add_argument("--json-out", default=None, help="Optional path to write summary JSON")
    p.add_argument("--interval", type=float, default=1.0, help="Stats print interval in seconds")
    return p.parse_args()


class MqttMonitor:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.topic = args.topic
        self.total = 0
        self.per_node: Dict[str, int] = defaultdict(int)
        self.interval = args.interval
        self._start = time.time()
        self._last_print = self._start
        self._running = True
        self._fail_count = 0
        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2 if _MQTT_V2 else mqtt.CallbackAPIVersion.VERSION1
        )
        if args.user:
            self._client.username_pw_set(args.user, args.password)

        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

    # ------------------------------------------------------------------ hooks
    def _on_connect(self, _client, _userdata, flags, rc, *_extra):
        if rc == 0:
            print(f"[*] Connected to broker (topic={self.topic})")
            self._client.subscribe(self.topic, qos=0)
            self._fail_count = 0
        else:
            reasons = {
                1: "incorrect protocol version",
                2: "invalid client identifier",
                3: "server unavailable",
                4: "bad username or password",
                5: "not authorized",
            }
            rc_value = rc.value if hasattr(rc, "value") else rc
            reason = reasons.get(rc_value, f"unknown ({rc})")
            print(f"[!] Connection failed rc={rc}: {reason}")
            if rc == 5:
                print(f"[!] Hint: check --user/--password and broker access control list")
            self._fail_count += 1

    def _on_disconnect(self, _client, _userdata, rc, *_extra):
        if rc != 0:
            print(f"[!] Unexpected disconnect rc={rc}")
            self._fail_count += 1

    def _on_message(self, _client, _userdata, msg):
        self.total += 1
        parts = msg.topic.split("/")
        node = parts[1] if len(parts) > 1 else "unknown"
        self.per_node[node] += 1

    # ------------------------------------------------------------- lifecycle
    def start(self) -> None:
        broker = self.args.broker
        host = broker.replace("tcp://", "").replace("ssl://", "").split(":")[0]
        port = self.args.port
        if ":" in broker.replace("tcp://", "").replace("ssl://", ""):
            try:
                port = int(broker.rsplit(":", 1)[-1])
            except ValueError:
                pass
        print(f"[*] Connecting to {host}:{port} ...")
        self._client.connect(host, port, keepalive=30)
        self._client.loop_start()

        try:
            self._loop()
        finally:
            self._client.loop_stop()
            try:
                self._client.disconnect()
            except Exception:
                pass
            self._print_summary(final=True)

    def _loop(self) -> None:
        while self._running:
            now = time.time()
            elapsed = now - self._start
            if self.args.duration is not None and elapsed >= self.args.duration:
                break
            if self._fail_count >= 5:
                print("[!] Too many connection failures, stopping.")
                break
            if now - self._last_print >= self.interval:
                self._print_stats(now)
                self._last_print = now
            time.sleep(0.1)

    # -------------------------------------------------------------- display
    def _rate(self, now: float) -> float:
        dt = now - self._start
        return self.total / dt if dt > 0 else 0.0

    def _print_stats(self, now: float) -> None:
        rate = self._rate(now)
        top = sorted(self.per_node.items(), key=lambda x: x[1], reverse=True)[:5]
        print(
            f" elapsed={now - self._start:6.1f}s | total={self.total:6d} | "
            f"rate={rate:6.1f} msg/s | last_interval={self.total - getattr(self, '_prev_total', 0):5d}"
        )
        if top:
            print("  top nodes: " + ", ".join(f"{n}={c}" for n, c in top))
        self._prev_total = self.total

    def _print_summary(self, final: bool = False) -> None:
        now = time.time()
        dt = now - self._start
        rate = self.total / dt if dt > 0 else 0.0
        tag = "FINAL" if final else "CURRENT"
        print(f"\n[{tag}] elapsed={dt:.1f}s | total={self.total} | avg_rate={rate:.2f} msg/s")
        if self.per_node:
            print(" per-node:")
            for node, count in sorted(self.per_node.items(), key=lambda x: x[1], reverse=True):
                print(f"   {node}: {count} ({count/dt if dt else 0:.2f} msg/s)")

        if self.args.json_out:
            payload = {
                "elapsed_s": round(dt, 3),
                "total": self.total,
                "avg_rate": round(rate, 3),
                "per_node": dict(self.per_node),
            }
            with open(self.args.json_out, "w") as fh:
                json.dump(payload, fh, indent=2)
            print(f"[*] Summary JSON written: {self.args.json_out}")

    def stop(self) -> None:
        self._running = False


def main() -> int:
    args = parse_args()
    monitor = MqttMonitor(args)

    def _sigint(_sig, _frame):
        monitor.stop()

    signal.signal(signal.SIGINT, _sigint)
    monitor.start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
