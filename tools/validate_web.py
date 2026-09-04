#!/usr/bin/env python3
"""Validate a web player directory for common deployment issues.

Usage:
    python tools/validate_web.py <path-to-web-dir>
    python tools/validate_web.py projects/sample

Checks:
  1. play.html exists
  2. No unsubstituted template tokens remain
  3. All src/href references point to existing files
  4. Binary .js file is exactly 1 line
  5. Binary .js file starts with processBase64Zcode('
  6. parchment_options contains story_name
  7. parchment.js is loaded (not just main.js)

Exit codes: 0 = all pass, 1 = any check failed
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.web import validate_web_dir


def main():
    parser = argparse.ArgumentParser(description="Validate a web player directory.")
    parser.add_argument("web_dir", help="Path to the web player directory")
    args = parser.parse_args()

    web_dir = Path(args.web_dir)
    if not web_dir.is_dir():
        print(f"ERROR: Not a directory: {web_dir}", file=sys.stderr)
        sys.exit(1)

    errors = validate_web_dir(web_dir)
    sys.exit(1 if errors > 0 else 0)


if __name__ == "__main__":
    main()
