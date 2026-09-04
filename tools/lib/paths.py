"""Path resolution for the Inform 7 workspace tools.

Layout (text-games/i7/):
    <game>/                one folder per game, each its own git repo
    tools/                 this tooling (TOOLS_DIR)
    tools/lib/             shared modules
    tools/web/             Parchment libraries + play templates (WEB_DIR)
    tools/interpreters/    native glulxe.exe / dfrotz.exe

Games are addressed by folder name (resolved under WORKSPACE_ROOT) or by path.
"""

import os
import re
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = TOOLS_DIR.parent
WEB_DIR = TOOLS_DIR / "web"
TEXT_GAMES_DIR = WORKSPACE_ROOT.parent

# The IF Hub checkout — only used to print the "ship it" hint. Override with IFHUB_ROOT.
HUB_ROOT = Path(os.environ.get("IFHUB_ROOT", str(TEXT_GAMES_DIR.parent / "ifhub")))

# Aliases kept for scripts that originated in IF Hub.
I7_ROOT = WORKSPACE_ROOT
PROJECTS_DIR = WORKSPACE_ROOT

# Compiler paths — override with INFORM7_HOME if installed elsewhere
_I7_HOME = Path(os.environ.get("INFORM7_HOME", r"C:\Program Files\Inform7IDE"))
I7_COMPILER = _I7_HOME / "Compilers" / "inform7.exe"
I6_COMPILER = _I7_HOME / "Compilers" / "inform6.exe"
INBLORB = _I7_HOME / "Compilers" / "inblorb.exe"
I7_INTERNAL = _I7_HOME / "Internal"

# Native interpreters (built via tools/interpreters/build.sh)
NATIVE_GLULXE = TOOLS_DIR / "interpreters" / "glulxe.exe"
NATIVE_DFROTZ = TOOLS_DIR / "interpreters" / "dfrotz.exe"

# Engine name -> workspace folder name (used by new_project.py)
ENGINE_DIR_KEYS = {"inform7": "i7", "zmachine": "zmachine"}


def engine_dir_key(engine: str) -> str:
    return ENGINE_DIR_KEYS.get(engine, engine)


def engine_tools_dir(engine: str = "inform7") -> Path:
    """This tools dir. Kept for scripts that used to ask per engine."""
    return TOOLS_DIR


def new_project_dir(engine: str, name: str) -> Path:
    """Where new_project.py creates a game: text-games/<engine-folder>/<name>/."""
    return TEXT_GAMES_DIR / engine_dir_key(engine) / name


def project_dir(name_or_path: str | Path) -> Path:
    """Resolve a game by folder name (under this workspace) or by path."""
    s = str(name_or_path)
    p = Path(s)
    if p.is_absolute() or "/" in s or "\\" in s or s in (".", ".."):
        return p.resolve()
    return WORKSPACE_ROOT / s


def game_source_dir(name: str) -> Path:
    """Games build in place; there is no separate source directory."""
    return Path()


def to_posix(path: str | Path) -> str:
    """C:\\code\\x -> /c/code/x"""
    s = str(path).replace("\\", "/")
    m = re.match(r"^([A-Za-z]):/", s)
    if m:
        s = "/" + m.group(1).lower() + "/" + s[3:]
    return s


def to_windows(path: str) -> str:
    """/c/code/x -> C:\\code\\x"""
    m = re.match(r"^/([a-zA-Z])/(.*)", path)
    if m:
        return f"{m.group(1).upper()}:\\{m.group(2).replace('/', chr(92))}"
    return path.replace("/", "\\")
