#!/usr/bin/env python3
"""Run regtest scenarios with full diagnostics.

Every scenario gets the same treatment: run through the interpreter,
save transcript, extract score/deaths/errors, detect win condition.
Scenarios that win are walkthrough candidates — the one marked
"primary" in the index is the canonical walkthrough.

Usage:
    python run_scenarios.py --config tests/project.conf <name>
    python run_scenarios.py --config tests/project.conf --all
    python run_scenarios.py --config tests/project.conf --category combat
    python run_scenarios.py --config tests/project.conf --list
    python run_scenarios.py --config tests/project.conf --all --json
"""

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

# Make tools/lib importable.
_TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_TOOLS_DIR))
from lib import config, process, regex

# Load extract_commands from same directory (avoid collision with ifhub's extract_commands)
_ec_spec = importlib.util.spec_from_file_location(
    "i7_extract_commands", str(_TOOLS_DIR / "extract_commands.py"))
_ec_mod = importlib.util.module_from_spec(_ec_spec)
_ec_spec.loader.exec_module(_ec_mod)
parse_regtest = _ec_mod.parse_regtest
resolve_commands = _ec_mod.resolve_commands


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


def get_scenario_seed(cfg, scenario_name, global_seed):
    """Get the best seed for a scenario: per-scenario > global > None."""
    seeds_path = cfg.project_dir / "tests" / "seeds.conf"
    engine_key = cfg.primary.seeds_key
    try:
        for line in seeds_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(":")
            if len(parts) >= 5 and parts[0] == engine_key and parts[1] == scenario_name:
                return parts[2]
    except OSError:
        pass
    return global_seed


def diagnose_transcript(transcript, cfg):
    """Run full diagnostics on a transcript. Returns a diagnostics dict."""
    def count(pattern):
        return regex.count_matches(pattern, transcript, ignorecase=True)
    def count_cs(pattern):
        return regex.count_matches(pattern, transcript, ignorecase=False)

    # Score extraction
    final_score = regex.pcre_search(cfg.scoring.score_regex, transcript, ignorecase=True) or ""
    if not final_score:
        final_score = regex.pcre_search(cfg.scoring.fallback_regex, transcript) or ""

    max_score = regex.pcre_search(cfg.scoring.max_regex, transcript) or str(cfg.scoring.default_max)

    # Counts
    deaths = count(cfg.diagnostics.death_patterns)
    cant_see = count_cs("can't see any such thing")
    cant_go = count_cs("can't go that way")
    parse_errors = count("that.s not something you can|I only understood")
    score_ups = count_cs("score has just gone up")
    score_downs = count_cs("score has just gone down")

    # Win detection
    won = bool(regex.pcre_findall(cfg.diagnostics.won_patterns, transcript, ignorecase=True))

    if cfg.diagnostics.scoreless:
        win = won
    else:
        try:
            win = int(final_score) >= cfg.scoring.pass_threshold
        except (ValueError, TypeError):
            win = False

    score_str = ""
    if final_score:
        score_str = f"{final_score}/{max_score}"

    return {
        "score": score_str,
        "win": win,
        "won_text": won,
        "deaths": deaths,
        "errors": cant_see + cant_go + parse_errors,
        "cant_see": cant_see,
        "cant_go": cant_go,
        "parse_errors": parse_errors,
        "score_ups": score_ups,
        "score_downs": score_downs,
    }


def interleave_transcript(raw_transcript, commands):
    """Interleave commands into a raw transcript.

    glulxe -q with piped stdin produces output with bare '>' prompts
    but no command echo. This splits on prompts and inserts the commands.
    Also appends the implicit quit/yes commands.
    """
    # Split transcript on lines that are just ">" (the prompt)
    # The raw output looks like: preamble\n\n>response1\n\n>response2...
    # where each > is a bare prompt with the response on the same or next line.
    parts = raw_transcript.split("\n>")
    if len(parts) <= 1:
        # No prompts found — return as-is with commands prepended
        return raw_transcript

    # All commands including the implicit score/quit/yes we appended
    all_cmds = list(commands)
    if not any(c.strip() == "score" for c in all_cmds[-5:]):
        all_cmds.append("score")
    all_cmds.extend(["quit", "yes"])

    lines = []
    # First part is the preamble (banner + initial room)
    lines.append(parts[0])

    for i, part in enumerate(parts[1:]):
        cmd = all_cmds[i] if i < len(all_cmds) else "?"
        lines.append(f"\n> {cmd}")
        # The part may start with the response on the same line as the >
        if part:
            lines.append(part)

    return "\n".join(lines)


def run_scenario(name, commands, cfg, seed, scenarios_dir):
    """Run a scenario through the interpreter, save transcript + commands."""
    scenarios_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = scenarios_dir / f"{name}.transcript.txt"
    commands_path = scenarios_dir / f"{name}.commands.txt"

    # Append score command so we can extract final score
    run_commands = list(commands)
    if not any(c.strip() == "score" for c in run_commands[-5:]):
        run_commands.append("score")

    input_text = "\n".join(run_commands) + "\nquit\nyes\n"

    result = process.run_interpreter(
        engine=cfg.primary.path,
        game=cfg.primary.game_path,
        input_text=input_text,
        seed=seed,
        seed_flag=cfg.primary.seed_flag,
        quiet=True,
    )

    raw_transcript = result.stdout or ""

    # Save interleaved transcript (commands + responses)
    transcript = interleave_transcript(raw_transcript, commands)
    transcript_path.write_text(transcript, encoding="utf-8")

    # Save plain commands list
    commands_path.write_text("\n".join(commands) + "\n", encoding="utf-8")

    diag = diagnose_transcript(raw_transcript, cfg)

    return {
        "name": name,
        "commands": len(commands),
        "transcript_lines": len(transcript.splitlines()),
        "exit_code": result.returncode,
        "output_file": str(transcript_path),
        "commands_file": str(commands_path),
        "seed": seed,
        "status": "pass" if result.returncode == 0 else "fail",
        **diag,
    }


def format_result_line(r):
    """Format a single scenario result for terminal display."""
    status = "WIN" if r.get("win") else "PASS" if r.get("status") == "pass" else "FAIL"
    parts = [status]
    if r.get("score"):
        parts.append(f"score={r['score']}")
    if r.get("deaths"):
        parts.append(f"deaths={r['deaths']}")
    if r.get("errors"):
        parts.append(f"errors={r['errors']}")
    parts.append(f"({r['transcript_lines']} lines)")
    return " ".join(parts)


def main():
    parser = argparse.ArgumentParser(
        description="Run regtest scenarios with full diagnostics."
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

    cfg = config.load_config(args.config)
    tests_dir = cfg.project_dir / "tests"
    scenarios_dir = tests_dir / "scenarios"

    # Find regtest file
    regtest_path = None
    if cfg.regtest_file and Path(cfg.regtest_file).is_file():
        regtest_path = cfg.regtest_file
    else:
        for p in tests_dir.glob("*.regtest"):
            regtest_path = str(p)
            break
    if not regtest_path:
        print("Error: no regtest file found", file=sys.stderr)
        sys.exit(1)

    # Parse regtest and load scenario index
    tests = parse_regtest(regtest_path)
    index = load_scenario_index(tests_dir)
    if index is None:
        index = build_index_from_regtest(tests)

    # Build lookup for index metadata
    index_lookup = {s["name"]: s for s in index}

    # Filter by category
    if args.category:
        cat_lower = args.category.lower()
        index = [s for s in index if cat_lower in s.get("category", "").lower()]

    # Global seed
    global_seed = args.seed or config.get_golden_seed(cfg.project_dir, cfg.primary.seeds_key) or ""

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
                primary = " [PRIMARY]" if s.get("primary") else ""
                print(f"    {s['name']:30s} {s.get('title', ''):<40s} ({len(cmds)} cmds){primary}")
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
    start_time = time.time()

    for name in to_run:
        if name not in tests:
            print(f"  SKIP {name} (not in regtest file)", file=sys.stderr)
            results.append({"name": name, "status": "skip", "detail": "not in regtest"})
            continue

        commands = resolve_commands(tests, name)
        seed = get_scenario_seed(cfg, name, global_seed)

        if not args.json:
            print(f"  {name:30s} ({len(commands):3d} cmds) ... ", end="", flush=True)

        r = run_scenario(name, commands, cfg, seed, scenarios_dir)

        # Tag with index metadata
        meta = index_lookup.get(name, {})
        r["category"] = meta.get("category", "Uncategorized")
        r["title"] = meta.get("title", name)
        r["primary"] = meta.get("primary", False)

        results.append(r)

        if r.get("win"):
            win_scenarios.append(name)

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
            "regtest_file": regtest_path,
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
            "scenarios": results,
        }
        json.dump(output, sys.stdout, indent=2)
        print()
    else:
        print(f"\n  Done: {passed} passed, {failed} failed, {skipped} skipped "
              f"({elapsed:.1f}s)")
        if win_scenarios:
            primary = next((n for n in win_scenarios
                            if index_lookup.get(n, {}).get("primary")), None)
            print(f"  Win scenarios ({wins}): {', '.join(win_scenarios)}")
            if primary:
                print(f"  Primary walkthrough: {primary}")

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
