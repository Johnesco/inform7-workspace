#!/usr/bin/env python3
"""Generic seed sweep for walkthrough testing.

Tries many RNG seeds to find one where the walkthrough achieves a passing score.

Usage:
    python tools/testing/find_seeds.py --config PATH
    python tools/testing/find_seeds.py --config PATH --alt
    python tools/testing/find_seeds.py --config PATH --max 500
    python tools/testing/find_seeds.py --config PATH --stop
    python tools/testing/find_seeds.py --config PATH --no-stop
"""

import argparse
import hashlib
import statistics
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import config, process, regex


def compute_sha256_prefix(path: Path, length: int = 8) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:length]
    except OSError:
        return "none"


def main():
    parser = argparse.ArgumentParser(description="Sweep RNG seeds for walkthrough testing.")
    parser.add_argument("--config", required=True, help="Path to project.conf")
    parser.add_argument("--alt", action="store_true", help="Use alternate engine")
    parser.add_argument("--max", type=int, default=200, help="Max seeds to try (default: 200)")
    parser.add_argument("--stop", action="store_true", default=True, help="Stop on first pass")
    parser.add_argument("--no-stop", action="store_true", help="Continue after finding pass")
    args = parser.parse_args()

    if args.no_stop:
        args.stop = False

    conf_path = Path(args.config)
    if not conf_path.exists():
        print(f"ERROR: Config file not found: {conf_path}", file=sys.stderr)
        sys.exit(2)

    cfg = config.load_config(conf_path)

    # Select engine
    if args.alt:
        if not cfg.alt.name:
            print("ERROR: Alternate engine not configured", file=sys.stderr)
            sys.exit(2)
        engine_name = cfg.alt.name
        engine_path = cfg.alt.path
        seed_flag = cfg.alt.seed_flag
        game_path = cfg.alt.game_path
        walkthrough = cfg.alt.walkthrough
    else:
        engine_name = cfg.primary.name
        engine_path = cfg.primary.path
        seed_flag = cfg.primary.seed_flag
        game_path = cfg.primary.game_path
        walkthrough = cfg.primary.walkthrough

    threshold = cfg.scoring.pass_threshold
    max_display = cfg.scoring.default_max

    print(f"=== {cfg.project_name} Seed Sweep ===")
    print(f"Mode:    {engine_name}")
    print(f"Range:   1..{args.max}")
    print(f"Target:  {threshold}/{max_display}")
    print()

    # Read walkthrough
    walk_p = Path(walkthrough)
    if not walk_p.exists():
        print(f"ERROR: Walkthrough not found: {walkthrough}", file=sys.stderr)
        sys.exit(2)
    walk_text = walk_p.read_text(encoding="utf-8")
    lines = walk_text.rstrip().split("\n")
    if not any(line.strip() == "score" for line in lines[-5:]):
        lines.append("score")
    input_text = "\n".join(lines) + "\n"

    # Statistics
    best_score = 0
    best_seed = 0
    worst_score = 999
    worst_seed = 0
    all_scores: list[int] = []
    pass_seeds: list[int] = []

    for seed in range(1, args.max + 1):
        result = process.run_interpreter(
            engine_path, game_path,
            input_text=input_text,
            seed=str(seed),
            seed_flag=seed_flag,
        )
        transcript = result.stdout or ""

        # Extract score
        score_str = regex.pcre_search(cfg.scoring.score_regex, transcript, ignorecase=True) or ""
        if not score_str:
            score_str = regex.pcre_search(cfg.scoring.fallback_regex, transcript) or "0"
        try:
            score = int(score_str) if score_str else 0
        except ValueError:
            score = 0

        all_scores.append(score)

        if score > best_score:
            best_score = score
            best_seed = seed
        if score < worst_score:
            worst_score = score
            worst_seed = seed

        if score >= threshold:
            pass_seeds.append(seed)
            print(f"[seed {seed}/{args.max}] *** {threshold}/{max_display} PASS *** (seed {seed})")

            if args.stop:
                game_hash = compute_sha256_prefix(Path(game_path))
                today = date.today().isoformat()
                print()
                print("=== Golden Seed Found! ===")
                print(f"Engine:  {engine_name}")
                print(f"Seed:    {seed}")
                print(f"Score:   {threshold}/{max_display}")
                print(f"Hash:    {game_hash}")
                print()
                print("seeds.conf line:")
                print(f"{engine_name}:{seed}:{game_hash}:{today}")
                sys.exit(0)
        elif seed % 10 == 0:
            print(f"[seed {seed}/{args.max}] best so far: {best_score}/{max_display} (seed {best_seed})")

    # Summary
    print()
    print("=== Seed Sweep Complete ===")
    print(f"Range:      1..{args.max}")
    print(f"Best score: {best_score}/{max_display} (seed {best_seed})")
    print(f"Worst:      {worst_score}/{max_display} (seed {worst_seed})")

    if all_scores:
        median = int(statistics.median(all_scores))
        average = sum(all_scores) // len(all_scores)
        print(f"Median:     {median}/{max_display}")
        print(f"Average:    {average}/{max_display}")

    print(f"Pass rate:  {len(pass_seeds)}/{args.max}")

    if pass_seeds:
        game_hash = compute_sha256_prefix(Path(game_path))
        today = date.today().isoformat()
        first_pass = pass_seeds[0]
        print()
        print(f"Recommended golden seed: {first_pass}")
        print("seeds.conf line:")
        print(f"{engine_name}:{first_pass}:{game_hash}:{today}")
        print()
        print(f"All passing seeds: {' '.join(str(s) for s in pass_seeds)}")
    else:
        print()
        print(f"NO SEED achieved {threshold}/{max_display}.")
        print(f"Best achievable: {best_score}/{max_display} (seed {best_seed})")
        print()
        print("This suggests the walkthrough itself has issues (not just RNG).")
        alt_flag = "--alt " if args.alt else ""
        print(f"Run with the best seed to diagnose:")
        print(f"  python tools/testing/run_walkthrough.py --config {args.config} {alt_flag}--seed {best_seed}")

    sys.exit(0 if pass_seeds else 1)


if __name__ == "__main__":
    main()
