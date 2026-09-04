#!/usr/bin/env python3
"""Unified I7 test suite orchestrator.

All testing is scenario-based. There is no separate "walkthrough" concept —
scenarios that happen to win the game are automatically walkthrough candidates.
The one marked "primary" in the scenario index is the canonical walkthrough.

Usage:
    python test_suite.py --config tests/project.conf
    python test_suite.py --config tests/project.conf --category combat
    python test_suite.py --config tests/project.conf --json
    python test_suite.py --config tests/project.conf --ci
"""

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

_TOOLS_DIR = Path(__file__).resolve().parent

# Import config loader and report writer from sibling modules
_rt_spec = importlib.util.spec_from_file_location(
    "i7_run_tests", str(_TOOLS_DIR / "run_tests.py"))
_rt_mod = importlib.util.module_from_spec(_rt_spec)
_rt_spec.loader.exec_module(_rt_mod)
load_config = _rt_mod.load_config


def compute_sha256_prefix(path, length=8):
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:length]
    except OSError:
        return "unknown"


def load_suite(tests_dir):
    """Load suite.json or return a minimal default."""
    suite_path = tests_dir / "suite.json"
    if suite_path.is_file():
        return json.loads(suite_path.read_text(encoding="utf-8"))
    layers = {}
    for ext in ("*.scenario", "*.regtest"):
        for p in tests_dir.glob(ext):
            layers["scenarios"] = {"enabled": True}
            break
    return {"version": 1, "layers": layers}


def run_scenarios(cfg, suite, tests_dir, category=None, verbose=False):
    """Unified scenario runs: assertions + diagnostics + transcripts."""
    sc_conf = suite.get("layers", {}).get("scenarios", {})
    if not sc_conf.get("enabled", True):
        return {"status": "skip", "detail": "disabled"}

    # Check if scenario file exists
    has_scenarios = False
    if cfg.regtest_file and Path(cfg.regtest_file).is_file():
        has_scenarios = True
    else:
        for ext in ("*.scenario", "*.regtest"):
            if any(tests_dir.glob(ext)):
                has_scenarios = True
                break
    if not has_scenarios:
        return {"status": "skip", "detail": "no scenario file"}

    conf_path = tests_dir / "project.conf"
    cmd = [sys.executable, str(_TOOLS_DIR / "run_tests.py"),
           "--config", str(conf_path), "--all", "--json"]
    if category:
        cmd.extend(["--category", category])

    result = subprocess.run(cmd, capture_output=True, text=True)

    if verbose and result.stdout:
        print(result.stdout[:2000])

    try:
        data = json.loads(result.stdout)
        # Save detailed results for the dashboard
        detail_path = tests_dir / "results"
        detail_path.mkdir(parents=True, exist_ok=True)
        (detail_path / "scenarios-latest.json").write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8")

        wins = data.get("win_scenarios", [])
        primary = data.get("primary")
        assertions = data.get("assertions", {})

        layer_result = {
            "status": "pass" if data.get("failed", 0) == 0 else "fail",
            "total": data.get("total", 0),
            "passed": data.get("passed", 0),
            "failed": data.get("failed", 0),
            "skipped": data.get("skipped", 0),
            "wins": len(wins),
            "win_scenarios": wins,
            "assertions": assertions,
            "duration": data.get("duration_seconds", 0),
        }
        if primary:
            layer_result["primary_walkthrough"] = primary
        return layer_result
    except (json.JSONDecodeError, TypeError):
        if result.returncode == 0:
            return {"status": "pass", "detail": "completed"}
        return {"status": "fail",
                "detail": (result.stderr or result.stdout or "").strip()[:200]}


def write_report(project_dir, layer_results, binary_hash="", duration=0.0):
    """Write structured test results to tests/results/latest.json."""
    import shutil
    from datetime import datetime, timezone

    results_dir = Path(project_dir) / "tests" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    # Determine overall status
    statuses = [lr.get("status", "skip") for lr in layer_results.values()]
    if any(s == "fail" for s in statuses):
        overall = "fail"
    elif any(s == "pass" for s in statuses):
        overall = "pass"
    else:
        overall = "skip"

    report = {
        "game": Path(project_dir).name,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "binary_hash": binary_hash,
        "duration_seconds": round(duration, 1),
        "layers": layer_results,
        "overall": overall,
    }

    latest = results_dir / "latest.json"
    latest.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    # Archive a timestamped copy
    history_dir = results_dir / "history"
    history_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    shutil.copy2(str(latest), str(history_dir / f"{ts}.json"))

    return report


def format_report(report, verbose=False):
    """Format a report dict as human-readable text."""
    lines = []
    lines.append(f"=== Test Report: {report['game']} ===")
    lines.append(f"  Time:     {report['timestamp']}")
    if report.get("binary_hash"):
        lines.append(f"  Binary:   {report['binary_hash']}")
    lines.append(f"  Duration: {report['duration_seconds']}s")
    lines.append("")

    for layer_name, lr in report.get("layers", {}).items():
        status = lr.get("status", "skip").upper()
        marker = "+" if status == "PASS" else "-" if status == "FAIL" else "~"
        detail = lr.get("detail", "")

        line = f"  {marker} {layer_name:15s} {status}"
        if "total" in lr and "passed" in lr:
            line += f" ({lr['passed']}/{lr['total']})"
        if lr.get("assertions", {}).get("total"):
            a = lr["assertions"]
            line += f"  assertions={a['passed']}/{a['total']}"
        if lr.get("wins"):
            line += f"  {lr['wins']} win-paths"
        if detail:
            line += f"  {detail}"
        lines.append(line)

    lines.append("")
    lines.append(f"  Overall: {report['overall'].upper()}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Unified I7 test suite orchestrator.")
    parser.add_argument("--config", required=True, help="Path to project.conf")
    parser.add_argument("--category", help="Category filter for scenarios")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    parser.add_argument("--ci", action="store_true", help="CI mode: JSON output, exit code")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    cfg = load_config(args.config)
    tests_dir = cfg.project_dir / "tests"
    suite = load_suite(tests_dir)

    binary_hash = compute_sha256_prefix(cfg.primary.game_path)
    start_time = time.time()

    if not args.json and not args.ci:
        print(f"  Running scenarios...", end=" ", flush=True)

    result = run_scenarios(cfg, suite, tests_dir, args.category, args.verbose)
    layer_results = {"scenarios": result}

    if not args.json and not args.ci:
        status = result.get("status", "skip").upper()
        detail = result.get("detail", "")
        if "total" in result:
            detail = f"{result.get('passed', 0)}/{result['total']}"
            wins = result.get("wins", 0)
            if wins:
                detail += f", {wins} win-paths"
            a = result.get("assertions", {})
            if a.get("total"):
                detail += f", {a['passed']}/{a['total']} assertions"
        print(f"{status}  {detail}")

    elapsed = time.time() - start_time

    report = write_report(cfg.project_dir, layer_results, binary_hash, elapsed)

    if args.json or args.ci:
        json.dump(report, sys.stdout, indent=2)
        print()
    else:
        print()
        print(format_report(report))

    sys.exit(1 if report["overall"] == "fail" else 0)


if __name__ == "__main__":
    main()
