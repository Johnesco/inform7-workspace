#!/usr/bin/env python3
"""Generate a walkthrough-guide.txt from walkthrough.txt + walkthrough_output.txt.

Pairs each walkthrough command with its game response from the transcript,
detects room changes and notable events, and inserts section headers and
annotations.

Usage:
    python3 generate-guide.py --walkthrough PATH --output PATH [--transcript PATH]
    python3 generate-guide.py --walkthrough PATH --output PATH --force

If --transcript is omitted, outputs a skeleton guide (commands only, no annotations).
"""

import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.transcript import (
    NAV_WORDS,
    detect_room_name,
    has_sound_prompt,
    parse_transcript,
)

GUIDE_MARKER = "# Auto-generated walkthrough guide"


WORD_TO_NUM = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "twenty-five": 25, "thirty": 30,
    "fifty": 50, "hundred": 100,
}


def normalize_points(text):
    """Convert word-form numbers to digits (e.g., 'five' -> '5')."""
    return str(WORD_TO_NUM.get(text.lower(), text))


def detect_events(response):
    """Detect notable events in a response."""
    events = []
    if "score has just gone up" in response:
        m = re.search(r"gone up by (\S+) points?", response)
        points = normalize_points(m.group(1)) if m else "?"
        events.append(f"+{points} points")
    if "score has just gone down" in response:
        m = re.search(r"gone down by (\S+) points?", response)
        points = normalize_points(m.group(1)) if m else "?"
        events.append(f"-{points} points")
    if re.search(r"you have died|eaten by a grue", response, re.IGNORECASE):
        events.append("DEATH")
    if re.search(r"You have won|Congratulations", response, re.IGNORECASE):
        events.append("GAME WON")
    return events


# ---------------------------------------------------------------------------
# Rich annotation detectors
# ---------------------------------------------------------------------------

def detect_taken(response, command):
    """Detect item pickup from 'Taken.' response. Returns item name or None."""
    if not response:
        return None
    first_line = response.split("\n")[0].strip()
    if not first_line.startswith("Taken"):
        return None
    m = re.match(r"(?:take|get|pick up)\s+(.+?)(?:\s+(?:from|off)\s+.+)?$",
                 command, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


def detect_unlock_open(response, command):
    """Detect unlock/open events. Returns list of annotation strings."""
    annotations = []
    if not response:
        return annotations
    resp_lower = response.lower()
    cmd_lower = command.lower().strip()

    # Unlock detection
    if cmd_lower.startswith("unlock"):
        m = re.match(r"unlock\s+(.+?)(?:\s+with\s+.+)?$", command, re.IGNORECASE)
        if m:
            annotations.append(f"Unlock the {m.group(1).strip()}")

    # Open detection (only when response indicates something was revealed)
    if cmd_lower.startswith("open") and re.search(r"reveal", resp_lower):
        if not re.search(r"already open", resp_lower):
            m = re.match(r"open\s+(.+)", command, re.IGNORECASE)
            if m:
                annotations.append(f"Open the {m.group(1).strip()}")

    return annotations


def detect_container_put(command):
    """Detect 'put X in Y' commands. Returns (item, container) or None."""
    m = re.match(r"put\s+(.+?)\s+in\s+(.+)", command, re.IGNORECASE)
    if m:
        return (m.group(1).strip(), m.group(2).strip())
    return None


def detect_npc_interaction(command):
    """Detect NPC interaction commands. Returns annotation string or None."""
    patterns = [
        (r"give\s+(.+?)\s+to\s+(.+)", "Give {0} to {1}"),
        (r"show\s+(.+?)\s+to\s+(.+)", "Show {0} to {1}"),
        (r"ask\s+(.+?)\s+about\s+(.+)", "Ask {0} about {1}"),
        (r"tell\s+(.+?)\s+about\s+(.+)", "Tell {0} about {1}"),
    ]
    for pattern, fmt in patterns:
        m = re.match(pattern, command, re.IGNORECASE)
        if m:
            return fmt.format(*[g.strip() for g in m.groups()])
    return None


COMBAT_VERBS = {"kill", "attack", "hit", "fight", "strike"}

# ---------------------------------------------------------------------------
# Response excerpt filtering
# ---------------------------------------------------------------------------

BORING_RESPONSES = {
    "taken", "dropped", "ok", "done", "closed", "locked", "unlocked",
    "opened", "worn", "removed",
}

SKIP_LINE_PATTERNS = [
    re.compile(r"score has just gone (up|down)", re.IGNORECASE),
    re.compile(r"^\[Your score", re.IGNORECASE),
    re.compile(r"^\[sound effect", re.IGNORECASE),
    re.compile(r"^\*\*\*"),
    re.compile(r"^Would you like to (RESTART|RESTORE|QUIT|UNDO)", re.IGNORECASE),
    re.compile(r"^Obvious exits?:", re.IGNORECASE),
    re.compile(r"^You can see\b", re.IGNORECASE),
    re.compile(r"^>"),
]

ERROR_PATTERNS = [
    re.compile(r"You can't see any such thing", re.IGNORECASE),
    re.compile(r"That's not something you can", re.IGNORECASE),
    re.compile(r"That's already (open|closed)", re.IGNORECASE),
    re.compile(r"You already have", re.IGNORECASE),
    re.compile(r"You aren't holding", re.IGNORECASE),
    re.compile(r"There is nothing .* to", re.IGNORECASE),
    re.compile(r"I didn't understand", re.IGNORECASE),
    re.compile(r"That noun did not make sense", re.IGNORECASE),
    re.compile(r"You can't go that way", re.IGNORECASE),
]


def wrap_excerpt(text, width=78):
    """Wrap text into comment lines: '# first line' then '#   continuation'.

    Returns list of strings like ['# The bell suddenly...', '#   wraiths...'].
    """
    prefix_first = "# "
    prefix_cont = "#   "
    result = []
    remaining = text
    first = True
    while remaining:
        prefix = prefix_first if first else prefix_cont
        max_chars = width - len(prefix)
        if len(remaining) <= max_chars:
            result.append(prefix + remaining)
            break
        # Find a break point at a space near max_chars
        brk = remaining.rfind(" ", 0, max_chars + 1)
        if brk <= 0:
            brk = max_chars  # Force break if no space found
        result.append(prefix + remaining[:brk])
        remaining = remaining[brk:].lstrip()
        first = False
    return result


def extract_response_excerpt(response, room, taken):
    """Extract an interesting narrative excerpt from a game response.

    Returns a list of comment lines (already wrapped), or empty list
    if the response is boring/generic.

    Args:
        response: Full response text from transcript
        room: Detected room name (or None) — used to strip room descriptions
        taken: Whether 'Taken.' was detected for this command
    """
    if not response:
        return []

    resp_lines = response.split("\n")

    # Filter out score/sound/game-end/meta lines
    filtered = []
    for line in resp_lines:
        stripped = line.strip()
        if not stripped:
            continue
        if any(pat.search(stripped) for pat in SKIP_LINE_PATTERNS):
            continue
        filtered.append(stripped)

    if not filtered:
        return []

    # If a room was detected, take only text BEFORE the room name line.
    # This captures narrative like "The trap door crashes shut..." that
    # precedes the new room heading.
    if room:
        pre_room = []
        for line in filtered:
            if line == room:
                break
            pre_room.append(line)
        filtered = pre_room
        if not filtered:
            return []

    # If "Taken." detected, strip that line but keep any extra text
    if taken:
        filtered = [l for l in filtered if not l.startswith("Taken")]
        if not filtered:
            return []

    # Skip "Dropped." entirely
    if len(filtered) == 1 and filtered[0].lower().startswith("dropped"):
        return []

    # Skip error responses
    full_text = " ".join(filtered)
    for pat in ERROR_PATTERNS:
        if pat.search(full_text):
            return []

    # Skip single-word boring responses
    if full_text.strip().rstrip(".").lower() in BORING_RESPONSES:
        return []

    # Cap at ~150 chars, break at sentence boundary
    if len(full_text) > 150:
        # Try to break at a sentence boundary
        truncated = full_text[:160]
        # Find last sentence-ending punctuation
        for end_char in [".", "!", "?"]:
            last_pos = truncated.rfind(end_char)
            if last_pos > 50:  # Only if we keep a reasonable chunk
                full_text = truncated[:last_pos + 1]
                break
        else:
            full_text = full_text[:150].rsplit(" ", 1)[0] + "..."

    # Skip if too short to be interesting
    if len(full_text) < 10:
        return []

    return wrap_excerpt(full_text)


def find_repeated_sequences(commands):
    """Find runs of 3+ identical non-navigation commands.

    Returns dict mapping start_index -> (end_index_inclusive, count).
    Simple navigation commands (n, s, e, w, etc.) are excluded since
    repeated movement is normal, not a notable action.
    """
    sequences = {}
    i = 0
    while i < len(commands):
        cmd_lower = commands[i].strip().lower()
        # Skip navigation commands
        if cmd_lower in NAV_WORDS:
            i += 1
            continue
        j = i + 1
        while j < len(commands) and commands[j].lower() == commands[i].lower():
            j += 1
        count = j - i
        if count >= 3:
            sequences[i] = (j - 1, count)
            i = j
        else:
            i += 1
    return sequences


def extract_combat_target(command):
    """Extract the target from a combat command like 'kill troll with sword'."""
    m = re.match(r"(?:kill|attack|hit|fight|strike)\s+(.+?)(?:\s+with\s+.+)?$",
                 command, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return "enemy"


def is_combat_command(command):
    """Check if a command starts with a combat verb."""
    first_word = command.strip().lower().split()[0] if command.strip() else ""
    return first_word in COMBAT_VERBS


# ---------------------------------------------------------------------------
# Hand-written guide detection
# ---------------------------------------------------------------------------

def is_hand_written(filepath):
    """Detect if an existing guide file appears to be hand-written.

    Auto-generated guides start with GUIDE_MARKER. If the file has that
    marker, it's auto-generated (safe to overwrite). Note that auto-generated
    excerpt comments (# narrative text...) don't trigger hand-written
    detection when GUIDE_MARKER is present.

    If there's no marker, we check for prose-style comments (long comment
    lines containing sentences). Two or more such lines indicate a
    hand-written guide.

    Legacy auto-generated guides (no marker, no prose) are safe to overwrite.
    """
    if not os.path.exists(filepath):
        return False
    with open(filepath, encoding="utf-8") as f:
        content = f.read()
    first_line = content.split("\n")[0].strip()
    if first_line == GUIDE_MARKER:
        return False  # Has our auto-generated marker

    # Count comment lines that look like prose
    prose_count = 0
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("# ") and not line.startswith("## "):
            comment = line[2:]
            if len(comment) > 40 and "." in comment:
                prose_count += 1

    return prose_count >= 2


# ---------------------------------------------------------------------------
# Guide generation
# ---------------------------------------------------------------------------

def generate_guide(commands, responses=None, sound_prompt=False):
    """Generate guide text from commands and optional transcript responses."""
    lines = [GUIDE_MARKER, ""]
    current_room = None

    # If the game has a sound prompt, the first command answers it and has no
    # corresponding > prompt in the transcript. Offset responses by -1.
    resp_offset = -1 if sound_prompt else 0

    # Pre-scan for repeated sequences (combat, digging, waiting, etc.)
    repeated = find_repeated_sequences(commands)
    in_repeated = set()
    for start, (end, count) in repeated.items():
        for idx in range(start + 1, end + 1):
            in_repeated.add(idx)

    # Stage tracking (only for longer games)
    total_commands = len(commands)
    use_stages = total_commands >= 50
    stage_num = 0
    cmds_since_stage = 0
    rooms_visited = {}  # room name -> visit count
    stage_gap = max(15, total_commands // 8)

    if use_stages:
        stage_num = 1
        lines.append(f"## Stage {stage_num}")
        lines.append("")

    prev_had_content = False  # True when previous cmd had annotations/excerpt
    cmds_in_current_room = 0  # Commands emitted since last room header

    for i, cmd in enumerate(commands):
        resp_idx = i + resp_offset
        response = None
        if responses and 0 <= resp_idx < len(responses):
            response = responses[resp_idx]

        cmds_since_stage += 1

        # Detect room change
        room = detect_room_name(response) if response else None
        if room and room != current_room:
            # Stage break: returning to a hub room after enough commands
            if use_stages:
                visit_count = rooms_visited.get(room, 0)
                if visit_count >= 3 and cmds_since_stage >= stage_gap:
                    stage_num += 1
                    cmds_since_stage = 0
                    lines.append("")
                    lines.append(f"## Stage {stage_num}")

            if lines and lines[-1] != "":
                lines.append("")
            lines.append(f"## {room}")
            lines.append("")
            rooms_visited[room] = rooms_visited.get(room, 0) + 1
            current_room = room
            prev_had_content = False
            cmds_in_current_room = 0

        cmds_in_current_room += 1

        # Build annotations for this command
        annotations = []
        taken = None

        # Repeated sequence start annotation
        if i in repeated:
            _, count = repeated[i]
            if is_combat_command(cmd):
                target = extract_combat_target(cmd)
                annotations.append(f"Combat: {target} ({count} attempts)")
            else:
                annotations.append(f"Repeat: {cmd} ({count} times)")

        # Annotations for non-repeated commands (skip interior of sequences)
        if i not in in_repeated:
            # Item pickup
            taken = detect_taken(response, cmd)
            if taken:
                annotations.append(f"Pick up the {taken}")

            # Unlock / open
            unlock_notes = detect_unlock_open(response, cmd)
            annotations.extend(unlock_notes)

            # Container interaction
            container = detect_container_put(cmd)
            if container:
                annotations.append(f"Store the {container[0]} in the {container[1]}")

            # NPC interaction
            npc = detect_npc_interaction(cmd)
            if npc:
                annotations.append(npc)

        # Score / death / win events (always detected, even in sequences)
        if response:
            events = detect_events(response)
            annotations.extend(events)

        # Extract response excerpt (skip interior of repeated sequences)
        excerpt_lines = []
        if i not in in_repeated and response:
            excerpt_lines = extract_response_excerpt(
                response, room, taken is not None
            )

        has_content = bool(annotations or excerpt_lines)

        # Insert blank line when transitioning from plain navigation to
        # annotated/excerpted action within the same room
        if has_content and not prev_had_content and cmds_in_current_room > 1:
            if lines and lines[-1] != "":
                lines.append("")

        # Emit annotations before the command
        for ann in annotations:
            lines.append(f"# {ann}")

        # Emit excerpt after annotations, before command
        for exc in excerpt_lines:
            lines.append(exc)

        # Output command
        lines.append(f"> {cmd}")

        prev_had_content = has_content

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(
        description="Generate walkthrough-guide.txt from walkthrough + transcript"
    )
    parser.add_argument(
        "--walkthrough", required=True,
        help="Path to walkthrough.txt (one command per line)"
    )
    parser.add_argument(
        "--transcript",
        help="Path to walkthrough_output.txt (game transcript)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output path (default: stdout)"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Overwrite even if output file appears hand-written"
    )
    args = parser.parse_args()

    # Check for hand-written guide
    if args.output and not args.force and is_hand_written(args.output):
        print(f"Skipping {args.output} -- appears to be a hand-written guide. "
              f"Use --force to overwrite.", file=sys.stderr)
        sys.exit(0)

    # Read commands
    with open(args.walkthrough, encoding="utf-8") as f:
        commands = [line.strip() for line in f if line.strip()]

    # Parse transcript if provided
    responses = None
    sound_prompt = False
    if args.transcript:
        preamble, responses = parse_transcript(args.transcript)
        sound_prompt = has_sound_prompt(preamble)
        if sound_prompt:
            print("Detected sound prompt -- offsetting command/response alignment", file=sys.stderr)

    # Generate guide
    guide = generate_guide(commands, responses, sound_prompt=sound_prompt)

    # Output
    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="\n") as f:
            f.write(guide)
        print(f"Guide written to {args.output} ({len(commands)} commands)", file=sys.stderr)
    else:
        print(guide, end="")


if __name__ == "__main__":
    main()
