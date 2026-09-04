"""Shared transcript parsing utilities.

Extracted from tools/testing/generate-guide.py so that both generate-guide.py
and generate_map.py (and any future transcript consumers) share one parser.
"""

import re

# ---------------------------------------------------------------------------
# Navigation words and direction mappings
# ---------------------------------------------------------------------------

NAV_WORDS = {
    "n", "s", "e", "w", "ne", "nw", "se", "sw", "u", "d",
    "north", "south", "east", "west", "northeast", "northwest",
    "southeast", "southwest", "up", "down", "in", "out",
}

# Long-form → short-form direction mapping
_DIRECTION_ALIASES = {
    "north": "n", "south": "s", "east": "e", "west": "w",
    "northeast": "ne", "northwest": "nw", "southeast": "se", "southwest": "sw",
    "up": "u", "down": "d", "in": "in", "out": "out",
    # Short forms map to themselves
    "n": "n", "s": "s", "e": "e", "w": "w",
    "ne": "ne", "nw": "nw", "se": "se", "sw": "sw",
    "u": "u", "d": "d",
}

DIRECTION_OPPOSITES = {
    "n": "s", "s": "n", "e": "w", "w": "e",
    "ne": "sw", "sw": "ne", "nw": "se", "se": "nw",
    "u": "d", "d": "u", "in": "out", "out": "in",
}

# Grid offsets for layout: (dx, dy)
# North/up = up on screen (y-1), south/down = down (y+1),
# east = right (x+1), west = left (x-1), diagonals accordingly.
# Up/down share the same axis as north/south — no separate floor layer.
DIRECTION_OFFSETS = {
    "n": (0, -1), "s": (0, 1),
    "e": (1, 0), "w": (-1, 0),
    "ne": (1, -1), "nw": (-1, -1),
    "se": (1, 1), "sw": (-1, 1),
    "u": (0, -1), "d": (0, 1),
    "in": (0, 0), "out": (0, 0),
}


# ---------------------------------------------------------------------------
# Transcript parsing
# ---------------------------------------------------------------------------

def parse_transcript(transcript_path):
    """Parse a glulxe transcript into (preamble, responses) tuple.

    The transcript format from CheapGlk is:
        >Response to command
        or
        >
        Room Name
        Description...

    Returns (preamble_text, [response strings]).
    The preamble is the text before the first > prompt (banner, sound prompt, etc.).
    Each response corresponds to one > prompt in the transcript.
    """
    with open(transcript_path, encoding="utf-8", errors="replace") as f:
        text = f.read()

    # Split on > prompts. The first chunk is the banner/preamble.
    # Each subsequent chunk is the response to one command.
    parts = re.split(r"^>", text, flags=re.MULTILINE)

    preamble = parts[0] if parts else ""
    responses = [part.strip() for part in parts[1:]]

    return preamble, responses


def has_sound_prompt(preamble):
    """Detect if the game preamble contains a sound prompt.

    Games with sound ask "Do you want sound? (y/n)" before the main game loop.
    This consumes the first walkthrough command without producing a > prompt,
    so the responses are offset by one from the commands.
    """
    return bool(re.search(r"Do you want sound|Sound disabled|Sound enabled",
                          preamble, re.IGNORECASE))


def detect_room_name(response):
    """Try to detect a room name from a response.

    Room names in Inform 7 transcripts appear as the first line of a
    movement response -- a short title line followed by a longer description.
    Heuristic: first line is short (<60 chars), starts with uppercase,
    doesn't start with common response words.
    """
    lines = response.split("\n")
    if not lines:
        return None

    first_line = lines[0].strip()

    # Skip empty, or lines that are clearly responses not room names
    if not first_line:
        # Room name might be on next non-empty line
        for line in lines:
            line = line.strip()
            if line:
                first_line = line
                break
        if not first_line:
            return None

    # Response patterns that are NOT room names
    non_room = [
        "Taken", "Dropped", "You ", "The ", "That", "It ", "I ", "With ",
        "There ", "Your ", "A ", "An ", "[", "Ok", "Nothing", "But ",
        "What ", "Which ", "How ", "Opening", "Closing", "Putting",
        "Sound ", "Welcome", "Do you",
    ]
    for prefix in non_room:
        if first_line.startswith(prefix):
            return None

    # Room names are typically short, title-case-ish
    if len(first_line) > 60:
        return None
    if not first_line[0].isupper():
        return None

    # Must have at least one more line (the description) to be a room entry
    non_empty_lines = [l for l in lines if l.strip()]
    if len(non_empty_lines) < 2:
        return None

    return first_line


def detect_room_entry(response):
    """Detect a room name and its description from a transcript response.

    Returns (room_name, description) or (None, None).
    """
    name = detect_room_name(response)
    if name is None:
        return None, None

    lines = response.split("\n")
    # Find the room name line, then collect description lines after it
    found = False
    desc_lines = []
    for line in lines:
        stripped = line.strip()
        if not found:
            if stripped == name:
                found = True
            continue
        # Collect non-empty lines until we hit a blank line after some content,
        # or a meta line like [Your score...
        if not stripped:
            if desc_lines:
                break
            continue
        if stripped.startswith("["):
            break
        if stripped.startswith(">"):
            break
        desc_lines.append(stripped)

    description = " ".join(desc_lines) if desc_lines else ""
    return name, description


def detect_preamble_room(preamble):
    """Detect the starting room from the game preamble/banner text.

    The preamble contains the banner (title, author, release info) followed
    by the initial room name and description. We scan from the bottom up
    to find the room name, which appears after the banner lines.

    Returns (room_name, description) or (None, None).
    """
    lines = preamble.split("\n")
    # Strip trailing empty lines
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return None, None

    # Strategy: find the last paragraph break (blank line) that separates
    # banner from room. The room name is the first non-empty line after
    # the banner block. We look for a pattern: short title-case line
    # followed by a longer description paragraph.
    #
    # Walk through paragraphs (separated by blank lines).
    paragraphs = []
    current = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current:
                paragraphs.append(current)
                current = []
        else:
            current.append(stripped)
    if current:
        paragraphs.append(current)

    # We need at least 2 paragraphs: banner + room (with desc)
    # Try to find a paragraph that looks like a room entry
    for idx in range(len(paragraphs) - 1, -1, -1):
        para = paragraphs[idx]
        if len(para) < 2:
            continue
        first = para[0]
        # Room name heuristics (same as detect_room_name)
        if len(first) > 60:
            continue
        if not first[0].isupper():
            continue
        # Should not be a banner line (Release, Serial, by Author)
        if any(kw in first for kw in ["Release", "Serial", "Inform 7"]):
            continue
        if " by " in first and len(first) < 40:
            # Likely "Title by Author" banner line
            continue
        # The second line should be longer (description), not another short line
        if len(para[1]) > 20:
            # This looks like a room name + description
            name = first
            # Filter out "You can see" lines from description
            desc_lines = [
                l for l in para[1:]
                if not l.startswith("You can see") and not l.startswith("[")
            ]
            desc = " ".join(desc_lines)
            return name, desc

    return None, None


def normalize_direction(command):
    """Normalize a navigation command to its short direction form.

    Returns the short direction string ("n", "se", "u", etc.) or None
    if the command is not a navigation direction.
    """
    cmd = command.strip().lower()
    return _DIRECTION_ALIASES.get(cmd)
