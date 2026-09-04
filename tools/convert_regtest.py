#!/usr/bin/env python3
"""Convert .regtest files to .scenario format.

Reads a .regtest file and its scenarios/index.json (if present),
outputs a .scenario file with inline metadata.

Usage:
    python convert_regtest.py tests/game.regtest
    python convert_regtest.py tests/game.regtest --index tests/scenarios/index.json
    python convert_regtest.py tests/game.regtest --dry-run
"""

import argparse
import json
import re
import sys
from pathlib import Path


def convert(regtest_path, index_path=None, dry_run=False):
    regtest_path = Path(regtest_path)
    lines = regtest_path.read_text(encoding="utf-8").splitlines()

    # Load index for metadata
    index_lookup = {}
    if index_path and Path(index_path).is_file():
        data = json.loads(Path(index_path).read_text(encoding="utf-8"))
        for s in data.get("scenarios", []):
            index_lookup[s["name"]] = s

    output = []
    in_vital_section = False

    for line in lines:
        stripped = line.rstrip()

        # Skip ** metadata lines (Plotkin's tool directives)
        if stripped.startswith("** "):
            continue

        # Blank lines pass through
        if not stripped or stripped.isspace():
            output.append("")
            continue

        # Comments pass through
        if stripped.startswith("#"):
            output.append(stripped)
            continue

        # Scenario header: * name
        m = re.match(r"^\*\s+(\S+)", stripped)
        if m:
            in_vital_section = False
            name = m.group(1)
            meta = index_lookup.get(name, {})
            title = meta.get("title", "")
            category = meta.get("category", "")
            primary = meta.get("primary", False)

            header = f"== {name}"
            if title:
                header += f": {title}"
            tags = []
            if category:
                tags.append(category.lower())
            if primary:
                tags.append("primary")
            if tags:
                header += f"  [{', '.join(tags)}]"

            output.append(header)
            continue

        # Include: >{include} name
        m = re.match(r"^>\{include\}\s*(\S+)", stripped)
        if m:
            output.append(f"@ {m.group(1)}")
            continue

        # Command: > text
        m = re.match(r"^>\s*(.*)", stripped)
        if m:
            in_vital_section = False
            output.append(f"> {m.group(1)}")
            continue

        # {vital} on its own line — next assertions are vital
        if stripped.strip() == "{vital}":
            in_vital_section = True
            continue

        # {vital}text — inline vital assertion
        if stripped.startswith("{vital}"):
            text = stripped[7:].strip()
            output.append(f"?? {text}")
            continue

        # Negated: !text
        if stripped.startswith("!"):
            text = stripped[1:]
            prefix = "??! " if in_vital_section else "?! "
            output.append(f"{prefix}{text}")
            continue

        # {invert}text
        if stripped.startswith("{invert}"):
            text = stripped[8:]
            prefix = "??! " if in_vital_section else "?! "
            output.append(f"{prefix}{text}")
            continue

        # {status}text — skip (not used, dumb mode)
        if stripped.startswith("{status}"):
            continue

        # Regular assertion (bare literal or /regex/)
        prefix = "?? " if in_vital_section else "? "
        output.append(f"{prefix}{stripped}")

    result = "\n".join(output).rstrip() + "\n"

    if dry_run:
        print(result)
    else:
        out_path = regtest_path.with_suffix(".scenario")
        out_path.write_text(result, encoding="utf-8")
        print(f"  {regtest_path} -> {out_path}")

    return result


def main():
    parser = argparse.ArgumentParser(description="Convert .regtest to .scenario")
    parser.add_argument("regtest", help="Path to .regtest file")
    parser.add_argument("--index", help="Path to scenarios/index.json")
    parser.add_argument("--dry-run", action="store_true", help="Print to stdout only")
    args = parser.parse_args()

    convert(args.regtest, args.index, args.dry_run)


if __name__ == "__main__":
    main()
