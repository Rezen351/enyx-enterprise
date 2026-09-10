"""MQTT firmware simulator core.

Reproduces the ESP32 aeroponic-node MQTT contract so the rest of the
microservice stack (Module discovery/auto-register, telemetry ingest, Control
commands, WS live) can be exercised end-to-end without real hardware.

Topics (prefix ``smartfarm``), exactly as the firmware / testing doc:
  * smartfarm/discovery                 -> publish on connect (node_id, mac, ip, fw, status)
  * smartfarm/status/<node_id>          -> LWT (offline) + retained online status
  * smartfarm/<node_id>/telemetry       -> periodic telemetry payload
  * smartfarm/actuator/<node_id>        -> SUBSCRIBE: set_output commands -> confirm
  * smartfarm/<node_id>/confirm         -> ACK with req_id, target, value, status
  * smartfarm/<node_id>/alert           -> emergency shutdown alert
  * smartfarm/<node_id>/pair            -> SUBSCRIBE: server pairing handshake
  * smartfarm/<node_id>/paired          -> publish pairing state
  * smartfarm/<node_id>/sim             -> SUBSCRIBE: test hooks (inject/emergency)
"""

from __future__ import annotations

import json
import logging
import random
import socket
import threading
import time
from typing import Any

import paho.mqtt.client as mqtt

from .config import TOPIC_PREFIX
from .hardware import VirtualHardware

logger = logging.getLogger("firmware_sim")

_FW_START = time.time()


def _uptime_s() -> int:
    return int(time.time() - _FW_START)


class FirmwareSimulator:
    def __init__(self, cfg: Any) -> None:
        self.cfg = cfg
        self.hw = VirtualHardware(cfg)
        self.node_id = cfg.node_id
        self.client: mqtt.Client | None = None
        self._stop = threading.Event()
        self._telemetry_thread: threading.Thread | None = None
        self.paired = bool(cfg.paired)
        self._local_ip_cache: str | None = None
        self._publish_count = 0

    # ---- topic helpers ----------------------------------------------------
    def t(self, suffix: str) -> str:
        return f"{TOPIC_PREFIX}/{suffix}"

    def _status_topic(self) -> str:
        return self.t(f"status/{self.node_id}")

    def _discovery_topic(self) -> str:
        return self.t("discovery")

    def _telemetry_topic(self) -> str:
        return self.t(f"{self.node_id}/telemetry")

    def _actuator_topic(self) -> str:
        return self.t(f"actuator/{self.node_id}")

    def _confirm_topic(self) -> str:
        return self.t(f"{self.node_id}/confirm")

    def _alert_topic(self) -> str:
        return self.t(f"{self.node_id}/alert")

    def _pair_topic(self) -> str:
        return self.t(f"{self.node_id}/pair")

    def _paired_topic(self) -> str:
        return self.t(f"{self.node_id}/paired")

    def _sim_topic(self) -> str:
        return self.t(f"{self.node_id}/sim")

    # ---- connect / lifecycle ---------------------------------------------
    def connect(self) -> None:
        m = self.cfg.mqtt
        client_id = f"SmartFarmNode-{self.node_id}"
        self.client = mqtt.Client(client_id=client_id, clean_session=False)
        if m.get("user"):
            self.client.username_pw_set(m["user"], m.get("pass", ""))
        # LWT: retained offline status published automatically on drop
        lwt = json.dumps({"status": "offline", "mac": self.cfg.mac})
        self.client.will_set(self._status_topic(), lwt, qos=1, retain=True)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

        host, port = self._parse_server(m["server"], m["port"])
        logger.info("[%s] connecting to %s:%s", self.node_id, host, port)
        self.client.connect(host, port, keepalive=30)
        self.client.loop_start()

    @staticmethod
    def _parse_server(server: str, port: int):
        s = server.replace("tcp://", "").replace("ssl://", "")
        if ":" in s:
            h, p = s.split(":", 1)
            return h, int(p)
        return s, int(port)

    def _on_connect(self, client, userdata, flags, rc):
        if rc != 0:
            logger.error("[%s] connect failed rc=%s", self.node_id, rc)
            return
        logger.info("[%s] connected", self.node_id)
        client.subscribe(self._actuator_topic(), qos=1)
        client.subscribe(self._pair_topic(), qos=1)
        client.subscribe(self._sim_topic(), qos=1)
        # retained online status (mirrors MqttManager online publish)
        online = json.dumps({
            "status": "online", "mac": self.cfg.mac,
            "ip": self._local_ip(), "fw": self.cfg.fw_version,
        })
        client.publish(self._status_topic(), online, qos=1, retain=True)
        self._publish_discovery()
        if self.paired:
            client.publish(self._paired_topic(),
                           json.dumps({"node_id": self.node_id, "paired": True}), qos=1)

    def _on_disconnect(self, client, userdata, rc):
        logger.warning("[%s] disconnected rc=%s", self.node_id, rc)

    def _local_ip(self) -> str:
        if self._local_ip_cache is not None:
            return self._local_ip_cache
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            self._local_ip_cache = ip
            return ip
        except Exception:
            return "127.0.0.1"

    def _publish_discovery(self) -> None:
        payload = {
            "node_id": self.node_id,
            "mac": self.cfg.mac,
            "ip": self._local_ip(),
            "fw_version": self.cfg.fw_version,
            "status": "online",
            "paired": self.paired,
        }
        self.client.publish(self._discovery_topic(), json.dumps(payload), qos=0)
        logger.info("[%s] discovery published (mac=%s)", self.node_id, self.cfg.mac)

    # ---- incoming commands ------------------------------------------------
    def _on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            try:
                doc = json.loads(msg.payload.decode())
            except Exception:
                logger.warning("[%s] non-JSON on %s", self.node_id, topic)
                return

            if topic == self._actuator_topic():
                self._handle_actuator(doc)
            elif topic == self._pair_topic():
                self._handle_pair(doc)
            elif topic == self._sim_topic():
                self._handle_sim(doc)
        except Exception as exc:  # never kill the loop thread
            logger.exception("[%s] message handling error: %s", self.node_id, exc)

    def _handle_actuator(self, doc: dict) -> None:
        if self.paired is False and doc.get("action") != "set_output":
            pass  # firmware always executes set_output; pairing is server-side
        action = doc.get("action", "")
        target = doc.get("target", "")
        value = int(doc.get("value", 0))
        if action == "set_output" and target:
            ok = self.hw.set_output(target, value)
            logger.info("[%s] actuator %s %s -> %s", self.node_id, action, target, value)
            if doc.get("req_id") is not None:
                self._publish_confirm(doc["req_id"], target, value,
                                      "executed" if ok else "target_not_found")
        elif action == "emergency_stop":
            self.hw.trigger_emergency()
            self._publish_alert("EMERGENCY_SHUTDOWN")
            logger.warning("[%s] EMERGENCY STOP (remote)", self.node_id)
            if doc.get("req_id") is not None:
                self._publish_confirm(doc["req_id"], "", 0, "emergency")

    def _publish_confirm(self, req_id: Any, target: str, value: int, status: str) -> None:
        payload = {
            "req_id": req_id, "target": target, "value": value, "status": status,
        }
        self.client.publish(self._confirm_topic(), json.dumps(payload), qos=1)

    def _handle_pair(self, doc: dict) -> None:
        now_paired = bool(doc.get("paired", doc.get("action") == "pair"))
        if now_paired != self.paired:
            self.paired = now_paired
            self.cfg.paired = now_paired
            from .config import save_instance
            save_instance(self.cfg)
        self.client.publish(self._paired_topic(),
                            json.dumps({"node_id": self.node_id, "paired": self.paired}), qos=1)
        logger.info("[%s] pairing -> %s", self.node_id, "paired" if self.paired else "unpaired")

    def _handle_sim(self, doc: dict) -> None:
        action = doc.get("action", "")
        if action == "emergency":
            self.hw.trigger_emergency()
            self._publish_alert("EMERGENCY_SHUTDOWN")
            logger.warning("[%s] EMERGENCY (sim)", self.node_id)
        elif action == "clear_emergency":
            self.hw.clear_emergency()
        elif action == "set_input":
            # test hook: force an input's engineering value for one cycle
            name = doc.get("target")
            val = float(doc.get("value", 0))
            if name:
                self.hw.force_input(name, val)
                logger.info("[%s] forced input %s=%s", self.node_id, name, val)
        elif action == "set_output":
            ok = self.hw.set_output(doc.get("target", ""), int(doc.get("value", 0)))
            logger.info("[%s] sim set_output %s=%s (%s)", self.node_id,
                        doc.get("target"), doc.get("value"), "ok" if ok else "unknown target")
        elif action == "discover":
            self._publish_discovery()

    def _publish_alert(self, kind: str) -> None:
        payload = {"alert": kind, "node_id": self.node_id, "uptime_s": _uptime_s()}
        self.client.publish(self._alert_topic(), json.dumps(payload), qos=1)

    # ---- telemetry loop ---------------------------------------------------
    def _build_telemetry(self) -> dict:
        # Sample once: firmware-shaped raw inputs + engineering sensors
        inputs_raw, sensors_eng = self.hw.read_all()

        # emergency latch from physical emergency button. The button is
        # INPUT_PULLUP + invert, so it is pressed when the raw (pre-invert)
        # pin goes LOW (0). Compute that from the post-invert value.
        if not self.hw.emergency:
            emerg = next((i for i in self.cfg.inputs if i["name"] == "btn_emergency"), None)
            if emerg:
                post = inputs_raw.get("btn_emergency", 1)
                pre = post if not emerg.get("invert") else (1 - post)
                if pre == 0:  # raw pin LOW = button pressed
                    self.hw.trigger_emergency()
                    self._publish_alert("EMERGENCY_SHUTDOWN")

        # local-control rules compare engineering values to thresholds
        fired = self.hw.evaluate_local_control(sensors_eng)

        # ``telemetry`` object is byte-compatible with the ESP32 firmware
        # (HardwareManager.cpp): inputs/outputs/modbus are flat scalar values.
        doc = {
            "node_id": self.node_id,
            "mac": self.cfg.mac,
            "fw_version": self.cfg.fw_version,
            "ts_publish": int(time.time() * 1000),
            "network": {
                "ssid": "Aeroponik 1",
                "ip_address": self._local_ip(),
                "wifi_rssi": random.randint(-70, -40),
            },
            "device_info": {
                "uptime_s": _uptime_s(),
                "cpu_freq_mhz": 240,
                "free_heap_kb": random.randint(180, 260),
                "flash_size_mb": 4,
            },
            "connection_stats": {
                "mqtt_connected": bool(self.client and self.client.is_connected()),
                "uptime_s": _uptime_s(),
            },
            "telemetry": {
                "inputs": inputs_raw,
                "outputs": dict(self.hw.output_states),
                "modbus": self.hw.poll_modbus(),
            },
        }
        return doc, fired

    def _telemetry_loop(self) -> None:
        rate = getattr(self.cfg, "publish_rate_hz", 0.0)
        if rate and rate > 0:
            interval = 1.0 / max(0.1, rate)
        else:
            interval = max(1, int(self.cfg.publish_interval))
        next_time = time.time() + interval
        while not self._stop.is_set():
            if self.client and self.client.is_connected():
                doc, fired = self._build_telemetry()
                for f in fired:
                    logger.info("[%s] local-control: %s", self.node_id, f)
                self.client.publish(self._telemetry_topic(), json.dumps(doc), qos=0)
                self._publish_count += 1
            now = time.time()
            sleep_time = next_time - now
            if sleep_time > 0:
                self._stop.wait(sleep_time)
            next_time += interval

    # ---- run / stop -------------------------------------------------------
    def run(self) -> None:
        self.connect()
        self._telemetry_thread = threading.Thread(target=self._telemetry_loop, daemon=True)
        self._telemetry_thread.start()
        logger.info("[%s] running (Ctrl+C to stop) interval=%ss",
                    self.node_id, self.cfg.publish_interval)
        try:
            while not self._stop.is_set():
                time.sleep(0.5)
        except KeyboardInterrupt:
            logger.info("[%s] interrupted", self.node_id)
        finally:
            self.stop()

    def stop(self) -> None:
        self._stop.set()
        if self.client:
            try:
                self.client.publish(self._status_topic(),
                                    json.dumps({"status": "offline", "mac": self.cfg.mac}),
                                    qos=1, retain=True)
                self.client.disconnect()
            except Exception:
                pass
            self.client.loop_stop()
