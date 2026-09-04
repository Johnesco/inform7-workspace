"""Convert run_tests.py --json output to IF Hub's test-results.json format.

Source schema (run_tests.py --json):
    {game, scenario_file, scenarios: [{name, title, status, assertions: {details: [
        {check, command, cmd_idx, passed, response, detail?}
    ]}}]}

Target schema (IF Hub tests-template.html):
    {version, storyId, timestamp, transcripts: [{file, title, commands: [
        {lineNumber, input, output, passed, skipped, assertions: [
            {type, passed, value}
        ]}
    ], summary}], summary}
"""

from __future__ import annotations

import re
from collections import OrderedDict
from datetime import datetime, timezone


def _parse_check(check_text: str) -> dict:
    """Convert a regtest check string to an IF Hub assertion object.

    Regtest formats:
        literal text        → {type: "ok-contains", value: "literal text"}
        /regex/             → {type: "ok-matches", value: "regex"}
        !literal            → {type: "ok-not-contains", value: "literal"}
        !/regex/            → {type: "ok-not-matches", value: "regex"}
        {invert}literal     → {type: "ok-not-contains", value: "literal"}
        {invert}/regex/     → {type: "ok-not-matches", value: "regex"}
    """
    text = check_text.strip()

    # Strip {vital} prefix — it's an abort-on-fail modifier, not an assertion type
    if text.startswith("{vital}"):
        text = text[7:].strip()

    # Detect negation
    negated = False
    if text.startswith("!"):
        negated = True
        text = text[1:]
    elif text.startswith("{invert}"):
        negated = True
        text = text[8:]

    # Detect regex vs literal
    if text.startswith("/"):
        pattern = text[1:]
        if pattern.endswith("/"):
            pattern = pattern[:-1]
        base_type = "ok-matches"
        value = pattern
    else:
        base_type = "ok-contains"
        value = text

    if negated:
        assertion_type = base_type.replace("ok-", "ok-not-")
    else:
        assertion_type = base_type

    return {"type": assertion_type, "passed": True, "value": value}


def convert(regtest_json: dict, story_id: str, version: str = "1.0") -> dict:
    """Convert run_tests.py --json output to IF Hub test-results.json.

    Args:
        regtest_json: Parsed JSON from run_tests.py --json stdout.
        story_id: Game identifier (e.g., "zork1", "cloak-inform7").
        version: Version string for the output.

    Returns:
        Dict matching the IF Hub test-results.json schema.
    """
    scenario_file = regtest_json.get("scenario_file", "")
    # Use just the filename, not the full path
    if scenario_file:
        scenario_file = scenario_file.replace("\\", "/").rsplit("/", 1)[-1]

    transcripts = []
    total_passed = 0
    total_failed = 0
    total_skipped = 0

    for scenario in regtest_json.get("scenarios", []):
        if scenario.get("status") == "skip":
            total_skipped += 1
            continue

        # Group assertion details by cmd_idx to build per-command entries
        details = scenario.get("assertions", {}).get("details", [])
        cmds_by_idx: OrderedDict[int, dict] = OrderedDict()

        for d in details:
            idx = d.get("cmd_idx", 0)
            if idx not in cmds_by_idx:
                cmds_by_idx[idx] = {
                    "lineNumber": idx,
                    "input": d.get("command", ""),
                    "output": d.get("response", ""),
                    "passed": True,
                    "skipped": False,
                    "assertions": [],
                }

            entry = cmds_by_idx[idx]
            assertion = _parse_check(d.get("check", ""))
            assertion["passed"] = d.get("passed", True)
            entry["assertions"].append(assertion)

            # Command fails if any assertion fails
            if not d.get("passed", True):
                entry["passed"] = False

        commands = list(cmds_by_idx.values())
        cmd_passed = sum(1 for c in commands if c["passed"])
        cmd_failed = sum(1 for c in commands if not c["passed"])

        transcript = {
            "file": scenario_file,
            "title": scenario.get("title", scenario.get("name", "Unknown")),
            "commands": commands,
            "summary": {
                "passed": cmd_passed,
                "failed": cmd_failed,
                "skipped": 0,
            },
        }
        transcripts.append(transcript)
        total_passed += cmd_passed
        total_failed += cmd_failed

    return {
        "version": version,
        "storyId": story_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "transcripts": transcripts,
        "summary": {
            "totalPassed": total_passed,
            "totalFailed": total_failed,
            "totalSkipped": total_skipped,
        },
    }
