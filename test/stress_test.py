"""
enyx-enterprise - Industry-Standard Web & API Stress Test Suite
Implements Load, Spike, Soak, Breakpoint, and WebSocket Concurrency Stress Testing.
"""

import os
import sys
import io
import json
import time
import math
import random
import argparse
import concurrent.futures
from datetime import datetime
from typing import List, Dict, Any
import requests

try:
    import websocket
except ImportError:
    websocket = None

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    _HAS_MPL = True
except ImportError:
    _HAS_MPL = False

import config


class Tee(io.TextIOBase):
    """Write stream wrapper that mirrors output to multiple sinks (console + log file)."""

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


def worker_loop(base_url: str, token: str, duration: float, target_rps: float, stats: Stats, phase: str = "all"):
    pool = config.weighted_endpoint_pool(phase)
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


def run_load_test(base_url: str, token: str, concurrency: int, duration: float, rps: float, phase: str = "all") -> Stats:
    stats = Stats()
    worker_rps = rps / max(concurrency, 1)
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(worker_loop, base_url, token, duration, worker_rps, stats, phase)
            for _ in range(concurrency)
        ]
        concurrent.futures.wait(futures)
    stats.finish()
    return stats


def run_spike_test(base_url: str, token: str, concurrency: int, baseline_rps: float, spike_rps: float, phase: str = "all") -> dict:
    print(f"[*] Spike Phase 1: Baseline Load ({baseline_rps} RPS for 10s)...")
    base_stats = run_load_test(base_url, token, concurrency, 10.0, baseline_rps, phase)

    print(f"[*] Spike Phase 2: Traffic Surge ({spike_rps} RPS for 15s)...")
    spike_stats = run_load_test(base_url, token, concurrency * 2, 15.0, spike_rps, phase)

    print(f"[*] Spike Phase 3: Recovery Load ({baseline_rps} RPS for 10s)...")
    recovery_stats = run_load_test(base_url, token, concurrency, 10.0, baseline_rps, phase)

    return {
        "baseline": base_stats,
        "spike": spike_stats,
        "recovery": recovery_stats,
    }


def run_breakpoint_test(base_url: str, token: str, phase: str = "all") -> dict:
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
        st = run_load_test(base_url, token, lvl["users"], lvl["duration"], lvl["rps"], phase)
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
            knee_point = results[-1]

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


def _stats_to_dict(stats: Stats, title: str) -> dict:
    return {
        "title": title,
        "total_requests": stats.total,
        "duration_s": round(stats.duration(), 2),
        "throughput_rps": round(stats.rps(), 2),
        "error_rate_pct": round(stats.error_rate(), 2),
        "latency_p50_ms": round(stats.percentile(50), 2),
        "latency_p95_ms": round(stats.percentile(95), 2),
        "latency_p99_ms": round(stats.percentile(99), 2),
        "status_codes": {str(k): v for k, v in sorted(stats.status_counter.items())},
    }


def save_report(report: dict, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    phase = str(report.get("phase", "all"))
    base = f"stress_test_fase{phase}_{ts}"
    json_path = os.path.join(out_dir, base + ".json")
    md_path = os.path.join(out_dir, base + ".md")

    with open(json_path, "w") as fh:
        json.dump(report, fh, indent=2, default=str)

    lines = [
        f"# enyx-enterprise Stress Test Report — Fase {phase}",
        "",
        f"- **Generated**: {report.get('generated', datetime.now().isoformat(timespec='seconds'))}",
        f"- **Mode**: {report.get('mode', 'n/a')}",
        f"- **Target Gateway**: {report.get('base_url', 'n/a')}",
        f"- **Phase scope**: Fase {phase} — 10 core microservices (Auth, Module, Analytics, Control, Alert, Notification, Stream, Audit, Export, WS-Gateway); AI/ML excluded from load per §4.4.2/§4.5.3" if phase == '1' else f"- **Phase scope**: Fase {phase} — 13 microservices (10 core + 3 AI/ML running), AI/ML excluded from load per §4.5.3",
        "",
    ]
    sections = report.get("sections", [])
    if sections:
        for sec in sections:
            lines.append(f"## {sec.get('title', 'Result')}")
            lines.append("")
            lines.append(f"- Total Requests : {sec.get('total_requests')}")
            lines.append(f"- Duration       : {sec.get('duration_s')} s")
            lines.append(f"- Throughput     : {sec.get('throughput_rps')} req/s")
            lines.append(f"- Error Rate     : {sec.get('error_rate_pct')} %")
            lines.append(f"- Latency P50    : {sec.get('latency_p50_ms')} ms")
            lines.append(f"- Latency P95    : {sec.get('latency_p95_ms')} ms")
            lines.append(f"- Latency P99    : {sec.get('latency_p99_ms')} ms")
            lines.append("")
            lines.append("Status Codes:")
            for code, count in sec.get("status_codes", {}).items():
                lines.append(f"- HTTP {code}: {count}")
            lines.append("")
    if report.get("breakpoint_levels"):
        lines.append("## Breakpoint Capacity Summary")
        lines.append("")
        lines.append("| Users | Target RPS | Actual RPS | P95 (ms) | Error % |")
        lines.append("|---|---|---|---|---|")
        for lvl in report["breakpoint_levels"]:
            lines.append(f"| {lvl['users']} | {lvl['target_rps']} | {lvl['actual_rps']} | {lvl['p95']} | {lvl['err']} |")
        lines.append("")
        if report.get("knee_point"):
            lines.append(f"**Knee point detected**: Users={report['knee_point']['users']}, RPS={report['knee_point']['target_rps']}")
        else:
            lines.append("**Knee point**: None detected (P95 < 2000ms, error < 10%).")
        lines.append("")

    with open(md_path, "w") as fh:
        fh.write("\n".join(lines))

    print(f"[*] Report saved: {md_path}")
    print(f"[*] Report saved: {json_path}")
    return md_path, json_path


def generate_charts(report: dict, out_dir: str, ts: str) -> List[str]:
    """Render PNG charts from the test report. Returns list of created chart paths."""
    if not _HAS_MPL:
        print("[!] matplotlib not installed; skipping chart generation. (pip install -r requirements.txt)")
        return []

    phase = str(report.get("phase", "all"))
    created: List[str] = []

    # 1) Breakpoint throughput / latency / error chart (multi-level)
    levels = report.get("breakpoint_levels")
    if levels:
        users = [d["users"] for d in levels]
        actual_rps = [d["actual_rps"] for d in levels]
        p95 = [d["p95"] for d in levels]
        err = [d["err"] for d in levels]

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
        fig.suptitle(f"enyx-enterprise — Breakpoint Capacity (Fase {phase})", fontsize=13, fontweight="bold")

        c1 = "#2980b9"
        ax1.set_xlabel("Concurrent Virtual Users")
        ax1.set_ylabel("Throughput (req/s)", color=c1, fontweight="bold")
        l1 = ax1.plot(users, actual_rps, marker="o", color=c1, linewidth=2.5, label="Actual Throughput (RPS)")
        ax1.tick_params(axis="y", labelcolor=c1)
        ax1.grid(True, linestyle="--", alpha=0.5)
        ax1_twin = ax1.twinx()
        c2 = "#e74c3c"
        ax1_twin.set_ylabel("Error Rate (%)", color=c2, fontweight="bold")
        l2 = ax1_twin.plot(users, err, marker="s", color=c2, linestyle="--", linewidth=2, label="Error Rate (%)")
        ax1_twin.tick_params(axis="y", labelcolor=c2)
        ax1_twin.set_ylim(0, max(max(err) * 1.5, 10))
        lines = l1 + l2
        ax1.legend(lines, [x.get_label() for x in lines], loc="upper left")
        ax1.set_title("Throughput & Error Rate vs Concurrency")

        ax2.plot(users, p95, marker="^", color="#8e44ad", linewidth=2.5, label="P95 Latency (ms)")
        ax2.set_xlabel("Concurrent Virtual Users")
        ax2.set_ylabel("Latency (ms)", fontweight="bold")
        ax2.set_title("P95 Latency Curve vs Concurrency")
        ax2.grid(True, linestyle="--", alpha=0.5)
        ax2.legend(loc="upper left")

        plt.tight_layout()
        bp_path = os.path.join(out_dir, f"stress_test_fase{phase}_{ts}_breakpoint.png")
        plt.savefig(bp_path, dpi=300)
        plt.close()
        created.append(bp_path)

    # 2) Per-section latency + throughput summary chart (load/spike/soak/ws)
    sections = report.get("sections", [])
    if sections:
        titles = [s.get("title", f"sec{i}") for i, s in enumerate(sections)]
        short = [t.split("(")[0].strip()[:18] for t in titles]
        p50 = [s.get("latency_p50_ms", 0) for s in sections]
        p95 = [s.get("latency_p95_ms", 0) for s in sections]
        p99 = [s.get("latency_p99_ms", 0) for s in sections]
        rps = [s.get("throughput_rps", 0) for s in sections]
        err = [s.get("error_rate_pct", 0) for s in sections]

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
        fig.suptitle(f"enyx-enterprise — Load Summary (Fase {phase})", fontsize=13, fontweight="bold")

        x = range(len(short))
        w = 0.27
        ax1.bar([i - w for i in x], p50, width=w, label="P50", color="#27ae60")
        ax1.bar(list(x), p95, width=w, label="P95", color="#f39c12")
        ax1.bar([i + w for i in x], p99, width=w, label="P99", color="#e74c3c")
        ax1.set_xticks(list(x))
        ax1.set_xticklabels(short, rotation=20, ha="right", fontsize=8)
        ax1.set_ylabel("Latency (ms)")
        ax1.set_title("Latency Percentiles by Phase")
        ax1.grid(True, axis="y", linestyle="--", alpha=0.5)
        ax1.legend()

        ax2.plot(short, rps, marker="o", color="#2980b9", linewidth=2.5, label="Throughput (RPS)")
        ax2_twin = ax2.twinx()
        ax2_twin.plot(short, err, marker="s", color="#e74c3c", linestyle="--", linewidth=2, label="Error Rate (%)")
        ax2_twin.set_ylabel("Error Rate (%)", color="#e74c3c")
        ax2_twin.set_ylim(0, max(max(err) * 1.5, 10))
        ax2.set_xticks(range(len(short)))
        ax2.set_xticklabels(short, rotation=20, ha="right", fontsize=8)
        ax2.set_ylabel("Throughput (req/s)", color="#2980b9")
        ax2.set_title("Throughput & Error Rate by Phase")
        ax2.grid(True, linestyle="--", alpha=0.5)
        ax2.legend(loc="upper left")

        plt.tight_layout()
        sum_path = os.path.join(out_dir, f"stress_test_fase{phase}_{ts}_summary.png")
        plt.savefig(sum_path, dpi=300)
        plt.close()
        created.append(sum_path)

    # 3) WebSocket concurrency chart
    ws = report.get("ws")
    if ws and "successful" in ws:
        fig, ax = plt.subplots(figsize=(6, 5))
        ax.bar(["Successful", "Failed"], [ws.get("successful", 0), ws.get("failed", 0)],
               color=["#27ae60", "#e74c3c"])
        ax.set_title(f"enyx-enterprise — WebSocket Concurrency (Fase {phase})\nRequested: {ws.get('concurrency', 0)}")
        ax.set_ylabel("Connections")
        ax.grid(True, axis="y", linestyle="--", alpha=0.5)
        plt.tight_layout()
        ws_path = os.path.join(out_dir, f"stress_test_fase{phase}_{ts}_websocket.png")
        plt.savefig(ws_path, dpi=300)
        plt.close()
        created.append(ws_path)

    for p in created:
        print(f"[*] Chart generated: {p}")
    return created


def main():
    parser = argparse.ArgumentParser(prog="stress_test", description="API & Web Stress Testing Engine")
    parser.add_argument("mode", nargs="?", choices=["load", "spike", "soak", "breakpoint", "ws"], default=None,
                        help="Stress test execution mode. Omit to run full Fase suite (--phase1/--phase2).")
    parser.add_argument("--base-url", default=config.BASE_URL, help="Base API Gateway URL")
    parser.add_argument("--username", default=config.ADMIN_USERNAME, help="Admin Username")
    parser.add_argument("--password", default=config.ADMIN_PASSWORD, help="Admin Password")
    parser.add_argument("--users", type=int, default=10, help="Number of concurrent virtual users")
    parser.add_argument("--rps", type=float, default=50, help="Target Requests Per Second")
    parser.add_argument("--duration", type=float, default=None, help="Test duration in seconds (default: 20s)")
    parser.add_argument("--spike-rps", type=float, default=250, help="Spike mode peak RPS")
    phase_group = parser.add_mutually_exclusive_group()
    phase_group.add_argument("--phase1", action="store_const", const="1", dest="phase",
                             help="Fase 1 scope: 10 core services only (no ML / model-control)")
    phase_group.add_argument("--phase2", action="store_const", const="2", dest="phase",
                             help="Fase 2 scope: full suite (all services)")
    parser.add_argument("--phase", choices=["1", "2"], default="1",
                        help="Service scope (default: 1). '1' = 10 core services, '2' = full suite")
    parser.add_argument("--log", default=None, help="Path to write the full test log (default: results/stress_test_fase<phase>_<timestamp>.log)")
    parser.add_argument("--results-dir", default=None, help="Results directory (default: test/results/phase<phase>)")

    args = parser.parse_args()
    if args.phase is None:
        args.phase = "1"

    report_phase = args.phase
    api_pool_phase = "1"
    run_suite = args.mode is None
    if args.duration is None:
        args.duration = 20

    results_base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    dir_phase = "1" if report_phase == "1" else "2"
    phase_dir = os.path.join(results_base, f"phase{dir_phase}")
    out_dir = args.results_dir if args.results_dir else phase_dir
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = args.log or os.path.join(out_dir, f"stress_test_fase{report_phase}_{ts}.log")
    log_file = open(log_path, "a", buffering=1)
    original_stdout, original_stderr = sys.stdout, sys.stderr
    sys.stdout = Tee(original_stdout, log_file)
    sys.stderr = Tee(original_stderr, log_file)

    print("=" * 65)
    print(f" enyx-enterprise Stress Test — Fase {report_phase} | mode={args.mode}")
    print(f" Started : {datetime.now().isoformat(timespec='seconds')}")
    print(f" Log file: {log_path}")
    print("=" * 65)

    print(f"[*] Target Gateway: {args.base_url}")
    print("[*] Authenticating with Auth Service...")
    token = get_auth_token(args.base_url, args.username, args.password)
    print("[*] Auth Token obtained successfully!")

    report = {
        "mode": args.mode,
        "phase": report_phase,
        "api_pool_phase": api_pool_phase,
        "base_url": args.base_url,
        "generated": datetime.now().isoformat(timespec="seconds"),
        "sections": [],
    }

    if run_suite:
        suite_phase = report_phase
        print(f"[*] === Running Fase {suite_phase} Full Suite (load + breakpoint) ===")
        print(f"[*] [1/2] HTTP Load Test ({args.users} users, {args.rps} RPS, 20s) ...")
        st = run_load_test(args.base_url, token, args.users, args.rps, 20.0, api_pool_phase)
        print_summary_table(st, "HTTP LOAD TEST RESULTS")
        report["sections"].append(_stats_to_dict(st, "HTTP LOAD TEST RESULTS"))

        print(f"[*] [2/2] Breakpoint Capacity Test ...")
        res = run_breakpoint_test(args.base_url, token, api_pool_phase)
        print("\n" + "=" * 65)
        print("  BREAKPOINT CAPACITY SUMMARY")
        print("=" * 65)
        for lvl in res["levels"]:
            print(f" Users: {lvl['users']:2d} | Target: {lvl['target_rps']:3d} RPS | Actual: {lvl['actual_rps']:5.1f} RPS | P95: {lvl['p95']:6.1f}ms | Errors: {lvl['err']:.1f}%")
        print("=" * 65 + "\n")
        report["breakpoint_levels"] = res["levels"]
        report["knee_point"] = res["knee_point"]

    elif args.mode == "load":
        print(f"[*] Running HTTP Load Test ({args.users} users, {args.rps} RPS, {args.duration}s) [Fase {report_phase}; core services only, AI/ML excluded per §4.4.2/§4.5.3]...")
        st = run_load_test(args.base_url, token, args.users, args.duration, args.rps, api_pool_phase)
        print_summary_table(st, "HTTP LOAD TEST RESULTS")
        report["sections"].append(_stats_to_dict(st, "HTTP LOAD TEST RESULTS"))

    elif args.mode == "spike":
        res = run_spike_test(args.base_url, token, args.users, args.rps, args.spike_rps, api_pool_phase)
        print_summary_table(res["baseline"], "SPIKE TEST - PHASE 1 (BASELINE)")
        print_summary_table(res["spike"], "SPIKE TEST - PHASE 2 (TRAFFIC SURGE)")
        print_summary_table(res["recovery"], "SPIKE TEST - PHASE 3 (RECOVERY)")
        report["sections"].append(_stats_to_dict(res["baseline"], "SPIKE TEST - PHASE 1 (BASELINE)"))
        report["sections"].append(_stats_to_dict(res["spike"], "SPIKE TEST - PHASE 2 (TRAFFIC SURGE)"))
        report["sections"].append(_stats_to_dict(res["recovery"], "SPIKE TEST - PHASE 3 (RECOVERY)"))

    elif args.mode == "soak":
        print(f"[*] Running Soak Endurance Test ({args.users} users, {args.rps} RPS, {args.duration}s) [Fase {report_phase}; core services only, AI/ML excluded per §4.4.2/§4.5.3]...")
        st = run_load_test(args.base_url, token, args.users, args.duration, args.rps, api_pool_phase)
        print_summary_table(st, "SOAK ENDURANCE TEST RESULTS")
        report["sections"].append(_stats_to_dict(st, "SOAK ENDURANCE TEST RESULTS"))

    elif args.mode == "breakpoint":
        res = run_breakpoint_test(args.base_url, token, api_pool_phase)
        print("\n" + "=" * 65)
        print("  BREAKPOINT CAPACITY SUMMARY")
        print("=" * 65)
        for lvl in res["levels"]:
            print(f" Users: {lvl['users']:2d} | Target: {lvl['target_rps']:3d} RPS | Actual: {lvl['actual_rps']:5.1f} RPS | P95: {lvl['p95']:6.1f}ms | Errors: {lvl['err']:.1f}%")
        print("=" * 65 + "\n")
        report["breakpoint_levels"] = res["levels"]
        report["knee_point"] = res["knee_point"]

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
        report["ws"] = ws_res

    save_report(report, out_dir)
    generate_charts(report, out_dir, ts)

    print("=" * 65)
    print(f" Stress Test completed at {datetime.now().isoformat(timespec='seconds')}")
    print(f" Full log available at: {log_path}")
    print("=" * 65)

    sys.stdout = original_stdout
    sys.stderr = original_stderr
    log_file.close()


if __name__ == "__main__":
    main()
