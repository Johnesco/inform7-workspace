#!/usr/bin/env python3
r"""Portable grep -oP replacement using Python re.

Git Bash's grep doesn't support -P (PCRE). This script handles the
subset of PCRE used by the test framework (primarily \K lookbehinds
and (?=...) lookaheads).

Usage:
    python3 pcre_grep.py [flags] PATTERN [FILE]

Flags:
    -o    Output only the matched portion (like grep -o)
    -i    Case-insensitive matching
    -c    Count matches instead of printing them
    -q    Quiet mode — exit 0 if match found, 1 otherwise
    -l    Print only the last match (like grep | tail -1)

If FILE is omitted, reads from stdin.

\K handling:
    Converts 'prefix\Ksuffix' to 'prefix(suffix)' and extracts
    the captured group. This avoids Python's fixed-width lookbehind
    limitation and works with variable-width prefixes like \s+.
"""

import re
import sys


HAS_K = False  # Module-level flag: pattern uses \K (capture group mode)


def convert_pattern(pattern):
    r"""Convert \K in pattern to a capturing group.

    PCRE \K resets the match start. We convert 'prefix\Ksuffix' to
    'prefix(suffix)' and use the captured group as the match result.
    This avoids Python's fixed-width lookbehind limitation.
    """
    global HAS_K
    if r'\K' not in pattern:
        HAS_K = False
        return pattern

    HAS_K = True
    parts = pattern.split(r'\K', 1)
    if len(parts) == 2:
        prefix, suffix = parts
        return f'{prefix}({suffix})'
    return pattern


def main():
    # Parse flags
    flags_str = set()
    args = []
    for arg in sys.argv[1:]:
        if arg.startswith('-') and len(arg) > 1 and not arg.startswith('--'):
            for ch in arg[1:]:
                flags_str.add(ch)
        else:
            args.append(arg)

    if not args:
        print("Usage: pcre_grep.py [flags] PATTERN [FILE]", file=sys.stderr)
        sys.exit(2)

    pattern_str = args[0]
    file_path = args[1] if len(args) > 1 else None

    flag_o = 'o' in flags_str
    flag_i = 'i' in flags_str
    flag_c = 'c' in flags_str
    flag_q = 'q' in flags_str
    flag_l = 'l' in flags_str

    # Convert \K to lookbehind
    python_pattern = convert_pattern(pattern_str)

    re_flags = 0
    if flag_i:
        re_flags |= re.IGNORECASE

    try:
        regex = re.compile(python_pattern, re_flags)
    except re.error as e:
        print(f"pcre_grep.py: invalid pattern: {e}", file=sys.stderr)
        sys.exit(2)

    # Read input
    if file_path:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                text = f.read()
        except FileNotFoundError:
            print(f"pcre_grep.py: {file_path}: No such file", file=sys.stderr)
            sys.exit(2)
    else:
        text = sys.stdin.read()

    # Find all matches
    matches = regex.findall(text)

    if flag_q:
        sys.exit(0 if matches else 1)

    if flag_c:
        print(len(matches))
        sys.exit(0 if matches else 1)

    if not matches:
        sys.exit(1)

    if flag_l:
        # Last match only
        print(matches[-1])
    else:
        for m in matches:
            print(m)

    sys.exit(0)


if __name__ == '__main__':
    main()
