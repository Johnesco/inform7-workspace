#!/usr/bin/env python3
"""Set up a Parchment web player for an Inform 7 project.

Copies the Parchment libraries from tools/web/parchment, base64-encodes the
compiled binary, and generates play.html from the template.

Usage:
    python tools/web/setup_web.py \
        --title "My Game" --ulx path/to/game.ulx --out path/to/project

    python tools/web/setup_web.py \
        --title "My Game" --blorb path/to/game.gblorb --out path/to/project

Safety: play.html is SKIPPED if it already exists
(they may contain custom CSS, effects, or hand-crafted content).
The game binary and Parchment libraries are always updated.
"""

import argparse
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import output, web, web_setup


def main():
    parser = argparse.ArgumentParser(description="Set up Parchment web player.")
    web_setup.add_common_args(parser)
    parser.add_argument("--ulx", help="Path to .ulx file")
    parser.add_argument("--blorb", help="Path to .gblorb file")
    parser.add_argument("--template", help="Custom play.html template")
    parser.add_argument("--mood", action="store_true", help="Copy mood-engine.js for mood theming")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    out_dir = Path(args.out)

    if args.blorb and args.ulx:
        print("Error: specify --ulx or --blorb, not both", file=sys.stderr)
        sys.exit(1)
    if not args.blorb and not args.ulx:
        print("Error: specify --ulx or --blorb", file=sys.stderr)
        sys.exit(1)

    # Determine binary
    if args.blorb:
        game_path = Path(args.blorb)
    else:
        game_path = Path(args.ulx)

    if not game_path.exists():
        print(f"Error: File not found: {game_path}", file=sys.stderr)
        sys.exit(1)

    game_basename = game_path.name
    story_js = f"{game_basename}.js"

    # Create output directories
    parchment_dir = out_dir / "lib" / "parchment"
    parchment_dir.mkdir(parents=True, exist_ok=True)

    # Copy Parchment libraries
    print("Copying Parchment libraries...")
    web.copy_parchment_libs(parchment_dir)

    # Copy mood engine if requested
    if args.mood:
        print("Copying mood-engine.js...")
        web.copy_mood_engine(parchment_dir)
        # The mood template links mood.css at the game root; seed one for a new
        # project so the overlay is a file the hub can show. Never overwrite.
        mood_css = out_dir / "mood.css"
        if not mood_css.exists():
            print("Seeding mood.css from the mood template...")
            shutil.copy2(str(script_dir / "templates" / "mood.css"), str(mood_css))

    # Base64-encode game binary
    print(f"Encoding {game_basename} -> {story_js}...")
    web.write_story_js(game_path, parchment_dir / story_js)

    # Generate play.html from template
    if args.template:
        template_path = Path(args.template)
    elif args.mood:
        template_path = script_dir / "templates" / "play-mood.html"
    else:
        template_path = script_dir / "play-template.html"
    play_html = out_dir / "play.html"

    if not web_setup.check_overwrite(play_html, args.force):
        # Warn if play.html has a custom overlay but no template was provided
        if play_html.exists() and args.force and not args.template:
            existing = play_html.read_text(encoding="utf-8")
            if any(m in existing for m in ["@property", "MutationObserver", "--mood-"]):
                output.warn("play.html contains a custom overlay but no --template was provided!")
                output.warn("  Create play-template.html to protect the overlay from --force rebuilds.")
        print("Generating play.html...")
        web.substitute_template(
            template_path, play_html,
            {
                "__TITLE__": args.title,
                "__STORY_FILE__": story_js,
                "__STORY_PATH__": f"lib/parchment/{story_js}",
                "__LIB_PATH__": "lib/parchment/",
            },
            cache_bust=True,
        )

    # Validate: play.html must load parchment.js
    html_text = play_html.read_text(encoding="utf-8")
    if re.search(r'src="[^"]*main\.js(\?[^"]*)?"', html_text) and \
       not re.search(r'src="[^"]*parchment\.js(\?[^"]*)?"', html_text):
        output.warn("play.html loads main.js instead of parchment.js!")
        output.warn("  Blorb sound will NOT work. Fix the template.")

    if "story_name" not in html_text:
        output.warn("play.html is missing story_name in parchment_options!")
        output.warn("  parchment.js will crash.")

    print()
    print(f"Web player ready at: {play_html}")
    print()
    print("To play locally:")
    print(f'  python -m http.server 8000 --directory "{out_dir}"')
    print("  # then open http://localhost:8000/play.html")


if __name__ == "__main__":
    main()
