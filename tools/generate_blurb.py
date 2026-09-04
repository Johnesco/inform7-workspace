#!/usr/bin/env python3
"""Generate a .blurb file for inblorb from an Inform 7 source file.

Parses story.ni for "Sound of ... is the file ..." declarations,
assigns resource IDs starting from 3 (1=cover, 2=small cover by convention),
and outputs a .blurb file suitable for inblorb.

Usage:
    python tools/generate_blurb.py \
        --ulx projects/zork1/zork1.ulx \
        --source projects/zork1/story.ni \
        --sounds projects/zork1/Sounds/ \
        --out projects/zork1/zork1.blurb
"""

import argparse
import re
import sys
from pathlib import Path


def to_windows_path(p: Path) -> str:
    """Convert a path to Windows format for inblorb.exe."""
    s = str(p.resolve())
    return s.replace("/", "\\")


def main():
    parser = argparse.ArgumentParser(description="Generate .blurb for inblorb.")
    parser.add_argument("--ulx", required=True, help="Path to .ulx file")
    parser.add_argument("--source", required=True, help="Path to story.ni")
    parser.add_argument("--sounds", required=True, help="Path to Sounds/ directory")
    parser.add_argument("--out", required=True, help="Output .blurb path")
    args = parser.parse_args()

    ulx_path = Path(args.ulx)
    source_path = Path(args.source)
    sounds_dir = Path(args.sounds)
    out_path = Path(args.out)

    if not source_path.exists():
        print(f"Error: Source file not found: {source_path}", file=sys.stderr)
        sys.exit(1)
    if not ulx_path.exists():
        print(f"Error: ULX file not found: {ulx_path}", file=sys.stderr)
        sys.exit(1)
    if not sounds_dir.is_dir():
        print(f"Error: Sounds directory not found: {sounds_dir}", file=sys.stderr)
        sys.exit(1)

    # Extract sound declarations: Sound of <name> is the file "<filename>"
    source_text = source_path.read_text(encoding="utf-8")
    sound_files = re.findall(r'Sound of .* is the file "([^"]*)"', source_text)

    if not sound_files:
        print(f"Error: No sound declarations found in {source_path}", file=sys.stderr)
        sys.exit(1)

    # Generate .blurb
    lines = [f'storyfile "{to_windows_path(ulx_path)}" include']
    resource_id = 3
    for filename in sound_files:
        sound_file = sounds_dir / filename
        if not sound_file.exists():
            print(f"WARNING: Sound file not found: {sound_file}", file=sys.stderr)
        lines.append(f'sound {resource_id} "{to_windows_path(sounds_dir / filename)}"')
        resource_id += 1

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    count = len(sound_files)
    print(f"Generated {out_path} with {count} sound resources (IDs 3-{3 + count - 1})")


if __name__ == "__main__":
    main()
