#!/usr/bin/env python3
"""Build an Inform 7 game (or wrap a Z-machine story) and lay out the files IF Hub expects.

Usage:
    python tools/build.py <game> [--no-test] [--sound] [--force] [--compile-only]

<game> is a folder name in this workspace (text-games/i7/<game>) or a path.
The engine comes from ifhub.conf:

  engine = inform7 (default)
    1. compile.py   story.ni -> <game>.ulx (or .gblorb with sound) -> play.html + lib/parchment/
    2. tests        walkthrough (run_walkthrough.py + generate-guide.py), regtests
                    (run_tests.py -> test-results.json -> tests.html), ifPlayer .test files
    3. validate     play.html sanity checks (done by compile.py)

  engine = zmachine
    Wraps the story file named by `binary =` (.z3/.z5/.z8, or an already encoded .js)
    in the same Parchment player. No compile, no CLI tests.

Everything is written into the game folder. That folder is what IF Hub receives:
    python C:/code/ifhub/tools/ship.py <game>           publish + register on the hub
    python C:/code/ifhub/tools/ship.py <game> --local   register only (local hub preview)
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import config, output, paths, process, test_results, web, web_setup

TRUE_VALUES = {"yes", "true", "1", "on", "blorb"}
STORY_SUFFIXES = (".z3", ".z4", ".z5", ".z8", ".zblorb", ".ulx", ".gblorb")
EXPORT_FILES = ("ifhub.conf", "play.html", "story.ni", "walkthrough.txt",
                "walkthrough_output.txt", "walkthrough-guide.txt", "tests.html")


def read_conf(path: Path) -> dict:
    """Flat `key = value` reader for ifhub.conf."""
    conf: dict[str, str] = {}
    if not path.exists():
        return conf
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("["):
            break
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        conf[k.strip()] = v.strip()
    return conf


# --- Inform 7 -----------------------------------------------------------------

def stage_compile(project_dir: Path, sound: bool, force: bool, compile_only: bool) -> None:
    cmd = [sys.executable, str(paths.TOOLS_DIR / "compile.py"), str(project_dir)]
    if sound:
        cmd.append("--sound")
    if force:
        cmd.append("--force")
    if compile_only:
        cmd.append("--compile-only")
    r = process.run(cmd)
    if r.returncode != 0:
        raise RuntimeError(f"compile failed (exit {r.returncode})")


def stage_test(project_dir: Path) -> bool:
    """Run whatever tests the game has. Returns True if anything ran."""
    ran = False
    py = sys.executable
    conf_file = project_dir / "tests" / "project.conf"

    if conf_file.exists():
        cfg = config.load_config(conf_file)
        seed = config.get_golden_seed(project_dir, "glulxe")

        # Walkthrough -> transcript -> guide (all copied to the game root)
        if cfg.primary.walkthrough and Path(cfg.primary.walkthrough).exists():
            print("  Running walkthrough...")
            ran = True
            wt_cmd = [py, str(paths.TOOLS_DIR / "run_walkthrough.py"), "--config", str(conf_file),
                      "--copy-output", str(project_dir)]
            if seed:
                wt_cmd.extend(["--seed", seed])
            r = process.run(wt_cmd)
            if r.returncode != 0:
                raise RuntimeError(f"walkthrough failed (exit {r.returncode})")

            wt_src_dir = project_dir / "tests" / "inform7"
            wt_output = wt_src_dir / "walkthrough_output.txt"
            wt_commands = wt_src_dir / "walkthrough.txt"
            if wt_output.exists() and wt_commands.exists():
                print("  Regenerating walkthrough guide...")
                guide_out = wt_src_dir / "walkthrough-guide.txt"
                process.run([py, str(paths.TOOLS_DIR / "generate-guide.py"),
                             "--walkthrough", str(wt_commands),
                             "--transcript", str(wt_output),
                             "-o", str(guide_out)])
                if guide_out.exists():
                    shutil.copy2(str(guide_out), str(project_dir / "walkthrough-guide.txt"))

        # Regtests -> test-results.json -> tests.html (ifPlayer report format)
        if cfg.regtest_file and Path(cfg.regtest_file).exists():
            print("  Running regtests...")
            ran = True
            r = process.run([py, str(paths.TOOLS_DIR / "run_tests.py"), "--config", str(conf_file),
                             "--all", "--json"], capture=True)
            if r.returncode != 0:
                if r.stdout:
                    print(r.stdout)
                if r.stderr:
                    print(r.stderr, file=sys.stderr)
                raise RuntimeError(f"regtests failed (exit {r.returncode})")
            if r.stdout and r.stdout.strip():
                hub_json = test_results.convert(json.loads(r.stdout), project_dir.name)
                json_out = project_dir / "test-results.json"
                json_out.write_text(json.dumps(hub_json, indent=2, ensure_ascii=False) + "\n",
                                    encoding="utf-8")
                print(f"  Wrote {json_out.name} ({hub_json['summary']['totalPassed']} passed, "
                      f"{hub_json['summary']['totalFailed']} failed)")
                from lib import report_adapter  # needs the ifplayer package
                html_out = project_dir / "tests.html"
                report_adapter.json_file_to_html(json_out, html_out, title=f"Tests — {project_dir.name}")
                print(f"  Wrote {html_out.name}")

    # ifPlayer .test files -> tests.html
    test_files = sorted(project_dir.glob("tests/*.test")) or sorted(project_dir.glob("tests/ifplayer/*.test"))
    if test_files:
        print(f"  Running ifPlayer tests ({len(test_files)} file(s))...")
        ran = True
        r = process.run([py, "-m", "ifplayer.cli", "test", *[str(f) for f in test_files],
                         "--html-report", str(project_dir / "tests.html"),
                         "--story-id", project_dir.name])
        if r.returncode != 0:
            raise RuntimeError(f"ifPlayer tests failed (exit {r.returncode})")

    return ran


def build_inform7(project_dir: Path, conf: dict, args) -> None:
    if not (project_dir / "story.ni").exists():
        raise RuntimeError(f"no story.ni in {project_dir}")
    sound = args.sound or (conf.get("sound", "").strip().lower() in TRUE_VALUES) \
        or (project_dir / "Sounds").is_dir()
    print(output.bold("--- compile"))
    stage_compile(project_dir, sound, args.force, args.compile_only)
    if args.compile_only or args.no_test:
        output.skip("tests skipped")
    else:
        print(output.bold("--- tests"))
        if not stage_test(project_dir):
            output.skip("no tests configured (tests/project.conf, tests/*.test)")


# --- Z-machine ----------------------------------------------------------------

def build_zmachine(project_dir: Path, conf: dict, args) -> None:
    """Wrap a story file in Parchment. `binary =` names it; a .js is used as-is."""
    binary = conf.get("binary", "")
    if not binary:
        found = [f for f in project_dir.iterdir() if f.suffix.lower() in STORY_SUFFIXES]
        if not found:
            raise RuntimeError("no story file: set `binary = <file>` in ifhub.conf")
        binary = found[0].name
    bin_path = project_dir / binary
    if not bin_path.exists():
        raise RuntimeError(f"story file not found: {bin_path}")

    print(output.bold("--- wrap"))
    parchment_dir = project_dir / "lib" / "parchment"
    parchment_dir.mkdir(parents=True, exist_ok=True)
    print("  Copying Parchment libraries...")
    web.copy_parchment_libs(parchment_dir)

    if bin_path.suffix.lower() == ".js":
        story_js = bin_path.name
        story_path = str(bin_path.relative_to(project_dir)).replace("\\", "/")
    else:
        story_js = f"{bin_path.name}.js"
        print(f"  Encoding {bin_path.name} -> lib/parchment/{story_js}...")
        web.write_story_js(bin_path, parchment_dir / story_js)
        story_path = f"lib/parchment/{story_js}"

    play_html = project_dir / "play.html"
    local_template = project_dir / "play-template.html"
    template = local_template if local_template.exists() else paths.WEB_DIR / "play-template.html"
    if not web_setup.check_overwrite(play_html, args.force):
        print(f"  Generating play.html from {template.name}...")
        web.substitute_template(template, play_html, {
            "__TITLE__": conf.get("title", project_dir.name),
            "__STORY_FILE__": story_js,
            "__STORY_PATH__": story_path,
            "__LIB_PATH__": "lib/parchment/",
        }, cache_bust=True)

    print()
    if web.validate_web_dir(project_dir):
        raise RuntimeError("play.html failed validation")
    output.skip("no CLI tests for Z-machine stories")


# --- Main ---------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Build an Inform 7 game or wrap a Z-machine story for local play and IF Hub.")
    parser.add_argument("game", help="Game folder name in this workspace, or a path")
    parser.add_argument("--no-test", action="store_true", help="Skip the test stage")
    parser.add_argument("--sound", action="store_true", help="Embed Sounds/*.ogg in a .gblorb (auto when ifhub.conf says so)")
    parser.add_argument("--force", action="store_true", help="Overwrite play.html")
    parser.add_argument("--compile-only", action="store_true", help="Compile the binary only; no web player, no tests")
    args = parser.parse_args()

    project_dir = paths.project_dir(args.game)
    if not project_dir.is_dir():
        print(f"ERROR: not a folder: {project_dir}", file=sys.stderr)
        sys.exit(1)
    conf = read_conf(project_dir / "ifhub.conf")
    engine = conf.get("engine", "inform7").lower()
    if engine not in ("inform7", "zmachine"):
        print(f"ERROR: ifhub.conf says engine = {engine}; this workspace builds inform7 and zmachine games.", file=sys.stderr)
        sys.exit(1)

    label = "Z-machine" if engine == "zmachine" else "Inform 7"
    print(output.bold(f"=== build {project_dir.name} ({label}) ==="))
    try:
        if engine == "zmachine":
            build_zmachine(project_dir, conf, args)
        else:
            build_inform7(project_dir, conf, args)
    except RuntimeError as e:
        print(output.red(output.bold(f"=== build failed: {e} ===")))
        sys.exit(1)

    print()
    print(output.bold("--- ready for IF Hub"))
    for name in EXPORT_FILES:
        if name == "story.ni" and engine == "zmachine":
            continue
        mark = "ok" if (project_dir / name).exists() else "--"
        print(f"  {mark:2}  {name}")
    if not (project_dir / "ifhub.conf").exists():
        output.warn("ifhub.conf is missing: the hub needs engine/title/description/tags in it")
    print()
    print(f"  Play locally:  python -m http.server 8000 --directory \"{project_dir}\"")
    print(f"  Ship to hub:   python {paths.to_posix(paths.HUB_ROOT / 'tools' / 'ship.py')} {project_dir.name}")


if __name__ == "__main__":
    main()
