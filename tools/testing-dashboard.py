#!/usr/bin/env python3
"""Testing Dashboard — web UI for the I7 test suite.

Serves a single-page dashboard that lists all I7 games, shows test status
(green pass / red fail), and lets you run tests and drill into results
down to individual scenario transcripts.

Usage:
    python testing-dashboard.py [--port 9100]
"""

import argparse
import json
import subprocess
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

_TOOLS_DIR = Path(__file__).resolve().parent
TEXT_GAMES_I7 = _TOOLS_DIR.parent
DASHBOARD_HTML = _TOOLS_DIR / "testing-dashboard.html"

# Track running tests
_running = {}  # game_name -> {"thread": Thread, "status": "running"/"done", "output": str}


def discover_games():
    """Find all I7 games with test infrastructure."""
    games = []
    for game_dir in sorted(TEXT_GAMES_I7.iterdir()):
        if not game_dir.is_dir() or game_dir.name.startswith(".") or game_dir.name == "tools":
            continue
        conf_path = game_dir / "tests" / "project.conf"
        if not conf_path.is_file():
            continue

        game = {"name": game_dir.name, "path": str(game_dir)}

        # Load suite.json
        suite_path = game_dir / "tests" / "suite.json"
        if suite_path.is_file():
            try:
                game["suite"] = json.loads(suite_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                game["suite"] = None
        else:
            game["suite"] = None

        # Load latest results
        results_path = game_dir / "tests" / "results" / "latest.json"
        if results_path.is_file():
            try:
                game["results"] = json.loads(results_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                game["results"] = None
        else:
            game["results"] = None

        # Check what test assets exist
        tests_dir = game_dir / "tests"
        game["has_scenarios"] = (any(tests_dir.glob("*.scenario"))
                                or any(tests_dir.glob("*.regtest")))
        game["has_scenarios"] = (tests_dir / "scenarios" / "index.json").is_file()

        # Load scenario index
        index_path = tests_dir / "scenarios" / "index.json"
        if index_path.is_file():
            try:
                game["scenario_index"] = json.loads(index_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                game["scenario_index"] = None
        else:
            game["scenario_index"] = None

        games.append(game)
    return games


def get_scenario_results(game_name):
    """Load detailed scenario results for a game."""
    game_dir = TEXT_GAMES_I7 / game_name
    detail_path = game_dir / "tests" / "results" / "scenarios-latest.json"
    if detail_path.is_file():
        try:
            return json.loads(detail_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    results_path = game_dir / "tests" / "results" / "latest.json"
    if not results_path.is_file():
        return None
    try:
        return json.loads(results_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def get_transcript(game_name, scenario_name):
    """Read a scenario transcript."""
    path = TEXT_GAMES_I7 / game_name / "tests" / "scenarios" / f"{scenario_name}.transcript.txt"
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return None


def get_commands(game_name, scenario_name):
    """Read a scenario's command list."""
    path = TEXT_GAMES_I7 / game_name / "tests" / "scenarios" / f"{scenario_name}.commands.txt"
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return None


def run_tests_background(game_name, layer=None):
    """Run tests for a game in a background thread."""
    def worker():
        conf = str(TEXT_GAMES_I7 / game_name / "tests" / "project.conf")
        cmd = [sys.executable, str(_TOOLS_DIR / "test_suite.py"),
               "--config", conf, "--json"]
        if layer:
            cmd.extend(["--layer", layer])
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            _running[game_name]["output"] = result.stdout
            _running[game_name]["status"] = "done"
            _running[game_name]["exit_code"] = result.returncode
        except subprocess.TimeoutExpired:
            _running[game_name]["output"] = '{"error": "timeout"}'
            _running[game_name]["status"] = "done"
            _running[game_name]["exit_code"] = 1
        except Exception as e:
            _running[game_name]["output"] = json.dumps({"error": str(e)})
            _running[game_name]["status"] = "done"
            _running[game_name]["exit_code"] = 1

    _running[game_name] = {"thread": None, "status": "running", "output": ""}
    t = threading.Thread(target=worker, daemon=True)
    _running[game_name]["thread"] = t
    t.start()


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            self.serve_html()
        elif path == "/api/games":
            self.serve_json(discover_games())
        elif path == "/api/results":
            game = params.get("game", [None])[0]
            if game:
                self.serve_json(get_scenario_results(game))
            else:
                self.send_error(400, "game parameter required")
        elif path == "/api/transcript":
            game = params.get("game", [None])[0]
            scenario = params.get("scenario", [None])[0]
            if game and scenario:
                text = get_transcript(game, scenario)
                if text is not None:
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.send_header("Cache-Control", "no-cache")
                    self.end_headers()
                    self.wfile.write(text.encode())
                else:
                    self.send_error(404, "transcript not found")
            else:
                self.send_error(400, "game and scenario parameters required")
        elif path == "/api/commands":
            game = params.get("game", [None])[0]
            scenario = params.get("scenario", [None])[0]
            if game and scenario:
                text = get_commands(game, scenario)
                if text is not None:
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.send_header("Cache-Control", "no-cache")
                    self.end_headers()
                    self.wfile.write(text.encode())
                else:
                    self.send_error(404, "commands not found")
            else:
                self.send_error(400, "game and scenario parameters required")
        elif path == "/api/status":
            game = params.get("game", [None])[0]
            if game and game in _running:
                self.serve_json(_running[game])
            else:
                self.serve_json({"status": "idle"})
        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == "/api/run":
            game = params.get("game", [None])[0]
            layer = params.get("layer", [None])[0]
            if not game:
                self.send_error(400, "game parameter required")
                return
            if game in _running and _running[game]["status"] == "running":
                self.serve_json({"error": "already running"})
                return
            run_tests_background(game, layer)
            self.serve_json({"status": "started", "game": game})
        else:
            self.send_error(404)

    def serve_json(self, data):
        body = json.dumps(data, default=str).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def serve_html(self):
        body = DASHBOARD_HTML.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        sys.stderr.write(f"  {fmt % args}\n")


def main():
    parser = argparse.ArgumentParser(description="I7 Testing Dashboard")
    parser.add_argument("--port", type=int, default=9100)
    args = parser.parse_args()

    server = HTTPServer(("127.0.0.1", args.port), DashboardHandler)
    print(f"Testing Dashboard: http://127.0.0.1:{args.port}/")
    print(f"Games directory:   {TEXT_GAMES_I7}")
    print(f"Stop: Ctrl+C\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
