"""Terminal output formatting — colors, status prefixes, step counters."""

import os
import sys

# Respect NO_COLOR convention (https://no-color.org/)
_NO_COLOR = "NO_COLOR" in os.environ

# ANSI escape codes
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
BOLD = "\033[1m"
NC = "\033[0m"


def _c(code: str, text: str) -> str:
    if _NO_COLOR:
        return text
    return f"{code}{text}{NC}"


def red(text: str) -> str:
    return _c(RED, text)


def green(text: str) -> str:
    return _c(GREEN, text)


def yellow(text: str) -> str:
    return _c(YELLOW, text)


def blue(text: str) -> str:
    return _c(BLUE, text)


def bold(text: str) -> str:
    return _c(BOLD, text)


def step(current: int, total: int, msg: str):
    """Print a step indicator: [2/6] Compiling..."""
    print(f"  [{current}/{total}] {msg}")


def banner(msg: str):
    """Print a section banner: === Section Header ==="""
    print(f"\n{bold(f'=== {msg} ===')}")


def ok(msg: str):
    print(f"  {green('OK')}:   {msg}")


def fail(msg: str):
    print(f"  {red('FAIL')}: {msg}", file=sys.stderr)


def warn(msg: str):
    print(f"  {yellow('WARN')}: {msg}", file=sys.stderr)


def skip(msg: str):
    print(f"  {yellow('SKIP')}: {msg}")
