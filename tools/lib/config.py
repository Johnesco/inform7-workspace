"""Project configuration loading — reads project.conf and seeds.conf.

project.conf is a bash-sourceable file. We parse the simple key=value
assignments and PIPELINE_* fields without actually sourcing bash.
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import paths


# ---------------------------------------------------------------------------
# Engine registry — shared by pipeline.py, run.py, dashboard.py
# ---------------------------------------------------------------------------


@dataclass
class EngineSpec:
    name: str                           # "inform7", "ink", "wwwbasic", etc.
    label: str                          # "Inform 7", "Ink", "wwwBASIC"
    source_extensions: tuple[str, ...]  # (".ni",), (".ink",), (".bas",)
    build_tool: str                     # "compile.py", "setup_ink.py", ""
    build_tool_args: tuple[str, ...] = ()
    has_cli_tests: bool = False         # True for inform7, zmachine
    binary_extensions: tuple[str, ...] = ()  # (".ulx", ".gblorb") or ()
    is_basic: bool = False

    def source_label(self, project_name: str) -> str:
        """Derive the display label for the source file (e.g. 'story.ni', 'game.bas')."""
        if self.name == "inform7":
            return "story.ni"
        ext = self.source_extensions[0] if self.source_extensions else ""
        return f"{project_name}{ext}"

    def repo_description(self, project_name: str) -> str:
        """Human-readable repo description for GitHub."""
        return f"{project_name} -- {self.label} Game"


ENGINE_REGISTRY: dict[str, EngineSpec] = {
    "inform7": EngineSpec(
        name="inform7", label="Inform 7",
        source_extensions=(".ni",),
        build_tool="compile.py",
        has_cli_tests=True,
        binary_extensions=(".ulx", ".gblorb"),
    ),
    "zmachine": EngineSpec(
        name="zmachine", label="Z-machine",
        source_extensions=(".z3", ".z5", ".z8"),
        build_tool="setup_web.py",
        has_cli_tests=True,
    ),
    "ink": EngineSpec(
        name="ink", label="Ink",
        source_extensions=(".ink",),
        build_tool="setup_ink.py",
    ),
    "wwwbasic": EngineSpec(
        name="wwwbasic", label="wwwBASIC",
        source_extensions=(".bas",),
        build_tool="setup_basic.py",
        build_tool_args=("--engine", "wwwbasic"),
        is_basic=True,
    ),
    "qbjc": EngineSpec(
        name="qbjc", label="qbjc",
        source_extensions=(".bas",),
        build_tool="setup_basic.py",
        build_tool_args=("--engine", "qbjc"),
        is_basic=True,
    ),
    "applesoft": EngineSpec(
        name="applesoft", label="Applesoft BASIC",
        source_extensions=(".bas",),
        build_tool="setup_basic.py",
        build_tool_args=("--engine", "applesoft"),
        is_basic=True,
    ),
    "bwbasic": EngineSpec(
        name="bwbasic", label="bwBASIC",
        source_extensions=(".bas",),
        build_tool="setup_basic.py",
        build_tool_args=("--engine", "bwbasic"),
        is_basic=True,
    ),
    # "basic" removed — each BASIC dialect must specify its engine explicitly
    # (wwwbasic, qbjc, applesoft, bwbasic) since each may need a different runtime.
    "jsdos": EngineSpec(
        name="jsdos", label="DOS (js-dos)",
        source_extensions=(".jsdos",),
        build_tool="setup_basic.py",
        build_tool_args=("--engine", "jsdos"),
    ),
    "twine": EngineSpec(
        name="twine", label="Twine",
        source_extensions=(".tw", ".twee"),
        build_tool="",
    ),
    "rez": EngineSpec(
        name="rez", label="Rez",
        source_extensions=(".rez",),
        build_tool="setup_rez.py",
    ),
}


def get_engine_spec(engine: str) -> EngineSpec | None:
    """Look up an EngineSpec by engine name."""
    return ENGINE_REGISTRY.get(engine)


# Map engine folder names to engine identifiers
_FOLDER_TO_ENGINE = {
    "i7": "inform7", "inform7": "inform7",
    "ink": "ink",
    "rez": "rez",
    "wwwbasic": "wwwbasic",
    "applesoft": "applesoft",
    "qbjc": "qbjc",
    "bwbasic": "bwbasic",
    "jsdos": "jsdos",
    "twine": "twine",
    "zmachine": "zmachine",
}


def detect_engine(project_dir: str | Path, conf_fields: dict | None = None) -> str:
    """Detect the engine type for a project.

    Priority: explicit ENGINE= in project.conf > parent folder name > filesystem heuristics.
    """
    if conf_fields:
        explicit = conf_fields.get("ENGINE", "").lower()
        if explicit:
            return explicit

    project_dir = str(project_dir)

    # Parent folder detection (text-games/<engine>/<game>/)
    parent = os.path.basename(os.path.dirname(project_dir))
    if parent in _FOLDER_TO_ENGINE:
        return _FOLDER_TO_ENGINE[parent]

    # Check ifhub.conf in project directory itself or registry source directory
    from . import paths as _paths
    for check_dir in (Path(project_dir), _paths.game_source_dir(os.path.basename(project_dir))):
        if check_dir == Path():
            continue
        ihconf = check_dir / "ifhub.conf"
        if ihconf.exists():
            for line in ihconf.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("engine"):
                    return line.split("=", 1)[1].strip().lower()

    # Filesystem heuristics (fallback for games not in engine folders)
    if os.path.isfile(os.path.join(project_dir, "story.ni")):
        return "inform7"

    try:
        files = os.listdir(project_dir)
    except OSError:
        return "unknown"

    if any(f == "wwwbasic.js" for f in files):
        return "wwwbasic"
    if any(f.lower().endswith(".jsdos") for f in files):
        return "jsdos"
    if any(f.lower().endswith((".tw", ".twee")) for f in files):
        return "twine"
    if any(f.lower().endswith(".ink") for f in files):
        return "ink"
    if any(f.lower().endswith(".rez") for f in files):
        return "rez"

    return "unknown"


def detect_source_file(project_dir: str | Path, engine: str,
                       conf_fields: dict | None = None) -> str:
    """Find the primary source file for a project."""
    if conf_fields:
        explicit = conf_fields.get("SOURCE", "")
        if explicit:
            return explicit

    # Check ifhub.conf for explicit source field (in project dir or registry source dir)
    from . import paths as _paths
    _check_dirs = [Path(project_dir)]
    _src = _paths.game_source_dir(Path(project_dir).name)
    if _src != Path():
        _check_dirs.append(_src)
    for check_dir in _check_dirs:
        ihconf = check_dir / "ifhub.conf"
        if ihconf.exists():
            for line in ihconf.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("source"):
                    return line.split("=", 1)[1].strip()

    if engine == "inform7":
        return "story.ni"

    project_dir = str(project_dir)
    try:
        files = os.listdir(project_dir)
    except OSError:
        return ""

    spec = get_engine_spec(engine)
    exts = spec.source_extensions if spec else ()
    if not exts:
        exts = (".bas", ".tw", ".twee", ".ink")

    # Collect candidates, prefer shortest name (avoids annotated/debug copies)
    candidates = [f for f in files if any(f.lower().endswith(e) for e in exts)]
    if candidates:
        return min(candidates, key=len)

    return ""


def parse_conf_fields(project_dir: str | Path) -> dict[str, str]:
    """Parse all KEY=VALUE fields from tests/project.conf.

    A shared helper for tools that need raw config fields without
    building a full ProjectConfig.
    """
    conf_path = Path(project_dir) / "tests" / "project.conf"
    return _parse_kv(conf_path, Path(project_dir))


# ---------------------------------------------------------------------------
# Project configuration dataclasses
# ---------------------------------------------------------------------------


@dataclass
class EngineConfig:
    name: str = ""
    path: str = ""
    seed_flag: str = "--rngseed"
    game_path: str = ""
    walkthrough: str = ""
    output_file: str = ""
    seeds_key: str = ""


@dataclass
class ScoringConfig:
    score_regex: str = r"score is (?P<score>[0-9]+)"
    fallback_regex: str = r"(?P<score>[0-9]+)(?= \(total of [0-9]+ points\))"
    max_regex: str = r"total of (?P<max>[0-9]+)"
    pass_threshold: int = 350
    default_max: int = 350


@dataclass
class DiagConfig:
    death_patterns: str = "you have died"
    won_patterns: str = "You have won"
    scoreless: bool = False
    # Parser-error wording is dialect-specific: Inform 7 says "You can't see any
    # such thing", the Infocom/ZIL parser says "You can't see any troll here!".
    # The alt_* variants are used for --alt runs and fall back to the primary
    # patterns when left empty, so single-engine projects need set nothing.
    unknown_object: str = "can't see any such thing"
    bad_exit: str = "can't go that way"
    other_error: str = "that.s not something you can|I only understood"
    alt_unknown_object: str = ""
    alt_bad_exit: str = ""
    alt_other_error: str = ""

    def errors_for(self, alt: bool) -> tuple[str, str, str]:
        """(unknown-object, bad-exit, other) patterns for the engine in use."""
        if alt:
            return (self.alt_unknown_object or self.unknown_object,
                    self.alt_bad_exit or self.bad_exit,
                    self.alt_other_error or self.other_error)
        return (self.unknown_object, self.bad_exit, self.other_error)


@dataclass
class PipelineConfig:
    sound: bool = False
    hub_id: str = ""
    tests: str = ""
    walkthrough_output_dir: str = ""
    binary_name: str = ""


@dataclass
class ProjectConfig:
    """Parsed project configuration."""

    project_name: str = ""
    project_dir: Path = field(default_factory=Path)
    primary: EngineConfig = field(default_factory=EngineConfig)
    alt: EngineConfig = field(default_factory=EngineConfig)
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    diagnostics: DiagConfig = field(default_factory=DiagConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    regtest_file: str = ""
    regtest_engine: str = ""
    regtest_game: str = ""


def _expand_vars(value: str, project_dir: Path) -> str:
    """Expand $PROJECT_DIR, $HOME, and $_IFHUB_ROOT in config values."""
    value = value.replace("$PROJECT_DIR", str(project_dir))
    value = value.replace("${PROJECT_DIR}", str(project_dir))
    value = value.replace("$HOME", os.path.expanduser("~"))
    value = value.replace("${HOME}", os.path.expanduser("~"))
    # $_IFHUB_ROOT is a legacy name from when games lived inside the hub; it now
    # means this workspace root, so $_IFHUB_ROOT/tools/interpreters/glulxe.exe resolves.
    ifhub_root = str(paths.WORKSPACE_ROOT)
    value = value.replace("$_IFHUB_ROOT", ifhub_root)
    value = value.replace("${_IFHUB_ROOT}", ifhub_root)
    return value


def _parse_kv(conf_path: Path, project_dir: Path) -> dict[str, str]:
    """Parse simple KEY=VALUE or KEY="VALUE" lines from a bash config file.

    Skips lines with conditionals, function defs, and complex bash logic.
    """
    kv: dict[str, str] = {}
    try:
        text = conf_path.read_text(encoding="utf-8")
    except OSError:
        return kv

    for line in text.splitlines():
        line = line.strip()
        # Skip comments, empty, conditionals, function defs
        if not line or line.startswith("#") or line.startswith("if ") or line.startswith("fi"):
            continue
        if line.startswith("else") or line.startswith("elif"):
            continue
        if "()" in line or line.startswith("local "):
            continue

        m = re.match(r'^(\w+)=["\']?(.*?)["\']?\s*$', line)
        if m:
            key = m.group(1)
            val = _expand_vars(m.group(2), project_dir)
            kv[key] = val

    return kv


def load_config(conf_path: Path | str) -> ProjectConfig:
    """Load a project configuration from a project.conf file.

    Parses simple assignments and resolves platform-appropriate engine paths.
    For engine paths that depend on platform detection (the if/else blocks in
    project.conf), we use our own detection logic.
    """
    conf_path = Path(conf_path)
    # project.conf lives in tests/, project_dir is one level up
    project_dir = conf_path.parent.parent
    kv = _parse_kv(conf_path, project_dir)

    cfg = ProjectConfig(project_dir=project_dir)
    cfg.project_name = kv.get("PROJECT_NAME", "")

    # Resolve engine paths using platform detection
    native_glulxe = paths.NATIVE_GLULXE
    native_dfrotz = paths.NATIVE_DFROTZ
    use_native = native_glulxe.exists() and os.access(str(native_glulxe), os.X_OK)

    if use_native:
        cfg.primary.path = str(native_glulxe)
        cfg.alt.path = str(native_dfrotz) if native_dfrotz.exists() else ""
    else:
        cfg.primary.path = kv.get("PRIMARY_ENGINE_PATH",
                                   os.path.expanduser("~/glulxe/glulxe"))
        cfg.alt.path = kv.get("ALT_ENGINE_PATH",
                               os.path.expanduser("~/frotz-install/usr/games/dfrotz"))

    # Primary engine
    cfg.primary.name = kv.get("PRIMARY_ENGINE_NAME", "glulxe")
    cfg.primary.seed_flag = kv.get("PRIMARY_ENGINE_SEED_FLAG", "--rngseed")
    cfg.primary.game_path = kv.get("PRIMARY_GAME_PATH",
                                    str(project_dir / f"{project_dir.name}.ulx"))
    cfg.primary.walkthrough = kv.get("PRIMARY_WALKTHROUGH",
                                      str(project_dir / "tests" / "inform7" / "walkthrough.txt"))
    cfg.primary.output_file = kv.get("PRIMARY_OUTPUT_FILE",
                                      str(project_dir / "tests" / "inform7" / "walkthrough_output.txt"))
    cfg.primary.seeds_key = kv.get("PRIMARY_SEEDS_KEY", "glulxe")

    # Alt engine
    cfg.alt.name = kv.get("ALT_ENGINE_NAME", "dfrotz")
    cfg.alt.seed_flag = kv.get("ALT_ENGINE_SEED_FLAG", "-s")
    cfg.alt.game_path = kv.get("ALT_GAME_PATH", "")
    cfg.alt.walkthrough = kv.get("ALT_WALKTHROUGH", "")
    cfg.alt.output_file = kv.get("ALT_OUTPUT_FILE", "")
    cfg.alt.seeds_key = kv.get("ALT_SEEDS_KEY", "dfrotz")

    # Scoring
    cfg.scoring.score_regex = kv.get("SCORE_REGEX", cfg.scoring.score_regex)
    cfg.scoring.fallback_regex = kv.get("SCORE_FALLBACK_REGEX", cfg.scoring.fallback_regex)
    cfg.scoring.max_regex = kv.get("MAX_SCORE_REGEX", cfg.scoring.max_regex)
    try:
        cfg.scoring.pass_threshold = int(kv.get("PASS_THRESHOLD", str(cfg.scoring.pass_threshold)))
    except ValueError:
        pass
    try:
        cfg.scoring.default_max = int(kv.get("DEFAULT_MAX_SCORE", str(cfg.scoring.default_max)))
    except ValueError:
        pass

    # Diagnostics
    cfg.diagnostics.death_patterns = kv.get("DEATH_PATTERNS", cfg.diagnostics.death_patterns)
    cfg.diagnostics.won_patterns = kv.get("WON_PATTERNS", cfg.diagnostics.won_patterns)
    cfg.diagnostics.scoreless = kv.get("SCORELESS_GAME", "").lower() == "true"
    d = cfg.diagnostics
    d.unknown_object = kv.get("ERROR_UNKNOWN_OBJECT", d.unknown_object)
    d.bad_exit = kv.get("ERROR_BAD_EXIT", d.bad_exit)
    d.other_error = kv.get("ERROR_OTHER", d.other_error)
    d.alt_unknown_object = kv.get("ALT_ERROR_UNKNOWN_OBJECT", d.alt_unknown_object)
    d.alt_bad_exit = kv.get("ALT_ERROR_BAD_EXIT", d.alt_bad_exit)
    d.alt_other_error = kv.get("ALT_ERROR_OTHER", d.alt_other_error)

    # RegTest
    cfg.regtest_file = kv.get("REGTEST_FILE", "")
    if use_native:
        cfg.regtest_engine = str(native_glulxe)
    else:
        cfg.regtest_engine = kv.get("REGTEST_ENGINE",
                                     os.path.expanduser("~/glulxe/glulxe"))
    cfg.regtest_game = kv.get("REGTEST_GAME", "")

    # Pipeline
    cfg.pipeline.sound = kv.get("PIPELINE_SOUND", "").lower() == "true"
    cfg.pipeline.hub_id = kv.get("PIPELINE_HUB_ID", "")
    cfg.pipeline.tests = kv.get("PIPELINE_TESTS", "")
    cfg.pipeline.walkthrough_output_dir = kv.get("PIPELINE_WALKTHROUGH_OUTPUT_DIR", "")
    cfg.pipeline.binary_name = kv.get("BINARY_NAME", "")

    return cfg


def parse_pipeline_fields(conf_path: str | Path) -> dict[str, str]:
    """Extract PIPELINE_* fields from a project.conf file.

    Backward-compatible helper used by run.py during the transition.
    Delegates to _parse_kv() for the actual KEY=VALUE parsing, then
    filters to only PIPELINE_* keys.
    """
    conf_path = Path(conf_path)
    # _parse_kv needs a project_dir for variable expansion; project.conf
    # lives in tests/, so project_dir is one level up.
    project_dir = conf_path.parent.parent
    all_fields = _parse_kv(conf_path, project_dir)
    return {k: v for k, v in all_fields.items() if k.startswith("PIPELINE_")}


def extract_story_metadata(project_dir: str | Path) -> dict[str, str]:
    """Extract bibliographic metadata from a project's story.ni.

    Parses:
      - Title and author from line 1: "Title" by "Author"
      - The story headline is "..."
      - The story description is "..."

    Returns a dict with keys: title, author, meta, description.
    All values default to sensible fallbacks if parsing fails.
    """
    source = Path(project_dir) / "story.ni"
    result = {
        "title": Path(project_dir).name.replace("-", " ").replace("_", " ").title(),
        "author": "",
        "meta": "An Interactive Fiction",
        "description": "An interactive fiction game.",
    }
    if not source.exists():
        return result

    try:
        text = source.read_text(encoding="utf-8")
    except OSError:
        return result

    lines = text.split("\n")

    # Line 1: "Title" by "Author"
    if lines:
        m = re.match(r'^"([^"]+)"\s+by\s+"([^"]+)"', lines[0])
        if m:
            result["title"] = m.group(1)
            result["author"] = m.group(2)

    # The story headline is "..."
    m = re.search(r'The story headline is "([^"]+)"', text, re.IGNORECASE)
    if m:
        result["meta"] = m.group(1)

    # The story description is "..."
    m = re.search(r'The story description is "([^"]+)"', text, re.IGNORECASE)
    if m:
        result["description"] = m.group(1)

    return result


def get_golden_seed(project_dir: str | Path, engine_key: str = "glulxe") -> str | None:
    """Read the first seed for the given engine from tests/seeds.conf."""
    seeds_path = Path(project_dir) / "tests" / "seeds.conf"
    try:
        for line in seeds_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(f"{engine_key}:"):
                parts = line.split(":")
                if len(parts) >= 2 and parts[1]:
                    return parts[1]
    except OSError:
        pass
    return None


def get_scenario_seeds(project_dir: str | Path, engine_key: str = "glulxe",
                       scenario: str = "") -> list[str]:
    """Read all seeds for a specific scenario from tests/seeds.conf.

    Supports both formats:
      4-field (global):   engine:seed:hash:date
      5-field (scenario): engine:scenario:seed:hash:date

    If scenario is empty, returns global seeds only.
    If scenario is given, returns scenario-specific seeds only.
    """
    seeds_path = Path(project_dir) / "tests" / "seeds.conf"
    result = []
    try:
        for line in seeds_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(":")
            if parts[0] != engine_key:
                continue
            if scenario:
                # Look for 5-field format: engine:scenario:seed:hash:date
                if len(parts) >= 5 and parts[1] == scenario:
                    result.append(parts[2])
            else:
                # Look for 4-field format: engine:seed:hash:date
                if len(parts) == 4 and parts[1]:
                    result.append(parts[1])
    except OSError:
        pass
    return result


def get_seed_hash(project_dir: str | Path, engine_key: str = "glulxe") -> str | None:
    """Read the binary hash for the given engine from tests/seeds.conf."""
    seeds_path = Path(project_dir) / "tests" / "seeds.conf"
    try:
        for line in seeds_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(f"{engine_key}:"):
                parts = line.split(":")
                if len(parts) >= 3 and parts[2] and parts[2] != "none":
                    return parts[2]
    except OSError:
        pass
    return None
