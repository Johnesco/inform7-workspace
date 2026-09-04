"""Subprocess execution helpers for IF Hub tools."""

import subprocess
import sys
from pathlib import Path


def run(
    cmd: list[str | Path],
    *,
    cwd: str | Path | None = None,
    capture: bool = False,
    timeout: int | None = None,
    input_text: str | None = None,
) -> subprocess.CompletedProcess:
    """Run an external command.

    Args:
        cmd: Command and arguments.
        cwd: Working directory.
        capture: If True, capture stdout/stderr as strings.
        timeout: Timeout in seconds.
        input_text: Text to pipe to stdin.

    Returns:
        CompletedProcess result.
    """
    str_cmd = [str(c) for c in cmd]
    kwargs: dict = {
        "cwd": str(cwd) if cwd else None,
        "timeout": timeout,
    }
    if capture:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE
        kwargs["text"] = True
    if input_text is not None:
        kwargs["input"] = input_text
        kwargs["text"] = True

    return subprocess.run(str_cmd, **kwargs)


def run_interpreter(
    engine: str | Path,
    game: str | Path,
    *,
    input_text: str = "",
    seed: str | None = None,
    seed_flag: str = "--rngseed",
    quiet: bool = True,
) -> subprocess.CompletedProcess:
    """Run a game through an interpreter, capturing output.

    Args:
        engine: Path to interpreter executable.
        game: Path to game file (.ulx, .gblorb, .z3).
        input_text: Commands to feed to the game.
        seed: RNG seed value (None = no seeding).
        seed_flag: CLI flag for the seed (e.g., --rngseed, -s).
        quiet: Pass -q to suppress interpreter chrome.

    Returns:
        CompletedProcess with stdout containing the transcript.
    """
    cmd: list[str | Path] = [engine]
    if seed:
        cmd.extend([seed_flag, seed])
    if quiet:
        cmd.append("-q")
    cmd.append(game)

    return run(cmd, capture=True, input_text=input_text)
