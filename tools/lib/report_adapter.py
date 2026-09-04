"""Adapter: test-results.json → ifplayer HTML report.

Converts the engine-agnostic test-results.json schema (produced by the
per-engine test converters) into ifplayer's TestResult
objects, then calls ifplayer's report.emit_html() to produce the exact
same HTML that ifplayer produces for native .test files.

This means every engine in IF Hub gets the same rich, transcript-first
HTML viewer — no separate JavaScript template needed.

Usage:
    from tools.lib.report_adapter import json_to_html

    html = json_to_html(json_data, title="Tests — zork1")
    Path("tests.html").write_text(html, encoding="utf-8")
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ifplayer import diff as diff_mod
from ifplayer import i7, report, runner, test_format


# ─── Assertion type mapping ────────────────────────────────────────────
#
# test-results.json uses:   ok-contains, ok-not-contains, ok-matches,
#                            ok-not-matches, ok-starts-with, ok-ends-with,
#                            ok-equals, event, state, event-not, state-not
#
# ifplayer uses:             contains, regex, not_contains
#
# We map to the closest ifplayer kind for display; the "raw_line" field
# carries the original type string for reference.

_KIND_MAP: dict[str, test_format.AssertKind] = {
    "ok-contains": "contains",
    "ok-not-contains": "not_contains",
    "ok-contains-any": "contains",   # match any of several values
    "ok-matches": "regex",
    "ok-not-matches": "regex",       # negated regex — note in label
    "ok-starts-with": "contains",
    "ok-ends-with": "contains",
    "ok-equals": "contains",
    "event": "contains",
    "event-not": "not_contains",
    "state": "contains",
    "state-not": "not_contains",
}


def _format_values(value: str | list) -> str:
    """Format a value or list of values for display."""
    if isinstance(value, list):
        return ", ".join(f'"{v}"' for v in value)
    return f'"{value}"'


def _flatten_value(value: str | list) -> str:
    """Flatten a list value to a string for ifplayer's Assertion.text field."""
    if isinstance(value, list):
        return " | ".join(value)
    return value


def _assertion_label(a_type: str, value: str | list) -> str:
    """Create a human-readable label for an assertion."""
    if a_type == "ok-contains-any":
        return f"Contains any of: {_format_values(value)}"
    labels = {
        "ok-contains": f'Contains "{value}"',
        "ok-not-contains": f'Not contains "{value}"',
        "ok-matches": f"Matches /{value}/",
        "ok-not-matches": f"Not matches /{value}/",
        "ok-starts-with": f'Starts with "{value}"',
        "ok-ends-with": f'Ends with "{value}"',
        "ok-equals": f'Equals "{value}"',
        "event": f"Event: {value}",
        "event-not": f"No event: {value}",
        "state": f"State: {value}",
        "state-not": f"Not state: {value}",
    }
    return labels.get(a_type, f"{a_type}: {value}")


def _raw_line(a_type: str, value: str | list) -> str:
    """Reconstruct a plausible raw assertion line for display."""
    if a_type == "ok-contains-any":
        vals = value if isinstance(value, list) else [value]
        return "? any: " + " | ".join(f'"{v}"' for v in vals)
    if a_type == "ok-contains":
        return f"? {value}"
    if a_type == "ok-not-contains":
        return f"?! {value}"
    if a_type == "ok-matches":
        return f"? /{value}/"
    if a_type == "ok-not-matches":
        return f"?! /{value}/"
    return f"? {value}"


def _compute_assertion_matches(
    output: str, a_type: str, value: str | list, passed: bool
) -> list[tuple[int, int]]:
    """Compute character ranges where the assertion matched in the output.

    This enables ifplayer's inline "show" toggle buttons that highlight
    the matching text in the game response.
    """
    if not output or not value:
        return []

    # For contains-any, highlight whichever values matched
    if a_type == "ok-contains-any":
        if not passed:
            return []  # nothing matched — nothing to highlight
        vals = value if isinstance(value, list) else [value]
        all_matches: list[tuple[int, int]] = []
        lower_out = output.lower()
        for v in vals:
            lower_val = v.lower()
            start = 0
            while True:
                idx = lower_out.find(lower_val, start)
                if idx == -1:
                    break
                all_matches.append((idx, idx + len(v)))
                start = idx + 1
        return sorted(all_matches)

    # For pass + positive assertion, or fail + negative assertion,
    # find where the pattern appears
    is_positive = a_type in ("ok-contains", "ok-starts-with", "ok-ends-with",
                              "ok-equals", "ok-matches")
    should_show = (passed and is_positive) or (not passed and not is_positive)

    if not should_show:
        return []

    if a_type in ("ok-matches", "ok-not-matches"):
        try:
            return [(m.start(), m.end()) for m in re.finditer(value, output)]
        except re.error:
            return []
    else:
        matches = []
        lower_out = output.lower()
        lower_val = value.lower()
        start = 0
        while True:
            idx = lower_out.find(lower_val, start)
            if idx == -1:
                break
            matches.append((idx, idx + len(value)))
            start = idx + 1
        return matches


def _convert_assertion(a: dict, output: str) -> runner.AssertionResult:
    """Convert one JSON assertion to an ifplayer AssertionResult."""
    a_type = a.get("type", "ok-contains")
    # ok-contains-any uses `values` (plural array)
    value = a.get("value", "") or a.get("values", "")
    passed = a.get("passed", True)

    kind = _KIND_MAP.get(a_type, "contains")
    label = _assertion_label(a_type, value)
    raw = _raw_line(a_type, value)

    # ifplayer Assertion.text expects a string; flatten arrays
    text_val = _flatten_value(value) if isinstance(value, list) else value

    assertion = test_format.Assertion(
        kind=kind,
        text=text_val,
        raw_line=raw,
        line_no=0,
        label=label,
    )

    matches = _compute_assertion_matches(output, a_type, value, passed)

    detail = ""
    if not passed:
        if a_type == "ok-contains-any":
            vals = value if isinstance(value, list) else [value]
            quoted = ", ".join(f'"{v}"' for v in vals)
            detail = f"Expected to find any of: {quoted} in output"
        elif a_type in ("ok-contains", "ok-starts-with", "ok-ends-with", "ok-equals"):
            detail = f'Expected to find "{value}" in output'
        elif a_type == "ok-not-contains":
            detail = f'Expected NOT to find "{value}" in output'
        elif a_type == "ok-matches":
            detail = f"Expected output to match /{value}/"
        elif a_type == "ok-not-matches":
            detail = f"Expected output NOT to match /{value}/"

    return runner.AssertionResult(
        assertion=assertion,
        passed=passed,
        detail=detail,
        matches=matches,
    )


def _parse_score(score_str: str) -> tuple[int, Optional[int]]:
    """Parse 'score 10' or '10/350' into (score, max)."""
    if not score_str:
        return (0, None)
    # "score 10"
    m = re.match(r"(?:score\s+)?(\d+)(?:\s*/\s*(\d+))?", str(score_str))
    if m:
        return (int(m.group(1)), int(m.group(2)) if m.group(2) else None)
    return (0, None)


def _convert_turn(cmd: dict, index: int) -> runner.TurnRecord:
    """Convert one JSON command to an ifplayer TurnRecord."""
    output = cmd.get("output", "")

    # Build assertions with match computation
    assertions = [
        _convert_assertion(a, output)
        for a in cmd.get("assertions", [])
    ]

    # Parse room from JSON or detect from output
    room_name = cmd.get("room")

    # Build TurnAnalysis
    score_delta = cmd.get("scoreDelta", 0) or 0
    parser_errors = cmd.get("parserErrors", []) or []
    outcome_val = cmd.get("outcome", "")

    analysis = i7.TurnAnalysis(
        room_name=room_name,
        score_delta=score_delta,
        won=outcome_val == "win",
        lost=outcome_val == "lose",
        parser_errors=parser_errors,
    )

    # Build GameState
    score_val, score_max = _parse_score(cmd.get("score", ""))
    room_identity = None
    if room_name:
        room_identity = i7.RoomIdentity(
            name=room_name,
            fingerprint="",
            instance=1,
        )

    state = i7.GameState(
        room=room_identity,
        score=score_val,
        score_max=score_max,
        turn=index + 1,
        ended=outcome_val in ("win", "lose", "end"),
        won=outcome_val == "win",
        lost=outcome_val == "lose",
    )

    # Build drift chunks if present
    drift = None
    if cmd.get("drift"):
        drift = [
            diff_mod.DiffChunk(kind=d.get("kind", "equal"), text=d.get("text", ""))
            for d in cmd["drift"]
        ]

    return runner.TurnRecord(
        index=index + 1,
        command=cmd.get("input", ""),
        observed_output=output,
        analysis=analysis,
        state_after=state,
        assertions=assertions,
        drift=drift,
        error=None,
        elapsed_ms=0.0,
    )


def _convert_transcript(tr: dict, story_id: str) -> runner.TestResult:
    """Convert one JSON transcript to an ifplayer TestResult."""
    commands = tr.get("commands", [])

    turns = [_convert_turn(cmd, i) for i, cmd in enumerate(commands)]

    # Determine outcome
    has_failures = any(t.status == "fail" for t in turns)
    outcome: runner.Outcome = "scenario"

    # Build a stub TestFile
    header = test_format.Header(
        test=tr.get("title", tr.get("file", "Test")),
        game=story_id,
    )
    test_file = test_format.TestFile(
        header=header,
        turns=[],  # not used by report.py
    )

    # Duration from summary if available
    duration_ms = 0.0
    summary = tr.get("summary", {})
    if "duration" in summary:
        duration_ms = float(summary["duration"])

    return runner.TestResult(
        test=test_file,
        turns=turns,
        outcome=outcome,
        duration_ms=duration_ms,
    )


def json_to_html(
    data: dict,
    *,
    title: Optional[str] = None,
) -> str:
    """Convert test-results.json data to ifplayer HTML report.

    Args:
        data: Parsed test-results.json dict.
        title: Page title (defaults to "Tests — {storyId}").

    Returns:
        Complete HTML document string.
    """
    story_id = data.get("storyId", "unknown")
    if title is None:
        title = f"Tests — {story_id}"

    transcripts = data.get("transcripts", [])
    results = [_convert_transcript(tr, story_id) for tr in transcripts]

    return report.emit_html(results, title=title)


def json_file_to_html(json_path: Path, html_path: Path, *, title: Optional[str] = None) -> None:
    """Read test-results.json, produce ifplayer HTML report.

    Args:
        json_path: Path to test-results.json.
        html_path: Output path for the HTML report.
        title: Optional page title.
    """
    data = json.loads(json_path.read_text(encoding="utf-8"))
    html_str = json_to_html(data, title=title)
    html_path.write_text(html_str, encoding="utf-8")


# ─── CLI entry point ───────────────────────────────────────────────────
#
# Usage:
#   python -m tools.lib.report_adapter test-results.json tests.html
#   python -m tools.lib.report_adapter test-results.json  # writes tests.html
#   python -m tools.lib.report_adapter test-results.json --title "My Tests"


def _cli() -> None:
    import argparse
    parser = argparse.ArgumentParser(
        description="Convert test-results.json to ifplayer HTML report",
    )
    parser.add_argument("json_path", type=Path, help="Path to test-results.json")
    parser.add_argument("html_path", type=Path, nargs="?", default=None,
                        help="Output HTML path (default: tests.html in same dir)")
    parser.add_argument("--title", default=None, help="Page title")
    args = parser.parse_args()

    html_out = args.html_path or args.json_path.parent / "tests.html"
    json_file_to_html(args.json_path, html_out, title=args.title)
    print(f"Wrote {html_out}")


if __name__ == "__main__":
    _cli()
