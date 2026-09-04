#!/usr/bin/env python3
"""Per-scenario RNG seed discovery.

Extends find_seeds.py to work at scenario granularity. For each scenario,
sweeps seeds 1..N, runs the scenario commands through the interpreter,
and reports which seeds produce successful runs.

Usage:
    python find_scenario_seeds.py --config tests/project.conf --scenario troll
    python find_scenario_seeds.py --config tests/project.conf --scenario troll --max 500
    python find_scenario_seeds.py --config tests/project.conf --all-rng
"""

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime
from pathlib import Path

_TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_TOOLS_DIR))
from lib import config, process

import importlib.util
_ec_spec = importlib.util.spec_from_file_location(
    "i7_extract_commands", str(_TOOLS_DIR / "extract_commands.py"))
_ec_mod = importlib.util.module_from_spec(_ec_spec)
_ec_spec.loader.exec_module(_ec_mod)
parse_regtest = _ec_mod.parse_regtest
resolve_commands = _ec_mod.resolve_commands


def compute_sha256_prefix(path, length=8):
    """Compute first N chars of SHA-256 hash of a file."""
    try:
        h = hashlib.sha256(Path(path).read_bytes())
        return h.hexdigest()[:length]
    except OSError:
        return "unknown"


def run_scenario_with_seed(commands, cfg, seed):
    """Run scenario commands with a specific seed, return transcript."""
    # Append score command so we can extract final score for win detection
    run_commands = list(commands)
    if not any(c.strip() == "score" for c in run_commands[-5:]):
        run_commands.append("score")
    input_text = "\n".join(run_commands) + "\nquit\nyes\n"
    result = process.run_interpreter(
        engine=cfg.primary.path,
        game=cfg.primary.game_path,
        input_text=input_text,
        seed=str(seed),
        seed_flag=cfg.primary.seed_flag,
        quiet=True,
    )
    return result.stdout or "", result.returncode


def check_scenario_success(transcript, cfg):
    """Check if a scenario transcript indicates success.

    A scenario succeeds if:
    - No death patterns found
    - No "can't see" / "can't go" errors dominating
    - Won patterns found (if scoreless game)
    - Score meets threshold (if scored game)
    """
    from lib import regex

    # Check for deaths
    death_count = regex.count_matches(cfg.diagnostics.death_patterns, transcript, ignorecase=True)
    if death_count > 0:
        return False, f"{death_count} deaths"

    # Check for win (scoreless games)
    if cfg.diagnostics.scoreless:
        won = regex.count_matches(cfg.diagnostics.won_patterns, transcript, ignorecase=True)
        return won > 0, "won" if won > 0 else "no win detected"

    # Check score (scored games)
    score_match = regex.pcre_search(cfg.scoring.score_regex, transcript, ignorecase=True)
    if score_match:
        try:
            score = int(score_match)
            passed = score >= cfg.scoring.pass_threshold
            return passed, f"score={score}/{cfg.scoring.pass_threshold}"
        except ValueError:
            pass

    # No death, no score info — assume pass (scenario might not have scoring)
    return True, "no errors"


def sweep_scenario(scenario_name, commands, cfg, max_seeds, stop_on_first):
    """Sweep seeds for a single scenario."""
    results = []
    passing = []

    for seed in range(1, max_seeds + 1):
        transcript, exit_code = run_scenario_with_seed(commands, cfg, seed)
        success, detail = check_scenario_success(transcript, cfg)
        results.append({"seed": seed, "success": success, "detail": detail})

        if success:
            passing.append(seed)
            if stop_on_first:
                break

        # Progress indicator
        if seed % 50 == 0:
            print(f"    ... seed {seed}/{max_seeds}, {len(passing)} passing so far",
                  file=sys.stderr)

    return results, passing


def main():
    parser = argparse.ArgumentParser(
        description="Per-scenario RNG seed discovery."
    )
    parser.add_argument("--config", required=True, help="Path to project.conf")
    parser.add_argument("--scenario", help="Specific scenario to sweep")
    parser.add_argument("--all-rng", action="store_true",
                        help="Sweep seeds for all seed-sensitive scenarios (from suite.json)")
    parser.add_argument("--max", type=int, default=200,
                        help="Maximum seed to test (default: 200)")
    parser.add_argument("--no-stop", action="store_true",
                        help="Don't stop on first passing seed")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")

    args = parser.parse_args()

    cfg = config.load_config(args.config)
    tests_dir = cfg.project_dir / "tests"

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

    tests = parse_regtest(regtest_path)
    binary_hash = compute_sha256_prefix(cfg.primary.game_path)
    date_str = datetime.now().strftime("%Y-%m-%d")

    scenarios_to_sweep = []

    if args.scenario:
        scenarios_to_sweep = [args.scenario]
    elif args.all_rng:
        # Read suite.json for seed-sensitive scenarios
        suite = None
        suite_path = tests_dir / "suite.json"
        if suite_path.is_file():
            suite = json.loads(suite_path.read_text(encoding="utf-8"))
        if suite:
            categories = suite.get("layers", {}).get("scenarios", {}).get("categories", {})
            index_path = tests_dir / "scenarios" / "index.json"
            if index_path.is_file():
                index = json.loads(index_path.read_text(encoding="utf-8"))
                for s in index.get("scenarios", []):
                    cat_key = s.get("category", "").lower().replace(" ", "-")
                    cat_config = categories.get(cat_key, {})
                    if cat_config.get("seed_sensitive"):
                        scenarios_to_sweep.append(s["name"])
        if not scenarios_to_sweep:
            print("No seed-sensitive scenarios found in suite.json", file=sys.stderr)
            sys.exit(1)
    else:
        parser.error("--scenario or --all-rng required")

    all_results = {}
    engine_key = cfg.primary.seeds_key

    for name in scenarios_to_sweep:
        if name not in tests:
            print(f"  SKIP {name} (not in regtest file)")
            continue

        commands = resolve_commands(tests, name)
        print(f"\n  Sweeping seeds for '{name}' ({len(commands)} commands, max={args.max})...")

        results, passing = sweep_scenario(
            name, commands, cfg, args.max, stop_on_first=not args.no_stop
        )

        all_results[name] = {
            "total_tested": len(results),
            "passing_seeds": passing,
            "pass_rate": f"{len(passing)}/{len(results)}",
        }

        if passing:
            print(f"  Passing seeds: {passing}")
            print(f"  seeds.conf line:")
            for s in passing:
                print(f"    {engine_key}:{name}:{s}:{binary_hash}:{date_str}")
        else:
            print(f"  No passing seeds found in 1..{args.max}")

    if args.json:
        json.dump(all_results, sys.stdout, indent=2)
        print()


if __name__ == "__main__":
    main()
