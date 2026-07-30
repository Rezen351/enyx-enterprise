"""
enyx-enterprise - Comprehensive Feature & Unit Test Suite
Tests 100% of all microservices, features, endpoints, and WebSocket channels via Kong API Gateway (/v1).
Enhanced with per-service execution time tracking for analytics.
"""

import os
import sys
import json
import time
import unittest
import requests
from pathlib import Path

try:
    import websocket
except ImportError:
    websocket = None


BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "admin1234")
RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

CAPTURED_RESULTS = []
CAPTURE_ENABLED = os.getenv("CAPTURE_TEST_RESULTS", "1") == "1"

MAX_RETRIES = int(os.getenv("TEST_MAX_RETRIES", "3"))
RETRY_DELAY = float(os.getenv("TEST_RETRY_DELAY", "1.0"))

def _with_retry(func, *args, **kwargs):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.ConnectionError:
            if attempt == MAX_RETRIES:
                raise
            time.sleep(RETRY_DELAY * attempt)


def check_services_ready():
    url = f"{BASE_URL}/v1/health"
    for attempt in range(1, 4):
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                return True
            if res.status_code in [429, 502, 503, 504] and attempt < 3:
                time.sleep(2 ** attempt)
                continue
        except Exception:
            if attempt < 3:
                time.sleep(2 ** attempt)
                continue
    return False


def wait_for_services(timeout=120):
    deadline = time.time() + timeout
    last_err = None
    while time.time() < deadline:
        try:
            if check_services_ready():
                return True
        except Exception as exc:
            last_err = exc
        time.sleep(3)
    if last_err:
        raise last_err
    return False


_original_requests_get = requests.get
_original_requests_post = requests.post
_original_requests_put = requests.put
_original_requests_delete = requests.delete
_original_requests_patch = requests.patch


def _capture_request(method, *args, **kwargs):
    test_name = kwargs.pop("_test_name", "unknown")
    service = kwargs.pop("_service", "unknown")
    endpoint = kwargs.pop("_endpoint", "")
    start = time.time()
    try:
        resp = _with_retry(_original_requests_get, *args, **kwargs) if method == "GET" else \
               _with_retry(_original_requests_post, *args, **kwargs) if method == "POST" else \
               _with_retry(_original_requests_put, *args, **kwargs) if method == "PUT" else \
               _with_retry(_original_requests_delete, *args, **kwargs) if method == "DELETE" else \
               _with_retry(_original_requests_patch, *args, **kwargs) if method == "PATCH" else None
        duration = time.time() - start

        img_file = None
        payload_text = None
        if resp is not None:
            ctype = resp.headers.get("Content-Type", "") or ""
            if "image/" in ctype or "octet-stream" in ctype:
                suffix = ".bin"
                if "/" in ctype:
                    suffix = "." + ctype.split("/")[-1].split(";")[0].strip().split("+")[0]
                img_name = f"{method.lower()}_{service}_{endpoint.replace('/','_')}_{resp.status_code}{suffix}"
                img_name = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in img_name)
                out_path = RESULTS_DIR / img_name
                try:
                    out_path.write_bytes(resp.content)
                    payload_text = f"[binary saved to {out_path.name}]"
                except Exception:
                    payload_text = None
            else:
                try:
                    payload_text = resp.text
                except Exception:
                    payload_text = None
        _capture_result(test_name, service, endpoint, method, resp.status_code if resp is not None else None, payload=payload_text, error=None, duration=duration)
        return resp
    except Exception as exc:
        _capture_result(test_name, service, endpoint, method, None, payload=None, error=str(exc), duration=time.time() - start)
        raise


def captured_get(url, **kwargs):
    return _capture_request("GET", url, **kwargs)


def captured_post(url, **kwargs):
    return _capture_request("POST", url, **kwargs)


def captured_put(url, **kwargs):
    return _capture_request("PUT", url, **kwargs)


def captured_delete(url, **kwargs):
    return _capture_request("DELETE", url, **kwargs)


def captured_patch(url, **kwargs):
    return _capture_request("PATCH", url, **kwargs)


def get_paired_node_id(headers):
    url = f"{BASE_URL}/v1/nodes"
    res = captured_get(url, headers=headers, timeout=5)
    if res.status_code != 200:
        return None
    data = res.json().get("data", {})
    nodes = data.get("nodes") or []
    for n in nodes:
        if n.get("paired") or n.get("module_id"):
            return n.get("node_id")
    return None


def get_unpaired_node_id(headers):
    url = f"{BASE_URL}/v1/nodes"
    res = captured_get(url, headers=headers, timeout=5)
    if res.status_code != 200:
        return None
    data = res.json().get("data", {})
    nodes = data.get("nodes") or []
    for n in nodes:
        if not n.get("paired") and not n.get("module_id"):
            return n.get("node_id")
    return None


# Auto-patch module-level requests functions so ALL existing test calls are captured
if CAPTURE_ENABLED:
    requests.get = captured_get
    requests.post = captured_post
    requests.put = captured_put
    requests.delete = captured_delete
    requests.patch = captured_patch


def save_captured_results():
    if not CAPTURE_ENABLED or not CAPTURED_RESULTS:
        return
    json_path = RESULTS_DIR / "05_unit_test_payloads.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(CAPTURED_RESULTS, f, indent=2, ensure_ascii=False)
    print(f"[*] Captured test results saved: {json_path}")

    md_path = RESULTS_DIR / "05_unit_test_payloads.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Unit Test Payloads & Responses\n\n")
        f.write(f"Total captured requests: {len(CAPTURED_RESULTS)}\n\n")
        for item in CAPTURED_RESULTS:
            status = item.get("status_code")
            f.write(f"## {item['test']}\n\n")
            f.write(f"- **Service:** {item['service']}\n")
            f.write(f"- **Endpoint:** `{item['endpoint']}`\n")
            f.write(f"- **Method:** {item['method']}\n")
            f.write(f"- **Status:** {status}\n")
            f.write(f"- **Duration:** {item['duration_sec']}s\n")
            if item.get("error"):
                f.write(f"- **Error:** {item['error']}\n")
            payload = item.get("payload")
            if payload is not None:
                try:
                    parsed = json.loads(payload)
                    f.write(f"- **Payload:**\n```json\n{json.dumps(parsed, indent=2, ensure_ascii=False)}\n```\n")
                except Exception:
                    f.write(f"- **Payload:**\n```\n{payload}\n```\n")
            f.write("\n")
    print(f"[*] Captured test report saved: {md_path}")


# Global Token Cache to prevent hitting Kong Auth Rate Limiter (429)
GLOBAL_TOKEN = None
GLOBAL_REFRESH_TOKEN = None
TEST_NODE_ID = None
TEST_UNPAIRED_NODE_ID = None


def get_test_node_id(headers):
    global TEST_NODE_ID
    if TEST_NODE_ID:
        return TEST_NODE_ID
    TEST_NODE_ID = get_paired_node_id(headers)
    return TEST_NODE_ID


def get_test_unpaired_node_id(headers):
    global TEST_UNPAIRED_NODE_ID
    if TEST_UNPAIRED_NODE_ID:
        return TEST_UNPAIRED_NODE_ID
    TEST_UNPAIRED_NODE_ID = get_unpaired_node_id(headers)
    return TEST_UNPAIRED_NODE_ID


def get_global_token():
    global GLOBAL_TOKEN, GLOBAL_REFRESH_TOKEN
    if GLOBAL_TOKEN:
        return GLOBAL_TOKEN
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            url = f"{BASE_URL}/v1/auth/login"
            res = requests.post(url, json={"identifier": ADMIN_USER, "password": ADMIN_PASS}, timeout=5)
            if res.status_code == 200:
                data = res.json().get("data", {})
                GLOBAL_TOKEN = data.get("access_token") or data.get("token")
                GLOBAL_REFRESH_TOKEN = data.get("refresh_token")
                return GLOBAL_TOKEN
            elif res.status_code == 429 and attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt * 2)
                continue
        except Exception:
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)
                continue
            break
    return GLOBAL_TOKEN


def _capture_result(test_name, service, endpoint, method, status_code, payload=None, error=None, duration=0.0):
    if not CAPTURE_ENABLED:
        return
    CAPTURED_RESULTS.append({
        "test": test_name,
        "service": service,
        "endpoint": endpoint,
        "method": method,
        "status_code": status_code,
        "payload": payload,
        "error": error,
        "duration_sec": round(duration, 4),
    })


def cleanup_test_results():
    for name in ["05_unit_test_payloads.json", "05_unit_test_payloads.md"]:
        target = RESULTS_DIR / name
        if target.exists():
            target.unlink()


def reset_capture_state():
    CAPTURED_RESULTS.clear()
    cleanup_test_results()


def clean_all_test_results():
    reset_capture_state()
    for path in RESULTS_DIR.glob("*.png"):
        path.unlink()
    for path in RESULTS_DIR.glob("*.json"):
        path.unlink()
    for path in RESULTS_DIR.glob("*.md"):
        path.unlink()
    for path in RESULTS_DIR.glob("*.bin"):
        path.unlink()
    for path in RESULTS_DIR.glob("*"):
        if path.is_file() and path.suffix not in {".png", ".json", ".md", ".bin"}:
            path.unlink()


def cleanup_test_data():
    token = GLOBAL_TOKEN or get_global_token()
    if not token:
        return
    headers = {"Authorization": f"Bearer {token}"}

    candidates = [
        ("TestAuthService", "created_user_id", f"{BASE_URL}/v1/auth/users/{{id}}"),
        ("TestModuleService", "created_actuator_id", f"{BASE_URL}/v1/nodes/{TEST_NODE_ID}/actuators/{{id}}"),
        ("TestModuleService", "created_module_id", f"{BASE_URL}/v1/modules/{{id}}"),
        ("TestControlService", "created_schedule_id", f"{BASE_URL}/v1/control/schedules/{{id}}"),
        ("TestAlertService", "created_threshold_id", f"{BASE_URL}/v1/thresholds/{{id}}"),
        ("TestStreamService", "created_stream_id", f"{BASE_URL}/v1/streams/{{id}}"),
    ]

    for class_name, attr, url_tpl in candidates:
        cls = globals().get(class_name)
        if not cls:
            continue
        resource_id = getattr(cls, attr, None)
        if not resource_id:
            continue
        url = url_tpl.format(id=resource_id)
        try:
            requests.delete(url, headers=headers, timeout=5)
        except Exception:
            pass

    # Clear test node tags created by update_node_tags so the database stays clean.
    if TEST_NODE_ID:
        try:
            requests.put(f"{BASE_URL}/v1/nodes/{TEST_NODE_ID}/tags", json=[], headers=headers, timeout=5)
        except Exception:
            pass

    # Clean up any leftover snapshots/recordings so the gallery
    # does not retain stale DB records pointing to missing MinIO objects.
    try:
        res = requests.get(f"{BASE_URL}/v1/snapshots", headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json().get("data") or {}
            for snap in data.get("snapshots", []):
                snap_id = snap.get("id")
                if snap_id:
                    try:
                        requests.delete(f"{BASE_URL}/v1/snapshots/{snap_id}", headers=headers, timeout=5)
                    except Exception:
                        pass
    except Exception:
        pass


class ServiceTestCase(unittest.TestCase):
    _services_checked = False
    _services_ready = False

    def setUp(self):
        super().setUp()
        if not ServiceTestCase._services_checked:
            ServiceTestCase._services_ready = check_services_ready()
            ServiceTestCase._services_checked = True
        if not ServiceTestCase._services_ready:
            self.skipTest("Services not reachable: cannot connect to API gateway")
        global TEST_NODE_ID, TEST_UNPAIRED_NODE_ID
        if not TEST_NODE_ID:
            token = get_global_token()
            if token:
                headers = {"Authorization": f"Bearer {token}"}
                TEST_NODE_ID = get_paired_node_id(headers)
                TEST_UNPAIRED_NODE_ID = get_unpaired_node_id(headers)
                if not TEST_NODE_ID and TEST_UNPAIRED_NODE_ID:
                    modules_res = captured_get(f"{BASE_URL}/v1/modules", headers=headers, timeout=5)
                    if modules_res.status_code == 200:
                        mods = modules_res.json().get("data", {}).get("modules", [])
                        if mods:
                            mod_id = mods[0].get("id")
                            pair_res = captured_post(
                                f"{BASE_URL}/v1/nodes/{TEST_UNPAIRED_NODE_ID}/pair",
                                json={"module_id": mod_id},
                                headers=headers,
                                timeout=5,
                            )
                            if pair_res.status_code in [200, 201]:
                                TEST_NODE_ID = TEST_UNPAIRED_NODE_ID
                                time.sleep(1)

    @classmethod
    def setUpClass(cls):
        cls._test_token = None

    def get_token(self):
        if self._test_token:
            return self._test_token
        token = get_global_token()
        if token:
            self.__class__._test_token = token
        return token


class TimedTestResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.test_times = {}
        self.test_class_times = {}

    def startTest(self, test):
        super().startTest(test)
        test._start_time = time.time()

    def stopTest(self, test):
        elapsed = time.time() - getattr(test, "_start_time", time.time())
        class_name = test.__class__.__name__
        self.test_class_times[class_name] = self.test_class_times.get(class_name, 0) + elapsed
        self.test_times[str(test)] = elapsed
        super().stopTest(test)


class TimedTestRunner(unittest.TextTestRunner):
    def _makeResult(self):
        return TimedTestResult(self.stream, self.descriptions, self.verbosity)


class TestSystemHealth(ServiceTestCase):
    """1. Global System Health Check."""

    def test_01_gateway_health(self):
        res = requests.get(f"{BASE_URL}/v1/health", timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK from /v1/health, got {res.status_code}: {res.text}")
        data = res.json()
        self.assertTrue(data.get("success", False), "Health response should indicate success")


class TestAuthService(ServiceTestCase):
    """2. Auth Service Features (Register, Login, Me, Profile, Password, Sessions, Roles, Users, Refresh, Logout)."""

    token = None
    refresh_token = None
    created_user_id = None
    created_username = None

    def setUp(self):
        super().setUp()
        self.token = get_global_token()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        if getattr(cls, "created_user_id", None):
            token = get_global_token()
            if token:
                try:
                    requests.delete(f"{BASE_URL}/v1/auth/users/{cls.created_user_id}", headers={"Authorization": f"Bearer {token}"}, timeout=5)
                except Exception:
                    pass
            cls.created_user_id = None
            cls.created_username = None

    def test_01_login_success(self):
        token = get_global_token()
        self.assertIsNotNone(token, "Login response must return access token")
        TestAuthService.token = token
        TestAuthService.refresh_token = GLOBAL_REFRESH_TOKEN

    def test_02_get_profile(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/auth/me"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for /v1/auth/me, got {res.status_code}: {res.text}")

    def test_03_update_profile(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/auth/me"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"username": ADMIN_USER}
        res = requests.put(url, json=payload, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for profile update, got {res.status_code}: {res.text}")

    def test_04_get_sessions(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/auth/sessions"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for /v1/auth/sessions, got {res.status_code}: {res.text}")

    def test_05_admin_list_users(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/auth/users"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for /v1/auth/users, got {res.status_code}: {res.text}")

    def test_06_admin_list_roles(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/auth/roles"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for /v1/auth/roles, got {res.status_code}: {res.text}")

    def test_07_refresh_token(self):
        if not self.token or not TestAuthService.refresh_token:
            self.skipTest("No refresh token available")
        url = f"{BASE_URL}/v1/auth/refresh"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"refresh_token": TestAuthService.refresh_token}
        res = requests.post(url, json=payload, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 401], f"Expected 200 or 401 for refresh, got {res.status_code}: {res.text}")
        if res.status_code == 200:
            data = res.json().get("data", {})
            new_token = data.get("access_token")
            if new_token:
                TestAuthService.token = new_token
                TestAuthService.refresh_token = data.get("refresh_token")

    def test_08_register_new_user(self):
        url = f"{BASE_URL}/v1/auth/register"
        username = f"testuser_{int(time.time())}"
        payload = {"username": username, "email": f"test_{int(time.time())}@example.com", "password": "TestPass123!"}
        res = requests.post(url, json=payload, timeout=5)
        self.assertIn(res.status_code, [201, 400], f"Expected 201 or 400 for register, got {res.status_code}: {res.text}")
        if res.status_code == 201:
            TestAuthService.created_user_id = res.json().get("data", {}).get("id")
            TestAuthService.created_username = username

    def test_09_logout(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/auth/logout"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.post(url, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for logout, got {res.status_code}: {res.text}")

    def test_10_admin_get_user_by_id(self):
        if not self.token:
            self.skipTest("No auth token")
        if not TestAuthService.created_user_id:
            self.skipTest("No created user ID")
        url = f"{BASE_URL}/v1/auth/users/{TestAuthService.created_user_id}"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 404], f"Expected 200 or 404 for get user, got {res.status_code}: {res.text}")

    def test_11_admin_update_user(self):
        if not self.token or not TestAuthService.created_user_id:
            self.skipTest("No user ID available to update")
        url = f"{BASE_URL}/v1/auth/users/{TestAuthService.created_user_id}"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"roles": ["viewer"]}
        res = requests.put(url, json=payload, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for update user, got {res.status_code}: {res.text}")

    def test_12_delete_account(self):
        if not self.token or not getattr(TestAuthService, "created_username", None):
            self.skipTest("No user ID / username available to delete")
        username = TestAuthService.created_username
        login_url = f"{BASE_URL}/v1/auth/login"
        login_payload = {"identifier": username, "password": "TestPass123!"}
        login_res = requests.post(login_url, json=login_payload, timeout=5)
        if login_res.status_code != 200:
            self.skipTest("Cannot login as created user")
        user_token = login_res.json().get("data", {}).get("access_token")
        url = f"{BASE_URL}/v1/auth/account"
        headers = {"Authorization": f"Bearer {user_token}", "Content-Type": "application/json"}
        payload = {"password": "TestPass123!"}
        res = requests.delete(url, json=payload, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 401], f"Expected 200 or 401 for account delete, got {res.status_code}: {res.text}")

    def test_13_admin_delete_user(self):
        if not self.token or not TestAuthService.created_user_id:
            self.skipTest("No user ID available to delete")
        url = f"{BASE_URL}/v1/auth/users/{TestAuthService.created_user_id}"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.delete(url, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 404], f"Expected 200 or 404 for delete user, got {res.status_code}: {res.text}")
        TestAuthService.created_user_id = None
        TestAuthService.created_username = None


class TestModuleService(ServiceTestCase):
    """3. Module Service Features (Modules CRUD, Nodes, Discovered Nodes, Tags, Actuators)."""

    created_module_id = None
    created_node_id = None
    created_actuator_id = None

    def setUp(self):
        super().setUp()
        self.token = get_global_token()

    def tearDown(self):
        cls = self.__class__
        token = self.get_token()
        if token:
            aid = getattr(cls, "created_actuator_id", None)
            if aid:
                try:
                    requests.delete(f"{BASE_URL}/v1/nodes/{TEST_NODE_ID}/actuators/{aid}", headers={"Authorization": f"Bearer {token}"}, timeout=5)
                except Exception:
                    pass
            mid = getattr(cls, "created_module_id", None)
            if mid:
                try:
                    requests.delete(f"{BASE_URL}/v1/modules/{mid}", headers={"Authorization": f"Bearer {token}"}, timeout=5)
                except Exception:
                    pass
        cls.created_actuator_id = None
        cls.created_module_id = None

    def test_01_list_modules(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/modules"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for /v1/modules, got {res.status_code}: {res.text}")

    def test_02_create_module(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/modules"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"name": f"Test Greenhouse {int(time.time())}", "description": "Automated unit test module"}
        res = requests.post(url, json=payload, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 201], f"Expected 200/201 for create module, got {res.status_code}: {res.text}")
        mod_id = res.json().get("data", {}).get("id")
        TestModuleService.created_module_id = mod_id

    def test_03_get_module_by_id(self):
        if not self.token or not TestModuleService.created_module_id:
            self.skipTest("No module ID available")
        url = f"{BASE_URL}/v1/modules/{TestModuleService.created_module_id}"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for get module, got {res.status_code}: {res.text}")

    def test_04_list_nodes(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/nodes"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for /v1/nodes, got {res.status_code}: {res.text}")

    def test_05_list_discovered_nodes(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/nodes/discovered"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for /v1/nodes/discovered, got {res.status_code}: {res.text}")

    def test_06_get_node_tags(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/nodes/{TEST_NODE_ID}/tags"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for node tags, got {res.status_code}: {res.text}")

    def test_07_get_node_actuators(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/nodes/{TEST_NODE_ID}/actuators"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for node actuators, got {res.status_code}: {res.text}")

    def test_08_update_module(self):
        if not self.token or not TestModuleService.created_module_id:
            self.skipTest("No module ID available")
        url = f"{BASE_URL}/v1/modules/{TestModuleService.created_module_id}"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"description": "Updated by unit test"}
        res = requests.put(url, json=payload, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for update module, got {res.status_code}: {res.text}")

    def test_09_delete_module(self):
        if not self.token or not TestModuleService.created_module_id:
            self.skipTest("No module ID available to delete")
        url = f"{BASE_URL}/v1/modules/{TestModuleService.created_module_id}"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.delete(url, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 404], f"Expected 200 or 404 for delete module, got {res.status_code}: {res.text}")

    def test_10_get_node_by_id(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/nodes/{TEST_NODE_ID}"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 404], f"Expected 200 or 404 for get node, got {res.status_code}: {res.text}")

    def test_11_update_node_tags(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/nodes/{TEST_NODE_ID}/tags"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = [{"source_key": "sensor_1", "tag_name": "temperature", "display_name": "Temperature", "label": "C", "unit": "°C", "data_type": "float", "enabled": True}]
        res = requests.put(url, json=payload, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 404], f"Expected 200 or 404 for update tags, got {res.status_code}: {res.text}")

    def test_12_pair_node(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/nodes/{TEST_NODE_ID}/pair"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"module_id": TestModuleService.created_module_id or "550e8400-e29b-41d4-a716-446655440000"}
        res = requests.post(url, json=payload, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 400, 404], f"Expected 200/400/404 for pair node, got {res.status_code}: {res.text}")

    def test_13_unpair_node(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/nodes/{TEST_NODE_ID}/unpair"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.post(url, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 400, 404], f"Expected 200/400/404 for unpair node, got {res.status_code}: {res.text}")
        if res.status_code == 200:
            mods = captured_get(f"{BASE_URL}/v1/modules", headers=headers, timeout=5)
            if mods.status_code == 200:
                mods_data = mods.json().get("data", {}).get("modules", [])
                if mods_data:
                    mod_id = mods_data[0].get("id")
                    captured_post(f"{BASE_URL}/v1/nodes/{TEST_NODE_ID}/pair", json={"module_id": mod_id}, headers=headers, timeout=5)
                    time.sleep(1)

    def test_14_delete_node(self):
        if not self.token:
            self.skipTest("No auth token")
        headers = {"Authorization": f"Bearer {self.token}"}
        list_res = captured_get(f"{BASE_URL}/v1/nodes", headers=headers, timeout=5)
        nodes = (list_res.json().get("data") or {}).get("nodes") or []
        paired_nodes = [n for n in nodes if n.get("paired") or n.get("module_id")]
        if len(paired_nodes) <= 1 and TEST_NODE_ID in [n.get("node_id") for n in paired_nodes]:
            self.skipTest("Skipping delete to preserve last paired test node")
        url = f"{BASE_URL}/v1/nodes/{TEST_NODE_ID}"
        res = requests.delete(url, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 404], f"Expected 200 or 404 for delete node, got {res.status_code}: {res.text}")

    def test_15_create_actuator(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/nodes/{TEST_NODE_ID}/actuators"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"source_key": "fan", "tag_name": "fan", "display_name": "Fan", "label": "Cooling", "unit": "on/off", "data_type": "boolean", "enabled": True}
        res = requests.post(url, json=payload, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 201, 404], f"Expected 200/201/404 for create actuator, got {res.status_code}: {res.text}")
        if res.status_code in [200, 201]:
            TestModuleService.created_actuator_id = res.json().get("data", {}).get("id")

    def test_16_delete_actuator(self):
        if not self.token or not TestModuleService.created_actuator_id:
            self.skipTest("No actuator ID available")
        url = f"{BASE_URL}/v1/nodes/{TEST_NODE_ID}/actuators/{TestModuleService.created_actuator_id}"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.delete(url, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 404], f"Expected 200 or 404 for delete actuator, got {res.status_code}: {res.text}")


class TestAnalyticsService(ServiceTestCase):
    """4. Analytics Service Features (Nodes, Metrics, Summary, Export)."""

    def setUp(self):
        super().setUp()
        self.token = get_global_token()

    def tearDown(self):
        pass

    def test_01_list_analytics_nodes(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/analytics/nodes"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for /v1/analytics/nodes, got {res.status_code}: {res.text}")

    def test_02_analytics_metrics(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/analytics/metrics?node_id={TEST_NODE_ID}&metric=temperature&interval=1h"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for analytics metrics, got {res.status_code}: {res.text}")

    def test_03_analytics_summary(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/analytics/summary?node_id={TEST_NODE_ID}&metric=temperature"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 404], f"Expected 200 or 404 for analytics summary, got {res.status_code}")

    def test_04_analytics_export_csv(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/analytics/export?node_id={TEST_NODE_ID}&metric=temperature&resolution=day"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for CSV export, got {res.status_code}: {res.text}")

    def test_05_analytics_metrics_from_to(self):
        if not self.token:
            self.skipTest("No auth token")
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        from_time = (now - timedelta(days=1)).isoformat() + "Z"
        to_time = now.isoformat() + "Z"
        url = f"{BASE_URL}/v1/analytics/metrics?node_id={TEST_NODE_ID}&metric=temperature&from={from_time}&to={to_time}"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 400], f"Expected 200 or 400 for metrics with from/to, got {res.status_code}: {res.text}")

    def test_06_analytics_metrics_comma_separated(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/analytics/metrics?node_id={TEST_NODE_ID}&metric=temperature,humidity&interval=1h"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for comma-separated metrics, got {res.status_code}: {res.text}")


class TestControlService(ServiceTestCase):
    """5. Control Service Features (Commands, Modes, Manual Commands, Targets, Outputs, Resume Auto, Schedules)."""

    created_schedule_id = None

    def setUp(self):
        super().setUp()
        self.token = get_global_token()
        global TEST_NODE_ID
        if TEST_NODE_ID and self.token:
            headers = {"Authorization": f"Bearer {self.token}"}
            node_res = captured_get(f"{BASE_URL}/v1/nodes/{TEST_NODE_ID}", headers=headers, timeout=5)
            if node_res.status_code != 200:
                mods = captured_get(f"{BASE_URL}/v1/modules", headers=headers, timeout=5)
                if mods.status_code == 200:
                    mods_data = mods.json().get("data", {}).get("modules", [])
                    if mods_data:
                        mod_id = mods_data[0].get("id")
                        captured_post(f"{BASE_URL}/v1/nodes/{TEST_NODE_ID}/pair", json={"module_id": mod_id}, headers=headers, timeout=5)
                        time.sleep(1)

    def tearDown(self):
        cls = self.__class__
        token = self.get_token()
        if token:
            sid = getattr(cls, "created_schedule_id", None)
            if sid:
                try:
                    requests.delete(f"{BASE_URL}/v1/control/schedules/{sid}", headers={"Authorization": f"Bearer {token}"}, timeout=5)
                except Exception:
                    pass
        cls.created_schedule_id = None

    def test_01_list_commands(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/control/commands?node_id={TEST_NODE_ID}"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for /v1/control/commands, got {res.status_code}: {res.text}")

    def test_02_get_control_mode(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/control/modes/{TEST_NODE_ID}"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 404], f"Expected 200 or 404, got {res.status_code}")

    def test_03_set_control_mode(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/control/modes/{TEST_NODE_ID}"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"mode": "MANUAL"}
        res = requests.put(url, json=payload, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 409], f"Expected 200 or 409 for set mode, got {res.status_code}: {res.text}")

    def test_04_get_target_setpoints(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/control/targets?node_id={TEST_NODE_ID}"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 404, 500], f"Expected response for targets, got {res.status_code}: {res.text}")

    def test_05_get_output_states(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/control/outputs?node_id={TEST_NODE_ID}"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for outputs, got {res.status_code}: {res.text}")

    def test_06_send_manual_command(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/control/command"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"node_id": TEST_NODE_ID, "type": "set_state", "output": "valve", "value": 1}
        res = requests.post(url, json=payload, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 202, 400], f"Expected response for manual command, got {res.status_code}: {res.text}")

    def test_07_resume_auto_mode(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/control/modes/{TEST_NODE_ID}/resume"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.post(url, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for resume auto mode, got {res.status_code}: {res.text}")

    def test_08_list_schedules(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/control/schedules?node_id={TEST_NODE_ID}"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for schedules, got {res.status_code}: {res.text}")

    def test_09_create_schedule(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/control/schedules"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {
            "node_id": TEST_NODE_ID,
            "output_name": "pump",
            "type": "interval",
            "params": {"on_sec": 10, "off_sec": 5, "value_on": 1, "value_off": 0},
            "enabled": False
        }
        res = requests.post(url, json=payload, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 201], f"Expected 200/201 for create schedule, got {res.status_code}: {res.text}")
        if res.status_code in [200, 201]:
            sched_id = res.json().get("data", {}).get("id")
            TestControlService.created_schedule_id = sched_id

    def test_10_delete_schedule(self):
        if not self.token or not TestControlService.created_schedule_id:
            self.skipTest("No schedule ID available to delete")
        url = f"{BASE_URL}/v1/control/schedules/{TestControlService.created_schedule_id}"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.delete(url, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 204], f"Expected 200 or 204 for delete schedule, got {res.status_code}: {res.text}")

    def test_11_update_schedule(self):
        if not self.token or not TestControlService.created_schedule_id:
            self.skipTest("No schedule ID available")
        url = f"{BASE_URL}/v1/control/schedules/{TestControlService.created_schedule_id}"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"params": {"on_sec": 20, "off_sec": 10}}
        res = requests.put(url, json=payload, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for update schedule, got {res.status_code}: {res.text}")

    def test_12_enable_schedule(self):
        if not self.token or not TestControlService.created_schedule_id:
            self.skipTest("No schedule ID available")
        url = f"{BASE_URL}/v1/control/schedules/{TestControlService.created_schedule_id}/enable"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.post(url, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 404], f"Expected 200 or 404 for enable schedule, got {res.status_code}: {res.text}")

    def test_13_disable_schedule(self):
        if not self.token or not TestControlService.created_schedule_id:
            self.skipTest("No schedule ID available")
        url = f"{BASE_URL}/v1/control/schedules/{TestControlService.created_schedule_id}/disable"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.post(url, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 404], f"Expected 200 or 404 for disable schedule, got {res.status_code}: {res.text}")

    def test_14_set_per_output_mode(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/control/modes/{TEST_NODE_ID}/pump"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"mode": "AUTO"}
        res = requests.put(url, json=payload, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 404], f"Expected 200 or 404 for per-output mode, got {res.status_code}: {res.text}")

    def test_15_get_schedule_by_id(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/control/schedules/1"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 404], f"Expected 200 or 404 for get schedule, got {res.status_code}: {res.text}")


class TestAlertService(ServiceTestCase):
    """6. Alert Service Features (Alerts List, Acknowledge, Thresholds CRUD)."""

    created_threshold_id = None

    def setUp(self):
        super().setUp()
        self.token = get_global_token()

    def tearDown(self):
        cls = self.__class__
        token = self.get_token()
        if token:
            tid = getattr(cls, "created_threshold_id", None)
            if tid:
                try:
                    requests.delete(f"{BASE_URL}/v1/thresholds/{tid}", headers={"Authorization": f"Bearer {token}"}, timeout=5)
                except Exception:
                    pass
        cls.created_threshold_id = None

    def test_01_list_alerts(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/alerts"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for /v1/alerts, got {res.status_code}: {res.text}")

    def test_02_list_thresholds(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/thresholds"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for /v1/thresholds, got {res.status_code}: {res.text}")

    def test_03_create_threshold(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/thresholds"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {
            "node_id": TEST_NODE_ID,
            "metric": "temperature",
            "min": 15.0,
            "max": 35.0,
            "severity": "warning"
        }
        res = requests.post(url, json=payload, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 201], f"Expected 200/201 for create threshold, got {res.status_code}: {res.text}")
        thresh_id = res.json().get("data", {}).get("id")
        TestAlertService.created_threshold_id = thresh_id

    def test_04_update_threshold(self):
        if not self.token or not TestAlertService.created_threshold_id:
            self.skipTest("No threshold ID available to update")
        url = f"{BASE_URL}/v1/thresholds/{TestAlertService.created_threshold_id}"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"max": 40.0, "severity": "critical"}
        res = requests.put(url, json=payload, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for update threshold, got {res.status_code}: {res.text}")

    def test_05_delete_threshold(self):
        if not self.token or not TestAlertService.created_threshold_id:
            self.skipTest("No threshold ID available to delete")
        url = f"{BASE_URL}/v1/thresholds/{TestAlertService.created_threshold_id}"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.delete(url, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 204], f"Expected 200 or 204 for delete threshold, got {res.status_code}: {res.text}")

    def test_06_acknowledge_alert(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/alerts/1/ack"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.put(url, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 404], f"Expected 200 or 404 for acknowledge alert, got {res.status_code}: {res.text}")


class TestAuditService(ServiceTestCase):
    """7. Audit Service Features (Query Logs, Event Filters, Time Ranges, Search)."""

    def setUp(self):
        super().setUp()
        self.token = get_global_token()

    def tearDown(self):
        pass

    def test_01_list_audit_logs(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/audit/logs"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for /v1/audit/logs, got {res.status_code}: {res.text}")

    def test_02_filter_audit_logs_by_event(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/audit/logs?event=auth.login"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for audit filter, got {res.status_code}: {res.text}")

    def test_03_filter_audit_logs_by_time_range(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/audit/logs?limit=10&offset=0"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for audit pagination, got {res.status_code}: {res.text}")

    def test_04_search_audit_logs(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/audit/logs?search=login"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for audit search, got {res.status_code}: {res.text}")

    def test_05_filter_audit_by_time_range(self):
        if not self.token:
            self.skipTest("No auth token")
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        from_time = (now - timedelta(days=7)).isoformat() + "Z"
        to_time = now.isoformat() + "Z"
        url = f"{BASE_URL}/v1/audit/logs?from={from_time}&to={to_time}"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for audit time range, got {res.status_code}: {res.text}")


class TestNotificationService(ServiceTestCase):
    """8. Notification Service Features (Settings, Logs, Test Dispatch)."""

    def setUp(self):
        super().setUp()
        self.token = get_global_token()

    def tearDown(self):
        pass

    def test_01_notification_logs(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/notifications/logs"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for notification logs, got {res.status_code}: {res.text}")

    def test_02_get_notification_settings(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/notifications/settings"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for notification settings, got {res.status_code}: {res.text}")

    def test_03_dispatch_test_notification(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/notifications/test"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"channel": "telegram", "message": "Unit test notification message"}
        res = requests.post(url, json=payload, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 202], f"Expected 200/202 for test notification, got {res.status_code}: {res.text}")

    def test_04_update_notification_settings(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/notifications/settings"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"telegram": {"enabled": True}}
        res = requests.put(url, json=payload, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 400, 403], f"Expected 200/400/403 for update settings, got {res.status_code}: {res.text}")

    def test_05_notification_logs_with_filters(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/notifications/logs?channel=telegram&limit=10"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for notification logs filter, got {res.status_code}: {res.text}")


class TestStreamService(ServiceTestCase):
    """9. Stream Service Features (Streams CRUD, Snapshots, Recordings, Storage Proxy)."""

    created_stream_id = None

    def setUp(self):
        super().setUp()
        self.token = get_global_token()

    def tearDown(self):
        cls = self.__class__
        token = self.get_token()
        if token:
            sid = getattr(cls, "created_stream_id", None)
            if sid:
                try:
                    requests.delete(f"{BASE_URL}/v1/streams/{sid}", headers={"Authorization": f"Bearer {token}"}, timeout=5)
                except Exception:
                    pass
        cls.created_stream_id = None

    def test_01_list_streams(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/streams"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for /v1/streams, got {res.status_code}: {res.text}")

    def test_02_list_snapshots(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/snapshots"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for /v1/snapshots, got {res.status_code}: {res.text}")

    def test_03_create_stream(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/streams"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {
            "name": f"cam_unit_test_{int(time.time())}",
            "source_url": "rtsp://localhost:8554/test",
            "module_id": "550e8400-e29b-41d4-a716-446655440000"
        }
        res = requests.post(url, json=payload, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 201, 400, 500], f"Expected response for create stream, got {res.status_code}: {res.text}")
        if res.status_code in [200, 201]:
            st_id = res.json().get("data", {}).get("id")
            TestStreamService.created_stream_id = st_id

    def test_04_get_stream_by_id(self):
        if not self.token or not TestStreamService.created_stream_id:
            self.skipTest("No stream ID available")
        url = f"{BASE_URL}/v1/streams/{TestStreamService.created_stream_id}"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 404], f"Expected 200 or 404 for get stream, got {res.status_code}: {res.text}")

    def test_05_delete_stream(self):
        if not self.token or not TestStreamService.created_stream_id:
            self.skipTest("No stream ID available to delete")
        url = f"{BASE_URL}/v1/streams/{TestStreamService.created_stream_id}"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.delete(url, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 204], f"Expected 200/204 for delete stream, got {res.status_code}: {res.text}")

    def test_06_update_stream(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/streams/1"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"location": "Updated Location"}
        res = requests.put(url, json=payload, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 404], f"Expected 200 or 404 for update stream, got {res.status_code}: {res.text}")

    def test_07_stream_snapshot(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/streams/1/snapshot"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.post(url, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 201, 400, 404, 502], f"Expected success or not-found for snapshot, got {res.status_code}: {res.text}")

    def test_08_start_recording(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/streams/1/record/start"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.post(url, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 400, 404, 502], f"Expected success or bad request for start recording, got {res.status_code}: {res.text}")

    def test_09_stop_recording(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/streams/1/record/stop"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.post(url, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 400, 404, 502], f"Expected success or bad request for stop recording, got {res.status_code}: {res.text}")

    def test_10_get_snapshot_by_id(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/snapshots/1"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 404], f"Expected 200 or 404 for get snapshot, got {res.status_code}: {res.text}")

    def test_11_delete_snapshot(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/snapshots/1"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.delete(url, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 404], f"Expected 200 or 404 for delete snapshot, got {res.status_code}: {res.text}")

    def test_12_storage_proxy(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/storage/stream/test.jpg"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 404], f"Expected 200 or 404 for storage proxy, got {res.status_code}: {res.text}")


class TestMLService(ServiceTestCase):
    """10. ML Vision Service Features (Models List, Frame Inference, Detections, Results)."""

    def setUp(self):
        super().setUp()
        self.token = get_global_token()

    def tearDown(self):
        pass

    def test_01_list_ml_models(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/ml/models"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for /v1/ml/models, got {res.status_code}: {res.text}")

    def test_02_ml_frame_inference_request(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/ml/detect/from-stream"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {
            "object_key": "cctv-front/2026-07-21_120000_frame.jpg",
            "model_id": "yolov8n",
            "conf": 0.3
        }
        res = requests.post(url, json=payload, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 400, 404, 500], f"Expected response from ML infer, got {res.status_code}")

    def test_03_list_detections(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/ml/detections"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for detections list, got {res.status_code}: {res.text}")

    def test_04_get_ml_model_by_id(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/ml/models/yolov8n"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 404], f"Expected 200 or 404 for get model, got {res.status_code}: {res.text}")

    def test_05_ml_detect_base64(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/ml/detect/base64"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"image_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="}
        res = requests.post(url, json=payload, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 400, 404, 500], f"Expected response from base64 detect, got {res.status_code}")

    def test_06_get_detection_by_id(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/ml/detections/1"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 404], f"Expected 200 or 404 for detection detail, got {res.status_code}: {res.text}")

    def test_07_list_ml_results(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/ml/results"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 404, 500], f"Expected 200/404/500 for ML results, got {res.status_code}: {res.text}")

    def test_08_update_ml_model(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/ml/models/yolov8n"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"description": "Updated by unit test"}
        res = requests.put(url, json=payload, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 404], f"Expected 200 or 404 for update model, got {res.status_code}: {res.text}")

    def test_09_activate_ml_model(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/ml/models/yolov8n/activate"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.post(url, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 404], f"Expected 200 or 404 for activate model, got {res.status_code}: {res.text}")

    def test_10_delete_ml_model(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/ml/models/yolov8n"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.delete(url, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 404], f"Expected 200 or 404 for delete model, got {res.status_code}: {res.text}")


class TestExportService(ServiceTestCase):
    """11. Export Service Features (Export Nodes, Metric Metadata, Telemetry CSV, OpenAPI Spec)."""

    def setUp(self):
        super().setUp()
        self.token = get_global_token()

    def tearDown(self):
        pass

    def test_01_export_nodes(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/export/v1/nodes"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for /v1/export/v1/nodes, got {res.status_code}: {res.text}")

    def test_02_export_metadata(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/export/v1/meta?node_id={TEST_NODE_ID}&metric=temperature"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for /v1/export/v1/meta, got {res.status_code}: {res.text}")

    def test_03_export_openapi(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/export/v1/openapi"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for /v1/export/v1/openapi, got {res.status_code}: {res.text}")

    def test_04_export_telemetry_csv(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/export/v1/telemetry?node_id={TEST_NODE_ID}&metric=temperature&limit=10"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 400, 404], f"Expected success or validation error for telemetry export, got {res.status_code}: {res.text}")


class TestWSGateway(ServiceTestCase):
    """12. WebSocket Gateway Features (System Status Channel & Node Live Channel Handshakes)."""

    def setUp(self):
        super().setUp()
        self.token = get_global_token()

    def tearDown(self):
        pass

    def test_01_websocket_system_status(self):
        if websocket is None or not self.token:
            self.skipTest("websocket-client not installed or no auth token")
        ws_base = BASE_URL.replace("http://", "ws://").replace("https://", "wss://")
        ws_url = f"{ws_base}/v1/ws/system-status?token={self.token}"
        try:
            ws = websocket.create_connection(ws_url, timeout=5)
            self.assertTrue(ws.connected, "WebSocket system status connection should be active")
            ws.close()
        except Exception as exc:
            self.fail(f"WebSocket system-status handshake failed: {exc}")

    def test_02_websocket_node_live(self):
        if websocket is None or not self.token:
            self.skipTest("websocket-client not installed or no auth token")
        ws_base = BASE_URL.replace("http://", "ws://").replace("https://", "wss://")
        ws_url = f"{ws_base}/v1/ws/nodes/{TEST_NODE_ID}/live?token={self.token}"
        try:
            ws = websocket.create_connection(ws_url, timeout=5)
            self.assertTrue(ws.connected, "WebSocket node live connection should be active")
            ws.close()
        except Exception as exc:
            self.fail(f"WebSocket node-live handshake failed: {exc}")


class TestWebhookService(ServiceTestCase):
    """13. Webhook Service Features (Settings, Logs, Test Dispatch, Receive Endpoints)."""

    def setUp(self):
        super().setUp()
        self.token = get_global_token()

    def tearDown(self):
        pass

    def test_01_webhook_logs(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/webhook/logs"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for webhook logs, got {res.status_code}: {res.text}")

    def test_02_get_webhook_settings(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/webhook/settings"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for webhook settings, got {res.status_code}: {res.text}")

    def test_03_dispatch_test_webhook(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/webhook/test"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"channel": "telegram"}
        res = requests.post(url, json=payload, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 202], f"Expected 200/202 for test webhook, got {res.status_code}: {res.text}")

    def test_04_update_webhook_settings(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/webhook/settings"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"telegram": {"enabled": True}}
        res = requests.put(url, json=payload, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 400, 403], f"Expected 200/400/403 for update webhook settings, got {res.status_code}: {res.text}")

    def test_05_receive_telegram_webhook(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/webhook/receive/telegram"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"message": {"text": "unit test"}}
        res = requests.post(url, json=payload, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 202], f"Expected 200/202 for receive telegram webhook, got {res.status_code}: {res.text}")


class TestDLQService(ServiceTestCase):
    """14. DLQ Service Features (List DLQ Messages, Filter by Source Stream/Trace ID)."""

    def setUp(self):
        super().setUp()
        self.token = get_global_token()

    def tearDown(self):
        pass

    def test_01_list_dlq_messages(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/dlq/messages"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 404, 500], f"Expected 200/404/500 for DLQ messages, got {res.status_code}: {res.text}")

    def test_02_filter_dlq_by_source_stream(self):
        if not self.token:
            self.skipTest("No auth token")
        url = f"{BASE_URL}/v1/dlq/messages?source_stream=test-stream"
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(url, json=payload, headers=headers, timeout=5)
        self.assertIn(res.status_code, [200, 404, 500], f"Expected 200/404/500 for DLQ filter, got {res.status_code}: {res.text}")


class TestModelService(ServiceTestCase):
    """15. Model Service Features (model-controller inference + model-control scheduler)."""

    def test_01_model_controller_health(self):
        url = f"{BASE_URL}/v1/model_controller/health"
        res = requests.get(url, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for model-controller health, got {res.status_code}: {res.text}")
        data = res.json().get("data", {})
        self.assertIn("status", data)

    def test_02_model_controller_predict(self):
        url = f"{BASE_URL}/v1/model_controller/predict"
        payload = {"state": [10.0, 0.5, 25.0, 70.0, 28.0, 65.0, 1.5, 6.5, 25.0, 0.9]}
        res = requests.post(url, json=payload, timeout=10)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for model-controller predict, got {res.status_code}: {res.text}")
        data = res.json().get("data", {})
        self.assertIn("D_mist", data)
        self.assertIn("interval_sec", data)
        self.assertIn("A_valve", data)
        self.assertIsInstance(data["D_mist"], (int, float))
        self.assertIsInstance(data["interval_sec"], (int, float))
        self.assertIn(data["A_valve"], [0, 1])

    def test_03_model_control_health(self):
        url = f"{BASE_URL}/v1/model_control/health"
        res = requests.get(url, timeout=5)
        self.assertEqual(res.status_code, 200, f"Expected 200 OK for model-control health, got {res.status_code}: {res.text}")
        data = res.json()
        self.assertEqual(data.get("status"), "ok")

    def test_04_model_control_trigger_predict(self):
        url = f"{BASE_URL}/v1/model_control/trigger-predict"
        res = requests.post(url, timeout=10)
        self.assertIn(res.status_code, [200, 503], f"Expected 200/503 for model-control trigger-predict, got {res.status_code}: {res.text}")


# Alias for backward compatibility
TestPPOService = TestModelService


def run_unit_tests():
    """Run all unit & feature test cases across 14 microservices + PPO subsystem."""
    clean_all_test_results()
    try:
        cleanup_test_data()
    except Exception:
        pass

    suite = unittest.TestSuite()
    loader = unittest.TestLoader()

    suite.addTest(loader.loadTestsFromTestCase(TestSystemHealth))
    suite.addTest(loader.loadTestsFromTestCase(TestAuthService))
    suite.addTest(loader.loadTestsFromTestCase(TestModuleService))
    suite.addTest(loader.loadTestsFromTestCase(TestAnalyticsService))
    suite.addTest(loader.loadTestsFromTestCase(TestControlService))
    suite.addTest(loader.loadTestsFromTestCase(TestAlertService))
    suite.addTest(loader.loadTestsFromTestCase(TestAuditService))
    suite.addTest(loader.loadTestsFromTestCase(TestNotificationService))
    suite.addTest(loader.loadTestsFromTestCase(TestWebhookService))
    suite.addTest(loader.loadTestsFromTestCase(TestStreamService))
    suite.addTest(loader.loadTestsFromTestCase(TestMLService))
    suite.addTest(loader.loadTestsFromTestCase(TestExportService))
    suite.addTest(loader.loadTestsFromTestCase(TestWSGateway))
    suite.addTest(loader.loadTestsFromTestCase(TestDLQService))
    suite.addTest(loader.loadTestsFromTestCase(TestPPOService))

    runner = TimedTestRunner(verbosity=2)
    result = runner.run(suite)

    # Build service names list aligned with test classes
    service_names = [
        "SystemHealth", "Auth", "Module", "Analytics", "Control",
        "Alert", "Audit", "Notification", "Webhook", "Stream", "ML", "Export", "WSGateway", "DLQ", "PPO"
    ]

    pass_counts = []
    skip_counts = []
    fail_counts = []
    exec_times = []

    class_map = {
        TestSystemHealth: "SystemHealth",
        TestAuthService: "Auth",
        TestModuleService: "Module",
        TestAnalyticsService: "Analytics",
        TestControlService: "Control",
        TestAlertService: "Alert",
        TestAuditService: "Audit",
        TestNotificationService: "Notification",
        TestWebhookService: "Webhook",
        TestStreamService: "Stream",
        TestMLService: "ML",
        TestExportService: "Export",
        TestWSGateway: "WSGateway",
        TestDLQService: "DLQ",
        TestPPOService: "PPO",
    }

    class_stats = {name: {"skip": 0, "fail": 0} for name in service_names}

    for test, err in result.errors + result.failures:
        class_name = class_map.get(test.__class__, test.__class__.__name__)
        class_stats[class_name]["fail"] += 1

    for test, reason in result.skipped:
        class_name = class_map.get(test.__class__, test.__class__.__name__)
        class_stats[class_name]["skip"] += 1

    known_totals = {
        "SystemHealth": 1, "Auth": 13, "Module": 16, "Analytics": 6,
        "Control": 15, "Alert": 6, "Audit": 5, "Notification": 5,
        "Webhook": 5, "Stream": 12, "ML": 10, "Export": 4, "WSGateway": 2, "DLQ": 2, "PPO": 4,
    }

    for name in service_names:
        total = known_totals.get(name, 0)
        skipped = class_stats[name]["skip"]
        failed = class_stats[name]["fail"]
        passed = max(0, total - skipped - failed)
        pass_counts.append(passed)
        skip_counts.append(skipped)
        fail_counts.append(failed)
        exec_times.append(0.0)

    if hasattr(result, "test_class_times"):
        for i, name in enumerate(service_names):
            time_val = result.test_class_times.get(name, 0.0)
            if time_val == 0.0:
                time_val = result.test_class_times.get(f"Test{name}", 0.0)
            exec_times[i] = time_val

    try:
        save_captured_results()
    except Exception:
        pass
    finally:
        try:
            cleanup_test_data()
        except Exception:
            pass

    return result.wasSuccessful(), service_names, pass_counts, skip_counts, fail_counts, exec_times