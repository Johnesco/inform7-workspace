#!/usr/bin/env python3
"""Game Explorer — tree-based interactive fiction exploration tool.

Builds an exploration tree by running commands through glulxe and recording
responses. Supports manual exploration (one command at a time) and automated
BFS/priority-based exploration.

The tree is stored as a flat node table in exploration.json alongside the
game files. Each path from root to leaf is a complete command sequence that
can be replayed to reach that game state.

Usage:
    python tools/explore.py init --game <name>
    python tools/explore.py try --game <name> --node <id> --command "take key"
    python tools/explore.py try-many --game <name> --node <id> --commands "n,s,e,w"
    python tools/explore.py show --game <name> [--node <id>] [--depth N]
    python tools/explore.py status --game <name>
    python tools/explore.py frontier --game <name> [--limit N]
    python tools/explore.py path --game <name> --node <id>
    python tools/explore.py auto --game <name> [--max-nodes N] [--strategy bfs|rooms-first]
    python tools/explore.py export --game <name> --node <id> [-o walkthrough.txt]

Stdlib only — no pip dependencies.
"""

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

# ---------------------------------------------------------------------------
# Path resolution (same pattern as run.py)
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
I7_ROOT = os.path.dirname(SCRIPT_DIR)
PROJECTS_DIR = I7_ROOT  # games are direct children of the workspace
TESTING_DIR = SCRIPT_DIR
INTERPRETERS_DIR = os.path.join(SCRIPT_DIR, "interpreters")


def to_posix(path: str) -> str:
    """Convert a Windows path to MSYS2/Git Bash posix form."""
    path = path.replace("\\", "/")
    m = re.match(r"^([A-Za-z]):/", path)
    if m:
        path = "/" + m.group(1).lower() + "/" + path[3:]
    return path


def find_bash() -> str:
    """Return the path to a usable bash executable."""
    git_bash = r"C:\Program Files\Git\bin\bash.exe"
    if os.path.isfile(git_bash):
        return git_bash
    found = shutil.which("bash")
    if found:
        return found
    print("ERROR: Cannot find bash.", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Import generate-guide.py functions via importlib
# ---------------------------------------------------------------------------

def _load_guide_module():
    """Import generate-guide.py as a module at runtime."""
    guide_path = os.path.join(TESTING_DIR, "generate-guide.py")
    if not os.path.isfile(guide_path):
        print(f"ERROR: generate-guide.py not found at {guide_path}", file=sys.stderr)
        sys.exit(1)
    spec = importlib.util.spec_from_file_location("generate_guide", guide_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_guide = None


def guide():
    """Lazy-load and cache the generate-guide module."""
    global _guide
    if _guide is None:
        _guide = _load_guide_module()
    return _guide


# ---------------------------------------------------------------------------
# Project resolution
# ---------------------------------------------------------------------------

def resolve_project(game_name: str) -> dict:
    """Resolve game paths and interpreter config for a project.

    Returns dict with keys: project_dir, game_path, engine_path, seed_flag,
    seed, exploration_path.
    """
    project_dir = os.path.join(PROJECTS_DIR, game_name)
    if not os.path.isdir(project_dir):
        print(f"ERROR: Project not found: {project_dir}", file=sys.stderr)
        sys.exit(1)

    # Try to read config from project.conf
    conf_path = os.path.join(project_dir, "tests", "project.conf")
    engine_path = None
    seed_flag = "--rngseed"
    game_path = None
    seed = None

    if os.path.isfile(conf_path):
        # Parse project.conf for key fields
        engine_path, game_path, seed = _parse_conf_for_explore(conf_path, project_dir)

    # Fallback: native glulxe.exe + <game>.ulx
    if not engine_path:
        native = os.path.join(INTERPRETERS_DIR, "glulxe.exe")
        if os.path.isfile(native):
            engine_path = native
        else:
            print("ERROR: No interpreter found. Build with tools/interpreters/build.sh",
                  file=sys.stderr)
            sys.exit(1)

    if not game_path:
        ulx = os.path.join(project_dir, f"{game_name}.ulx")
        gblorb = os.path.join(project_dir, f"{game_name}.gblorb")
        if os.path.isfile(gblorb):
            game_path = gblorb
        elif os.path.isfile(ulx):
            game_path = ulx
        else:
            print(f"ERROR: No game binary found in {project_dir}", file=sys.stderr)
            sys.exit(1)

    if not seed:
        seed = _get_golden_seed(project_dir)

    exploration_path = os.path.join(project_dir, "exploration.json")

    return {
        "project_dir": project_dir,
        "game_path": game_path,
        "engine_path": engine_path,
        "seed_flag": seed_flag,
        "seed": seed,
        "exploration_path": exploration_path,
    }


def _parse_conf_for_explore(conf_path: str, project_dir: str) -> tuple:
    """Extract engine/game paths from project.conf via bash sourcing."""
    bash = find_bash()
    # Source the config and echo the values we need
    script = f'''
        export PROJECT_DIR="{to_posix(project_dir)}"
        source "{to_posix(conf_path)}"
        echo "$PRIMARY_ENGINE_PATH"
        echo "$PRIMARY_GAME_PATH"
    '''
    try:
        result = subprocess.run(
            [bash, "-c", script],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            engine = lines[0].strip() if len(lines) > 0 else ""
            game = lines[1].strip() if len(lines) > 1 else ""
            # Convert posix paths back to native if needed
            if engine and os.path.isfile(engine):
                return engine, game if game and os.path.isfile(game) else None, None
    except (subprocess.TimeoutExpired, OSError):
        pass
    return None, None, None


def _get_golden_seed(project_dir: str) -> str | None:
    """Read the first glulxe seed from tests/seeds.conf."""
    seeds_path = os.path.join(project_dir, "tests", "seeds.conf")
    try:
        with open(seeds_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("glulxe:"):
                    parts = line.split(":")
                    if len(parts) >= 2:
                        return parts[1]
    except OSError:
        pass
    return None


# ---------------------------------------------------------------------------
# Node data structure
# ---------------------------------------------------------------------------

@dataclass
class Node:
    id: str                                 # "root", "n1", "n2", ...
    command: Optional[str] = None           # None for root
    response: str = ""                      # full response text
    excerpt: str = ""                       # filtered excerpt for display
    room: Optional[str] = None              # detected room name
    score: int = 0                          # cumulative score
    events: list = field(default_factory=list)     # ["+2 points", "DEATH", ...]
    fingerprint: str = ""                   # "entrance-hall_0pts"
    parent: Optional[str] = None            # parent node ID
    children: list = field(default_factory=list)   # child node IDs
    status: str = "frontier"                # explored | frontier | error | terminal | loop
    depth: int = 0                          # 0 for root
    interest: float = 0.0                   # priority score for frontier ordering

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Node":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


def make_fingerprint(room: str | None, score: int) -> str:
    """Create a lightweight state fingerprint from room + score."""
    room_slug = re.sub(r"[^a-z0-9]+", "-", (room or "unknown").lower()).strip("-")
    return f"{room_slug}_{score}pts"


# ---------------------------------------------------------------------------
# Exploration tree
# ---------------------------------------------------------------------------

class ExplorationTree:
    """Flat node table with parent/children references."""

    def __init__(self):
        self.nodes: dict[str, Node] = {}
        self.next_id: int = 1
        self.meta: dict = {}

    def new_id(self) -> str:
        nid = f"n{self.next_id}"
        self.next_id += 1
        return nid

    def add_node(self, node: Node):
        self.nodes[node.id] = node
        if node.parent and node.parent in self.nodes:
            parent = self.nodes[node.parent]
            if node.id not in parent.children:
                parent.children.append(node.id)

    def get_path(self, node_id: str) -> list[Node]:
        """Return the list of nodes from root to node_id (inclusive)."""
        path = []
        nid = node_id
        while nid is not None:
            if nid not in self.nodes:
                break
            path.append(self.nodes[nid])
            nid = self.nodes[nid].parent
        path.reverse()
        return path

    def get_commands(self, node_id: str) -> list[str]:
        """Return the command sequence from root to node_id."""
        path = self.get_path(node_id)
        return [n.command for n in path if n.command is not None]

    def get_frontier(self) -> list[Node]:
        """Return all frontier nodes sorted by interest (descending)."""
        frontier = [n for n in self.nodes.values() if n.status == "frontier"]
        frontier.sort(key=lambda n: n.interest, reverse=True)
        return frontier

    def check_loop(self, node_id: str, fingerprint: str) -> bool:
        """Check if fingerprint matches any ancestor (loop detection)."""
        path = self.get_path(node_id)
        # Check ancestors (not including self)
        for ancestor in path[:-1]:
            if ancestor.fingerprint == fingerprint:
                return True
        return False

    def check_convergence(self, fingerprint: str, exclude_id: str) -> str | None:
        """Check if fingerprint matches any non-ancestor node (convergence)."""
        for node in self.nodes.values():
            if node.id != exclude_id and node.fingerprint == fingerprint:
                return node.id
        return None

    def save(self, path: str):
        """Atomic write to JSON file."""
        data = {
            "meta": self.meta,
            "next_id": self.next_id,
            "nodes": {nid: node.to_dict() for nid, node in self.nodes.items()},
        }
        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        # Atomic rename (works on Windows if target doesn't exist)
        if os.path.exists(path):
            os.remove(path)
        os.rename(tmp_path, path)

    @classmethod
    def load(cls, path: str) -> "ExplorationTree":
        """Load tree from JSON file."""
        if not os.path.isfile(path):
            print(f"ERROR: No exploration tree at {path}", file=sys.stderr)
            print("Run 'explore.py init --game <name>' first.", file=sys.stderr)
            sys.exit(1)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        tree = cls()
        tree.meta = data.get("meta", {})
        tree.next_id = data.get("next_id", 1)
        for nid, nd in data.get("nodes", {}).items():
            tree.nodes[nid] = Node.from_dict(nd)
        return tree


# ---------------------------------------------------------------------------
# Interpreter invocation
# ---------------------------------------------------------------------------

def run_game(config: dict, commands: list[str]) -> str:
    """Run a list of commands through the interpreter and return output.

    Returns the full stdout output from the interpreter.
    """
    engine = config["engine_path"]
    game = config["game_path"]
    seed = config.get("seed")
    seed_flag = config.get("seed_flag", "--rngseed")

    cmd_list = [engine]
    if seed:
        cmd_list.extend([seed_flag, str(seed)])
    cmd_list.extend(["-q", game])

    # Write commands to a temp file
    input_text = "\n".join(commands) + "\n"

    try:
        result = subprocess.run(
            cmd_list,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        return "[TIMEOUT: interpreter did not respond within 30 seconds]"
    except OSError as e:
        print(f"ERROR: Failed to run interpreter: {e}", file=sys.stderr)
        sys.exit(1)


def run_and_get_last_response(config: dict, commands: list[str]) -> tuple[str, str]:
    """Run commands and return (full_output, last_response).

    The last response is the text after the final > prompt.
    """
    output = run_game(config, commands)
    g = guide()
    preamble, responses = g.parse_transcript(output, from_string=True) \
        if hasattr(g, 'parse_transcript') and 'from_string' in g.parse_transcript.__code__.co_varnames \
        else _parse_transcript_from_string(output)
    last = responses[-1] if responses else preamble
    return output, last


def _parse_transcript_from_string(text: str) -> tuple[str, list[str]]:
    """Parse transcript text into (preamble, responses).

    Same logic as generate-guide's parse_transcript but from a string
    instead of a file.
    """
    parts = re.split(r"^>", text, flags=re.MULTILINE)
    preamble = parts[0] if parts else ""
    responses = [part.strip() for part in parts[1:]]
    return preamble, responses


def run_for_node(config: dict, tree: ExplorationTree,
                 parent_id: str, new_command: str) -> tuple[str, list[str]]:
    """Replay path to parent + new command, return (last_response, all_responses).

    Returns the final response text and the list of all responses.
    """
    # Build full command sequence: path to parent + new command
    path_commands = tree.get_commands(parent_id)
    all_commands = path_commands + [new_command]

    output = run_game(config, all_commands)
    preamble, responses = _parse_transcript_from_string(output)

    # Account for sound prompt offset
    g = guide()
    sound_offset = 1 if g.has_sound_prompt(preamble) else 0

    # The last response corresponds to new_command
    expected_idx = len(all_commands) - 1 - sound_offset
    if 0 <= expected_idx < len(responses):
        last_response = responses[expected_idx]
    elif responses:
        last_response = responses[-1]
    else:
        last_response = preamble

    return last_response, responses


# ---------------------------------------------------------------------------
# Object and command extraction from response text
# ---------------------------------------------------------------------------

# Patterns to extract visible objects from room descriptions
OBJECT_PATTERNS = [
    re.compile(r"You can (?:also )?see (.*?)(?:\.|here)", re.IGNORECASE),
    re.compile(r"On the (.+?) (?:is|are) (.+?)\."),
    re.compile(r"In the (.+?) (?:is|are) (.+?)\."),
]


def extract_objects(response: str) -> list[str]:
    """Extract visible object names from a game response."""
    objects = []
    for pat in OBJECT_PATTERNS:
        for match in pat.finditer(response):
            # Split on commas and "and" to get individual items
            text = match.group(match.lastindex)
            items = re.split(r",\s*(?:and\s+)?|\s+and\s+", text)
            for item in items:
                item = item.strip().rstrip(".")
                # Remove articles
                item = re.sub(r"^(?:a|an|the|some)\s+", "", item, flags=re.IGNORECASE)
                if item and len(item) < 50:
                    objects.append(item)
    return objects


# Additional error patterns for exploration (beyond generate-guide's set)
# These catch custom game responses that indicate failed/no-op commands
EXPLORE_ERROR_PATTERNS = [
    re.compile(r"no passage in that direction", re.IGNORECASE),
    re.compile(r"nothing happens", re.IGNORECASE),
    re.compile(r"no exit that way", re.IGNORECASE),
    re.compile(r"can't go that way", re.IGNORECASE),
    re.compile(r"you see nothing special", re.IGNORECASE),
    re.compile(r"you don't find anything", re.IGNORECASE),
    re.compile(r"there's no way to go", re.IGNORECASE),
    re.compile(r"that doesn't seem to", re.IGNORECASE),
    re.compile(r"you aren't in anything", re.IGNORECASE),
    re.compile(r"there is no way (down|up)", re.IGNORECASE),
    re.compile(r"you are carrying nothing", re.IGNORECASE),
    re.compile(r"I beg your pardon", re.IGNORECASE),
]


# Standard navigation commands
NAV_COMMANDS = ["n", "s", "e", "w", "ne", "nw", "se", "sw", "up", "down", "in", "out"]


def generate_explore_commands(response: str) -> list[str]:
    """Generate commands to try at a frontier node based on its response.

    Priority: navigation > observation > manipulation.
    """
    commands = []

    # 1. Navigation (always try all directions)
    commands.extend(NAV_COMMANDS)

    # 2. Observation
    commands.extend(["look", "inventory"])

    # 3. Object-specific commands
    objects = extract_objects(response)
    for obj in objects:
        commands.append(f"examine {obj}")
        commands.append(f"take {obj}")

    return commands


# ---------------------------------------------------------------------------
# Interest scoring
# ---------------------------------------------------------------------------

def compute_interest(node: Node, parent: Node | None) -> float:
    """Compute interest score for a frontier node."""
    score = 0.0

    # New room discovery
    if parent and node.room and node.room != parent.room:
        score += 10.0

    # Score increase
    if parent:
        delta = node.score - parent.score
        if delta > 0:
            score += 5.0 * delta

    # Item taken
    if any("Pick up" in e or "Taken" in e for e in node.events):
        score += 3.0

    # Same room as parent (less interesting)
    if parent and node.room == parent.room:
        score -= 2.0

    # Depth penalty (deep nodes less interesting)
    if node.depth > 30:
        score -= float(node.depth - 30)

    return score


# ---------------------------------------------------------------------------
# Subcommand implementations
# ---------------------------------------------------------------------------

def cmd_init(args, config: dict):
    """Initialize exploration tree with root node from game preamble."""
    exploration_path = config["exploration_path"]

    if os.path.isfile(exploration_path) and not args.force:
        print(f"Exploration tree already exists: {exploration_path}")
        print("Use --force to reinitialize.")
        return

    # Run game with no commands to get the opening
    output = run_game(config, [])
    preamble, responses = _parse_transcript_from_string(output)

    g = guide()

    # Detect room from preamble. The preamble has a banner section
    # (title, subtitle, release, description) then blank line then the
    # room heading + description. Split on double-newline to skip banner.
    room = None
    if preamble:
        # Split on blank lines — room description is after the banner block
        blocks = re.split(r"\n\s*\n", preamble.strip())
        if len(blocks) >= 2:
            # Try each post-banner block for a room name
            for block in blocks[1:]:
                room = g.detect_room_name(block.strip())
                if room:
                    break

    # Fallback: try first response
    if not room and responses:
        room = g.detect_room_name(responses[0])

    fingerprint = make_fingerprint(room, 0)

    # Build excerpt from preamble
    excerpt = ""
    preamble_lines = [l.strip() for l in preamble.split("\n") if l.strip()]
    if len(preamble_lines) > 3:
        # Skip banner lines, take description
        excerpt = " ".join(preamble_lines[3:])[:150]

    root = Node(
        id="root",
        command=None,
        response=preamble + ("\n\n" + responses[0] if responses else ""),
        excerpt=excerpt,
        room=room,
        score=0,
        events=[],
        fingerprint=fingerprint,
        parent=None,
        children=[],
        status="frontier",
        depth=0,
        interest=10.0,
    )

    tree = ExplorationTree()
    tree.meta = {
        "game": args.game,
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "engine": os.path.basename(config["engine_path"]),
        "seed": config.get("seed"),
    }
    tree.add_node(root)
    tree.save(exploration_path)

    print(f"Initialized exploration tree: {exploration_path}")
    print(f"  Room: {room or '(unknown)'}")
    print(f"  Root node: root (status=frontier)")
    if excerpt:
        print(f"  {excerpt[:80]}...")


def cmd_try(args, config: dict):
    """Try a command from a specific node, adding the result as a child."""
    tree = ExplorationTree.load(config["exploration_path"])
    parent_id = args.node
    command = args.command

    if parent_id not in tree.nodes:
        print(f"ERROR: Node '{parent_id}' not found", file=sys.stderr)
        sys.exit(1)

    parent = tree.nodes[parent_id]

    # Check if this command was already tried from this node
    for child_id in parent.children:
        child = tree.nodes[child_id]
        if child.command and child.command.lower() == command.lower():
            print(f"Command '{command}' already tried from {parent_id} -> {child_id}")
            print(f"  Room: {child.room or '(same)'}, Status: {child.status}")
            return

    # Run the command
    last_response, all_responses = run_for_node(config, tree, parent_id, command)

    # Analyze the response
    node = _build_node(tree, parent, command, last_response)
    tree.add_node(node)

    # Mark parent as explored if it was frontier
    if parent.status == "frontier":
        parent.status = "explored"

    tree.save(config["exploration_path"])

    # Report
    status_icon = {"explored": "+", "frontier": "?", "error": "!", "terminal": "X", "loop": "~"}
    icon = status_icon.get(node.status, " ")
    print(f"[{icon}] {node.id}: {command}")
    if node.room and node.room != parent.room:
        print(f"    Room: {node.room}")
    if node.events:
        print(f"    Events: {', '.join(node.events)}")
    if node.excerpt:
        print(f"    {node.excerpt[:80]}")
    print(f"    Status: {node.status}, Depth: {node.depth}, Interest: {node.interest:.1f}")


def _build_node(tree: ExplorationTree, parent: Node, command: str,
                response: str) -> Node:
    """Analyze a response and create a new node."""
    g = guide()

    # Detect room
    room = g.detect_room_name(response) if response else None
    if not room:
        room = parent.room  # Same room

    # Detect events
    events = g.detect_events(response) if response else []

    # Calculate cumulative score
    score = parent.score
    for evt in events:
        m = re.match(r"([+-])(\d+) points", evt)
        if m:
            delta = int(m.group(2))
            if m.group(1) == "+":
                score += delta
            else:
                score -= delta

    fingerprint = make_fingerprint(room, score)
    depth = parent.depth + 1

    # Determine status
    status = "frontier"

    # Check for error responses (guide patterns + explore-specific patterns)
    all_error_pats = list(guide().ERROR_PATTERNS) + EXPLORE_ERROR_PATTERNS
    for pat in all_error_pats:
        if pat.search(response):
            status = "error"
            break

    # Check for terminal states (death, win)
    if any("DEATH" in e for e in events):
        status = "terminal"
    elif any("GAME WON" in e for e in events):
        status = "terminal"

    # Check for loops (same fingerprint as ancestor)
    if status == "frontier" and tree.check_loop(parent.id, fingerprint):
        status = "loop"

    # Extract excerpt
    taken = g.detect_taken(response, command) if response else None
    excerpt_lines = g.extract_response_excerpt(response, room if room != parent.room else None,
                                                taken is not None) if response else []
    excerpt = ""
    if excerpt_lines:
        # Strip the "# " prefix from wrap_excerpt output
        excerpt = " ".join(line.lstrip("# ").strip() for line in excerpt_lines)

    nid = tree.new_id()
    node = Node(
        id=nid,
        command=command,
        response=response,
        excerpt=excerpt,
        room=room,
        score=score,
        events=list(events),
        fingerprint=fingerprint,
        parent=parent.id,
        children=[],
        status=status,
        depth=depth,
        interest=0.0,
    )
    node.interest = compute_interest(node, parent)

    return node


def cmd_try_many(args, config: dict):
    """Try multiple commands from a single node."""
    tree = ExplorationTree.load(config["exploration_path"])
    parent_id = args.node

    if parent_id not in tree.nodes:
        print(f"ERROR: Node '{parent_id}' not found", file=sys.stderr)
        sys.exit(1)

    commands = [c.strip() for c in args.commands.split(",") if c.strip()]
    if not commands:
        print("ERROR: No commands provided", file=sys.stderr)
        sys.exit(1)

    parent = tree.nodes[parent_id]
    added = 0
    skipped = 0

    for command in commands:
        # Check if already tried
        already = False
        for child_id in parent.children:
            child = tree.nodes[child_id]
            if child.command and child.command.lower() == command.lower():
                already = True
                break
        if already:
            skipped += 1
            continue

        # Run the command
        last_response, _ = run_for_node(config, tree, parent_id, command)
        node = _build_node(tree, parent, command, last_response)
        tree.add_node(node)
        added += 1

        # Brief report
        status_icon = {"explored": "+", "frontier": "?", "error": "!", "terminal": "X", "loop": "~"}
        icon = status_icon.get(node.status, " ")
        room_info = f" -> {node.room}" if node.room and node.room != parent.room else ""
        print(f"  [{icon}] {node.id}: {command}{room_info}")

    # Mark parent as explored
    if parent.status == "frontier":
        parent.status = "explored"

    tree.save(config["exploration_path"])
    print(f"\nAdded {added} nodes, skipped {skipped} duplicates")


def cmd_show(args, config: dict):
    """Show ASCII tree visualization."""
    tree = ExplorationTree.load(config["exploration_path"])
    root_id = args.node or "root"
    max_depth = args.depth

    if root_id not in tree.nodes:
        print(f"ERROR: Node '{root_id}' not found", file=sys.stderr)
        sys.exit(1)

    _print_tree(tree, root_id, max_depth)


def _print_tree(tree: ExplorationTree, node_id: str, max_depth: int | None,
                prefix: str = "", is_last: bool = True, current_depth: int = 0):
    """Recursively print tree in ASCII format."""
    if max_depth is not None and current_depth > max_depth:
        return

    node = tree.nodes[node_id]
    status_icon = {
        "explored": "+", "frontier": "?", "error": "!",
        "terminal": "X", "loop": "~",
    }
    icon = status_icon.get(node.status, " ")

    # Build the display line
    if node.id == "root":
        connector = ""
        child_prefix = ""
    else:
        connector = "`-- " if is_last else "|-- "
        child_prefix = "    " if is_last else "|   "

    cmd = node.command or "(start)"
    room_info = f" [{node.room}]" if node.room else ""
    score_info = f" {node.score}pts" if node.score > 0 else ""
    event_info = ""
    if node.events:
        event_info = f" ({', '.join(node.events)})"

    line = f"{prefix}{connector}[{icon}] {node.id}: {cmd}{room_info}{score_info}{event_info}"
    print(line)

    # Print children
    children = [tree.nodes[cid] for cid in node.children if cid in tree.nodes]
    for i, child in enumerate(children):
        is_last_child = (i == len(children) - 1)
        _print_tree(tree, child.id, max_depth,
                    prefix + child_prefix, is_last_child, current_depth + 1)


def cmd_status(args, config: dict):
    """Show exploration statistics."""
    tree = ExplorationTree.load(config["exploration_path"])

    total = len(tree.nodes)
    statuses = {}
    rooms = set()
    max_depth = 0
    min_score = 0
    max_score = 0

    for node in tree.nodes.values():
        statuses[node.status] = statuses.get(node.status, 0) + 1
        if node.room:
            rooms.add(node.room)
        max_depth = max(max_depth, node.depth)
        min_score = min(min_score, node.score)
        max_score = max(max_score, node.score)

    print(f"Game: {tree.meta.get('game', '?')}")
    print(f"Created: {tree.meta.get('created', '?')}")
    print(f"Engine: {tree.meta.get('engine', '?')}, Seed: {tree.meta.get('seed', 'none')}")
    print()
    print(f"Total nodes: {total}")
    for status, count in sorted(statuses.items()):
        print(f"  {status}: {count}")
    print(f"Rooms discovered: {len(rooms)}")
    if rooms:
        for room in sorted(rooms):
            print(f"  - {room}")
    print(f"Max depth: {max_depth}")
    print(f"Score range: {min_score} - {max_score}")


def cmd_frontier(args, config: dict):
    """List frontier nodes ranked by interest."""
    tree = ExplorationTree.load(config["exploration_path"])
    frontier = tree.get_frontier()
    limit = args.limit or len(frontier)

    if not frontier:
        print("No frontier nodes — exploration is complete.")
        return

    print(f"Frontier nodes ({len(frontier)} total, showing {min(limit, len(frontier))}):")
    print()
    for node in frontier[:limit]:
        room_info = f" [{node.room}]" if node.room else ""
        path_cmds = tree.get_commands(node.id)
        path_str = " > ".join(path_cmds[-3:]) if path_cmds else "(root)"
        if len(path_cmds) > 3:
            path_str = "... > " + path_str
        print(f"  {node.id}: interest={node.interest:.1f}, depth={node.depth}{room_info}")
        print(f"    Path: {path_str}")
        if node.excerpt:
            print(f"    {node.excerpt[:70]}")
        print()


def cmd_path(args, config: dict):
    """Print command sequence from root to node."""
    tree = ExplorationTree.load(config["exploration_path"])
    node_id = args.node

    if node_id not in tree.nodes:
        print(f"ERROR: Node '{node_id}' not found", file=sys.stderr)
        sys.exit(1)

    commands = tree.get_commands(node_id)
    if not commands:
        print("(root node — no commands)")
        return

    for cmd in commands:
        print(cmd)


def cmd_auto(args, config: dict):
    """Automated exploration using BFS or rooms-first strategy."""
    tree = ExplorationTree.load(config["exploration_path"])
    max_nodes = args.max_nodes
    strategy = args.strategy
    added = 0
    rooms_found = set()
    errors = 0

    # Collect existing rooms
    for node in tree.nodes.values():
        if node.room:
            rooms_found.add(node.room)

    print(f"Auto-exploring {args.game} (strategy={strategy}, max={max_nodes})")
    print(f"Starting with {len(tree.nodes)} nodes, {len(rooms_found)} rooms")
    print()

    while added < max_nodes:
        # Pick next node to explore
        frontier = tree.get_frontier()
        if not frontier:
            print("No more frontier nodes — exploration complete.")
            break

        if strategy == "rooms-first":
            # Prioritize nodes that might discover new rooms
            frontier.sort(key=lambda n: n.interest, reverse=True)

        target = frontier[0]

        # Generate commands to try
        commands = generate_explore_commands(target.response)

        # Filter out already-tried commands
        tried = set()
        for child_id in target.children:
            if child_id in tree.nodes:
                child = tree.nodes[child_id]
                if child.command:
                    tried.add(child.command.lower())
        commands = [c for c in commands if c.lower() not in tried]

        if not commands:
            # No more commands to try — mark as explored
            target.status = "explored"
            tree.save(config["exploration_path"])
            continue

        # Try each command
        for command in commands:
            if added >= max_nodes:
                break

            try:
                last_response, _ = run_for_node(config, tree, target.id, command)
            except Exception as e:
                print(f"  ERROR running '{command}': {e}", file=sys.stderr)
                errors += 1
                continue

            node = _build_node(tree, target, command, last_response)
            tree.add_node(node)
            added += 1

            # Track new room discoveries
            new_room = ""
            if node.room and node.room not in rooms_found:
                rooms_found.add(node.room)
                new_room = f" ** NEW ROOM: {node.room} **"

            # Progress report
            status_icon = {"explored": "+", "frontier": "?", "error": "!", "terminal": "X", "loop": "~"}
            icon = status_icon.get(node.status, " ")
            print(f"  [{icon}] {node.id}: {command} -> {node.room or '?'}{new_room}")

            if node.events:
                print(f"       Events: {', '.join(node.events)}")

        # Mark target as explored
        target.status = "explored"
        tree.save(config["exploration_path"])

    # Final summary
    tree.save(config["exploration_path"])
    print()
    print(f"Added {added} nodes ({errors} errors)")
    print(f"Total: {len(tree.nodes)} nodes, {len(rooms_found)} rooms")


def cmd_serve(args, config: dict):
    """Serve the exploration viewer in a browser."""
    import http.server
    import webbrowser

    viewer_path = os.path.join(SCRIPT_DIR, "explore-viewer.html")
    data_path = config["exploration_path"]
    port = args.port

    if not os.path.isfile(viewer_path):
        print(f"ERROR: Viewer not found: {viewer_path}", file=sys.stderr)
        sys.exit(1)
    if not os.path.isfile(data_path):
        print(f"ERROR: No exploration data at {data_path}", file=sys.stderr)
        print("Run 'explore.py init --game <name>' first.", file=sys.stderr)
        sys.exit(1)

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/" or self.path == "/index.html":
                self._serve_file(viewer_path, "text/html; charset=utf-8")
            elif self.path == "/data.json":
                # Re-read on every request so live exploration updates appear
                self._serve_file(data_path, "application/json; charset=utf-8")
            else:
                self.send_error(404)

        def _serve_file(self, filepath, content_type):
            try:
                with open(filepath, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", len(content))
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(content)
            except OSError:
                self.send_error(404)

        def log_message(self, format, *args):
            pass  # Suppress request logging

    url = f"http://127.0.0.1:{port}"
    print(f"Serving exploration viewer at {url}")
    print(f"Data: {data_path}")
    print("Press Ctrl-C to stop.\n")

    server = http.server.HTTPServer(("127.0.0.1", port), Handler)
    webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


def cmd_export(args, config: dict):
    """Export path from root to node as a walkthrough file."""
    tree = ExplorationTree.load(config["exploration_path"])
    node_id = args.node

    if node_id not in tree.nodes:
        print(f"ERROR: Node '{node_id}' not found", file=sys.stderr)
        sys.exit(1)

    commands = tree.get_commands(node_id)
    if not commands:
        print("(root node — no commands to export)")
        return

    output = "\n".join(commands) + "\n"

    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="\n") as f:
            f.write(output)
        print(f"Exported {len(commands)} commands to {args.output}")
    else:
        sys.stdout.write(output)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Game Explorer — tree-based IF exploration tool"
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # --- init ---
    p_init = subparsers.add_parser("init", help="Initialize exploration tree")
    p_init.add_argument("--game", required=True, help="Game name (project folder)")
    p_init.add_argument("--force", action="store_true", help="Overwrite existing tree")
    p_init.add_argument("--seed", help="Override RNG seed")

    # --- try ---
    p_try = subparsers.add_parser("try", help="Try a command from a node")
    p_try.add_argument("--game", required=True)
    p_try.add_argument("--node", required=True, help="Parent node ID")
    p_try.add_argument("--command", required=True, help="Command to try")
    p_try.add_argument("--seed", help="Override RNG seed")

    # --- try-many ---
    p_try_many = subparsers.add_parser("try-many", help="Try multiple commands from a node")
    p_try_many.add_argument("--game", required=True)
    p_try_many.add_argument("--node", required=True, help="Parent node ID")
    p_try_many.add_argument("--commands", required=True, help="Comma-separated commands")
    p_try_many.add_argument("--seed", help="Override RNG seed")

    # --- show ---
    p_show = subparsers.add_parser("show", help="Show tree visualization")
    p_show.add_argument("--game", required=True)
    p_show.add_argument("--node", default=None, help="Root node for subtree (default: root)")
    p_show.add_argument("--depth", type=int, default=None, help="Max depth to display")

    # --- status ---
    p_status = subparsers.add_parser("status", help="Show exploration statistics")
    p_status.add_argument("--game", required=True)

    # --- frontier ---
    p_frontier = subparsers.add_parser("frontier", help="List frontier nodes")
    p_frontier.add_argument("--game", required=True)
    p_frontier.add_argument("--limit", type=int, default=None, help="Max nodes to show")

    # --- path ---
    p_path = subparsers.add_parser("path", help="Print command path to a node")
    p_path.add_argument("--game", required=True)
    p_path.add_argument("--node", required=True, help="Target node ID")

    # --- auto ---
    p_auto = subparsers.add_parser("auto", help="Automated exploration")
    p_auto.add_argument("--game", required=True)
    p_auto.add_argument("--max-nodes", type=int, default=50, help="Max nodes to add (default: 50)")
    p_auto.add_argument("--strategy", choices=["bfs", "rooms-first"], default="rooms-first",
                        help="Exploration strategy (default: rooms-first)")
    p_auto.add_argument("--seed", help="Override RNG seed")

    # --- serve ---
    p_serve = subparsers.add_parser("serve", help="Open exploration viewer in browser")
    p_serve.add_argument("--game", required=True)
    p_serve.add_argument("--port", type=int, default=8080, help="Server port (default: 8080)")

    # --- export ---
    p_export = subparsers.add_parser("export", help="Export path as walkthrough")
    p_export.add_argument("--game", required=True)
    p_export.add_argument("--node", required=True, help="Target node ID")
    p_export.add_argument("--output", "-o", help="Output file (default: stdout)")

    args = parser.parse_args()

    # Resolve project config
    config = resolve_project(args.game)

    # Apply seed override
    if hasattr(args, "seed") and args.seed:
        config["seed"] = args.seed

    # Dispatch
    dispatch = {
        "init": cmd_init,
        "try": cmd_try,
        "try-many": cmd_try_many,
        "show": cmd_show,
        "status": cmd_status,
        "frontier": cmd_frontier,
        "path": cmd_path,
        "auto": cmd_auto,
        "serve": cmd_serve,
        "export": cmd_export,
    }

    dispatch[args.subcommand](args, config)


if __name__ == "__main__":
    main()
