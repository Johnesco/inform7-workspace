#!/usr/bin/env python3
"""Compile an Inform 7 project and optionally update its web player.

Usage:
    python tools/compile.py <game-name-or-path> [--sound] [--source PATH] [--compile-only] [--force]

Normally run through tools/build.py, which also runs the tests.

Steps:
  1. Compiles story.ni -> story.i6 (Inform 7 -> Inform 6)
  2. Compiles story.i6 -> <name>.ulx (Inform 6 -> Glulx)
  When --sound is passed:
    2b. generate_blurb.py -> <name>.blurb
    2c. inblorb <name>.blurb -> <name>.gblorb
  3. Cleans up intermediates (story.i6, .blurb)
  4. Sets up web player (unless --compile-only)
"""

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import config, output, paths, process, web


def main():
    parser = argparse.ArgumentParser(description="Compile an Inform 7 project.")
    parser.add_argument("game", help="Game name (project directory)")
    parser.add_argument("--sound", action="store_true", help="Embed audio in .gblorb")
    parser.add_argument("--source", help="Use this story.ni instead of the project's own")
    parser.add_argument("--compile-only", action="store_true", help="Skip web player update")
    parser.add_argument("--force", action="store_true", help="Overwrite play.html")
    parser.add_argument("--binary-name", help="Override binary filename (default: game dir name)")
    args = parser.parse_args()

    project_dir = paths.project_dir(args.game)
    source_file = Path(args.source) if args.source else project_dir / "story.ni"

    # Resolve binary name: CLI flag > project.conf BINARY_NAME > game dir name
    bin_name = args.binary_name
    if not bin_name:
        conf_file = project_dir / "tests" / "project.conf"
        if conf_file.exists():
            from lib.config import _parse_kv
            kv = _parse_kv(conf_file, project_dir)
            bin_name = kv.get("BINARY_NAME", "")
    if not bin_name:
        bin_name = project_dir.name

    if not source_file.exists():
        print(f"ERROR: story.ni not found at {source_file}", file=sys.stderr)
        sys.exit(1)

    # Pre-flight: check for colons in title
    title_line = source_file.read_text(encoding="utf-8").split("\n", 1)[0]
    import re
    m = re.match(r'^"([^"]*)"', title_line)
    game_title = m.group(1) if m else args.game

    if ":" in title_line:
        print("ERROR: story.ni title contains a colon:", file=sys.stderr)
        print(f"  {title_line}", file=sys.stderr)
        print("  Colons produce invalid filenames on Windows.", file=sys.stderr)
        sys.exit(1)

    # Pre-flight: verify Sounds/ directory for --sound
    if args.sound and not (project_dir / "Sounds").is_dir():
        print(f"ERROR: --sound requires a Sounds/ directory at {project_dir / 'Sounds'}", file=sys.stderr)
        sys.exit(1)

    total_steps = 6 if args.sound else 4
    print(f"=== Compiling {args.game} ===")

    # Step 1: I7 -> I6
    output.step(1, total_steps, "Inform 7 -> Inform 6...")
    r = process.run([
        str(paths.I7_COMPILER),
        "-internal", str(paths.I7_INTERNAL),
        "-source", str(source_file),
        "-o", str(project_dir / "story.i6"),
        "-silence",
    ])
    if r.returncode != 0:
        print("ERROR: Inform 7 compilation failed.", file=sys.stderr)
        sys.exit(r.returncode)

    # Step 2: I6 -> Glulx
    output.step(2, total_steps, "Inform 6 -> Glulx...")
    r = process.run([
        str(paths.I6_COMPILER), "-w", "-G",
        str(project_dir / "story.i6"),
        str(project_dir / f"{bin_name}.ulx"),
    ])
    if r.returncode != 0:
        print("ERROR: Inform 6 compilation failed.", file=sys.stderr)
        sys.exit(r.returncode)

    if args.sound:
        # Step 2b: Generate blurb
        output.step(3, total_steps, "Generating blurb...")
        r = process.run([
            sys.executable, str(paths.TOOLS_DIR / "generate_blurb.py"),
            "--ulx", str(project_dir / f"{bin_name}.ulx"),
            "--source", str(source_file),
            "--sounds", str(project_dir / "Sounds"),
            "--out", str(project_dir / f"{bin_name}.blurb"),
        ])
        if r.returncode != 0:
            sys.exit(r.returncode)

        # Step 2c: Build blorb
        output.step(4, total_steps, "Building blorb...")
        r = process.run([
            str(paths.INBLORB),
            str(project_dir / f"{bin_name}.blurb"),
            str(project_dir / f"{bin_name}.gblorb"),
        ])
        if r.returncode != 0:
            print("ERROR: inblorb failed.", file=sys.stderr)
            sys.exit(r.returncode)

    # Clean intermediates
    output.step(total_steps - 1, total_steps, "Cleaning up...")
    (project_dir / "story.i6").unlink(missing_ok=True)
    if args.sound:
        (project_dir / f"{bin_name}.blurb").unlink(missing_ok=True)

    # Update web player
    if not args.compile_only:
        output.step(total_steps, total_steps, "Updating web player...")

        setup_cmd = [
            sys.executable, str(paths.WEB_DIR / "setup_web.py"),
            "--title", game_title,
            "--out", str(project_dir),
        ]
        if args.sound:
            setup_cmd.extend(["--blorb", str(project_dir / f"{bin_name}.gblorb")])
        else:
            setup_cmd.extend(["--ulx", str(project_dir / f"{bin_name}.ulx")])
        if (project_dir / "play-template.html").exists():
            setup_cmd.extend(["--template", str(project_dir / "play-template.html")])
            print(f"  Using project template: {project_dir / 'play-template.html'}")
            # Auto-detect mood engine usage in template
            tmpl_text = (project_dir / "play-template.html").read_text(encoding="utf-8")
            if "mood-engine.js" in tmpl_text:
                setup_cmd.append("--mood")
                print("  Mood engine detected — will copy mood-engine.js")
        if args.force:
            setup_cmd.append("--force")

        r = process.run(setup_cmd)
        if r.returncode != 0:
            sys.exit(r.returncode)

        # Generate walkthrough transcript if commands and interpreter exist
        # NOTE: Guide generation + copy logic parallels pipeline.py stage_test().
        # Kept separate: compile.py runs the interpreter and copies 3 files,
        # while pipeline.py delegates to run_walkthrough.py and copies only the guide.
        walk_cmds = project_dir / "tests" / "inform7" / "walkthrough.txt"
        walk_out = project_dir / "tests" / "inform7" / "walkthrough_output.txt"
        walk_guide = project_dir / "tests" / "inform7" / "walkthrough-guide.txt"
        glulxe = paths.NATIVE_GLULXE

        if walk_cmds.exists() and glulxe.exists():
            print()
            print("Generating walkthrough transcript...")
            (project_dir / "tests" / "inform7").mkdir(parents=True, exist_ok=True)
            r = process.run_interpreter(
                str(glulxe), str(project_dir / f"{bin_name}.ulx"),
                input_text=walk_cmds.read_text(encoding="utf-8"),
                seed=None,
            )
            if r.stdout:
                walk_out.write_text(r.stdout, encoding="utf-8")
                print(f"  Transcript: {walk_out}")

                # Generate guide
                guide_r = process.run([
                    sys.executable, str(paths.TOOLS_DIR / "generate-guide.py"),
                    "--walkthrough", str(walk_cmds),
                    "--transcript", str(walk_out),
                    "-o", str(walk_guide),
                ], capture=True)

                # Copy to project root
                shutil.copy2(str(walk_out), str(project_dir))
                shutil.copy2(str(walk_cmds), str(project_dir))
                if walk_guide.exists():
                    shutil.copy2(str(walk_guide), str(project_dir))

        # Validate
        print()
        print("Validating web player...")
        web.validate_web_dir(project_dir)
    else:
        output.step(total_steps, total_steps, "Skipping web player (--compile-only)")

    # Summary
    ulx_path = project_dir / f"{bin_name}.ulx"
    ulx_size = ulx_path.stat().st_size if ulx_path.exists() else 0
    print()
    print("=== Done ===")
    print(f"  Binary: {ulx_path} ({ulx_size} bytes)")
    if args.sound:
        gblorb_path = project_dir / f"{bin_name}.gblorb"
        gblorb_size = gblorb_path.stat().st_size if gblorb_path.exists() else 0
        print(f"  Blorb:  {gblorb_path} ({gblorb_size} bytes)")
    if not args.compile_only:
        print(f"  Web:    {project_dir / 'play.html'}")
    print()
    if paths.NATIVE_GLULXE.exists():
        print(f"  Test:   cd {project_dir} && python {paths.TOOLS_DIR}/run_tests.py --config tests/project.conf")
    print(f"  Play:   python -m http.server 8000 --directory {project_dir}")


if __name__ == "__main__":
    main()
