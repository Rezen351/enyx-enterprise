"""Per-instance configuration and identity management for the firmware simulator.

Each cloned device gets its own JSON config file under ``instances/``. The
identity (node_id, mac, fw_version) is written once and stays FIXED for the
life of that instance, so you can run many clones that all behave like real,
distinct ESP32 nodes while sharing the same broker.
"""

from __future__ import annotations

import json
import os
import random
import re
import string
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Defaults — mirror firmware/aeroponic-node/include/Config.h & HardwareManager
# ---------------------------------------------------------------------------

TOPIC_PREFIX = "smartfarm"
DEFAULT_FW_VERSION = "1.0.0"
DEFAULT_PUBLISH_INTERVAL = 5  # seconds
DEFAULT_MQTT = {"server": "tcp://mosquitto:1883", "port": 1883, "user": "esp32", "pass": "esp32pass", "use_tls": False}

# Default virtual pin layout — mirrors the real node ECE334219870 so a clone
# publishes an *identical* payload structure (digital inputs/outputs + cwt modbus).
DEFAULT_INPUTS = [
    {"pin": 34, "name": "input1", "type": "DIGITAL", "pull": "NONE",
     "debounce_ms": 0, "interrupt": "NONE", "analog_min": 0, "analog_max": 0, "invert": False},
    {"pin": 35, "name": "input2", "type": "DIGITAL", "pull": "NONE",
     "debounce_ms": 0, "interrupt": "NONE", "analog_min": 0, "analog_max": 0, "invert": False},
    {"pin": 32, "name": "input3", "type": "DIGITAL", "pull": "NONE",
     "debounce_ms": 0, "interrupt": "NONE", "analog_min": 0, "analog_max": 0, "invert": False},
    {"pin": 33, "name": "input4", "type": "DIGITAL", "pull": "NONE",
     "debounce_ms": 0, "interrupt": "NONE", "analog_min": 0, "analog_max": 0, "invert": False},
]

DEFAULT_OUTPUTS = [
    {"pin": 25, "name": "load1", "type": "DIGITAL"},
    {"pin": 26, "name": "load2", "type": "DIGITAL"},
    {"pin": 27, "name": "load3", "type": "DIGITAL"},
    {"pin": 14, "name": "load4", "type": "DIGITAL"},
    {"pin": 12, "name": "buzzer", "type": "DIGITAL"},
]

# Sample RS485 devices so modbus telemetry is populated out of the box.
DEFAULT_MODBUS = [
    {
        "name": "cwt1",
        "slave_id": 1,
        "baudrate": 9600,
        "registers": [
            {"address": 0, "name": "hum", "type": "HOLDING", "multiplier": 1.0},
            {"address": 1, "name": "temp", "type": "HOLDING", "multiplier": 1.0},
        ],
    },
    {
        "name": "cwt2",
        "slave_id": 2,
        "baudrate": 9600,
        "registers": [
            {"address": 0, "name": "hum", "type": "HOLDING", "multiplier": 1.0},
            {"address": 1, "name": "temp", "type": "HOLDING", "multiplier": 1.0},
        ],
    },
]

DEFAULT_LOCAL_CONTROL_RULES = []


def _random_mac() -> str:
    return ":".join(
        "".join(random.choices(string.hexdigits[:16].upper(), k=2)) for _ in range(6)
    )


def _next_node_id(instances_dir: str) -> str:
    """Find the lowest unused node-NN id so clones get a stable, distinct id."""
    used = set()
    if os.path.isdir(instances_dir):
        for fn in os.listdir(instances_dir):
            m = re.match(r"(node-\d+)\.json$", fn)
            if m:
                used.add(m.group(1))
    n = 1
    while True:
        candidate = f"node-{n:02d}"
        if candidate not in used:
            return candidate
        n += 1


@dataclass
class InstanceConfig:
    node_id: str
    mac: str = ""
    fw_version: str = DEFAULT_FW_VERSION
    mqtt: dict[str, Any] = field(default_factory=lambda: dict(DEFAULT_MQTT))
    publish_interval: int = DEFAULT_PUBLISH_INTERVAL
    inputs: list[dict] = field(default_factory=lambda: [dict(i) for i in DEFAULT_INPUTS])
    outputs: list[dict] = field(default_factory=lambda: [dict(o) for o in DEFAULT_OUTPUTS])
    modbus: list[dict] = field(default_factory=lambda: [dict(m) for m in DEFAULT_MODBUS])
    local_control_rules: list[dict] = field(default_factory=lambda: [dict(r) for r in DEFAULT_LOCAL_CONTROL_RULES])
    paired: bool = False
    # simulated baselines so values look believable per sensor
    sim: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "mac": self.mac,
            "fw_version": self.fw_version,
            "mqtt": self.mqtt,
            "publish_interval": self.publish_interval,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "modbus": self.modbus,
            "local_control_rules": self.local_control_rules,
            "paired": self.paired,
            "sim": self.sim,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "InstanceConfig":
        cfg = cls(
            node_id=d["node_id"],
            mac=d.get("mac", ""),
            fw_version=d.get("fw_version", DEFAULT_FW_VERSION),
            mqtt={**DEFAULT_MQTT, **d.get("mqtt", {})},
            publish_interval=d.get("publish_interval", DEFAULT_PUBLISH_INTERVAL),
            inputs=d.get("inputs", [dict(i) for i in DEFAULT_INPUTS]),
            outputs=d.get("outputs", [dict(o) for o in DEFAULT_OUTPUTS]),
            modbus=d.get("modbus", []),
            local_control_rules=d.get("local_control_rules", [dict(r) for r in DEFAULT_LOCAL_CONTROL_RULES]),
            paired=d.get("paired", False),
            sim=d.get("sim", {}),
        )
        if not cfg.mac:
            cfg.mac = _random_mac()
        return cfg


def instances_dir() -> str:
    base = os.environ.get("FIRMWARE_SIM_HOME")
    if base:
        return base
    # firmware-sim/instances relative to this file's package root
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(here, "instances")


def instance_path(node_id: str) -> str:
    return os.path.join(instances_dir(), f"{node_id}.json")


def list_instances() -> list[str]:
    d = instances_dir()
    if not os.path.isdir(d):
        return []
    return sorted(
        re.sub(r"\.json$", "", fn) for fn in os.listdir(d) if re.match(r"node-.*\.json$", fn)
    )


def create_instance(node_id: str | None = None, base: InstanceConfig | None = None,
                    mqtt_override: dict | None = None) -> InstanceConfig:
    """Create (and persist) a new instance with a FIXED identity.

    If ``node_id`` is None a stable, unused node-NN id is generated. The MAC is
    randomly generated once and stored, so every clone is permanently distinct.
    """
    d = instances_dir()
    os.makedirs(d, exist_ok=True)

    if node_id is None:
        node_id = _next_node_id(d)

    if base is None:
        cfg = InstanceConfig(node_id=node_id, mac=_random_mac())
    else:
        cfg = InstanceConfig(
            node_id=node_id,
            mac=_random_mac(),
            fw_version=base.fw_version,
            mqtt=dict(base.mqtt),
            publish_interval=base.publish_interval,
            inputs=[dict(i) for i in base.inputs],
            outputs=[dict(o) for o in base.outputs],
            modbus=[dict(m) for m in base.modbus],
            local_control_rules=[dict(r) for r in base.local_control_rules],
            sim=dict(base.sim),
        )

    if mqtt_override:
        cfg.mqtt.update(mqtt_override)

    save_instance(cfg)
    return cfg


def save_instance(cfg: InstanceConfig) -> None:
    os.makedirs(instances_dir(), exist_ok=True)
    with open(instance_path(cfg.node_id), "w") as f:
        json.dump(cfg.to_dict(), f, indent=2)


def load_instance(node_id: str) -> InstanceConfig | None:
    p = instance_path(node_id)
    if not os.path.isfile(p):
        return None
    with open(p) as f:
        return InstanceConfig.from_dict(json.load(f))


def delete_instance(node_id: str) -> bool:
    p = instance_path(node_id)
    if os.path.isfile(p):
        os.remove(p)
        return True
    return False
