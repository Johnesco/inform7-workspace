#!/usr/bin/env python3
"""I7 scenario runner — assertions, diagnostics, and transcripts in one pass.

Runs .scenario files: each scenario is a named sequence of commands with
optional assertions, producing transcripts and diagnostics (score, deaths,
errors, win detection).

Usage:
    python run_tests.py --config tests/project.conf --list
    python run_tests.py --config tests/project.conf --all
    python run_tests.py --config tests/project.conf --all --json
    python run_tests.py --config tests/project.conf smoke
    python run_tests.py --config tests/project.conf --category combat
    python run_tests.py --config tests/project.conf --seed 42 --all
"""

import argparse
import json
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

_TOOLS_DIR = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# .scenario file parser
# ---------------------------------------------------------------------------

def parse_scenario_file(path):
    """Parse a .scenario file into scenarios dict and metadata.

    Returns (scenarios, metadata) where:
      scenarios: dict of name -> list of ("command"|"include"|"check", value)
      metadata:  dict of name -> {"title": str, "category": str, "primary": bool}

    Format:
      == name                          scenario header
      == name: Title                   with title
      == name: Title  [category]       with category
      == name: Title  [cat, primary]   with category + primary flag
      > command                        game input
      @ other-name                     include another scenario
      ? text                           literal assertion
      ? /regex/                        regex assertion
      ?! text                          negated assertion
      ?? text                          vital assertion (abort on failure)
      ??! text                         vital negated assertion
      # comment                        comment / walkthrough annotation
    """
    scenarios = {}
    metadata = {}
    current = None

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n").rstrip("\r")

            if not line or line.isspace():
                continue
            if line.startswith("#"):
                continue

            # Scenario header: == name  or  == name: Title  [tags]
            m = re.match(r"^==\s+(\S+)(?:\s*:\s*(.+?))?\s*(?:\[([^\]]*)\])?\s*$", line)
            if m:
                current = m.group(1)
                scenarios[current] = []
                title = (m.group(2) or "").strip()
                tags_str = m.group(3) or ""
                tags = [t.strip().lower() for t in tags_str.split(",") if t.strip()]
                primary = "primary" in tags
                category = next((t for t in tags if t != "primary"), "")
                # Title-case the category
                if category:
                    category = category.title()
                metadata[current] = {
                    "title": title or current,
                    "category": category,
                    "primary": primary,
                }
                continue

            if current is None:
                continue

            # Include: @ name
            m = re.match(r"^@\s+(\S+)", line)
            if m:
                scenarios[current].append(("include", m.group(1)))
                continue

            # Command: > text
            m = re.match(r"^>\s*(.*)", line)
            if m:
                scenarios[current].append(("command", m.group(1)))
                continue

            # Vital negated assertion: ??! text
            if line.startswith("??! ") or line.startswith("??!"):
                text = line[3:].strip()
                scenarios[current].append(("check", f"{{vital}}!{text}"))
                continue

            # Vital assertion: ?? text
            if line.startswith("?? ") or line.startswith("??"):
                text = line[2:].strip()
                scenarios[current].append(("check", f"{{vital}}{text}"))
                continue

            # Negated assertion: ?! text
            if line.startswith("?! ") or line.startswith("?!"):
                text = line[2:].strip()
                scenarios[current].append(("check", f"!{text}"))
                continue

            # Assertion: ? text
            if line.startswith("? ") or (line.startswith("?") and len(line) > 1):
                text = line[1:].strip()
                scenarios[current].append(("check", text))
                continue

    return scenarios, metadata


def resolve_commands(scenarios, name, _visiting=None):
    """Recursively resolve a scenario into a flat list of command strings."""
    if name not in scenarios:
        return []
    if _visiting is None:
        _visiting = set()
    if name in _visiting:
        return []
    _visiting = _visiting | {name}

    commands = []
    for kind, value in scenarios[name]:
        if kind == "include":
            commands.extend(resolve_commands(scenarios, value, _visiting))
        elif kind == "command":
            commands.append(value)
    return commands


def resolve_checks(scenarios, name, _visiting=None):
    """Recursively resolve into (command_index, check_text) pairs."""
    if name not in scenarios:
        return []
    if _visiting is None:
        _visiting = set()
    if name in _visiting:
        return []
    _visiting = _visiting | {name}

    result = []
    cmd_count = 0
    for kind, value in scenarios[name]:
        if kind == "include":
            included = resolve_checks(scenarios, value, _visiting)
            for idx, check in included:
                result.append((cmd_count + idx, check))
            cmd_count += len(resolve_commands(scenarios, value))
        elif kind == "command":
            cmd_count += 1
        elif kind == "check":
            result.append((cmd_count, value))
    return result


def find_scenario_file(tests_dir, cfg_scenario_file=""):
    """Find the .scenario file for a project. Falls back to .regtest."""
    # Always prefer .scenario files over legacy .regtest
    for p in tests_dir.glob("*.scenario"):
        return str(p)
    # Fall back to config-specified file or any .regtest
    if cfg_scenario_file and Path(cfg_scenario_file).is_file():
        return str(Path(cfg_scenario_file))
    for p in tests_dir.glob("*.regtest"):
        return str(p)
    return None


# ---------------------------------------------------------------------------
# Config loading — source bash project.conf and capture variables
# ---------------------------------------------------------------------------

class EngineConfig:
    def __init__(self, name="", path="", game_path="", seed_flag="", seeds_key=""):
        self.name = name
        self.path = path
        self.game_path = game_path
        self.seed_flag = seed_flag
        self.seeds_key = seeds_key


class ScoringConfig:
    def __init__(self):
        self.score_regex = ""
        self.fallback_regex = ""
        self.max_regex = ""
        self.pass_threshold = 0
        self.default_max = 0


class DiagnosticsConfig:
    def __init__(self):
        self.death_patterns = ""
        self.won_patterns = ""
        self.scoreless = False


class ProjectConfig:
    def __init__(self):
        self.project_name = ""
        self.project_dir = Path(".")
        self.regtest_file = ""
        self.primary = EngineConfig()
        self.scoring = ScoringConfig()
        self.diagnostics = DiagnosticsConfig()


def load_config(config_path):
    """Source a bash project.conf and capture the exported variables."""
    config_path = Path(config_path).resolve()
    project_dir = config_path.parent.parent  # tests/project.conf -> project/

    # Source the script in bash with PROJECT_DIR set, then print all vars
    script = (
        f'export PROJECT_DIR="{project_dir.as_posix()}"; '
        f'source "{config_path.as_posix()}"; '
        'echo ":::PROJECT_NAME=$PROJECT_NAME"; '
        'echo ":::PRIMARY_ENGINE_NAME=$PRIMARY_ENGINE_NAME"; '
        'echo ":::PRIMARY_ENGINE_PATH=$PRIMARY_ENGINE_PATH"; '
        'echo ":::PRIMARY_ENGINE_SEED_FLAG=$PRIMARY_ENGINE_SEED_FLAG"; '
        'echo ":::PRIMARY_GAME_PATH=$PRIMARY_GAME_PATH"; '
        'echo ":::PRIMARY_SEEDS_KEY=$PRIMARY_SEEDS_KEY"; '
        'echo ":::REGTEST_FILE=$REGTEST_FILE"; '
        'echo ":::SCORE_REGEX=$SCORE_REGEX"; '
        'echo ":::SCORE_FALLBACK_REGEX=$SCORE_FALLBACK_REGEX"; '
        'echo ":::MAX_SCORE_REGEX=$MAX_SCORE_REGEX"; '
        'echo ":::PASS_THRESHOLD=$PASS_THRESHOLD"; '
        'echo ":::DEFAULT_MAX_SCORE=$DEFAULT_MAX_SCORE"; '
        'echo ":::DEATH_PATTERNS=$DEATH_PATTERNS"; '
        'echo ":::WON_PATTERNS=$WON_PATTERNS"; '
    )

    result = subprocess.run(
        ["bash", "-c", script],
        capture_output=True, text=True, timeout=10,
    )

    vals = {}
    for line in result.stdout.splitlines():
        if line.startswith(":::"):
            key, _, value = line[3:].partition("=")
            vals[key] = value

    cfg = ProjectConfig()
    cfg.project_name = vals.get("PROJECT_NAME", "")
    cfg.project_dir = project_dir

    cfg.primary = EngineConfig(
        name=vals.get("PRIMARY_ENGINE_NAME") or "glulxe",
        path=vals.get("PRIMARY_ENGINE_PATH") or "",
        game_path=vals.get("PRIMARY_GAME_PATH") or "",
        seed_flag=vals.get("PRIMARY_ENGINE_SEED_FLAG") or "--rngseed",
        seeds_key=vals.get("PRIMARY_SEEDS_KEY") or "glulxe",
    )

    cfg.regtest_file = vals.get("REGTEST_FILE", "")

    # Fallback: if the engine path is empty or doesn't exist, look for it
    # relative to the tools directory (i7/tools/interpreters/).
    if not cfg.primary.path or not Path(cfg.primary.path).is_file():
        local_interp = _TOOLS_DIR / "interpreters" / (cfg.primary.name + ".exe")
        if local_interp.is_file():
            cfg.primary.path = str(local_interp)
        else:
            # Try without .exe (WSL/Linux)
            local_interp = _TOOLS_DIR / "interpreters" / cfg.primary.name
            if local_interp.is_file():
                cfg.primary.path = str(local_interp)

    # Default seed flag if not set
    if not cfg.primary.seed_flag:
        cfg.primary.seed_flag = "--rngseed"

    cfg.scoring = ScoringConfig()
    cfg.scoring.score_regex = vals.get("SCORE_REGEX", "")
    cfg.scoring.fallback_regex = vals.get("SCORE_FALLBACK_REGEX", "")
    cfg.scoring.max_regex = vals.get("MAX_SCORE_REGEX", "")
    try:
        cfg.scoring.pass_threshold = int(vals.get("PASS_THRESHOLD", "0"))
    except ValueError:
        cfg.scoring.pass_threshold = 0
    try:
        cfg.scoring.default_max = int(vals.get("DEFAULT_MAX_SCORE", "0"))
    except ValueError:
        cfg.scoring.default_max = 0

    cfg.diagnostics = DiagnosticsConfig()
    cfg.diagnostics.death_patterns = vals.get("DEATH_PATTERNS", "")
    cfg.diagnostics.won_patterns = vals.get("WON_PATTERNS", "")

    return cfg


def get_golden_seed(project_dir, seeds_key):
    """Read the global golden seed from seeds.conf."""
    seeds_path = Path(project_dir) / "tests" / "seeds.conf"
    try:
        for line in seeds_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(":")
            # 4-part: engine:seed:hash:date (global)
            if len(parts) >= 4 and parts[0] == seeds_key and not parts[1].isalpha():
                return parts[1]
            # 5-part: engine:scenario:seed:hash:date (per-scenario, skip for global)
    except OSError:
        pass
    return ""


def get_scenario_seed(project_dir, seeds_key, scenario_name, global_seed):
    """Get the best seed for a scenario: per-scenario > global."""
    seeds_path = Path(project_dir) / "tests" / "seeds.conf"
    try:
        for line in seeds_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(":")
            # 5-part: engine:scenario:seed:hash:date
            if (len(parts) >= 5 and parts[0] == seeds_key
                    and parts[1] == scenario_name):
                return parts[2]
    except OSError:
        pass
    return global_seed


# ---------------------------------------------------------------------------
# Interpreter I/O — dumb/cheap mode, command-by-command
# ---------------------------------------------------------------------------

TIMEOUT_SECS = 10


def launch_interpreter(engine_path, game_path, seed="", seed_flag="--rngseed"):
    """Launch glulxe in quiet dumb mode. Returns (process, read_func).

    read_func() reads output until the next '\\n>' prompt and returns the
    text (excluding the trailing prompt marker).
    """
    cmd = [engine_path, "-q"]
    if seed:
        cmd.extend([seed_flag, str(seed)])
    cmd.append(game_path)

    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    def read_until_prompt():
        """Read byte-by-byte until \\n> prompt. Windows-safe via threading."""
        output = bytearray()
        timeout_time = time.time() + TIMEOUT_SECS
        read_error = [None]

        def _reader():
            try:
                while True:
                    ch = proc.stdout.read(1)
                    if ch == b'':
                        break
                    if ch == b'\r':
                        continue
                    output.extend(ch)
                    if output[-2:] == b'\n>':
                        break
            except Exception as e:
                read_error[0] = e

        t = threading.Thread(target=_reader, daemon=True)
        t.start()
        remaining = timeout_time - time.time()
        t.join(timeout=max(remaining, 0.1))

        if read_error[0]:
            raise read_error[0]
        if t.is_alive():
            raise TimeoutError(f"Timed out after {TIMEOUT_SECS}s awaiting output")

        text = output.decode("utf-8", errors="replace")
        # Strip trailing prompt marker
        if text.endswith("\n>"):
            text = text[:-2]
        return text

    return proc, read_until_prompt


def send_command(proc, command):
    """Send a line of input to the interpreter."""
    proc.stdin.write((command + "\n").encode())
    proc.stdin.flush()


# ---------------------------------------------------------------------------
# Assertion checking
# ---------------------------------------------------------------------------

def evaluate_check(check_text, response_lines):
    """Evaluate a single assertion against response text.

    Returns (passed: bool, detail: str).
    """
    text = check_text
    response = "\n".join(response_lines)

    # Vital modifier — strip it, caller handles abort logic
    vital = False
    if text.startswith("{vital}"):
        text = text[7:].strip()
        vital = True
    elif text.strip() == "{vital}":
        # Bare {vital} on its own line — it's a modifier for the next check,
        # not a check itself. Skip it.
        return True, "vital-modifier"

    # Status window check — we don't have status window in dumb mode, skip
    if text.startswith("{status}"):
        return True, "status-skipped"

    # Negated check: starts with !
    negated = False
    if text.startswith("!"):
        negated = True
        text = text[1:]
    elif text.startswith("{invert}"):
        negated = True
        text = text[8:]

    # Regex check: starts and optionally ends with /
    if text.startswith("/"):
        # Strip leading / and optional trailing /
        pattern = text[1:]
        if pattern.endswith("/"):
            pattern = pattern[:-1]
        try:
            found = bool(re.search(pattern, response, re.IGNORECASE))
        except re.error:
            return False, f"bad regex: {pattern}"
    else:
        # Literal check
        found = text in response

    if negated:
        passed = not found
        if not passed:
            return False, f"should NOT match: {check_text}"
    else:
        passed = found
        if not passed:
            return False, f"not found: {check_text}"

    return True, ""


# ---------------------------------------------------------------------------
# Scenario runner
# ---------------------------------------------------------------------------

def run_scenario(name, tests, cfg, seed, scenarios_dir):
    """Run a single scenario: commands + assertions + transcript + diagnostics."""
    commands = resolve_commands(tests, name)
    checks = resolve_checks(tests, name)

    # Group checks by command index (1-based: check at index N applies after
    # command N; index 0 means before any command / preamble checks)
    checks_by_cmd = {}
    for cmd_idx, check_text in checks:
        checks_by_cmd.setdefault(cmd_idx, []).append(check_text)

    # Launch interpreter
    try:
        proc, read_output = launch_interpreter(
            cfg.primary.path, cfg.primary.game_path,
            seed=seed, seed_flag=cfg.primary.seed_flag,
        )
    except (OSError, FileNotFoundError) as e:
        return {
            "name": name, "status": "fail",
            "detail": f"interpreter launch failed: {e}",
            "commands": len(commands), "transcript_lines": 0,
            "assertions": {"total": 0, "passed": 0, "failed": 0, "failures": []},
        }

    transcript_parts = []
    assertion_results = {"total": 0, "passed": 0, "failed": 0, "failures": [],
                         "details": []}
    aborted = False

    try:
        # Read preamble (banner + initial room)
        preamble = read_output()
        transcript_parts.append(preamble)

        # Check preamble assertions (command index 0)
        for check_text in checks_by_cmd.get(0, []):
            _eval_and_record(check_text, preamble.split("\n"),
                             assertion_results, 0, command="(preamble)")

        # Send commands one at a time
        for i, command in enumerate(commands, 1):
            send_command(proc, command)
            response = read_output()

            transcript_parts.append(f"\n> {command}")
            transcript_parts.append(response)

            # Evaluate assertions for this command position
            is_vital_section = False
            for check_text in checks_by_cmd.get(i, []):
                if check_text.strip() == "{vital}":
                    is_vital_section = True
                    continue
                passed, detail = _eval_and_record(
                    check_text, response.split("\n"), assertion_results, i,
                    command=command)
                if not passed and (is_vital_section
                                   or check_text.startswith("{vital}")):
                    aborted = True
                    break
            if aborted:
                break

        # Send score command if not already at end
        if not aborted and not any(c.strip() == "score" for c in commands[-5:]):
            send_command(proc, "score")
            score_response = read_output()
            transcript_parts.append(f"\n> score")
            transcript_parts.append(score_response)

    except (TimeoutError, OSError) as e:
        transcript_parts.append(f"\n[ERROR: {e}]")
    finally:
        # Close stdin to signal EOF — interpreter exits cleanly
        try:
            proc.stdin.close()
        except OSError:
            pass
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()

    # Build transcript
    transcript = "\n".join(transcript_parts)

    # Save files
    scenarios_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = scenarios_dir / f"{name}.transcript.txt"
    commands_path = scenarios_dir / f"{name}.commands.txt"
    # The banner carries the compile date as the serial number; normalise it so
    # tracked transcripts do not change on every rebuild (Johnesco/zork1#180).
    transcript = re.sub(r"(Serial number )\d{6}", r"\1XXXXXX", transcript)
    transcript_path.write_text(transcript, encoding="utf-8")
    commands_path.write_text("\n".join(commands) + "\n", encoding="utf-8")

    # Aggregate diagnostics
    diag = diagnose_transcript(transcript, cfg)

    # Determine status — ignore returncode from terminate/kill
    if aborted:
        status = "fail"
    elif assertion_results["failed"] > 0:
        status = "fail"
    else:
        status = "pass"

    return {
        "name": name,
        "status": status,
        "seed": seed,
        "commands": len(commands),
        "transcript_lines": len(transcript.splitlines()),
        "exit_code": proc.returncode,
        "transcript_file": str(transcript_path),
        "commands_file": str(commands_path),
        "assertions": assertion_results,
        **diag,
    }


def _eval_and_record(check_text, response_lines, results, cmd_idx, command=""):
    """Evaluate a check and record the result. Returns (passed, detail)."""
    passed, detail = evaluate_check(check_text, response_lines)
    if detail in ("vital-modifier", "status-skipped"):
        return True, detail
    results["total"] += 1

    # Capture a snippet of the response (trim to keep JSON reasonable)
    response_text = "\n".join(response_lines).strip()
    if len(response_text) > 300:
        response_text = response_text[:300] + "..."

    entry = {
        "check": check_text,
        "command": command,
        "cmd_idx": cmd_idx,
        "passed": passed,
        "response": response_text,
    }
    if passed:
        results["passed"] += 1
    else:
        results["failed"] += 1
        entry["detail"] = detail
        results["failures"].append(f"cmd {cmd_idx}: {detail}")
    results["details"].append(entry)
    return passed, detail


# ---------------------------------------------------------------------------
# Aggregate diagnostics — analyze full transcript
# ---------------------------------------------------------------------------

def _count_matches(pattern, text, ignorecase=False):
    """Count regex matches in text."""
    if not pattern:
        return 0
    flags = re.IGNORECASE if ignorecase else 0
    try:
        return len(re.findall(pattern, text, flags))
    except re.error:
        return 0


def _first_match(pattern, text, ignorecase=False):
    """Find first regex match, returning the matched group or empty string."""
    if not pattern:
        return ""
    flags = re.IGNORECASE if ignorecase else 0
    try:
        m = re.search(pattern, text, flags)
        return m.group(0) if m else ""
    except re.error:
        return ""


def diagnose_transcript(transcript, cfg):
    """Run full diagnostics on a transcript."""
    # Score extraction — handle PCRE \K by converting to lookbehind or group
    score_regex = _pcre_to_python(cfg.scoring.score_regex)
    fallback_regex = _pcre_to_python(cfg.scoring.fallback_regex)
    max_regex = _pcre_to_python(cfg.scoring.max_regex)

    final_score = _first_match(score_regex, transcript, ignorecase=True)
    if not final_score:
        final_score = _first_match(fallback_regex, transcript)

    max_score = _first_match(max_regex, transcript) or str(cfg.scoring.default_max)

    # Counts
    deaths = _count_matches(cfg.diagnostics.death_patterns, transcript, ignorecase=True)
    cant_see = _count_matches(r"can't see any such thing", transcript)
    cant_go = _count_matches(r"can't go that way", transcript)
    parse_errors = _count_matches(
        r"that.s not something you can|I only understood", transcript, ignorecase=True)
    score_ups = _count_matches(r"score has just gone up", transcript)
    score_downs = _count_matches(r"score has just gone down", transcript)

    # Win detection
    won_text = bool(re.findall(
        cfg.diagnostics.won_patterns, transcript, re.IGNORECASE
    )) if cfg.diagnostics.won_patterns else False

    if cfg.diagnostics.scoreless:
        win = won_text
    else:
        try:
            win = int(final_score) >= cfg.scoring.pass_threshold
        except (ValueError, TypeError):
            win = False

    score_str = f"{final_score}/{max_score}" if final_score else ""

    return {
        "score": score_str,
        "win": win,
        "won_text": won_text,
        "deaths": deaths,
        "errors": cant_see + cant_go + parse_errors,
        "cant_see": cant_see,
        "cant_go": cant_go,
        "parse_errors": parse_errors,
        "score_ups": score_ups,
        "score_downs": score_downs,
    }


def _pcre_to_python(pattern):
    r"""Convert simple PCRE patterns to Python regex.

    Handles \K (lookbehind reset) by converting 'prefix\Kpattern' to a
    lookbehind: '(?<=prefix)pattern'. Only handles simple cases.
    """
    if not pattern or r"\K" not in pattern:
        return pattern
    parts = pattern.split(r"\K", 1)
    prefix = parts[0]
    suffix = parts[1] if len(parts) > 1 else ""
    return f"(?<={prefix}){suffix}"


# ---------------------------------------------------------------------------
# Scenario index loading
# ---------------------------------------------------------------------------

def load_scenario_index(tests_dir):
    """Load scenarios/index.json if it exists."""
    index_path = tests_dir / "scenarios" / "index.json"
    if index_path.is_file():
        data = json.loads(index_path.read_text(encoding="utf-8"))
        return data.get("scenarios", [])
    return None


def build_index_from_regtest(tests):
    """Build a minimal scenario index from regtest test names."""
    return [{"name": name, "title": name, "category": "Uncategorized"}
            for name in tests]


# ---------------------------------------------------------------------------
# CLI + output
# ---------------------------------------------------------------------------

def format_result_line(r):
    """Format a single scenario result for terminal display."""
    if r.get("win"):
        status = "WIN"
    elif r.get("status") == "pass":
        status = "PASS"
    else:
        status = "FAIL"

    parts = [f"{status:4s}"]

    a = r.get("assertions", {})
    if a.get("total", 0) > 0:
        parts.append(f"assert={a['passed']}/{a['total']}")

    if r.get("score"):
        parts.append(f"score={r['score']}")
    if r.get("deaths"):
        parts.append(f"deaths={r['deaths']}")
    if r.get("errors"):
        parts.append(f"errors={r['errors']}")
    parts.append(f"({r.get('transcript_lines', 0)} lines)")

    return " ".join(parts)


def main():
    parser = argparse.ArgumentParser(
        description="Unified I7 test runner — assertions, diagnostics, transcripts."
    )
    parser.add_argument("--config", required=True, help="Path to project.conf")
    parser.add_argument("--list", action="store_true", dest="list_scenarios",
                        help="List available scenarios")
    parser.add_argument("--all", action="store_true", help="Run all scenarios")
    parser.add_argument("--category", help="Run only scenarios in this category")
    parser.add_argument("--seed", help="Override seed for all scenarios")
    parser.add_argument("--json", action="store_true", help="Output structured JSON")
    parser.add_argument("name", nargs="?", help="Scenario name to run")

    args = parser.parse_args()

    cfg = load_config(args.config)
    tests_dir = cfg.project_dir / "tests"
    scenarios_dir = tests_dir / "scenarios"

    # Find scenario file (.scenario or .regtest fallback)
    scenario_path = find_scenario_file(tests_dir, cfg.regtest_file)
    if not scenario_path:
        print("Error: no .scenario file found", file=sys.stderr)
        sys.exit(1)

    # Parse scenario file — metadata comes from file headers
    tests, file_metadata = parse_scenario_file(scenario_path)

    # Build index: prefer inline metadata from .scenario file,
    # fall back to scenarios/index.json for legacy .regtest files
    if file_metadata:
        index = [{"name": name, **meta} for name, meta in file_metadata.items()]
    else:
        index = load_scenario_index(tests_dir)
        if index is None:
            index = [{"name": n, "title": n, "category": "Uncategorized"}
                     for n in tests]

    index_lookup = {s["name"]: s for s in index}

    # Filter by category
    if args.category:
        cat_lower = args.category.lower()
        index = [s for s in index if cat_lower in s.get("category", "").lower()]

    # Global seed
    global_seed = (args.seed
                   or get_golden_seed(cfg.project_dir, cfg.primary.seeds_key)
                   or "")

    # List mode
    if args.list_scenarios:
        categories = {}
        for s in index:
            cat = s.get("category", "Uncategorized")
            categories.setdefault(cat, []).append(s)
        for cat, scenarios in categories.items():
            print(f"\n  {cat}:")
            for s in scenarios:
                cmds = resolve_commands(tests, s["name"]) if s["name"] in tests else []
                checks = resolve_checks(tests, s["name"]) if s["name"] in tests else []
                primary = " [PRIMARY]" if s.get("primary") else ""
                print(f"    {s['name']:30s} {s.get('title', ''):<40s} "
                      f"({len(cmds)} cmds, {len(checks)} checks){primary}")
        print(f"\n  Total: {len(index)} scenarios")
        return

    # Determine which to run
    if args.all:
        to_run = [s["name"] for s in index if s["name"] in tests]
    elif args.name:
        to_run = [args.name]
    else:
        parser.error("Specify a scenario name, --all, or --list")

    # Run
    results = []
    win_scenarios = []
    total_assertions = {"total": 0, "passed": 0, "failed": 0}
    start_time = time.time()

    for name in to_run:
        if name not in tests:
            print(f"  SKIP {name} (not in regtest file)", file=sys.stderr)
            results.append({"name": name, "status": "skip",
                            "detail": "not in regtest"})
            continue

        seed = get_scenario_seed(
            cfg.project_dir, cfg.primary.seeds_key, name, global_seed)

        if not args.json:
            cmds = resolve_commands(tests, name)
            print(f"  {name:30s} ({len(cmds):3d} cmds) ... ",
                  end="", flush=True)

        r = run_scenario(name, tests, cfg, seed, scenarios_dir)

        # Tag with index metadata
        meta = index_lookup.get(name, {})
        r["category"] = meta.get("category", "Uncategorized")
        r["title"] = meta.get("title", name)
        r["primary"] = meta.get("primary", False)

        results.append(r)

        if r.get("win"):
            win_scenarios.append(name)

        # Accumulate assertion totals
        a = r.get("assertions", {})
        total_assertions["total"] += a.get("total", 0)
        total_assertions["passed"] += a.get("passed", 0)
        total_assertions["failed"] += a.get("failed", 0)

        if not args.json:
            print(format_result_line(r))

    elapsed = time.time() - start_time

    # Summary
    total = len(results)
    passed = sum(1 for r in results if r.get("status") == "pass")
    failed = sum(1 for r in results if r.get("status") == "fail")
    skipped = sum(1 for r in results if r.get("status") == "skip")
    wins = len(win_scenarios)

    if args.json:
        output = {
            "game": cfg.project_name,
            "scenario_file": scenario_path,
            "seed": global_seed,
            "duration_seconds": round(elapsed, 1),
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "wins": wins,
            "win_scenarios": win_scenarios,
            "primary": next((n for n in win_scenarios
                             if index_lookup.get(n, {}).get("primary")), None),
            "assertions": total_assertions,
            "scenarios": results,
        }
        json.dump(output, sys.stdout, indent=2)
        print()
    else:
        print(f"\n  Done: {passed} passed, {failed} failed, {skipped} skipped "
              f"({elapsed:.1f}s)")
        print(f"  Assertions: {total_assertions['passed']}/{total_assertions['total']}")
        if total_assertions["failed"] > 0:
            print(f"  Assertion failures: {total_assertions['failed']}")
        if win_scenarios:
            primary = next((n for n in win_scenarios
                            if index_lookup.get(n, {}).get("primary")), None)
            print(f"  Win scenarios ({wins}): {', '.join(win_scenarios)}")
            if primary:
                print(f"  Primary walkthrough: {primary}")

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
