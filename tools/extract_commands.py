#!/usr/bin/env python3
"""Extract flat command lists from regtest scenario files.

Parses a regtest file (format: https://eblong.com/zarf/plotex/regtest.html)
into named tests, recursively resolves >{include} directives, and outputs
plain command lists (one per line).

Promoted from zork1/tests/extract-scenario-commands.py to shared i7 tooling.

Usage:
    python extract_commands.py --regtest FILE TESTNAME
    python extract_commands.py --regtest FILE --list
    python extract_commands.py --regtest FILE --all --out-dir DIR
    python extract_commands.py --config tests/project.conf TESTNAME
    python extract_commands.py --config tests/project.conf --list
"""

import argparse
import json
import re
import sys
from pathlib import Path

_TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_TOOLS_DIR))


def parse_regtest(path):
    """Parse a regtest file into a dict of test_name -> list of items.

    Each item is either:
      ("command", text)   — a command to send
      ("include", name)   — an include directive referencing another test
      ("check", text)     — an assertion line (regex, literal, negation)
    """
    tests = {}
    current_test = None

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n").rstrip("\r")

            if not line or line.isspace():
                continue
            if line.startswith("#"):
                continue
            if line.startswith("** "):
                continue

            # Test header: * testname
            m = re.match(r"^\*\s+(\S+)", line)
            if m:
                current_test = m.group(1)
                tests[current_test] = []
                continue

            if current_test is None:
                continue

            # Include directive: >{include} othername
            m = re.match(r"^>\{include\}\s*(\S+)", line)
            if m:
                tests[current_test].append(("include", m.group(1)))
                continue

            # Command: > text
            m = re.match(r"^>\s*(.*)", line)
            if m:
                tests[current_test].append(("command", m.group(1)))
                continue

            # Everything else is an assertion — store it for tools that need checks
            tests[current_test].append(("check", line))

    return tests


def resolve_commands(tests, test_name, _visiting=None):
    """Recursively resolve a test into a flat list of command strings.

    Detects circular includes and raises an error if found.
    """
    if test_name not in tests:
        print(f"Error: unknown test '{test_name}'", file=sys.stderr)
        print("Use --list to see available tests.", file=sys.stderr)
        sys.exit(1)

    if _visiting is None:
        _visiting = set()

    if test_name in _visiting:
        cycle = " -> ".join(sorted(_visiting)) + f" -> {test_name}"
        print(f"Error: circular include detected: {cycle}", file=sys.stderr)
        sys.exit(1)

    _visiting = _visiting | {test_name}

    commands = []
    for kind, value in tests[test_name]:
        if kind == "include":
            commands.extend(resolve_commands(tests, value, _visiting))
        elif kind == "command":
            commands.append(value)

    return commands


def resolve_checks(tests, test_name, _visiting=None):
    """Recursively resolve a test into a flat list of (command_index, check) pairs.

    Returns list of tuples: (command_count_before_check, check_text).
    This allows matching checks to specific commands for assertion validation.
    """
    if test_name not in tests:
        return []

    if _visiting is None:
        _visiting = set()
    if test_name in _visiting:
        return []
    _visiting = _visiting | {test_name}

    result = []
    cmd_count = 0
    for kind, value in tests[test_name]:
        if kind == "include":
            included = resolve_checks(tests, value, _visiting)
            # Offset command indices
            for idx, check in included:
                result.append((cmd_count + idx, check))
            # Count commands from included test
            cmd_count += len(resolve_commands(tests, value))
        elif kind == "command":
            cmd_count += 1
        elif kind == "check":
            result.append((cmd_count, value))

    return result


def find_regtest_from_config(config_path):
    """Resolve the regtest file path from a project.conf file."""
    # Import config module
    from lib import config
    cfg = config.load_config(config_path)
    if cfg.regtest_file and Path(cfg.regtest_file).is_file():
        return cfg.regtest_file
    # Fallback: look for <game>.regtest in tests/
    tests_dir = Path(config_path).parent
    for p in tests_dir.glob("*.regtest"):
        return str(p)
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Extract commands from regtest scenarios."
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--regtest", help="Path to regtest file")
    source.add_argument("--config", help="Path to project.conf (resolves regtest file)")

    parser.add_argument("--list", action="store_true", dest="list_tests",
                        help="List all available test names and exit")
    parser.add_argument("--all", action="store_true",
                        help="Extract commands for all tests")
    parser.add_argument("--out-dir", help="Output directory for --all mode")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON (test name -> command list)")
    parser.add_argument("testname", nargs="?",
                        help="Name of the test to extract commands for")

    args = parser.parse_args()

    # Resolve regtest file
    regtest_path = args.regtest
    if args.config:
        regtest_path = find_regtest_from_config(args.config)
        if not regtest_path:
            print("Error: no regtest file found from config", file=sys.stderr)
            sys.exit(1)
    if not regtest_path:
        parser.error("--regtest or --config is required")
    if not Path(regtest_path).is_file():
        print(f"Error: regtest file not found: {regtest_path}", file=sys.stderr)
        sys.exit(1)

    tests = parse_regtest(regtest_path)

    if args.list_tests:
        for name in tests:
            cmds = resolve_commands(tests, name)
            print(f"  {name:30s} ({len(cmds)} commands)")
        return

    if args.all:
        if args.json:
            result = {}
            for name in tests:
                result[name] = resolve_commands(tests, name)
            json.dump(result, sys.stdout, indent=2)
            print()
            return

        out_dir = Path(args.out_dir) if args.out_dir else None
        if out_dir:
            out_dir.mkdir(parents=True, exist_ok=True)

        for name in tests:
            cmds = resolve_commands(tests, name)
            if out_dir:
                out_file = out_dir / f"{name}.commands.txt"
                out_file.write_text("\n".join(cmds) + "\n", encoding="utf-8")
                print(f"  {name:30s} -> {out_file} ({len(cmds)} commands)")
            else:
                print(f"# {name} ({len(cmds)} commands)")
                for cmd in cmds:
                    print(cmd)
                print()
        return

    if args.testname is None:
        parser.error("TESTNAME is required (or use --list / --all)")

    commands = resolve_commands(tests, args.testname)

    if args.json:
        json.dump(commands, sys.stdout, indent=2)
        print()
    else:
        for cmd in commands:
            print(cmd)


if __name__ == "__main__":
    main()
