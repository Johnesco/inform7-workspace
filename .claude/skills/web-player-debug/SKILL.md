# Web Player Debug (Parchment Troubleshooting)

globs: ["**/play.html", "**/play-template.html", "**/*.ulx.js", "**/*.gblorb.js", "**/parchment/**", "site/**", "tools/web/**"]

## Quick Checklist

When debugging Parchment web player issues:

1. **"Error loading story 200"** — `.ulx.js` has newlines inside the string. Must be exactly 1 line (`wc -l`)
2. **"Error loading engine: 404"** — Missing `quixe.js` or `glulxe.js` in `lib/parchment/`. Need all 12 files
3. **Sound silent** — Using `main.js` instead of `parchment.js`. Must load `parchment.js` for AudioContext
4. **Colon in title** — Breaks `inblorb` on Windows. Use dash instead
5. **`Sounds/` not found** — Must be at project root, not `.materials/Sounds/`
6. **Browser cache** — Ctrl+Shift+R or incognito after changing JS files
7. **`story_name` undefined** — Every play page needs `story_name` in `parchment_options`
8. **`.Input` spans missing** — WASM mode doesn't use `.Input` class. Track via MutationObserver node text
9. **`file://` CORS** — Always serve via `python -m http.server`, never open as `file://`

See `reference/parchment-troubleshooting.md` for full details and code examples.
