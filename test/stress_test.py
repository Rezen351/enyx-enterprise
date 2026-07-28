"""
enyx-enterprise - Industry-Standard Web & API Stress Test Suite
Implements Load, Spike, Soak, Breakpoint, and WebSocket Concurrency Stress Testing.
"""

import os
import sys
import time
import math
import random
import argparse
import concurrent.futures
from typing import List, Dict, Any
import requests

try:
    import websocket
except ImportError:
    websocket = None

import config


class Stats:
    def __init__(self):
        self.latencies: List[float] = []
        self.status_counter: Dict[int, int] = {}
        self.total: int = 0
        self.start_time: float = time.time()
        self.end_time: float = 0.0

    def add(self, latency_ms: float, status_code: int):
        self.total += 1
        self.latencies.append(latency_ms)
        self.status_counter[status_code] = self.status_counter.get(status_code, 0) + 1

    def finish(self):
        self.end_time = time.time()

    def duration(self) -> float:
        end = self.end_time if self.end_time > 0 else time.time()
        return max(end - self.start_time, 0.001)

    def rps(self) -> float:
        return self.total / self.duration()

    def percentile(self, p: float) -> float:
        if not self.latencies:
            return 0.0
        sorted_l = sorted(self.latencies)
        idx = math.ceil((p / 100.0) * len(sorted_l)) - 1
        return sorted_l[max(0, min(idx, len(sorted_l) - 1))]

    def p50(self) -> float:
        return self.percentile(50)

    def p99(self) -> float:
        return self.percentile(99)

    def status_code_distribution(self) -> dict:
        return dict(self.status_counter)

    def error_rate(self) -> float:
        if self.total == 0:
            return 0.0
        errors = sum(count for status, count in self.status_counter.items() if status >= 400 and status != 429)
        return (errors / self.total) * 100.0


def get_auth_token(base_url: str, username: str, password: str) -> str:
    url = f"{base_url}/v1/auth/login"
    last_status = None
    last_text = ""
    for attempt in range(1, 4):
        try:
            res = requests.post(url, json={"identifier": username, "password": password}, timeout=10)
            last_status = res.status_code
            last_text = res.text
            if res.status_code == 200:
                data = res.json().get("data", {})
                return data.get("access_token") or data.get("token")
            if res.status_code == 429 and attempt < 3:
                time.sleep(2 ** attempt)
                continue
        except Exception:
            if attempt < 3:
                time.sleep(2 ** attempt)
                continue
    raise RuntimeError(f"Login failed after retries: {last_status} {last_text}")


def execute_request(base_url: str, token: str, endpoint: dict) -> tuple:
    url = f"{base_url}{endpoint['path']}"
    headers = {}
    if endpoint["auth"] and token:
        headers["Authorization"] = f"Bearer {token}"

    start = time.time()
    try:
        timeout = 10
        if endpoint["method"] == "GET":
            res = requests.get(url, headers=headers, timeout=timeout)
        elif endpoint["method"] == "POST":
            res = requests.post(url, json=endpoint.get("body"), headers=headers, timeout=timeout)
        else:
            res = requests.request(endpoint["method"], url, headers=headers, timeout=timeout)
        latency = (time.time() - start) * 1000.0
        return latency, res.status_code
    except Exception:
        latency = (time.time() - start) * 1000.0
        return latency, 599


def worker_loop(base_url: str, token: str, duration: float, target_rps: float, stats: Stats):
    pool = config.weighted_endpoint_pool()
    end_by = time.time() + duration
    interval = 1.0 / max(target_rps, 1)

    while time.time() < end_by:
        t0 = time.time()
        ep = random.choice(pool)
        latency, status = execute_request(base_url, token, ep)
        stats.add(latency, status)
        elapsed = time.time() - t0
        sleep_time = interval - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)


def run_load_test(base_url: str, token: str, concurrency: int, duration: float, rps: float) -> Stats:
    stats = Stats()
    worker_rps = rps / max(concurrency, 1)
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(worker_loop, base_url, token, duration, worker_rps, stats)
            for _ in range(concurrency)
        ]
        concurrent.futures.wait(futures)
    stats.finish()
    return stats


def run_spike_test(base_url: str, token: str, concurrency: int, baseline_rps: float, spike_rps: float) -> dict:
    print(f"[*] Spike Phase 1: Baseline Load ({baseline_rps} RPS for 10s)...")
    base_stats = run_load_test(base_url, token, concurrency, 10.0, baseline_rps)

    print(f"[*] Spike Phase 2: Traffic Surge ({spike_rps} RPS for 15s)...")
    spike_stats = run_load_test(base_url, token, concurrency * 2, 15.0, spike_rps)

    print(f"[*] Spike Phase 3: Recovery Load ({baseline_rps} RPS for 10s)...")
    recovery_stats = run_load_test(base_url, token, concurrency, 10.0, baseline_rps)

    return {
        "baseline": base_stats,
        "spike": spike_stats,
        "recovery": recovery_stats,
    }


def run_breakpoint_test(base_url: str, token: str) -> dict:
    print("[*] Starting Breakpoint Capacity Test (Finding System Knee / Max Throughput)...")
    levels = [
        {"users": 5, "rps": 10, "duration": 8},
        {"users": 10, "rps": 50, "duration": 8},
        {"users": 20, "rps": 100, "duration": 8},
        {"users": 40, "rps": 250, "duration": 8},
        {"users": 60, "rps": 500, "duration": 8},
    ]

    results = []
    knee_point = None

    for lvl in levels:
        print(f"  -> Testing Concurrency={lvl['users']}, Target RPS={lvl['rps']}...")
        st = run_load_test(base_url, token, lvl["users"], lvl["duration"], lvl["rps"])
        p50 = st.p50()
        p95 = st.percentile(95)
        p99 = st.p99()
        err_rate = st.error_rate()
        status_dist = st.status_code_distribution()
        results.append({
            "users": lvl["users"],
            "target_rps": lvl["rps"],
            "actual_rps": st.rps(),
            "p50": p50,
            "p95": p95,
            "p99": p99,
            "err": err_rate,
            "status_codes": status_dist,
        })

        print(f"     Actual RPS: {st.rps():.1f} | P50: {p50:.1f}ms | P95: {p95:.1f}ms | P99: {p99:.1f}ms | Error Rate: {err_rate:.1f}%")
        
        if (p95 > 2000.0 or err_rate > 10.0) and knee_point is None:
            knee_point = lvl

    return {"levels": results, "knee_point": knee_point}


def run_ws_stress(base_url: str, token: str, concurrency: int, duration: float) -> dict:
    if websocket is None:
        return {"error": "websocket-client package not installed"}

    ws_base = base_url.replace("http://", "ws://").replace("https://", "wss://")
    url = f"{ws_base}/v1/ws/system-status?token={token}"

    successful = 0
    failed = 0
    active_conns = []

    print(f"[*] Opening {concurrency} concurrent WebSocket connections to {url}...")
    for _ in range(concurrency):
        try:
            ws = websocket.create_connection(url, timeout=3)
            active_conns.append(ws)
            successful += 1
        except Exception:
            failed += 1

    print(f"[*] Holding {len(active_conns)} WebSocket connections open for {duration}s...")
    time.sleep(duration)

    for ws in active_conns:
        try:
            ws.close()
        except Exception:
            pass

    return {"concurrency": concurrency, "successful": successful, "failed": failed}


def print_summary_table(stats: Stats, title: str):
    print("\n" + "=" * 65)
    print(f"  {title}")
    print("=" * 65)
    print(f" Total Requests     : {stats.total}")
    print(f" Duration           : {stats.duration():.2f} s")
    print(f" Throughput         : {stats.rps():.2f} req/s")
    print(f" Error Rate         : {stats.error_rate():.2f} %")
    print(f" Latency P50        : {stats.percentile(50):.2f} ms")
    print(f" Latency P95        : {stats.percentile(95):.2f} ms")
    print(f" Latency P99        : {stats.percentile(99):.2f} ms")
    print("-" * 65)
    print(" Status Codes Breakdown:")
    for code, count in sorted(stats.status_counter.items()):
        status_name = "OK" if code == 200 else ("Rate Limited (Kong)" if code == 429 else "Error")
        print(f"   HTTP {code} ({status_name}): {count}")
    print("=" * 65 + "\n")


def main():
    parser = argparse.ArgumentParser(prog="stress_test", description="API & Web Stress Testing Engine")
    parser.add_argument("mode", choices=["load", "spike", "soak", "breakpoint", "ws"], help="Stress test execution mode")
    parser.add_argument("--base-url", default=config.BASE_URL, help="Base API Gateway URL")
    parser.add_argument("--username", default=config.ADMIN_USERNAME, help="Admin Username")
    parser.add_argument("--password", default=config.ADMIN_PASSWORD, help="Admin Password")
    parser.add_argument("--users", type=int, default=10, help="Number of concurrent virtual users")
    parser.add_argument("--rps", type=float, default=50, help="Target Requests Per Second")
    parser.add_argument("--duration", type=float, default=15, help="Test duration in seconds")
    parser.add_argument("--spike-rps", type=float, default=250, help="Spike mode peak RPS")

    args = parser.parse_args()

    print(f"[*] Target Gateway: {args.base_url}")
    print("[*] Authenticating with Auth Service...")
    token = get_auth_token(args.base_url, args.username, args.password)
    print("[*] Auth Token obtained successfully!")

    if args.mode == "load":
        print(f"[*] Running HTTP Load Test ({args.users} users, {args.rps} RPS, {args.duration}s)...")
        st = run_load_test(args.base_url, token, args.users, args.duration, args.rps)
        print_summary_table(st, "HTTP LOAD TEST RESULTS")

    elif args.mode == "spike":
        res = run_spike_test(args.base_url, token, args.users, args.rps, args.spike_rps)
        print_summary_table(res["baseline"], "SPIKE TEST - PHASE 1 (BASELINE)")
        print_summary_table(res["spike"], "SPIKE TEST - PHASE 2 (TRAFFIC SURGE)")
        print_summary_table(res["recovery"], "SPIKE TEST - PHASE 3 (RECOVERY)")

    elif args.mode == "soak":
        print(f"[*] Running Soak Endurance Test ({args.users} users, {args.rps} RPS, {args.duration}s)...")
        st = run_load_test(args.base_url, token, args.users, args.duration, args.rps)
        print_summary_table(st, "SOAK ENDURANCE TEST RESULTS")

    elif args.mode == "breakpoint":
        res = run_breakpoint_test(args.base_url, token)
        print("\n" + "=" * 65)
        print("  BREAKPOINT CAPACITY SUMMARY")
        print("=" * 65)
        for lvl in res["levels"]:
            print(f" Users: {lvl['users']:2d} | Target: {lvl['target_rps']:3d} RPS | Actual: {lvl['actual_rps']:5.1f} RPS | P95: {lvl['p95']:6.1f}ms | Errors: {lvl['err']:.1f}%")
        print("=" * 65 + "\n")

    elif args.mode == "ws":
        print(f"[*] Running WebSocket Stress Test ({args.users} connections, {args.duration}s hold)...")
        ws_res = run_ws_stress(args.base_url, token, args.users, args.duration)
        print("\n" + "=" * 65)
        print("  WEBSOCKET STRESS TEST RESULTS")
        print("=" * 65)
        print(f" Requested Concurrency : {ws_res['concurrency']}")
        print(f" Successful Handshakes: {ws_res['successful']}")
        print(f" Failed Handshakes    : {ws_res['failed']}")
        print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
