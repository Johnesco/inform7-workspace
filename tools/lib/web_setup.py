"""Shared utilities for web player setup scripts.

Used by the setup_*.py web player scripts
to avoid duplicating output-directory creation, play.html overwrite checks,
and common argparse arguments.
"""

from pathlib import Path


def ensure_output_dir(out_dir: Path) -> None:
    """Create the output directory (and parents) if it doesn't exist."""
    out_dir.mkdir(parents=True, exist_ok=True)


def check_overwrite(html_path: Path, force: bool) -> bool:
    """Check whether html_path should be skipped.

    Returns True if the file exists and *force* is False (caller should skip).
    Prints a message when skipping.
    """
    if html_path.exists() and not force:
        print(f"  {html_path.name} already exists (use --force to overwrite)")
        return True
    return False


def add_common_args(parser) -> None:
    """Add --title, --out, and --force arguments shared by all setup scripts."""
    parser.add_argument("--title", required=True, help="Game title")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing play.html")
