r"""Regex utilities — absorbs pcre_grep.py functionality.

Handles the \K PCRE extension used by the test framework's score extraction
patterns, converting it to Python capturing groups.
"""

import re


def convert_k_pattern(pattern: str) -> tuple[str, bool]:
    r"""Convert \K in a PCRE pattern to a Python capturing group.

    Returns (converted_pattern, has_k).
    """
    if r"\K" not in pattern:
        return pattern, False
    parts = pattern.split(r"\K", 1)
    if len(parts) == 2:
        return f"{parts[0]}({parts[1]})", True
    return pattern, False


def pcre_search(pattern: str, text: str, *, ignorecase: bool = False) -> str | None:
    r"""Search for a PCRE-style pattern, returning the match (or \K group).

    Returns the last match found, or None.
    """
    py_pattern, has_k = convert_k_pattern(pattern)
    flags = re.IGNORECASE if ignorecase else 0
    matches = re.findall(py_pattern, text, flags)
    if not matches:
        return None
    return matches[-1] if matches else None


def pcre_findall(pattern: str, text: str, *, ignorecase: bool = False) -> list[str]:
    """Find all matches of a PCRE-style pattern."""
    py_pattern, has_k = convert_k_pattern(pattern)
    flags = re.IGNORECASE if ignorecase else 0
    return re.findall(py_pattern, text, flags)


def count_matches(pattern: str, text: str, *, ignorecase: bool = True) -> int:
    """Count regex matches in text (case-insensitive by default)."""
    flags = re.IGNORECASE if ignorecase else 0
    return len(re.findall(pattern, text, flags))
