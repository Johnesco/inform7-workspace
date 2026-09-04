#!/usr/bin/env python3
"""Structured test report generator.

Collects results from all test suite layers and writes a JSON report
to tests/results/latest.json.

Usage:
    # Typically called by test_suite.py, not directly.
    python report.py --config tests/project.conf --results '{"layers": {...}}'
"""

import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_TOOLS_DIR))
from lib import config


def write_report(project_dir, layer_results, binary_hash="", duration=0.0):
    """Write structured test results to tests/results/latest.json."""
    results_dir = Path(project_dir) / "tests" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    cfg_fields = config.parse_conf_fields(project_dir)

    # Determine overall status
    statuses = [lr.get("status", "skip") for lr in layer_results.values()]
    if any(s == "fail" for s in statuses):
        overall = "fail"
    elif any(s == "pass" for s in statuses):
        overall = "pass"
    else:
        overall = "skip"

    report = {
        "game": cfg_fields.get("PROJECT_NAME", Path(project_dir).name),
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
        if "score" in lr:
            line += f" score={lr['score']}"
        if detail:
            line += f"  {detail}"
        lines.append(line)

    lines.append("")
    lines.append(f"  Overall: {report['overall'].upper()}")
    return "\n".join(lines)
