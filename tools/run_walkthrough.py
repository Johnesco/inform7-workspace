#!/usr/bin/env python3
"""Generic walkthrough test runner for Inform 7 projects.

Runs a walkthrough through an interpreter with optional RNG seeding
and produces diagnostic output.

Usage:
    python tools/testing/run_walkthrough.py --config PATH
    python tools/testing/run_walkthrough.py --config PATH --alt
    python tools/testing/run_walkthrough.py --config PATH --seed 42
    python tools/testing/run_walkthrough.py --config PATH --no-seed
    python tools/testing/run_walkthrough.py --config PATH --diff
    python tools/testing/run_walkthrough.py --config PATH --quiet
    python tools/testing/run_walkthrough.py --config PATH --no-save
    python tools/testing/run_walkthrough.py --config PATH --copy-output DIR
"""

import argparse
import hashlib
import importlib.util
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import config, process, regex


def compute_sha256_prefix(path: Path, length: int = 8) -> str:
    """Compute first N chars of SHA-256 hash of a file."""
    try:
        h = hashlib.sha256(path.read_bytes())
        return h.hexdigest()[:length]
    except OSError:
        return "unknown"


def load_diagnostics_extra(project_dir: Path):
    """Try to load a project_hooks.py with diagnostics_extra(), or fall back to bash-style."""
    hooks_path = project_dir / "tests" / "project_hooks.py"
    if hooks_path.exists():
        spec = importlib.util.spec_from_file_location("project_hooks", hooks_path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "diagnostics_extra"):
                return mod.diagnostics_extra
    return None


def main():
    parser = argparse.ArgumentParser(description="Run walkthrough test.")
    parser.add_argument("--config", required=True, help="Path to project.conf")
    parser.add_argument("--alt", action="store_true", help="Use alternate engine")
    parser.add_argument("--seed", help="RNG seed override")
    parser.add_argument("--no-seed", action="store_true", help="True randomness")
    parser.add_argument("--diff", action="store_true", help="Diff vs saved baseline")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress diagnostics")
    parser.add_argument("--no-save", action="store_true", help="Don't overwrite saved output")
    parser.add_argument("--copy-output", help="Copy output to this directory")
    args = parser.parse_args()

    conf_path = Path(args.config)
    if not conf_path.exists():
        print(f"ERROR: Config file not found: {conf_path}", file=sys.stderr)
        sys.exit(2)

    cfg = config.load_config(conf_path)

    # Select engine
    if args.alt:
        if not cfg.alt.name:
            print("ERROR: Alternate engine not configured in project.conf", file=sys.stderr)
            sys.exit(2)
        engine_name = cfg.alt.name
        engine_path = cfg.alt.path
        seed_flag = cfg.alt.seed_flag
        game_path = cfg.alt.game_path
        walkthrough = cfg.alt.walkthrough
        output_file = cfg.alt.output_file
        seeds_key = cfg.alt.seeds_key
    else:
        engine_name = cfg.primary.name
        engine_path = cfg.primary.path
        seed_flag = cfg.primary.seed_flag
        game_path = cfg.primary.game_path
        walkthrough = cfg.primary.walkthrough
        output_file = cfg.primary.output_file
        seeds_key = cfg.primary.seeds_key

    # Verify files
    if not Path(engine_path).exists():
        print(f"ERROR: Engine not found: {engine_path}", file=sys.stderr)
        sys.exit(2)
    game_p = Path(game_path)
    if not game_p.exists():
        print(f"ERROR: Game file not found: {game_path}", file=sys.stderr)
        sys.exit(2)
    walk_p = Path(walkthrough)
    if not walk_p.exists():
        print(f"ERROR: Walkthrough not found: {walkthrough}", file=sys.stderr)
        sys.exit(2)

    # Determine seed
    seed = args.seed
    if args.no_seed:
        seed = None
    elif not seed:
        seed = config.get_golden_seed(cfg.project_dir, seeds_key)
        if seed:
            # Check binary hash staleness
            stored_hash = config.get_seed_hash(cfg.project_dir, seeds_key)
            if stored_hash:
                current_hash = compute_sha256_prefix(game_p)
                if current_hash != stored_hash and current_hash != "unknown" and not args.quiet:
                    print(f"WARNING: Game binary hash changed ({stored_hash} -> {current_hash}). "
                          f"Golden seed may need re-discovery.", file=sys.stderr)

    # Read walkthrough commands, ensure trailing "score"
    walk_text = walk_p.read_text(encoding="utf-8")
    lines = walk_text.rstrip().split("\n")
    if not any(line.strip() == "score" for line in lines[-5:]):
        lines.append("score")
    input_text = "\n".join(lines) + "\n"

    # Run the walkthrough
    result = process.run_interpreter(
        engine_path, game_path,
        input_text=input_text,
        seed=seed,
        seed_flag=seed_flag,
    )
    transcript = result.stdout or ""

    # === Diagnostics ===
    def count(pattern: str) -> int:
        return regex.count_matches(pattern, transcript, ignorecase=True)

    def count_cs(pattern: str) -> int:
        return regex.count_matches(pattern, transcript, ignorecase=False)

    # Score extraction
    final_score = regex.pcre_search(cfg.scoring.score_regex, transcript, ignorecase=True) or ""
    if not final_score:
        final_score = regex.pcre_search(cfg.scoring.fallback_regex, transcript) or "?"
    if not final_score:
        final_score = "?"

    max_score = regex.pcre_search(cfg.scoring.max_regex, transcript) or str(cfg.scoring.default_max)
    if not max_score:
        max_score = str(cfg.scoring.default_max)

    # Deaths, errors, scoring
    death_count = count(cfg.diagnostics.death_patterns)
    cant_see = count_cs("can't see any such thing")
    cant_go = count_cs("can't go that way")
    not_possible = count("that.s not something you can|I only understood")
    score_ups = count_cs("score has just gone up")
    score_downs = count_cs("score has just gone down")

    # Won flag
    won_flag = bool(regex.pcre_findall(cfg.diagnostics.won_patterns, transcript, ignorecase=True))

    # Pass/fail
    if cfg.diagnostics.scoreless:
        # Scoreless games: pass if endgame text is detected
        passed = won_flag
    else:
        try:
            score_int = int(final_score)
            passed = score_int >= cfg.scoring.pass_threshold
        except ValueError:
            passed = False

    # Print diagnostics
    if not args.quiet:
        check = "+" if passed else "FAIL"
        print(f"=== {cfg.project_name} Walkthrough Test ===")
        print(f"Engine:  {engine_name}")
        if seed:
            print(f"Seed:    {seed}")
        else:
            print("Seed:    (none -- true randomness)")
        print(f"Score:   {final_score}/{max_score}  {check}")
        print(f"Deaths:  {death_count}")

        # Project-specific diagnostics
        diag_fn = load_diagnostics_extra(cfg.project_dir)
        if diag_fn:
            diag_fn(transcript)

        print(f'Errors:  {cant_see} "can\'t see" / {cant_go} "can\'t go" / {not_possible} other')
        print(f"Scoring: {score_ups} increases, {score_downs} decreases")
        print(f"Endgame: {'REACHED' if won_flag else 'NOT reached'}")
        print(f"Result:  {'PASS' if passed else 'FAIL -- see output for details'}")

    # Diff mode
    if args.diff:
        output_p = Path(output_file)
        if output_p.exists():
            print("\n=== Diff vs saved baseline ===")
            import difflib
            baseline = output_p.read_text(encoding="utf-8").splitlines()
            current = transcript.splitlines()
            diff = difflib.unified_diff(baseline, current, lineterm="",
                                        fromfile="baseline", tofile="current")
            diff_text = "\n".join(diff)
            if diff_text:
                print(diff_text)
            else:
                print("(no differences)")
        else:
            print(f"\nNo saved baseline found at: {output_file}")

    # Save output
    if not args.no_save:
        output_p = Path(output_file)
        output_p.parent.mkdir(parents=True, exist_ok=True)
        output_p.write_text(transcript, encoding="utf-8")
        if not args.quiet:
            print(f"\nOutput saved to: {output_file}")

    # Copy output if requested
    if args.copy_output and passed and Path(output_file).exists():
        copy_dir = Path(args.copy_output)
        if copy_dir.is_dir():
            shutil.copy2(output_file, str(copy_dir / "walkthrough_output.txt"))
            if not args.quiet:
                print(f"Output copied to: {copy_dir / 'walkthrough_output.txt'}")
        else:
            print(f"WARNING: --copy-output directory not found: {copy_dir}", file=sys.stderr)

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
