import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_env():
    env_path = ROOT / ".env"
    if env_path.exists():
        with env_path.open() as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())


_load_env()

BASE_URL = os.getenv("KONG_PUBLIC_URL", "http://localhost:8000").rstrip("/")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090").rstrip("/")
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3000").rstrip("/")

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin1234")

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC_PREFIX = os.getenv("MQTT_TOPIC_PREFIX", "smartfarm")

WS_PATH = "/v1/ws/system-status"

JWT_SECRET = os.getenv("JWT_SECRET", "")

ENDPOINTS = [
    {
        "name": "health-check",
        "method": "GET",
        "path": "/v1/health",
        "auth": False,
        "weight": 15,
        "body": None,
    },
    {
        "name": "auth-me",
        "method": "GET",
        "path": "/v1/auth/me",
        "auth": True,
        "weight": 12,
        "body": None,
    },
    {
        "name": "modules-list",
        "method": "GET",
        "path": "/v1/modules",
        "auth": True,
        "weight": 12,
        "body": None,
    },
    {
        "name": "nodes-list",
        "method": "GET",
        "path": "/v1/nodes",
        "auth": True,
        "weight": 8,
        "body": None,
    },
    {
        "name": "analytics-nodes",
        "method": "GET",
        "path": "/v1/analytics/nodes",
        "auth": True,
        "weight": 8,
        "body": None,
    },
    {
        "name": "control-commands",
        "method": "GET",
        "path": "/v1/control/commands?node_id=node-1",
        "auth": True,
        "weight": 6,
        "body": None,
    },
    {
        "name": "streams-list",
        "method": "GET",
        "path": "/v1/streams",
        "auth": True,
        "weight": 6,
        "body": None,
    },
    {
        "name": "ml-models",
        "method": "GET",
        "path": "/v1/ml/models",
        "auth": True,
        "weight": 4,
        "body": None,
    },
    {
        "name": "export-nodes",
        "method": "GET",
        "path": "/v1/export/v1/nodes",
        "auth": True,
        "weight": 4,
        "body": None,
    },
    {
        "name": "analytics-metrics",
        "method": "GET",
        "path": "/v1/analytics/metrics?node_id=node-1&metric=temperature&interval=1h",
        "auth": True,
        "weight": 6,
        "body": None,
    },
    {
        "name": "control-outputs",
        "method": "GET",
        "path": "/v1/control/outputs?node_id=node-1",
        "auth": True,
        "weight": 4,
        "body": None,
    },
    {
        "name": "alerts-list",
        "method": "GET",
        "path": "/v1/alerts",
        "auth": True,
        "weight": 4,
        "body": None,
    },
    {
        "name": "audit-logs",
        "method": "GET",
        "path": "/v1/audit/logs?limit=10",
        "auth": True,
        "weight": 4,
        "body": None,
    },
    {
        "name": "notification-logs",
        "method": "GET",
        "path": "/v1/notifications/logs?limit=10",
        "auth": True,
        "weight": 3,
        "body": None,
    },
    {
        "name": "webhook-logs",
        "method": "GET",
        "path": "/v1/webhook/logs?limit=10",
        "auth": True,
        "weight": 3,
        "body": None,
    },
    {
        "name": "snapshots-list",
        "method": "GET",
        "path": "/v1/snapshots",
        "auth": True,
        "weight": 4,
        "body": None,
    },
    {
        "name": "ml-detections",
        "method": "GET",
        "path": "/v1/ml/detections",
        "auth": True,
        "weight": 4,
        "body": None,
    },
    {
        "name": "export-meta",
        "method": "GET",
        "path": "/v1/export/v1/meta?node_id=node-1&metric=temperature",
        "auth": True,
        "weight": 4,
        "body": None,
    },
    {
        "name": "dlq-messages",
        "method": "GET",
        "path": "/v1/dlq/messages",
        "auth": True,
        "weight": 3,
        "body": None,
    },
    {
        "name": "ppo-controller-health",
        "method": "GET",
        "path": "/v1/ppo_controller/health",
        "auth": False,
        "weight": 3,
        "body": None,
    },
    {
        "name": "ppo-control-health",
        "method": "GET",
        "path": "/v1/ppo/health",
        "auth": False,
        "weight": 3,
        "body": None,
    },
]


def weighted_endpoint_pool():
    pool = []
    for ep in ENDPOINTS:
        pool.extend([ep] * ep["weight"])
    return pool
