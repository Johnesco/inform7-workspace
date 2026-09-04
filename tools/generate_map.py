#!/usr/bin/env python3
"""Generate an interactive map from walkthrough + transcript data.

Parses walkthrough commands and transcript responses to build a directed
room graph, lays it out on a grid, renders SVG, and produces an
interactive HTML map page.

Usage:
    python tools/generate_map.py <game> [options]

    Arguments:
        game                Project name (auto-finds walkthrough files)

    Options:
        --walkthrough PATH  Override walkthrough.txt path
        --transcript PATH   Override walkthrough_output.txt path
        --out PATH          Output directory (default: project root)
        --json-only         Only output map.json
        --disambiguate      Split same-name rooms into separate nodes (maze mode)
        --force             Overwrite existing files
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import paths
from lib.transcript import (
    DIRECTION_OFFSETS,
    DIRECTION_OPPOSITES,
    detect_preamble_room,
    detect_room_entry,
    has_sound_prompt,
    normalize_direction,
    parse_transcript,
)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class Room:
    id: str                     # slug: "west-of-house", "maze-1"
    name: str                   # display: "West of House"
    description: str = ""       # first-seen description text
    visits: int = 0
    x: int = 0                  # grid coordinate (set by layout)
    y: int = 0


@dataclass
class Edge:
    from_room: str              # room id
    to_room: str                # room id
    direction: str              # "n", "se", "u", "pray", etc.
    is_standard: bool = True    # False for teleport/non-compass moves
    bidirectional: bool = False # True only when reverse trip observed


@dataclass
class GameMap:
    title: str = ""
    rooms: dict = field(default_factory=dict)   # id -> Room
    edges: list = field(default_factory=list)    # list of Edge
    start_room: str = ""                        # id of first room


# ---------------------------------------------------------------------------
# Room ID generation
# ---------------------------------------------------------------------------


def slugify(name):
    """Convert a room name to a URL-safe slug."""
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s or "room"


# ---------------------------------------------------------------------------
# Parser: walkthrough + transcript → GameMap
# ---------------------------------------------------------------------------


def parse_map(commands, responses, preamble="", sound_prompt=False,
              disambiguate=False):
    """Parse walkthrough commands and transcript responses into a GameMap.

    Args:
        commands: List of walkthrough command strings.
        responses: List of transcript response strings.
        preamble: The transcript text before the first > prompt (banner area).
        sound_prompt: Whether the game has a sound prompt offset.
        disambiguate: If True, create separate nodes for same-name rooms
                      when reachable via different paths (maze mode).
                      Default False: same name = same room.

    Returns:
        A populated GameMap.
    """
    game_map = GameMap()
    resp_offset = -1 if sound_prompt else 0

    # Room tracking
    current_room = None         # Room object
    slug_counts = {}            # slug -> count (for generating unique IDs)
    name_desc_to_ids = {}       # (name, desc) -> [room_id, ...]
    edge_index = {}             # (room_id, direction) -> room_id
    seen_edges = set()          # (from_id, to_id, direction) for dedup

    def make_room_id(name, desc):
        """Generate a unique room ID, handling duplicates."""
        slug = slugify(name)
        key = (name, desc)

        if not disambiguate:
            # Collapse all same-name rooms
            key = (name, "")
            if key in name_desc_to_ids:
                return name_desc_to_ids[key][0]
            rid = slug
            slug_counts[slug] = slug_counts.get(slug, 0) + 1
            if slug_counts[slug] > 1:
                rid = f"{slug}-{slug_counts[slug]}"
            name_desc_to_ids[key] = [rid]
            return rid

        if key in name_desc_to_ids:
            # Exact match — return first (only split if disambiguation needed)
            return name_desc_to_ids[key][0]

        # Check if this slug already exists with different desc
        slug_counts[slug] = slug_counts.get(slug, 0) + 1
        if slug_counts[slug] == 1:
            rid = slug
        else:
            rid = f"{slug}-{slug_counts[slug]}"

        name_desc_to_ids[key] = [rid]
        return rid

    def find_or_create_room(name, desc, direction, from_room_id):
        """Find existing room or create new one, with maze disambiguation."""
        if disambiguate and from_room_id and direction:
            # Check if we've traveled this exact path before
            edge_key = (from_room_id, direction)
            if edge_key in edge_index:
                existing_id = edge_index[edge_key]
                if existing_id in game_map.rooms:
                    return existing_id

        rid = make_room_id(name, desc)
        if rid not in game_map.rooms:
            game_map.rooms[rid] = Room(id=rid, name=name, description=desc)
        return rid

    # Detect the starting room from the preamble (text before first > prompt).
    # The preamble contains the banner + the initial room description.
    if preamble:
        preamble_name, preamble_desc = detect_preamble_room(preamble)
        if preamble_name:
            rid = make_room_id(preamble_name, preamble_desc)
            game_map.rooms[rid] = Room(
                id=rid, name=preamble_name, description=preamble_desc, visits=1
            )
            game_map.start_room = rid
            current_room = game_map.rooms[rid]

    for i, cmd in enumerate(commands):
        resp_idx = i + resp_offset
        response = None
        if responses and 0 <= resp_idx < len(responses):
            response = responses[resp_idx]

        if response is None:
            continue

        # Detect room
        room_name, room_desc = detect_room_entry(response)

        if room_name is None:
            continue

        direction = normalize_direction(cmd)
        is_standard = direction is not None
        if direction is None:
            # Non-navigation command that moved us — record command as label
            direction = cmd.strip().lower()

        from_id = current_room.id if current_room else None
        room_id = find_or_create_room(room_name, room_desc, direction, from_id)
        room = game_map.rooms[room_id]
        room.visits += 1

        # Set start room
        if not game_map.start_room:
            game_map.start_room = room_id

        # Record edge (deduplicate by from/to/direction)
        if current_room and current_room.id != room_id:
            edge_key_dedup = (current_room.id, room_id, direction)
            if edge_key_dedup not in seen_edges:
                seen_edges.add(edge_key_dedup)
                edge = Edge(
                    from_room=current_room.id,
                    to_room=room_id,
                    direction=direction,
                    is_standard=is_standard,
                )
                game_map.edges.append(edge)
            if is_standard:
                edge_index[(current_room.id, direction)] = room_id

        current_room = room

    # Bidirectionality inference
    edge_set = {}
    for edge in game_map.edges:
        key = (edge.from_room, edge.to_room, edge.direction)
        edge_set[key] = edge

    for edge in game_map.edges:
        if not edge.is_standard:
            continue
        opposite = DIRECTION_OPPOSITES.get(edge.direction)
        if not opposite:
            continue
        reverse_key = (edge.to_room, edge.from_room, opposite)
        if reverse_key in edge_set:
            edge.bidirectional = True
            edge_set[reverse_key].bidirectional = True

    return game_map


# ---------------------------------------------------------------------------
# Layout engine: grid placement via BFS
# ---------------------------------------------------------------------------


def layout_map(game_map):
    """Assign (x, y) grid coordinates to all rooms.

    Departure direction determines placement:
      north/up → y-1 (up on screen), south/down → y+1 (down),
      east → x+1 (right), west → x-1 (left), diagonals accordingly.
    Arrival edges can come from any visual angle — only the departure
    direction from the source room matters for where the target is placed.
    """
    if not game_map.rooms:
        return

    # Build adjacency list (outgoing standard edges only for layout)
    adj = {}  # room_id -> [(target_id, direction), ...]
    for edge in game_map.edges:
        if edge.is_standard:
            adj.setdefault(edge.from_room, []).append((edge.to_room, edge.direction))

    occupied = {}  # (x, y) -> room_id
    placed = set()

    def find_open_cell(target_x, target_y, prefer_dx=0, prefer_dy=0):
        """Spiral search for nearest open cell, preferring given axis."""
        if (target_x, target_y) not in occupied:
            return target_x, target_y

        # Try doubling in the preferred direction first
        if prefer_dx or prefer_dy:
            px, py = target_x + prefer_dx, target_y + prefer_dy
            if (px, py) not in occupied:
                return px, py

        # Spiral outward
        for dist in range(1, 30):
            for ddx in range(-dist, dist + 1):
                for ddy in range(-dist, dist + 1):
                    if ddx == 0 and ddy == 0:
                        continue
                    cx, cy = target_x + ddx, target_y + ddy
                    if (cx, cy) not in occupied:
                        return cx, cy
        return target_x + 30, target_y

    # Place starting room at origin
    start_id = game_map.start_room
    if not start_id or start_id not in game_map.rooms:
        start_id = next(iter(game_map.rooms))

    game_map.rooms[start_id].x = 0
    game_map.rooms[start_id].y = 0
    occupied[(0, 0)] = start_id
    placed.add(start_id)

    # BFS — process rooms in walkthrough visit order
    queue = [start_id]
    visited_bfs = {start_id}

    while queue:
        room_id = queue.pop(0)
        room = game_map.rooms[room_id]

        for target_id, direction in adj.get(room_id, []):
            if target_id in placed:
                continue

            dx, dy = DIRECTION_OFFSETS.get(direction, (0, 0))

            if dx == 0 and dy == 0:
                # in/out — no spatial meaning; place to the right
                target_x, target_y = room.x + 1, room.y
            else:
                target_x = room.x + dx
                target_y = room.y + dy

            if (target_x, target_y) in occupied:
                target_x, target_y = find_open_cell(
                    target_x, target_y, dx, dy
                )

            r = game_map.rooms[target_id]
            r.x = target_x
            r.y = target_y
            occupied[(target_x, target_y)] = target_id
            placed.add(target_id)

            if target_id not in visited_bfs:
                visited_bfs.add(target_id)
                queue.append(target_id)

    # Place any rooms not reached by standard edges (teleport targets)
    for room_id in list(game_map.rooms.keys()):
        if room_id not in placed:
            nearest = None
            for edge in game_map.edges:
                if edge.to_room == room_id and edge.from_room in placed:
                    nearest = edge.from_room
                    break
                if edge.from_room == room_id and edge.to_room in placed:
                    nearest = edge.to_room
                    break

            if nearest:
                nr = game_map.rooms[nearest]
                tx, ty = find_open_cell(nr.x + 1, nr.y)
            else:
                tx, ty = find_open_cell(0, 0)

            game_map.rooms[room_id].x = tx
            game_map.rooms[room_id].y = ty
            occupied[(tx, ty)] = room_id
            placed.add(room_id)

    # Normalize so min x=0, min y=0
    if game_map.rooms:
        min_x = min(r.x for r in game_map.rooms.values())
        min_y = min(r.y for r in game_map.rooms.values())
        for r in game_map.rooms.values():
            r.x -= min_x
            r.y -= min_y


# ---------------------------------------------------------------------------
# SVG renderer
# ---------------------------------------------------------------------------

CELL_W = 160       # grid cell width (px)
CELL_H = 120       # grid cell height (px)
ROOM_W = 130       # room box width
ROOM_H = 44        # room box height
PAD = 60           # viewport padding


def _room_center(room):
    """Get the pixel center of a room."""
    cx = room.x * CELL_W + CELL_W // 2
    cy = room.y * CELL_H + CELL_H // 2
    return cx, cy


def _esc_xml(s):
    """Escape text for XML."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _truncate_label(name, max_chars=16):
    """Truncate a room name for the SVG label."""
    if len(name) <= max_chars:
        return name
    return name[:max_chars - 1] + "\u2026"


def render_svg(game_map):
    """Render the map as SVG markup (without <svg> wrapper — for embedding)."""
    if not game_map.rooms:
        return ""

    parts = []

    # Defs: arrowhead marker
    parts.append("""<defs>
  <marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5"
          markerWidth="8" markerHeight="6" orient="auto-start-reverse">
    <path d="M 0 0 L 10 5 L 0 10 z" fill="#776655"/>
  </marker>
  <marker id="arrow-hi" viewBox="0 0 10 10" refX="10" refY="5"
          markerWidth="8" markerHeight="6" orient="auto-start-reverse">
    <path d="M 0 0 L 10 5 L 0 10 z" fill="#e8d090"/>
  </marker>
</defs>""")

    # Collect room centers for edge drawing
    centers = {}
    for room in game_map.rooms.values():
        centers[room.id] = _room_center(room)

    # Draw edges first (behind rooms)
    seen_edges = set()
    for edge in game_map.edges:
        if edge.from_room not in centers or edge.to_room not in centers:
            continue

        # Skip duplicate edges (same from/to pair)
        edge_pair = (edge.from_room, edge.to_room)
        reverse_pair = (edge.to_room, edge.from_room)
        if edge_pair in seen_edges:
            continue
        if edge.bidirectional and reverse_pair in seen_edges:
            continue
        seen_edges.add(edge_pair)

        x1, y1 = centers[edge.from_room]
        x2, y2 = centers[edge.to_room]

        # Shorten lines to stop at room box edges
        dx = x2 - x1
        dy = y2 - y1
        dist = (dx * dx + dy * dy) ** 0.5
        if dist < 1:
            continue

        # Shorten from box boundary (approximate)
        shorten = ROOM_W // 2 + 4
        ratio = shorten / dist if dist > 0 else 0
        sx1 = x1 + dx * ratio
        sy1 = y1 + dy * ratio
        sx2 = x2 - dx * ratio
        sy2 = y2 - dy * ratio

        stroke = "#3a3520"
        dash = ""
        marker = ""
        label = ""

        if not edge.is_standard:
            # Teleport/non-compass
            dash = ' stroke-dasharray="6,4"'
            marker = ' marker-end="url(#arrow)"'
            label = edge.direction
        elif not edge.bidirectional:
            # One-way standard
            marker = ' marker-end="url(#arrow)"'
        # else: bidirectional — no arrowhead

        # Label for in/out edges
        if edge.direction in ("in", "out"):
            label = edge.direction

        # Detect if line needs to curve (when source and target are not
        # cardinally aligned — use a gentle bezier)
        needs_curve = abs(dx) > 20 and abs(dy) > 20 and (
            abs(dx) < CELL_W * 0.5 or abs(dy) < CELL_H * 0.5
        )

        data_attrs = f'data-from="{edge.from_room}" data-to="{edge.to_room}"'

        if needs_curve:
            # Quadratic bezier with control point offset
            cpx = (sx1 + sx2) / 2 + dy * 0.15
            cpy = (sy1 + sy2) / 2 - dx * 0.15
            parts.append(
                f'<path d="M {sx1},{sy1} Q {cpx},{cpy} {sx2},{sy2}" '
                f'fill="none" stroke="{stroke}" stroke-width="1.5"{dash}{marker} '
                f'class="edge-line" {data_attrs}/>'
            )
        else:
            parts.append(
                f'<line x1="{sx1}" y1="{sy1}" x2="{sx2}" y2="{sy2}" '
                f'stroke="{stroke}" stroke-width="1.5"{dash}{marker} '
                f'class="edge-line" {data_attrs}/>'
            )

        # Direction label for teleport/in/out
        if label:
            mx = (sx1 + sx2) / 2
            my = (sy1 + sy2) / 2 - 12
            parts.append(
                f'<text x="{mx}" y="{my}" text-anchor="middle" '
                f'fill="#665544" font-family="sans-serif" font-size="10" '
                f'font-style="italic">{_esc_xml(label)}</text>'
            )

    # Draw rooms
    for room in game_map.rooms.values():
        cx, cy = centers[room.id]
        rx = cx - ROOM_W // 2
        ry = cy - ROOM_H // 2

        is_start = room.id == game_map.start_room
        fill = "#1a1810" if is_start else "#141210"
        stroke = "#8bab6e" if is_start else "#3a3520"
        stroke_w = "1.5" if is_start else "1"
        text_fill = "#e8d8b0" if is_start else "#c4b48a"

        label = _truncate_label(room.name)

        start_class = " start" if is_start else ""
        parts.append(
            f'<g class="room-box{start_class}" data-room="{room.id}">'
            f'<rect x="{rx}" y="{ry}" width="{ROOM_W}" height="{ROOM_H}" '
            f'rx="6" ry="6" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_w}"/>'
            f'<text x="{cx}" y="{cy + 1}" text-anchor="middle" dominant-baseline="central" '
            f'fill="{text_fill}" font-family="Georgia, serif" font-size="12">'
            f'{_esc_xml(label)}</text>'
            f'</g>'
        )

    return "\n".join(parts)


def compute_viewbox(game_map):
    """Compute the SVG viewBox to fit all rooms."""
    if not game_map.rooms:
        return [0, 0, 400, 300]

    xs = [r.x * CELL_W + CELL_W // 2 for r in game_map.rooms.values()]
    ys = [r.y * CELL_H + CELL_H // 2 for r in game_map.rooms.values()]

    min_x = min(xs) - ROOM_W // 2 - PAD
    min_y = min(ys) - ROOM_H // 2 - PAD
    max_x = max(xs) + ROOM_W // 2 + PAD
    max_y = max(ys) + ROOM_H // 2 + PAD

    return [min_x, min_y, max_x - min_x, max_y - min_y]


# ---------------------------------------------------------------------------
# JSON serialization
# ---------------------------------------------------------------------------


def map_to_json(game_map, viewbox):
    """Serialize the map to a JSON-compatible dict."""
    rooms = []
    for room in game_map.rooms.values():
        cx, cy = _room_center(room)
        rooms.append({
            "id": room.id,
            "name": room.name,
            "description": room.description,
            "visits": room.visits,
            "x": room.x,
            "y": room.y,
            "cx": cx,
            "cy": cy,
        })

    edges = []
    for edge in game_map.edges:
        edges.append({
            "from": edge.from_room,
            "to": edge.to_room,
            "direction": edge.direction,
            "isStandard": edge.is_standard,
            "bidirectional": edge.bidirectional,
        })

    return {
        "title": game_map.title,
        "startRoom": game_map.start_room,
        "rooms": rooms,
        "edges": edges,
        "viewBox": viewbox,
    }


# ---------------------------------------------------------------------------
# HTML assembly
# ---------------------------------------------------------------------------


def generate_html(game_map, svg_content, map_data_json):
    """Generate the interactive HTML map page."""
    template_path = paths.WEB_DIR / "map-template.html"
    if not template_path.exists():
        print(f"ERROR: Map template not found: {template_path}", file=sys.stderr)
        sys.exit(1)

    html = template_path.read_text(encoding="utf-8")

    room_count = len(game_map.rooms)
    edge_count = len([e for e in game_map.edges
                      if not any(e2 for e2 in game_map.edges
                                 if e2.from_room == e.to_room
                                 and e2.to_room == e.from_room
                                 and e2.direction == DIRECTION_OPPOSITES.get(e.direction)
                                 and e2 is not e)])
    # Simpler: count unique undirected pairs
    pairs = set()
    for e in game_map.edges:
        pair = tuple(sorted([e.from_room, e.to_room]))
        pairs.add(pair)
    connection_count = len(pairs)

    replacements = {
        "__TITLE__": game_map.title,
        "__SVG_CONTENT__": svg_content,
        "__MAP_DATA__": json.dumps(map_data_json),
        "__ROOM_COUNT__": str(room_count),
        "__EDGE_COUNT__": str(connection_count),
        "__BACK_HREF__": "./",
    }

    for placeholder, value in replacements.items():
        html = html.replace(placeholder, value)

    return html


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Generate an interactive map from walkthrough data"
    )
    parser.add_argument(
        "game",
        help="Project name (auto-finds walkthrough files under projects/<game>/)"
    )
    parser.add_argument(
        "--walkthrough",
        help="Override walkthrough.txt path"
    )
    parser.add_argument(
        "--transcript",
        help="Override walkthrough_output.txt path"
    )
    parser.add_argument(
        "--out",
        help="Output directory (default: project root)"
    )
    parser.add_argument(
        "--json-only", action="store_true",
        help="Only output map.json"
    )
    parser.add_argument(
        "--disambiguate", action="store_true",
        help="Split same-name rooms into separate nodes (maze mode)"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Overwrite existing files"
    )
    args = parser.parse_args()

    # Resolve paths
    project_dir = paths.project_dir(args.game)
    if not project_dir.exists():
        print(f"ERROR: Project directory not found: {project_dir}", file=sys.stderr)
        sys.exit(1)

    wt_path = Path(args.walkthrough) if args.walkthrough else (
        project_dir / "tests" / "inform7" / "walkthrough.txt"
    )
    tr_path = Path(args.transcript) if args.transcript else (
        project_dir / "tests" / "inform7" / "walkthrough_output.txt"
    )
    out_dir = Path(args.out) if args.out else project_dir

    if not wt_path.exists():
        print(f"ERROR: Walkthrough not found: {wt_path}", file=sys.stderr)
        sys.exit(1)
    if not tr_path.exists():
        print(f"ERROR: Transcript not found: {tr_path}", file=sys.stderr)
        sys.exit(1)

    # Read input files
    with open(wt_path, encoding="utf-8") as f:
        commands = [line.strip() for line in f if line.strip()]

    preamble, responses = parse_transcript(str(tr_path))
    sound_prompt = has_sound_prompt(preamble)

    if sound_prompt:
        print("Detected sound prompt — offsetting command/response alignment",
              file=sys.stderr)

    # Extract game title from preamble
    title = args.game.replace("-", " ").title()
    preamble_lines = [l.strip() for l in preamble.split("\n") if l.strip()]
    if preamble_lines:
        # First non-empty line of preamble is typically the game title
        candidate = preamble_lines[0]
        if len(candidate) < 60 and not candidate.startswith("["):
            title = candidate

    # Parse
    game_map = parse_map(commands, responses, preamble, sound_prompt,
                         args.disambiguate)
    game_map.title = title

    if not game_map.rooms:
        print("WARNING: No rooms detected in transcript", file=sys.stderr)
        sys.exit(1)

    print(f"Parsed {len(game_map.rooms)} rooms, {len(game_map.edges)} edges",
          file=sys.stderr)

    # Layout
    layout_map(game_map)

    # Render
    viewbox = compute_viewbox(game_map)
    map_data = map_to_json(game_map, viewbox)

    # Output map.json
    json_path = out_dir / "map.json"
    if not json_path.exists() or args.force:
        json_path.write_text(
            json.dumps(map_data, indent=2) + "\n", encoding="utf-8"
        )
        print(f"Wrote {json_path}", file=sys.stderr)
    else:
        print(f"Skipping {json_path} (exists, use --force)", file=sys.stderr)

    if args.json_only:
        return

    # Output map.html
    svg_content = render_svg(game_map)
    html = generate_html(game_map, svg_content, map_data)
    html_path = out_dir / "map.html"
    if not html_path.exists() or args.force:
        html_path.write_text(html, encoding="utf-8")
        print(f"Wrote {html_path}", file=sys.stderr)
    else:
        print(f"Skipping {html_path} (exists, use --force)", file=sys.stderr)

    print(f"Done: {len(game_map.rooms)} rooms, start={game_map.start_room}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
