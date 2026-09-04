# Parchment Troubleshooting

## `.ulx.js` Binary Wrapping Format

Parchment loads game binaries as `.ulx.js` files — JavaScript files that deliver the base64-encoded `.ulx` binary via a JSONP-style callback. The **required format** is:

```
processBase64Zcode('BASE64_ENCODED_BINARY')
```

- Single quotes around the base64 string (not double quotes)
- No `var` declaration, no semicolons — just the bare function call
- The base64 string is the raw `.ulx` file encoded with `base64 -w 0` (no line wrapping)
- **The entire file must be a single line** — no newlines inside the JS string literal (see below)
- The `processBase64Zcode` function is defined by Parchment's `main.js`; it decodes the base64 and boots the interpreter
- **Why not raw binary?** Parchment loads the game via a `<script src="...">` tag (JSONP pattern). This avoids CORS restrictions that would block `fetch()` on `file://` URLs. The Inform compilers output raw `.ulx` binaries and have no concept of Parchment — the wrapping step is a deployment concern, not skippable

**Converting from other formats:** Some older setups wrap the binary as `var defined_game_b64 = "...";` — this does NOT work with the standard Parchment loader used in our projects. To convert:

```bash
sed 's/^var defined_game_b64 = "/processBase64Zcode('"'"'/; s/";$/'"'"')/' old.ulx.js > new.ulx.js
```

## Error: "Error loading story 200"

**Cause:** The `.ulx.js` (or `.gblorb.js`) file has **newlines inside the JavaScript string literal**. The file exists (HTTP 200) but the JS is syntactically broken — single-quoted strings cannot contain literal newlines. The `processBase64Zcode` callback never fires, and Parchment reports "Error loading story 200" or hangs on the loading spinner.

Two common causes:
1. **`base64` without `-w 0`** — wraps output at 76 characters, inserting newlines throughout
2. **`echo` instead of `printf`** when building the file in multiple steps — `echo` appends a trailing newline after the opening `processBase64Zcode('`, putting a newline inside the string

**Safe one-shot approach** (recommended):
```bash
B64=$(base64 -w 0 game.ulx) && echo "processBase64Zcode('${B64}')" > game.ulx.js
```
This works because `$(...)` command substitution strips the trailing newline from `base64 -w 0`.

**Safe multi-step approach** (for large files):
```bash
printf "processBase64Zcode('" > game.ulx.js
base64 -w 0 game.ulx | tr -d '\n\r' >> game.ulx.js
printf "')\n" >> game.ulx.js
```

**Diagnosis:** Run `wc -l game.ulx.js` — it must report exactly **1 line**. If it reports more, the file has interior newlines and will fail.

## Error: "Error loading engine: 404"

**Cause:** Parchment's `main.js` dynamically loads the interpreter engine (`quixe.js` or `glulxe.js`) at runtime via the `lib_path` option. If these engine files are missing from `lib/parchment/`, the load fails with a 404.

**The required 12 files** in `lib/parchment/` are:

| File | Role | What happens if missing |
|------|------|------------------------|
| `jquery.min.js` | DOM library | Page fails to initialize |
| `main.js` | Game loader | No game loads at all |
| `main.css` | Layout styling | Game works but looks broken |
| `parchment.css` | Engine styling | Game works but looks broken |
| `parchment.js` | Engine variant | Fallback to quixe, may still work |
| **`quixe.js`** | **JS Glulx interpreter** | **"Error loading engine: 404"** |
| **`glulxe.js`** | **WASM Glulx interpreter** | **"Error loading engine: 404"** |
| `ie.js` | IE compatibility | Modern browsers unaffected |
| `bocfel.js` | Z-machine interpreter | Z-machine games won't load |
| `resourcemap.js` | Resource mapping | Blorb resources may not load |
| `zvm.js` | Z-machine VM | Z-machine games won't load |
| `waiting.gif` | Loading indicator | No loading animation |

The CSS and jQuery files produce visible errors if missing. The **engine files** (`quixe.js`, `glulxe.js`) are the sneaky ones — they're loaded asynchronously by `main.js`, so the page appears to load fine until the engine request returns 404.

**Fix:** Always copy all 12 library files. Use `setup_web.py` which handles this automatically.

## Sound Gotchas (Known Blockers)

1. **parchment.js vs main.js** — Parchment 2025.1 ships two JS files. `parchment.js` (134KB) has real AudioContext sound support. `main.js` (176KB) has only stub `glk_schannel_*` functions that throw errors and hardcodes `gestalt_Sound=0`. If `play.html` loads `main.js` instead of `parchment.js`, sound is silently disabled and the game prints `[Sound effect number N here.]` text fallback. **Always load `parchment.js`.** Both templates and `setup_web.py` now validate this.

2. **Colon in story title** — Inform 7 derives filenames from the title. A colon (`:`) in the title (e.g. `"Zork I: The Great"`) produces invalid filenames on Windows, causing `inblorb` to fail. **Use a dash instead** (e.g. `"Zork I - The Great"`). `compile.py` now checks for this and exits early with a clear message.

3. **Sounds/ directory location** — `compile.py --sound` expects `.ogg` files at `project/Sounds/` (project root), NOT inside `.materials/Sounds/`. If your sounds are in `.materials/`, copy them: `cp -r project/name.materials/Sounds project/Sounds`. `compile.py` now checks for this before starting the expensive I7 compilation.

4. **Browser cache after rebuild** — After changing Parchment JS files (e.g. switching main.js → parchment.js), browsers may serve the cached old version. `setup_web.py` and `compile.py` append `?v=<timestamp>` cache-busting params to `.js` and `.css` references. If testing manually, use Ctrl+Shift+R or an incognito window.

5. **Missing `story_name` in parchment_options** — `parchment.js` calls `.substring()` on `parchment_options.story_name` to detect the file type (`.ulx.js`, `.gblorb.js`, `.z3.js`). If `story_name` is missing or undefined, you get `TypeError: Cannot read properties of undefined (reading 'substring')`. Every play page must include `story_name` in its `parchment_options`. For dynamic pages (like `ifhub/play.html`), derive it from the binary path: `story_name: binaryPath.split('/').pop()`.

## MutationObserver Gotchas

6. **`.Input` spans not available in WASM mode** — Parchment's Emglken WASM engine does **not** wrap user input in `.Input` CSS class spans. Code that queries `.BufferWindow .Input` elements (e.g., `document.querySelectorAll('.BufferWindow .Input')`) will find nothing. Instead, track user input by watching added nodes in the MutationObserver — the user's command text appears as a regular element node immediately before the game's response in the DOM mutation sequence. Store each node's text in a variable (`lastNodeText`) and check it when detecting game responses.

## Note on `file://` Protocol

Opening `play.html` directly as a `file://` URL may also fail due to browser CORS restrictions on local JSONP requests. Always use a local HTTP server (`python -m http.server`).
