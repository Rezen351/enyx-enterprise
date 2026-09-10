#!/usr/bin/env python3
"""enyx-enterprise - Passive Ingest Observer

Subscribes to telemetry MQTT topics and passively collects ingest metrics
over a fixed duration. Does NOT create virtual nodes or write anything.

Metrics collected:
  - total telemetry messages
  - per-node message count and rate
  - average / peak 1-second rate
  - MQTT publish-to-subscribe latency estimate using ts_publish in payload (if present)
  - disconnect / reconnect count

Optional:
  - Prometheus snapshot scrape for container CPU/RAM of core stack
    (module-service, nats, mosquitto, timescaledb-module)
  - Matplotlib charts saved as PNG

Usage examples:
    python3 test/ingest_observer.py --duration 300
    python3 test/ingest_observer.py --duration 600 --topic "smartfarm/+/telemetry" --json-out results/ingest.json
    python3 test/ingest_observer.py --duration 300 --prometheus http://localhost:9090 --charts
    python3 test/ingest_observer.py --duration 300 --charts --chart-out results/ingest_charts.png
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import paho.mqtt.client as mqtt

    _MQTT_V2 = hasattr(mqtt, "CallbackAPIVersion")
except ImportError:
    print("Missing dependency: paho-mqtt")
    print("  python3 -m pip install paho-mqtt")
    sys.exit(1)

try:
    import matplotlib  # type: ignore[import-untyped]

    matplotlib.use("Agg")  # Non-interactive backend
    import matplotlib.pyplot as plt  # type: ignore[import-untyped]
    import numpy as np  # type: ignore[import-untyped]

    _MATPLOTLIB_AVAILABLE = True
except ImportError:
    _MATPLOTLIB_AVAILABLE = False

try:
    import requests as _requests  # type: ignore[import-untyped]
except ImportError:
    _requests = None  # type: ignore[assignment]

DEFAULT_BROKER = os.getenv("MQTT_BROKER", "tcp://localhost:1883")
DEFAULT_TOPIC = "smartfarm/+/telemetry"
DEFAULT_DURATION = 300.0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Passive MQTT telemetry ingest observer")
    p.add_argument("--broker", default=DEFAULT_BROKER, help="MQTT broker address")
    p.add_argument("--port", type=int, default=1883, help="MQTT broker port (ignored if embedded in broker)")
    p.add_argument("--topic", default=DEFAULT_TOPIC, help="MQTT wildcard topic")
    p.add_argument("--user", default=None, help="MQTT username")
    p.add_argument("--password", default=None, help="MQTT password")
    p.add_argument("--duration", type=float, default=DEFAULT_DURATION, help="Run duration in seconds")
    p.add_argument("--json-out", default=None, help="Path to write summary JSON")
    p.add_argument("--interval", type=float, default=5.0, help="Running stats print interval in seconds")
    p.add_argument("--prometheus", default=None, help="Prometheus base URL, e.g. http://localhost:9090")
    p.add_argument("--latency-p95-target", type=float, default=2.0, help="Latency P95 target for reporting")
    p.add_argument("--charts", action="store_true", help="Generate matplotlib charts after the run")
    p.add_argument("--chart-out", default=None, help="Chart PNG output path (default: alongside --json-out or results/ingest_observer_charts.png)")
    return p.parse_args()


class IngestObserver:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.topic = args.topic
        self.total = 0
        self.per_node: Dict[str, int] = defaultdict(int)
        self.per_node_latencies: Dict[str, List[float]] = defaultdict(list)
        self._start = time.time()
        self._last_print = self._start
        self._last_total = 0
        self._last_print_time = self._start
        self._running = True
        self._fail_count = 0
        self._disconnects = 0
        self._peak_1s_rate = 0.0
        self._window: List[Tuple[float, int]] = []  # (timestamp, count delta)
        self._timeline: List[Tuple[float, int, Dict[str, int]]] = []  # (elapsed, total, per_node_snapshot)
        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2 if _MQTT_V2 else mqtt.CallbackAPIVersion.VERSION1,
            client_id="ingest-observer",
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
            reasons = {1: "incorrect protocol version", 2: "invalid client identifier", 3: "service unavailable", 4: "bad credentials", 5: "not authorized"}
            rc_value = rc.value if hasattr(rc, "value") else rc
            reason = reasons.get(rc_value, f"unknown ({rc})")
            print(f"[!] Connection failed rc={rc}: {reason}")
            self._fail_count += 1

    def _on_disconnect(self, _client, _userdata, rc, *_extra):
        if rc != 0:
            print(f"[!] Unexpected disconnect rc={rc}")
            self._disconnects += 1
        self._fail_count += 1

    def _on_message(self, _client, _userdata, msg):
        now = time.time()
        self.total += 1
        parts = msg.topic.split("/")
        node = parts[1] if len(parts) > 1 else "unknown"
        self.per_node[node] += 1

        try:
            payload = json.loads(msg.payload or b"{}")
            ts_publish = payload.get("ts_publish") or payload.get("telemetry", {}).get("ts_publish")
            if ts_publish is not None:
                lat = now - (float(ts_publish) / 1000.0)
                if 0 <= lat < 60:
                    self.per_node_latencies[node].append(lat)
        except Exception:
            pass

        self._window.append((now, 1))
        cutoff = now - 1.0
        while self._window and self._window[0][0] < cutoff:
            self._window.pop(0)
        rate_1s = len(self._window)
        if rate_1s > self._peak_1s_rate:
            self._peak_1s_rate = float(rate_1s)

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

        print(f"[*] Connecting to {host}:{port} topic={self.topic} duration={self.args.duration}s")
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
            if elapsed >= self.args.duration:
                break
            if self._fail_count >= 10:
                print("[!] Too many failures, stopping observer early.")
                break
            if now - self._last_print >= self.args.interval:
                self._record_timeline(now)
                self._print_running(now)
                self._last_print = now
            time.sleep(0.1)

    def _record_timeline(self, now: float) -> None:
        self._timeline.append((now - self._start, self.total, dict(self.per_node)))

    # -------------------------------------------------------------- helpers
    def _rate(self, now: float) -> float:
        dt = now - self._start
        return self.total / dt if dt > 0 else 0.0

    def _print_running(self, now: float) -> None:
        elapsed = now - self._start
        rate = self._rate(now)
        interval_msgs = self.total - self._last_total
        interval_rate = interval_msgs / max(1.0, now - self._last_print_time)
        self._last_total = self.total
        self._last_print_time = now
        top = sorted(self.per_node.items(), key=lambda x: x[1], reverse=True)[:5]
        print(
            f"[OBS] elapsed={elapsed:6.1f}s | total={self.total:6d} | "
            f"avg={rate:6.1f} msg/s | last_interval={interval_rate:6.1f} msg/s | peak_1s={self._peak_1s_rate:6.1f} msg/s"
        )
        if top:
            print("       top nodes: " + ", ".join(f"{n}={c}" for n, c in top))

    def _latency_percentile(self, samples: List[float], p: float) -> float:
        if not samples:
            return 0.0
        s = sorted(samples)
        k = (len(s) - 1) * (p / 100.0)
        f = int(k)
        c = min(f + 1, len(s) - 1)
        if f == c:
            return s[f]
        return s[f] + (k - f) * (s[c] - s[f])

    def _snapshot_prometheus(self) -> Dict[str, Any]:
        if not self.args.prometheus or _requests is None:
            return {}
        base = self.args.prometheus.rstrip("/")
        targets_url = f"{base}/api/v1/targets"
        targets_ok = 0
        try:
            r = _requests.get(targets_url, timeout=10)
            if r.status_code == 200:
                targets_ok = len(r.json().get("data", {}).get("activeTargets", []))
        except Exception:
            pass

        containers = ["module-service", "nats", "mosquitto", "timescaledb-module"]
        instant_url = f"{base}/api/v1/query"
        result: Dict[str, Any] = {"active_targets": targets_ok, "containers": {}}
        for c in containers:
            q = (
                f'sum(rate(container_cpu_usage_seconds_total{{'
                f'container_label_io_kubernetes_container_name="{c}"'
                f'}}[1m]))'
            )
            try:
                r = _requests.get(instant_url, params={"query": q}, timeout=10)
                if r.status_code == 200:
                    res = (((r.json() or {}).get("data") or {}).get("result") or [])
                    val = float((res[0].get("value") or [0, "0"])[1]) if res else 0.0
                    result["containers"][c] = {"cpu_cores": val}
                else:
                    result["containers"][c] = {"cpu_cores": 0.0}
            except Exception:
                result["containers"][c] = {"cpu_cores": 0.0}
        return result

    # -------------------------------------------------------------- summary / charts
    def _print_summary(self, final: bool = False) -> None:
        now = time.time()
        elapsed = now - self._start
        rate = self.total / elapsed if elapsed > 0 else 0.0
        tag = "FINAL" if final else "CURRENT"
        print(f"\n[{tag}] elapsed={elapsed:.1f}s | total={self.total} | avg_rate={rate:.2f} msg/s | peak_1s={self._peak_1s_rate:.1f} msg/s | disconnects={self._disconnects}")
        if self.per_node:
            print(" per-node:")
            for node, count in sorted(self.per_node.items(), key=lambda x: x[1], reverse=True):
                latencies = self.per_node_latencies.get(node, [])
                p50 = self._latency_percentile(latencies, 50)
                p95 = self._latency_percentile(latencies, 95)
                lat_info = f"latency_p50={p50*1000:.1f}ms p95={p95*1000:.1f}ms (n={len(latencies)})" if latencies else "latency=n/a"
                print(f"   {node}: {count} ({count/elapsed:.2f} msg/s) | {lat_info}")

        all_latencies: List[float] = []
        for v in self.per_node_latencies.values():
            all_latencies.extend(v)
        overall_p95 = self._latency_percentile(all_latencies, 95)
        prom = self._snapshot_prometheus()

        summary = {
            "elapsed_s": round(elapsed, 3),
            "total_messages": self.total,
            "avg_rate_msg_per_s": round(rate, 3),
            "peak_1s_rate_msg_per_s": round(self._peak_1s_rate, 3),
            "disconnects": self._disconnects,
            "per_node": {
                node: {
                    "messages": count,
                    "rate_msg_per_s": round(count / elapsed, 3) if elapsed > 0 else 0.0,
                    "latency_samples": len(self.per_node_latencies.get(node, [])),
                    "latency_p50_s": round(self._latency_percentile(self.per_node_latencies.get(node, []), 50), 4),
                    "latency_p95_s": round(self._latency_percentile(self.per_node_latencies.get(node, []), 95), 4),
                }
                for node, count in sorted(self.per_node.items())
            },
            "overall_latency_p95_s": round(overall_p95, 4),
            "latency_p95_target_s": self.args.latency_p95_target,
            "prometheus_snapshot": prom,
            "timeline": self._timeline,
        }
        if self.args.json_out:
            path = self.args.json_out
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w") as fh:
                json.dump(summary, fh, indent=2)
            print(f"[*] Summary JSON written: {path}")

        if self.args.charts and _MATPLOTLIB_AVAILABLE:
            chart_path = self._resolve_chart_path()
            self._generate_charts(summary, chart_path)

    def _resolve_chart_path(self) -> Path:
        if self.args.chart_out:
            return Path(self.args.chart_out)
        if self.args.json_out:
            p = Path(self.args.json_out)
            return p.with_suffix("").with_name(p.stem + "_charts.png")
        return Path("test/results/ingest_observer_charts.png")

    def _generate_charts(self, summary: Dict[str, Any], out_path: Path) -> None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        nodes = list((summary.get("per_node") or {}).keys())
        counts = [(summary.get("per_node") or {}).get(n, {}).get("messages", 0) for n in nodes]
        rates = [(summary.get("per_node") or {}).get(n, {}).get("rate_msg_per_s", 0.0) for n in nodes]
        latencies_p95 = [(summary.get("per_node") or {}).get(n, {}).get("latency_p95_s", 0.0) for n in nodes]
        timeline = summary.get("timeline") or []

        fig = plt.figure(figsize=(16, 10))
        fig.suptitle("enyx-enterprise - Passive Ingest Observer Analytics", fontsize=15, fontweight="bold")

        # Subplot 1: per-node message count
        ax1 = fig.add_subplot(2, 2, 1)
        if nodes:
            ax1.bar(nodes, counts, color="#3498db")
            ax1.set_ylabel("Messages")
            ax1.set_title("1. Messages per Node")
            ax1.grid(axis="y", linestyle="--", alpha=0.5)
            ax1.tick_params(axis="x", rotation=30)
            for bar, c in zip(ax1.patches, counts):
                ax1.text(bar.get_x() + bar.get_width() / 2.0, bar.get_height() + max(counts) * 0.01, str(c), ha="center", va="bottom", fontsize=9)
        else:
            ax1.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax1.transAxes)
            ax1.set_title("1. Messages per Node")

        # Subplot 2: per-node average rate
        ax2 = fig.add_subplot(2, 2, 2)
        if nodes:
            ax2.bar(nodes, rates, color="#2ecc71")
            ax2.set_ylabel("msg/s")
            ax2.set_title("2. Average Ingest Rate per Node")
            ax2.grid(axis="y", linestyle="--", alpha=0.5)
            ax2.tick_params(axis="x", rotation=30)
            for bar, r in zip(ax2.patches, rates):
                ax2.text(bar.get_x() + bar.get_width() / 2.0, bar.get_height() + max(rates) * 0.01, f"{r:.2f}", ha="center", va="bottom", fontsize=9)
        else:
            ax2.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax2.transAxes)
            ax2.set_title("2. Average Ingest Rate per Node")

        # Subplot 3: total messages over time (from timeline)
        ax3 = fig.add_subplot(2, 2, 3)
        if timeline:
            xs = [t[0] for t in timeline]
            ys = [t[1] for t in timeline]
            ax3.plot(xs, ys, marker="o", color="#2980b9", linewidth=2.5, label="Cumulative Messages")
            ax3.set_xlabel("Elapsed (s)")
            ax3.set_ylabel("Total Messages")
            ax3.set_title("3. Cumulative Ingest Over Time")
            ax3.grid(True, linestyle="--", alpha=0.5)
            ax3.legend(loc="upper left")
        else:
            ax3.text(0.5, 0.5, "No timeline data", ha="center", va="center", transform=ax3.transAxes)
            ax3.set_title("3. Cumulative Ingest Over Time")

        # Subplot 4: latency P95 per node + target line (ms scale)
        ax4 = fig.add_subplot(2, 2, 4)
        if nodes and any(v > 0 for v in latencies_p95):
            latencies_p95_ms = [v * 1000.0 for v in latencies_p95]
            x = np.arange(len(nodes))
            ax4.bar(x, latencies_p95_ms, color="#9b59b6")
            target_ms = summary.get("latency_p95_target_s", 2.0) * 1000.0
            ax4.axhline(target_ms, color="#e74c3c", linestyle="--", linewidth=2, label=f"Target P95={target_ms:.0f} ms")
            ax4.set_xticks(x)
            ax4.set_xticklabels(nodes, rotation=30, ha="right", fontsize=9)
            ax4.set_ylabel("Latency P95 (ms)")
            ax4.set_title("4. MQTT Publish-to-Subscribe Latency P95 per Node")
            ax4.grid(axis="y", linestyle="--", alpha=0.5)
            ax4.legend(loc="upper right")
            for i, v in enumerate(latencies_p95_ms):
                if v > 0:
                    ax4.text(i, v + max(latencies_p95_ms) * 0.02, f"{v:.1f} ms", ha="center", va="bottom", fontsize=9)
        else:
            ax4.text(0.5, 0.5, "No latency samples (ts_publish missing in payload)", ha="center", va="center", transform=ax4.transAxes)
            ax4.set_title("4. MQTT Publish-to-Subscribe Latency P95 per Node")

        plt.tight_layout(rect=[0, 0, 1, 0.96])
        plt.savefig(out_path, dpi=300)
        plt.close()
        print(f"[*] Ingest Observer Charts generated: {out_path}")

    def stop(self) -> None:
        self._running = False


def main() -> int:
    args = parse_args()
    observer = IngestObserver(args)

    def _sigint(_sig, _frame):
        observer.stop()

    signal.signal(signal.SIGINT, _sigint)
    observer.start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
