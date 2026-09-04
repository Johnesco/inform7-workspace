"""Web player operations — base64 encoding, template substitution, validation."""

import base64
import re
import shutil
import time
from pathlib import Path

from . import output, paths

# The 13 Parchment library files that every project needs
PARCHMENT_FILES = [
    "jquery.min.js",
    "main.js",
    "main.css",
    "parchment.js",
    "parchment.css",
    "quixe.js",
    "glulxe.js",
    "ie.js",
    "bocfel.js",
    "resourcemap.js",
    "zvm.js",
    "waiting.gif",
    "theme-listener.js",
]

# Mood engine library file
MOOD_ENGINE_FILE = "mood-engine.js"


def copy_mood_engine(dest_dir: Path):
    """Copy mood-engine.js from the shared hub source to a project's parchment dir."""
    src = paths.WEB_DIR / "parchment" / MOOD_ENGINE_FILE
    if src.exists():
        shutil.copy2(str(src), str(dest_dir / MOOD_ENGINE_FILE))


def base64_encode_binary(binary_path: Path) -> str:
    """Read a binary file and return its base64 encoding (no line wrapping)."""
    data = binary_path.read_bytes()
    return base64.b64encode(data).decode("ascii")


def write_story_js(binary_path: Path, output_path: Path):
    """Encode a game binary to the processBase64Zcode JS format."""
    b64 = base64_encode_binary(binary_path)
    output_path.write_text(f"processBase64Zcode('{b64}')", encoding="utf-8")


def copy_parchment_libs(dest_dir: Path):
    """Copy the 12 Parchment engine files from the shared hub source."""
    source_dir = paths.WEB_DIR / "parchment"
    dest_dir.mkdir(parents=True, exist_ok=True)
    for filename in PARCHMENT_FILES:
        src = source_dir / filename
        if src.exists():
            shutil.copy2(str(src), str(dest_dir / filename))


def substitute_template(
    template_path: Path,
    output_path: Path,
    replacements: dict[str, str],
    cache_bust: bool = False,
):
    """Apply placeholder substitutions to a template file.

    Args:
        template_path: Source template file.
        output_path: Destination file.
        replacements: Dict of __PLACEHOLDER__ -> value mappings.
        cache_bust: If True, append ?v=<timestamp> to .js and .css references.
    """
    text = template_path.read_text(encoding="utf-8")
    for placeholder, value in replacements.items():
        text = text.replace(placeholder, value)
    if cache_bust:
        bust = f"v={int(time.time())}"
        text = re.sub(r'\.js"', f'.js?{bust}"', text)
        text = re.sub(r'\.css"', f'.css?{bust}"', text)
    output_path.write_text(text, encoding="utf-8")


def validate_web_dir(web_dir: Path) -> int:
    """Validate a web player directory. Returns the number of errors found.

    Checks:
      1. play.html exists
      2. No unsubstituted template tokens
      3. All src/href references resolve
      4. Binary .js file is exactly 1 line
      5. Binary .js file starts with processBase64Zcode('
      6. parchment_options contains story_name
      7. parchment.js is loaded
    """
    errors = 0

    def _fail(msg: str):
        nonlocal errors
        output.fail(msg)
        errors += 1

    print(f"Validating: {web_dir}")

    # Check 1: play.html exists
    play_html = web_dir / "play.html"
    if not play_html.exists():
        _fail("play.html not found")
        print(f"\nValidation failed with {errors} error(s).")
        return errors
    output.ok("play.html exists")

    html_text = play_html.read_text(encoding="utf-8")

    # Check 2: No unsubstituted template tokens
    tokens = re.findall(r"__(?:TITLE|STORY_FILE|STORY_PATH|LIB_PATH|BINARY)__", html_text)
    if tokens:
        _fail(f"Unsubstituted template tokens: {' '.join(set(tokens))}")
    else:
        output.ok("No unsubstituted template tokens")

    # Check 3: All src/href references resolve
    refs = re.findall(r'(?:src|href)="([^"]*)"', html_text)
    missing = 0
    for ref in refs:
        if re.match(r"^(https?://|data:|#|javascript:)", ref):
            continue
        # Strip query params
        ref_clean = re.sub(r"\?.*$", "", ref)
        if not (web_dir / ref_clean).exists():
            _fail(f"Referenced file not found: {ref_clean}")
            missing += 1
    if missing == 0:
        output.ok("All src/href references resolve")

    # Check 4 & 5: Binary .js file
    binary_file = ""
    m = re.search(r"story_name:\s*'([^']*)'", html_text)
    if m:
        binary_file = m.group(1)
    if not binary_file:
        m = re.search(r"default_story:.*\[.*'([^']*)'", html_text)
        if m:
            binary_file = Path(m.group(1)).name

    if binary_file:
        binary_path = None
        for candidate in [web_dir / binary_file, web_dir / "lib" / "parchment" / binary_file]:
            if candidate.exists():
                binary_path = candidate
                break

        if binary_path:
            content = binary_path.read_text(encoding="utf-8")
            line_count = content.count("\n")
            # A single line with no trailing newline = 0 newlines, which is fine
            # A single line with trailing newline = 1 newline
            actual_lines = content.count("\n") + (0 if content.endswith("\n") else 1)
            if actual_lines != 1:
                _fail(f"Binary {binary_file} has {actual_lines} lines (must be exactly 1)")
            else:
                output.ok(f"Binary {binary_file} is 1 line")

            if content.startswith("processBase64Zcode('"):
                output.ok(f"Binary {binary_file} has correct JSONP format")
            else:
                _fail(f"Binary {binary_file} does not start with processBase64Zcode('")
        else:
            _fail(f"Binary file {binary_file} not found in {web_dir}")
    else:
        _fail("Could not determine binary filename from play.html")

    # Check 6: story_name in parchment_options
    if "story_name" in html_text:
        output.ok("parchment_options contains story_name")
    else:
        _fail("parchment_options missing story_name (causes TypeError crash)")

    # Check 7: parchment.js is loaded
    if "parchment.js" in html_text:
        output.ok("parchment.js is loaded")
    elif "main.js" in html_text:
        _fail("main.js loaded instead of parchment.js (silently disables sound)")
    else:
        _fail("Neither parchment.js nor main.js found in play.html")

    print()
    if errors > 0:
        print(f"Validation FAILED with {errors} error(s).")
    else:
        print("Validation passed.")
    return errors
