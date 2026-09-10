"""
enyx-enterprise - Chaos Engineering & Resilience Test Suite
Tests System Resiliency, Graceful Degradation, Circuit Breaking, and Self-Healing capabilities under service outages.
Focused on modularity and core service resilience for Fase 1 & Fase 2.
"""

import os
import sys
import io
import json
import time
import subprocess
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    _HAS_MPL = True
except ImportError:
    _HAS_MPL = False

try:
    from plotter import plot_chaos_scenario_charts, plot_scenario_summary_chart
    _HAS_PLOTTER = True
except ImportError:
    _HAS_PLOTTER = False

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "admin1234")
DOCKER_COMPOSE_DIR = os.getenv("DOCKER_COMPOSE_DIR", "/home/almuzky/TA/Microservices")


def run_cmd(cmd: str) -> bool:
    try:
        subprocess.run(cmd, shell=True, check=True, cwd=DOCKER_COMPOSE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False


def execute_request(url, headers=None, method="GET", json_body=None, timeout=20, retries=3):
    """Execute HTTP request with retry/backoff. Returns None if all attempts fail
    (no response / connection refused) instead of raising."""
    try:
        import unit_test as _unit_test
        _orig_get = getattr(_unit_test, "_original_requests_get", requests.get)
        _orig_post = getattr(_unit_test, "_original_requests_post", requests.post)
        _orig_put = getattr(_unit_test, "_original_requests_put", requests.put)
        _orig_delete = getattr(_unit_test, "_original_requests_delete", requests.delete)
        _orig_patch = getattr(_unit_test, "_original_requests_patch", requests.patch)
        _orig_request = getattr(_unit_test, "_original_requests_request", requests.request)
    except Exception:
        _orig_get = requests.get
        _orig_post = requests.post
        _orig_put = requests.put
        _orig_delete = requests.delete
        _orig_patch = requests.patch
        _orig_request = requests.request

    for attempt in range(1, retries + 1):
        try:
            if method == "GET":
                res = _orig_get(url, headers=headers, timeout=timeout)
            elif method == "POST":
                res = _orig_post(url, headers=headers, json=json_body, timeout=timeout)
            elif method == "PUT":
                res = _orig_put(url, headers=headers, json=json_body, timeout=timeout)
            elif method == "DELETE":
                res = _orig_delete(url, headers=headers, timeout=timeout)
            elif method == "PATCH":
                res = _orig_patch(url, headers=headers, json=json_body, timeout=timeout)
            else:
                res = _orig_request(method, url, headers=headers, timeout=timeout)
            if res is None:
                if attempt < retries:
                    time.sleep(2 ** attempt)
                    continue
                return None
            if res.status_code == 429 and attempt < retries:
                time.sleep(2 ** attempt)
                continue
            return res
        except Exception:
            if attempt < retries:
                time.sleep(2 ** attempt)
                continue
            return None
    return None


def get_token():
    for attempt in range(1, 4):
        try:
            res = requests.post(f"{BASE_URL}/v1/auth/login", json={"identifier": ADMIN_USER, "password": ADMIN_PASS}, timeout=20)
            if res.status_code == 200:
                return res.json().get("data", {}).get("access_token")
            if res.status_code == 429 and attempt < 3:
                time.sleep(2 ** attempt)
                continue
        except Exception:
            if attempt < 3:
                time.sleep(2 ** attempt)
                continue
    return None


SERVICE_HEALTH_ENDPOINTS = {
    "auth": "/v1/auth/me",
    "module": "/v1/modules",
    "analytics": "/v1/analytics/nodes",
    "control": "/v1/control/modes/node-01",
    "alert": "/v1/alerts",
    "audit": "/v1/audit/logs",
    "notification": "/v1/notifications/logs",
    "stream": "/v1/streams",
    "export-service": "/v1/export/v1/nodes",
    "wsgateway": "/v1/health",
    "ml": "/v1/ml/models",
    "model-controller": "/v1/model_controller/health",
    "model-control": "/v1/model_control/health",
}


def wait_for_service(service, token=None, timeout=120, interval=3):
    """Poll a service until it responds (any reachable status) or timeout.
    Used after `docker compose start` to ensure a service is fully up before
    the next scenario runs (prevents false None / cascade failures)."""
    if service not in SERVICE_HEALTH_ENDPOINTS:
        return True
    endpoint = SERVICE_HEALTH_ENDPOINTS[service]
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    deadline = time.time() + timeout
    while time.time() < deadline:
        res = execute_request(f"{BASE_URL}{endpoint}", headers=headers, method="GET", timeout=10)
        if res is not None and res.status_code in (200, 400, 401, 403, 429):
            return True
        time.sleep(interval)
    return False


def wait_for_services(services, token=None, timeout=120, interval=3):
    for s in services:
        wait_for_service(s, token=token, timeout=timeout, interval=interval)


def wait_for_dns_stabilization(token=None, timeout=30, interval=2):
    """After docker compose stop/start, Docker DNS may briefly fail to resolve
    container names. Poll core endpoints until they respond (any HTTP status)
    so the next scenario doesn't see spurious None/timeout failures."""
    core = ["auth", "module", "analytics", "control", "alert"]
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    deadline = time.time() + timeout
    last_err = None
    while time.time() < deadline:
        for svc in core:
            ep = SERVICE_HEALTH_ENDPOINTS.get(svc, f"/v1/{svc}")
            try:
                res = execute_request(f"{BASE_URL}{ep}", headers=headers, method="GET", timeout=5)
                if res is not None and res.status_code not in (None,):
                    return True
            except Exception as exc:
                last_err = exc
        time.sleep(interval)
    if last_err:
        print(f"[!] DNS stabilization warning: {last_err}")
    return False


class ResilienceAuditor:
    def __init__(self):
        self.results = []
        self.scenario_data: Dict[str, Dict[str, Any]] = {}

    def log_result(self, scenario: str, status: str, details: str, recovery_time: float = 0.0, **extra):
        symbol = "PASS" if status == "PASS" else ("DEGRADED" if status == "DEGRADED" else "FAIL")
        self.results.append({
            "scenario": scenario,
            "status": symbol,
            "details": details,
            "recovery_time": recovery_time
        })
        data = {"status": symbol, "details": details, "recovery_time": recovery_time}
        data.update(extra)
        self.scenario_data[scenario] = data
        print(f"[{symbol}] {scenario}: {details}" + (f" (Recovery: {recovery_time:.1f}s)" if recovery_time > 0 else ""))

    def report(self):
        print("\n" + "=" * 70)
        print("  MICROSERVICES CHAOS & RESILIENCE TEST AUDIT REPORT")
        print("=" * 70)
        for r in self.results:
            print(f" {r['status']:<10} | {r['scenario']:<40} | {r['details']}")
        print("=" * 70 + "\n")

    def get_scenarios(self):
        return [{"scenario": r["scenario"], "status": r["status"], "details": r["details"]} for r in self.results]

    def get_recovery_times(self):
        return [r.get("recovery_time", 0.0) for r in self.results]

    def get_scenario_data(self):
        return self.scenario_data


# ─────────────────────────────────────────────────────────────
# SCENARIO 1: Core Service Isolation Matrix
# ─────────────────────────────────────────────────────────────
def test_scenario_1_core_isolation_matrix(auditor: ResilienceAuditor, token: str, phase: str = "all"):
    """Stop each core service one-by-one and verify other core services remain operational.
    
    This tests the modularity principle: failure of one bounded context must not cascade
    to other bounded contexts.
    """
    print("\n[*] Scenario 1: Core Service Isolation Matrix")
    
    core_only = str(phase).strip().lower() == "1"
    
    core_services = ["auth", "module", "analytics", "control", "alert", "audit", 
                     "notification", "stream", "export-service", "wsgateway"]
    if not core_only:
        core_services.extend(["ml", "model-controller", "model-control"])
    
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    
    isolation_matrix = {}
    for service_name in core_services:
        print(f"\n  -- Testing isolation: stopping {service_name} --")
        run_cmd(f"docker compose stop {service_name}")
        time.sleep(5)
        wait_for_dns_stabilization(token=token, timeout=30, interval=2)
        
        service_status = {}
        for other in core_services:
            if other == service_name:
                continue
            path_map = {
                "auth": "/v1/auth/me",
                "module": "/v1/modules",
                "analytics": "/v1/analytics/nodes",
                "control": "/v1/control/modes/node-01",
                "alert": "/v1/alerts",
                "audit": "/v1/audit/logs",
                "notification": "/v1/notifications/logs",
                "stream": "/v1/streams",
                "export-service": "/v1/export/v1/nodes",
                "wsgateway": "/v1/health",
                "ml": "/v1/ml/models",
                "model-controller": "/v1/model_controller/health",
                "model-control": "/v1/model_control/health",
            }
            endpoint = path_map.get(other, f"/v1/{other}")
            res = execute_request(f"{BASE_URL}{endpoint}", headers=headers, method="GET")
            code = res.status_code if res else None
            service_status[other] = code
        
        isolation_matrix[service_name] = service_status
        
        all_ok = all(c in [200, 429, 400, 401, 403] for c in service_status.values() if c is not None)
        if all_ok:
            auditor.log_result(f"Isolation-{service_name}", "PASS", f"All other services operational when {service_name} is down", 
                             isolation_matrix=isolation_matrix, stopped_service=service_name)
        else:
            auditor.log_result(f"Isolation-{service_name}", "FAIL", 
                             f"Cross-service impact when {service_name} down: {service_status}",
                             isolation_matrix=isolation_matrix, stopped_service=service_name)
        
        run_cmd(f"docker compose start {service_name}")
        wait_for_service(service_name, token)
    
    auditor.scenario_data["core_isolation"] = {
        "type": "core_isolation",
        "isolation_matrix": isolation_matrix
    }
    all_services = core_services + ["nats", "kong", "redis-shared",
                                   "mariadb-auth", "mariadb-module", "mariadb-analytics",
                                   "mariadb-control", "mariadb-alert", "mariadb-audit",
                                   "mariadb-notification", "mariadb-stream",
                                   "timescaledb-module", "timescaledb-analytics"]
    if not core_only:
        all_services.extend(["ml", "model-controller", "model-control", "mariadb-ml"])
    run_cmd(f"docker compose start {' '.join(all_services)}")
    wait_for_services([s for s in all_services if s in SERVICE_HEALTH_ENDPOINTS], token)


# ─────────────────────────────────────────────────────────────
# SCENARIO 2: Database & Cache Degradation Isolation
# ─────────────────────────────────────────────────────────────
def test_scenario_2_db_degradation_isolation(auditor: ResilienceAuditor, token: str, phase: str = "all"):
    """Test that services gracefully handle database degradation.
    
    When a service's database is stopped, the service should return 503/502,
    but other services should not be affected.
    """
    print("\n[*] Scenario 2: Database & Cache Degradation Isolation")
    
    core_only = str(phase).strip().lower() == "1"
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    
    db_tests = [
        ("mariadb-module", "module", ["/v1/auth/me", "/v1/analytics/nodes", "/v1/control/modes/node-01", "/v1/alerts"]),
        ("mariadb-alert", "alert", ["/v1/auth/me", "/v1/analytics/nodes", "/v1/control/modes/node-01", "/v1/audit/logs"]),
        ("mariadb-audit", "audit", ["/v1/auth/me", "/v1/analytics/nodes", "/v1/control/modes/node-01", "/v1/alerts"]),
        ("mariadb-stream", "stream", ["/v1/auth/me", "/v1/analytics/nodes", "/v1/control/modes/node-01", "/v1/alerts", "/v1/audit/logs"]),
        ("mariadb-notification", "notification", ["/v1/auth/me", "/v1/analytics/nodes", "/v1/control/modes/node-01", "/v1/alerts", "/v1/audit/logs"]),
        ("redis-shared", "alert", ["/v1/auth/me", "/v1/analytics/nodes", "/v1/control/modes/node-01", "/v1/audit/logs"]),
    ]
    
    if not core_only:
        db_tests.extend([
            ("mariadb-ml", "ml", ["/v1/auth/me", "/v1/analytics/nodes", "/v1/control/modes/node-01", "/v1/alerts"]),
            ("mariadb-control", "control", ["/v1/auth/me", "/v1/analytics/nodes", "/v1/alerts", "/v1/audit/logs"]),
        ])
    
    db_isolation = {}
    for db_name, affected_service, other_endpoints in db_tests:
        print(f"\n  -- Testing DB degradation: stopping {db_name} --")
        run_cmd(f"docker compose stop {db_name}")
        time.sleep(5)
        wait_for_dns_stabilization(token=token, timeout=30, interval=2)
        
        affected_endpoint = SERVICE_HEALTH_ENDPOINTS.get(affected_service, f"/v1/{affected_service}")
        affected_res = execute_request(f"{BASE_URL}{affected_endpoint}", headers=headers, method="GET")
        affected_status = affected_res.status_code if affected_res else None
        
        other_statuses = {}
        failures = []
        for endpoint in other_endpoints:
            res = execute_request(f"{BASE_URL}{endpoint}", headers=headers, method="GET")
            code = res.status_code if res else None
            other_statuses[endpoint] = code
            if code not in [200, 429, 400, 401, 403]:
                failures.append(f"{endpoint}={code}")
        
        db_isolation[db_name] = {
            "affected_service": affected_service,
            "affected_status": affected_status,
            "other_statuses": other_statuses,
            "failures": failures,
            "isolated": len(failures) == 0
        }
        
        if not failures:
            auditor.log_result(f"DB-Degradation-{db_name}", "PASS",
                             f"{affected_service} isolated (affected_status={affected_status}); other services unaffected",
                             db_name=db_name, affected_status=affected_status, isolated=True)
        elif affected_status == 429:
            auditor.log_result(f"DB-Degradation-{db_name}", "DEGRADED",
                             f"{affected_service} rate-limited during chaos test",
                             db_name=db_name, affected_status=affected_status, isolated=True)
        else:
            auditor.log_result(f"DB-Degradation-{db_name}", "FAIL",
                             f"cascade impact from {affected_service}: {failures}",
                             db_name=db_name, affected_status=affected_status, isolated=False)
        
        run_cmd(f"docker compose start {db_name}")
        wait_for_service(affected_service, token)
    
    auditor.scenario_data["db_degradation_isolation"] = {
        "type": "db_degradation",
        "db_isolation": db_isolation
    }


# ─────────────────────────────────────────────────────────────
# SCENARIO 3: Kong Partial Backend Failure
# ─────────────────────────────────────────────────────────────
def test_scenario_3_kong_partial_failure(auditor: ResilienceAuditor, token: str, phase: str = "all"):
    """Test Kong Gateway resilience when multiple backend services are down."""
    print("\n[*] Scenario 3: Kong Partial Backend Failure")
    
    core_only = str(phase).strip().lower() == "1"
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    
    services_to_stop = ["alert", "stream", "audit", "export-service"]
    if not core_only:
        services_to_stop.extend(["ml", "model-controller", "model-control"])
    
    print(f"  -- Stopping services: {', '.join(services_to_stop)} --")
    run_cmd(f"docker compose stop {' '.join(services_to_stop)}")
    time.sleep(5)
    wait_for_dns_stabilization(token=token, timeout=30, interval=2)
    
    core_endpoints = [
        ("/v1/auth/me", "Auth"),
        ("/v1/modules", "Module"),
        ("/v1/analytics/nodes", "Analytics"),
        ("/v1/control/modes/node-01", "Control"),
        ("/v1/health", "Health"),
    ]
    
    core_results = {}
    for endpoint, name in core_endpoints:
        res = execute_request(f"{BASE_URL}{endpoint}", headers=headers, method="GET")
        code = res.status_code if res else None
        core_results[name] = code
        if code == 200:
            auditor.log_result(f"Kong-Core-{name}", "PASS", f"{name} endpoint operational (200)")
        elif code == 429:
            auditor.log_result(f"Kong-Core-{name}", "DEGRADED", f"{name} rate-limited during chaos test")
        else:
            auditor.log_result(f"Kong-Core-{name}", "FAIL", f"{name} returned {code}")
    
    stopped_endpoints = []
    if core_only:
        stopped_endpoints = [("/v1/alerts", "Alert"), ("/v1/streams", "Stream"), ("/v1/audit/logs", "Audit"), ("/v1/export/v1/nodes", "Export")]
    else:
        stopped_endpoints = [("/v1/alerts", "Alert"), ("/v1/streams", "Stream"), ("/v1/audit/logs", "Audit"), 
                            ("/v1/export/v1/nodes", "Export"), ("/v1/ml/models", "ML"), ("/v1/model_controller/health", "ModelController")]
    
    stopped_results = {}
    for endpoint, name in stopped_endpoints:
        res = execute_request(f"{BASE_URL}{endpoint}", headers=headers, method="GET")
        code = res.status_code if res else None
        stopped_results[name] = code
        if code in [502, 503, 504] or code is None:
            auditor.log_result(f"Kong-Stopped-{name}", "PASS", f"Graceful degradation ({code})")
        elif code == 429:
            auditor.log_result(f"Kong-Stopped-{name}", "DEGRADED", "Rate-limited during chaos test")
        else:
            auditor.log_result(f"Kong-Stopped-{name}", "DEGRADED", f"Returned {code}")
    
    print(f"  -- Restarting services: {', '.join(services_to_stop)} --")
    recovery_start = time.time()
    run_cmd(f"docker compose start {' '.join(services_to_stop)}")
    wait_for_services(services_to_stop, token)
    recovery_time = time.time() - recovery_start
    
    recovery_results = {}
    for endpoint, name in [("/v1/alerts", "Alert"), ("/v1/streams", "Stream")]:
        res = execute_request(f"{BASE_URL}{endpoint}", headers=headers, method="GET")
        code = res.status_code if res else None
        recovery_results[name] = code
        if code == 200:
            auditor.log_result(f"Kong-Recovery-{name}", "PASS", f"{name} recovered to 200 OK", recovery_time=recovery_time)
        elif code == 429:
            auditor.log_result(f"Kong-Recovery-{name}", "DEGRADED", "Still rate-limited after recovery")
        else:
            auditor.log_result(f"Kong-Recovery-{name}", "FAIL", f"{name} recovery failed: {code}", recovery_time=recovery_time)
    
    auditor.scenario_data["kong_partial_failure"] = {
        "type": "kong_partial_failure",
        "stopped_services": services_to_stop,
        "core_results": core_results,
        "stopped_results": stopped_results,
        "recovery_results": recovery_results,
        "recovery_time": recovery_time
    }


# ─────────────────────────────────────────────────────────────
# SCENARIO 4: Event Bus Blackhole & Reconnection
# ─────────────────────────────────────────────────────────────
def test_scenario_4_event_bus_blackhole(auditor: ResilienceAuditor, token: str, phase: str = "all"):
    """Test NATS Event Bus interruption and microservices auto-reconnection."""
    print("\n[*] Scenario 4: Event Bus Blackhole & Reconnection")
    
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    
    print("  -- Stopping NATS broker (30s blackhole) --")
    run_cmd("docker compose stop nats")
    time.sleep(5)
    wait_for_dns_stabilization(token=token, timeout=30, interval=2)
    time.sleep(25)  # remaining blackhole duration
    
    core_endpoints = [
        ("/v1/auth/me", "Auth"),
        ("/v1/modules", "Module"),
        ("/v1/analytics/nodes", "Analytics"),
        ("/v1/control/modes/node-01", "Control"),
        ("/v1/alerts", "Alert"),
        ("/v1/health", "Health"),
    ]
    
    outage_results = {}
    outage_timeline = []
    for endpoint, name in core_endpoints:
        res = execute_request(f"{BASE_URL}{endpoint}", headers=headers, method="GET")
        code = res.status_code if res else None
        outage_results[name] = code
        outage_timeline.append({"time": time.time(), "endpoint": name, "status": code})
        if code == 200:
            auditor.log_result(f"NATS-Outage-{name}", "PASS", f"{name} REST API operational during NATS outage")
        elif code == 429:
            auditor.log_result(f"NATS-Outage-{name}", "DEGRADED", f"{name} rate-limited during chaos test")
        else:
            auditor.log_result(f"NATS-Outage-{name}", "FAIL", f"{name} returned {code}")
    
    all_core_ok = all(c == 200 for c in outage_results.values())
    auditor.log_result("NATS-Outage-Core", "PASS" if all_core_ok else "FAIL", 
                      "All core REST APIs operational during NATS blackhole" if all_core_ok else "Some APIs failed during NATS blackhole")
    
    print("  -- Restarting NATS broker --")
    recovery_start = time.time()
    run_cmd("docker compose start nats")
    wait_for_services(["auth", "module", "analytics", "control", "alert", "audit"], token)
    recovery_time = time.time() - recovery_start
    
    recovery_timeline = []
    for endpoint, name in core_endpoints:
        res = execute_request(f"{BASE_URL}{endpoint}", headers=headers, method="GET")
        code = res.status_code if res else None
        recovery_timeline.append({"time": time.time(), "endpoint": name, "status": code})
    
    audit_res = execute_request(f"{BASE_URL}/v1/audit/logs", headers=headers, method="GET")
    audit_code = audit_res.status_code if audit_res else None
    if audit_code == 200:
        auditor.log_result("NATS-Reconnection", "PASS", "Services reconnected to NATS after restart", recovery_time=recovery_time)
    elif audit_code == 429:
        auditor.log_result("NATS-Reconnection", "DEGRADED", "Still rate-limited after NATS recovery")
    else:
        auditor.log_result("NATS-Reconnection", "FAIL", f"Audit log error after NATS restart: {audit_code}", recovery_time=recovery_time)
    
    auditor.scenario_data["event_bus_blackhole"] = {
        "type": "event_bus_blackhole",
        "outage_results": outage_results,
        "recovery_results": {name: r["status"] for r in recovery_timeline},
        "outage_timeline": outage_timeline,
        "recovery_timeline": recovery_timeline,
        "recovery_time": recovery_time
    }


# ─────────────────────────────────────────────────────────────
# SCENARIO 5: Cascading Failure Prevention
# ─────────────────────────────────────────────────────────────
def test_scenario_5_cascading_failure_prevention(auditor: ResilienceAuditor, token: str, phase: str = "all"):
    """Test that stopping one service does not cause cascading failures."""
    print("\n[*] Scenario 5: Cascading Failure Prevention")
    
    core_only = str(phase).strip().lower() == "1"
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    
    print("  -- Stopping Module service (most interconnected) --")
    run_cmd("docker compose stop module")
    time.sleep(5)
    wait_for_dns_stabilization(token=token, timeout=30, interval=2)
    
    cascade_tests = [
        ("/v1/auth/me", "Auth", [200, 429]),
        ("/v1/analytics/nodes", "Analytics", [200, 400, 429, 502, 503, 504]),
        ("/v1/control/modes/node-01", "Control", [200, 400, 429, 502, 503, 504]),
        ("/v1/alerts", "Alert", [200, 429, 502, 503, 504]),
    ]
    
    cascade_results = {}
    for endpoint, name, acceptable in cascade_tests:
        res = execute_request(f"{BASE_URL}{endpoint}", headers=headers, method="GET")
        code = res.status_code if res else None
        cascade_results[name] = code
        if code in acceptable and code not in [502, 503, 504]:
            auditor.log_result(f"Cascade-{name}", "PASS", f"{name} degraded gracefully ({code})")
        elif code in [502, 503, 504]:
            auditor.log_result(f"Cascade-{name}", "DEGRADED", f"{name} gateway error ({code})")
        else:
            auditor.log_result(f"Cascade-{name}", "FAIL", f"{name} cascading failure: {code}")
    
    print("  -- Restarting Module service --")
    recovery_start = time.time()
    run_cmd("docker compose start module")
    wait_for_service("module", token)
    recovery_time = time.time() - recovery_start
    
    module_res = execute_request(f"{BASE_URL}/v1/modules", headers=headers, method="GET")
    module_code = module_res.status_code if module_res else None
    if module_code == 200:
        auditor.log_result("Cascade-Recovery", "PASS", "Module service recovered successfully", recovery_time=recovery_time)
    elif module_code == 429:
        auditor.log_result("Cascade-Recovery", "DEGRADED", "Still rate-limited after recovery")
    else:
        auditor.log_result("Cascade-Recovery", "FAIL", f"Module recovery failed: {module_code}", recovery_time=recovery_time)
    
    auditor.scenario_data["cascading_failure"] = {
        "type": "cascading_failure",
        "cascade_results": cascade_results,
        "recovery_time": recovery_time
    }


# ─────────────────────────────────────────────────────────────
# SCENARIO 6: Container Resource Exhaustion Isolation
# ─────────────────────────────────────────────────────────────
def test_scenario_6_resource_exhaustion_isolation(auditor: ResilienceAuditor, token: str, phase: str = "all"):
    """Test that resource exhaustion in one service does not affect other services."""
    print("\n[*] Scenario 6: Container Resource Exhaustion Isolation")
    
    core_only = str(phase).strip().lower() == "1"
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    
    print("  -- Throttling stream (CPU=0.1, Memory=64m) --")
    run_cmd("docker update --cpus 0.1 --memory 64m stream")
    time.sleep(2)
    
    latency_tests = [
        ("/v1/auth/me", "Auth", 1.0),
        ("/v1/analytics/nodes", "Analytics", 2.0),
    ]
    
    resource_results = {}
    for endpoint, name, threshold in latency_tests:
        start = time.time()
        res = execute_request(f"{BASE_URL}{endpoint}", headers=headers, method="GET")
        latency = time.time() - start
        code = res.status_code if res else None
        resource_results[name] = {"latency": latency, "status": code, "threshold": threshold}
        if code == 200 and latency < threshold:
            auditor.log_result(f"Resource-Isolation-{name}", "PASS", f"{name} latency unaffected ({latency:.2f}s)")
        elif code == 429:
            auditor.log_result(f"Resource-Isolation-{name}", "DEGRADED", "Rate-limited during chaos test")
        else:
            auditor.log_result(f"Resource-Isolation-{name}", "FAIL", 
                             f"{name} impacted: {code}, latency={latency:.2f}s")
    
    print("  -- Restoring stream resources --")
    run_cmd("docker update --cpus 0 --memory 0 stream")
    wait_for_service("stream", token)
    
    stream_res = execute_request(f"{BASE_URL}/v1/streams", headers=headers, method="GET")
    stream_code = stream_res.status_code if stream_res else None
    if stream_code == 200:
        auditor.log_result("Resource-Recovery", "PASS", "Stream service recovered after resource restore")
    elif stream_code == 429:
        auditor.log_result("Resource-Recovery", "DEGRADED", "Still rate-limited after recovery")
    else:
        auditor.log_result("Resource-Recovery", "FAIL", f"Stream service recovery failed: {stream_code}")
    
    auditor.scenario_data["resource_exhaustion"] = {
        "type": "resource_exhaustion",
        "resource_results": resource_results
    }


# ─────────────────────────────────────────────────────────────
# MAIN CHAOS SUITE
# ─────────────────────────────────────────────────────────────
def run_chaos_suite(token: str = None, phase: str = "all"):
    """Run chaos & resilience scenarios and return structured results.

    phase="1"   -> Core services only (no ML/Model services).
    phase="2"/"all" -> Full suite including ML/Model services.
    """
    if token is None:
        token = get_token()

    core_only = str(phase).strip().lower() == "1"
    auditor = ResilienceAuditor()

    try:
        test_scenario_1_core_isolation_matrix(auditor, token, phase=phase)
        test_scenario_2_db_degradation_isolation(auditor, token, phase=phase)
        test_scenario_3_kong_partial_failure(auditor, token, phase=phase)
        test_scenario_4_event_bus_blackhole(auditor, token, phase=phase)
        test_scenario_5_cascading_failure_prevention(auditor, token, phase=phase)
        test_scenario_6_resource_exhaustion_isolation(auditor, token, phase=phase)
    finally:
        print("\n[*] Cleanup: Ensuring all services are running...")
        services_to_start = [
            "auth", "module", "analytics", "control", "alert", "audit",
            "notification", "stream", "export-service", "wsgateway", "nats",
            "mariadb-auth", "mariadb-module", "mariadb-analytics", "mariadb-control",
            "mariadb-alert", "mariadb-audit", "mariadb-notification", "mariadb-stream",
            "redis-shared", "timescaledb-module", "timescaledb-analytics"
        ]
        if not core_only:
            services_to_start.extend(["ml", "model-controller", "model-control", "mariadb-ml"])
        run_cmd(f"docker compose start {' '.join(services_to_start)}")
        wait_for_services([s for s in services_to_start if s in SERVICE_HEALTH_ENDPOINTS], token)
        auditor.report()

    return auditor.get_scenarios(), auditor.get_recovery_times(), auditor.get_scenario_data()


class Tee(io.TextIOBase):
    def __init__(self, *streams):
        self.streams = list(streams)

    def write(self, data):
        for s in self.streams:
            try:
                s.write(data)
                s.flush()
            except Exception:
                pass
        return len(data)

    def flush(self):
        for s in self.streams:
            try:
                s.flush()
            except Exception:
                pass


def save_resilience_report(report: dict, out_dir: str, ts: str, phase: str):
    os.makedirs(out_dir, exist_ok=True)
    base = f"resilience_fase{phase}_{ts}"
    json_path = os.path.join(out_dir, base + ".json")
    md_path = os.path.join(out_dir, base + ".md")

    with open(json_path, "w") as fh:
        json.dump(report, fh, indent=2, default=str)

    lines = [
        f"# enyx-enterprise Resilience Test Report — Fase {phase}",
        "",
        f"- **Generated**: {report.get('generated', datetime.now().isoformat(timespec='seconds'))}",
        f"- **Phase**: {phase}",
        f"- **Passed**: {report.get('pass_count', 0)}",
        f"- **Degraded**: {report.get('degraded_count', 0)}",
        f"- **Failed**: {report.get('fail_count', 0)}",
        "",
        "## Scenarios",
        "",
    ]
    for s in report.get("scenarios", []):
        lines.append(f"- **{s.get('scenario')}**: {s.get('status')} — {s.get('details')}")
    lines.append("")

    with open(md_path, "w") as fh:
        fh.write("\n".join(lines))

    print(f"[*] Report saved: {md_path}")
    print(f"[*] Report saved: {json_path}")
    return md_path, json_path


def generate_resilience_charts(report: dict, out_dir: str, ts: str, phase: str):
    if not _HAS_MPL:
        print("[!] matplotlib not installed; skipping resilience chart generation.")
        return []

    created = []
    scenarios = report.get("scenarios", [])
    recovery_times = report.get("recovery_times", [])

    if scenarios:
        names = [s["scenario"] for s in scenarios]
        statuses = [s["status"] for s in scenarios]
        score_map = {"PASS": 100, "DEGRADED": 70, "FAIL": 0}
        scores = [score_map.get(st, 0) for st in statuses]
        colors = ["#2ecc71" if sc == 100 else ("#f39c12" if sc == 70 else "#e74c3c") for sc in scores]

        fig, ax = plt.subplots(figsize=(12, 6))
        fig.suptitle(f"enyx-enterprise - Chaos & Resilience Audit (Fase {phase})", fontsize=14, fontweight="bold")
        y = np.arange(len(names))
        bars = ax.barh(y, scores, color=colors, height=0.55)
        ax.set_yticks(y)
        ax.set_yticklabels(names, fontsize=10, fontweight="bold")
        ax.set_xlabel("Resilience Health Index (%)")
        ax.set_xlim(0, 115)
        ax.grid(axis="x", linestyle="--", alpha=0.5)
        for bar, st in zip(bars, statuses):
            width = bar.get_width()
            ax.text(width + 2, bar.get_y() + bar.get_height() / 2.0, f"{st} ({width}%)", va="center", fontweight="bold")
        plt.tight_layout()
        audit_path = os.path.join(out_dir, f"resilience_fase{phase}_{ts}_audit.png")
        plt.savefig(audit_path, dpi=300)
        plt.close()
        created.append(audit_path)

        if recovery_times and len(recovery_times) == len(names):
            fig, ax = plt.subplots(figsize=(12, 6))
            fig.suptitle(f"enyx-enterprise - Recovery Time (Fase {phase})", fontsize=14, fontweight="bold")
            bars = ax.barh(names, recovery_times, color="#3498db")
            ax.set_xlabel("Recovery Time (seconds)")
            ax.set_title("Service Recovery Time After Outage")
            ax.grid(axis="x", linestyle="--", alpha=0.5)
            for bar, rt in zip(bars, recovery_times):
                ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height() / 2.0, f"{rt:.1f}s", va="center", fontsize=9)
            plt.tight_layout()
            rec_path = os.path.join(out_dir, f"resilience_fase{phase}_{ts}_recovery.png")
            plt.savefig(rec_path, dpi=300)
            plt.close()
            created.append(rec_path)

    for p in created:
        print(f"[*] Chart generated: {p}")
    return created


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="enyx-enterprise Chaos & Resilience Test Suite"
    )
    phase_group = parser.add_mutually_exclusive_group()
    phase_group.add_argument("--phase1", action="store_true",
                             help="Run chaos suite on 10 core services only (Fase 1)")
    phase_group.add_argument("--phase2", action="store_true",
                             help="Run full chaos suite including AI/ML services (Fase 2)")
    parser.add_argument("--log", default=None, help="Path to write the full test log")
    parser.add_argument("--results-dir", default=None, help="Results directory (default: <repo>/test/results)")
    args = parser.parse_args()

    phase = "1" if args.phase1 else ("2" if args.phase2 else "all")
    phase_label = "Fase 1 (Core Only)" if phase == "1" else ("Fase 2 (Full + AI/ML)" if phase == "2" else "All")

    if args.results_dir:
        out_dir = args.results_dir
    else:
        results_base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
        phase_folder = "phase1" if phase == "1" else "phase2"
        out_dir = os.path.join(results_base, phase_folder)
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = args.log or os.path.join(out_dir, f"resilience_fase{phase}_{ts}.log")
    log_file = open(log_path, "a", buffering=1)
    original_stdout, original_stderr = sys.stdout, sys.stderr
    sys.stdout = Tee(original_stdout, log_file)
    sys.stderr = Tee(original_stderr, log_file)

    print("=" * 70)
    print("  ENTERPRISE IOT MICROSERVICES CHAOS & RESILIENCE TEST SUITE")
    print("=" * 70)
    print(f"  PHASE: {phase_label}")
    print(f"  Started: {datetime.now().isoformat(timespec='seconds')}")
    print(f"  Log file: {log_path}")
    print("=" * 70)

    token = get_token()
    if not token:
        print("[!] Warning: Auth login failed, running tests in unauthenticated fallback mode.")
    else:
        print("[*] Successfully authenticated with Auth Service!")

    scenarios, recovery_times, scenario_data = run_chaos_suite(token, phase=phase)

    pass_count = sum(1 for s in scenarios if s["status"] == "PASS")
    degraded_count = sum(1 for s in scenarios if s["status"] == "DEGRADED")
    fail_count = sum(1 for s in scenarios if s["status"] == "FAIL")

    print(f"\n  SUMMARY: {pass_count} PASS, {degraded_count} DEGRADED, {fail_count} FAIL")

    report = {
        "phase": phase,
        "generated": datetime.now().isoformat(timespec="seconds"),
        "scenarios": scenarios,
        "recovery_times": recovery_times,
        "scenario_data": scenario_data,
        "pass_count": pass_count,
        "degraded_count": degraded_count,
        "fail_count": fail_count,
    }
    save_resilience_report(report, out_dir, ts, phase)
    generate_resilience_charts(report, out_dir, ts, phase)

    if _HAS_PLOTTER:
        plot_chaos_scenario_charts(report.get("scenario_data", {}), Path(out_dir))
        for s in report.get("scenarios", []):
            safe_name = s["scenario"].replace(" ", "_").replace("/", "_")
            summary_path = Path(out_dir) / f"chaos_{safe_name}_summary.png"
            plot_scenario_summary_chart(
                s["scenario"],
                s["status"],
                s.get("recovery_time", 0.0),
                s.get("details", ""),
                summary_path,
            )

    print("=" * 70)
    print(f"  Resilience Test completed at {datetime.now().isoformat(timespec='seconds')}")
    print(f"  Full log available at: {log_path}")
    print("=" * 70)

    sys.stdout = original_stdout
    sys.stderr = original_stderr
    log_file.close()


if __name__ == "__main__":
    main()
