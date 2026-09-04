# Build Pipeline Guide

End-to-end walkthrough: from writing Inform 7 source to playing in a browser with sound.

## Overview

```
story.ni ──► inform7.exe ──► story.i6 ──► inform6.exe ──► game.ulx
                                                              │
                                                      base64 -w 0
                                                              │
                                                        game.ulx.js
                                                              │
                                              ┌───────────────┤
                                              ▼               ▼
                                     Project web/       ifhub deploy
                                     (local play)       (GitHub Pages)
```

## Step 1: Write the Source

Create `story.ni` in your project directory:

```
projects/<game>/story.ni
```

First line must be the title and author:

```inform7
"My Game" by "Author Name"
```

See `reference/syntax-guide.md` for Inform 7 syntax. Key rules:

- Use `[apostrophe]`, `[quotation mark]`, `[bracket]` instead of literal special characters in text
- Organize with `Part`, `Chapter`, `Section` headings
- Do NOT create `.inform` bundles — we compile directly from `.ni` files

## Step 2: Compile

Two-step CLI compilation. No IDE needed.

### Step 2a: Inform 7 → Inform 6

```bash
"/c/Program Files/Inform7IDE/Compilers/inform7.exe" \
    -internal "/c/Program Files/Inform7IDE/Internal" \
    -source projects/<game>/story.ni \
    -o projects/<game>/story.i6 \
    -silence
```

Exit code 0 = success. Any errors print to stderr with line numbers.

### Step 2b: Inform 6 → Glulx

```bash
"/c/Program Files/Inform7IDE/Compilers/inform6.exe" -w -G \
    projects/<game>/story.i6 \
    projects/<game>/<game>.ulx
```

Flags: `-w` suppresses warnings, `-G` targets Glulx format (.ulx).

### Step 2c: Clean Up

```bash
rm projects/<game>/story.i6
```

The `.i6` file is an intermediate artifact. Only `story.ni` (source) and `<game>.ulx` (binary) matter.

### One-Liner

```bash
cd projects/<game> && \
"/c/Program Files/Inform7IDE/Compilers/inform7.exe" \
    -internal "/c/Program Files/Inform7IDE/Internal" \
    -source story.ni -o story.i6 -silence && \
"/c/Program Files/Inform7IDE/Compilers/inform6.exe" -w -G story.i6 <game>.ulx && \
rm story.i6
```

## Step 3: Set Up the Web Player

Parchment is a browser-based Glulx interpreter. Each project gets Parchment libraries and the encoded game binary at the project root (flat layout, no `web/` subdirectory).

### Option A: Use the Setup Script

```bash
python tools/web/setup_web.py \
    --title "My Game" \
    --ulx projects/<game>/<game>.ulx \
    --out projects/<game>
```

This creates:

```
projects/<game>/
├── play.html                  ← Ready-to-serve player page
└── lib/parchment/
    ├── jquery.min.js
    ├── main.js
    ├── main.css
    ├── parchment.js
    ├── parchment.css
    ├── quixe.js               ← JS Glulx interpreter
    ├── glulxe.js              ← WASM Glulx interpreter
    └── <game>.ulx.js          ← Base64-encoded game binary
```

All 7 Parchment library files are required. Missing `quixe.js` or `glulxe.js` causes "Error loading engine: 404".

### Option B: Manual Setup

If the project already has a web player, just update the binary:

```bash
B64=$(base64 -w 0 projects/<game>/<game>.ulx) && \
echo "processBase64Zcode('${B64}')" > projects/<game>/lib/parchment/<game>.ulx.js
```

The `.ulx.js` format is a JSONP callback — single quotes, no semicolons:

```
processBase64Zcode('BASE64_ENCODED_BINARY')
```

**Critical: the file must be exactly 1 line.** Any newline inside the JS string literal causes "Error loading story 200" — the file loads (HTTP 200) but the JS is broken and `processBase64Zcode` never fires. The one-shot `B64=$(...)` approach above is safe because command substitution strips trailing newlines. If building the file in multiple steps, use `printf` (not `echo`, which adds trailing newlines) and pipe base64 through `tr -d '\n\r'`:

```bash
printf "processBase64Zcode('" > game.ulx.js
base64 -w 0 game.ulx | tr -d '\n\r' >> game.ulx.js
printf "')\n" >> game.ulx.js
```

Verify with `wc -l game.ulx.js` — must report **1**.

## Step 4: Test Locally

```bash
python -m http.server 8000 --directory projects/<game>
# Open http://localhost:8000/play.html
```

Do NOT open `play.html` as a `file://` URL — browsers block the JSONP script loading due to CORS.

## Step 5: Add Sound (Optional)

> **Note (March 2026)**: All sound games now use **native Glk/blorb sound** instead of the JS overlay described below. Compile with `python tools/compile.py <game> --sound` to embed `.ogg` audio in a `.gblorb` binary. The overlay system has been archived to `reference/sound-overlay/`. The instructions below are retained for historical reference only.

Sound uses a JavaScript overlay that watches the game's DOM output. Two trigger modes:

| Mode | How It Works | Recompile Needed? |
|------|-------------|-------------------|
| **Text matching** | Regex patterns matched against game output | No |
| **Style_user1** | Hidden commands emitted from `story.ni` | Yes |

### 5a: Copy the Sound Engine

```bash
python tools/web/setup_web.py --sound ...
# Or manually:
cp tools/web/sound-engine.js projects/<game>/lib/
```

### 5b: Create Sound Config

Create `projects/<game>/lib/sound-config.js`:

```javascript
SoundEngine.init({
  storageKey: '<game>-audio-muted',

  // Style_user1 triggers (precise, from story.ni)
  sfx: {
    glass: { src: 'audio/sfx/glass.mp3', volume: 0.4 }
  },

  // Text-matching triggers (regex against game output)
  textTriggers: [
    { id: 'bird', pattern: /chirping of a song bird/i,
      src: 'audio/sfx/bird.mp3', volume: 0.25, cooldownMs: 10000 }
  ]
});
```

### 5c: Add Audio Files

```
projects/<game>/audio/
└── sfx/
    ├── glass.mp3
    └── bird.mp3
```

Format: MP3. Keep effects short (1-5 seconds). CC0 sources: [BigSoundBank](https://bigsoundbank.com), [Freesound](https://freesound.org).

### 5d: Update play.html

Add to the `<style>` block:

```css
.Style_user1 { display: none; }
```

Add before `</body>`:

```html
<script src="lib/sound-engine.js"></script>
<script src="lib/sound-config.js"></script>
```

### 5e: Add Style_user1 Triggers to story.ni (If Using)

```inform7
Include Glulx Text Effects by Emily Short.

To issue sound command (T - text):
	say "[first custom style][T][roman type]".
```

Then emit commands at the desired moments:

```inform7
Instead of opening the coffin:
	issue sound command "SFX:creak";
	say "The lid groans open."
```

The `SFX:` prefix is required. The id after it must match a key in the `sfx` object in `sound-config.js`. After adding Style_user1 triggers, recompile (Step 2) and update the web binary (Step 3b).

Text-matching triggers require no source changes and no recompilation.

### 5f: Test Sound Locally

```bash
python -m http.server 8000 --directory projects/<game>
```

Play through to the trigger point. Verify:
- Sound plays at the right moment
- Style_user1 text is invisible (no "SFX:..." visible in game output)
- Mute button appears and persists state

## Step 6: Deploy to IF Hub

IF Hub serves all games through a unified browser interface at GitHub Pages.

### 6a: Create a Landing Page

Copy `tools/web/landing-template.html` to `projects/<game>/landing.html` and fill in the `ifhub:*` meta tags:

```html
<meta name="ifhub:title" content="My Game">
<meta name="ifhub:meta" content="A Subtitle">
<meta name="ifhub:description" content="Landing page description.">
```

Add game-specific content (prose, version history, community links, etc.) to the HTML body.

### 6b: Register the Game

Add an entry to `site/games.json`:

```json
{
  "id": "<game>",
  "title": "My Game",
  "sourceLabel": "<game>.ni",
  "source": "games/<game>/story.ni",
  "binary": "games/<game>/<game>.ulx.js",
  "sound": "blorb",
  "landing": "projects/<game>/landing.html",
  "deploy": {
    "source": "projects/<game>/story.ni",
    "binary": "projects/<game>/lib/parchment/<game>.ulx.js",
    "walkthroughDir": "projects/<game>"
  }
}
```

Set `"sound": "blorb"` for games with native Glk sound. Omit `walkthroughDir` if the game has no walkthrough files.

### 6c: Run the Deploy

```bash
python /c/code/ifhub/tools/publish.py <game-name>
```

This publishes the game to GitHub Pages. The hub serves games in-place from each project's own GitHub Pages URL — no file copying into `site/games/` is needed.

### 6d: Test the Hub Locally

```bash
python -m http.server 8000 --directory ifhub
# Open http://localhost:8000/
```

Verify:
- Game appears in the dropdown on `app.html`
- Game loads and plays correctly
- Sound controls appear (if sound-enabled)
- Standalone page works at `games/<game>/index.html`

### 6e: Push to Deploy

```bash
python /c/code/ifhub/tools/push_hub.py <game-name>
```

GitHub Pages deploys automatically from the push.

## Quick Reference: Common Operations

### Recompile and Update Web After Editing story.ni

```bash
cd projects/<game>

# Compile
"/c/Program Files/Inform7IDE/Compilers/inform7.exe" \
    -internal "/c/Program Files/Inform7IDE/Internal" \
    -source story.ni -o story.i6 -silence && \
"/c/Program Files/Inform7IDE/Compilers/inform6.exe" -w -G story.i6 <game>.ulx && \
rm story.i6

# Update web binary
B64=$(base64 -w 0 <game>.ulx) && \
echo "processBase64Zcode('${B64}')" > web/lib/parchment/<game>.ulx.js
```

### Update ifhub After Recompiling

```bash
python /c/code/ifhub/tools/publish.py <game-name>
```

### Add a Text-Matching Sound Trigger (No Recompile)

Edit `projects/<game>/lib/sound-config.js` — add to `textTriggers`:

```javascript
{ id: 'door', pattern: /door creaks/i,
  src: 'audio/sfx/door.mp3', volume: 0.3, cooldownMs: 5000 }
```

Drop the audio file in `web/audio/sfx/`. Refresh the browser.

### Add a Style_user1 Sound Trigger (Requires Recompile)

1. Add to `sfx` in `sound-config.js`:
   ```javascript
   creak: { src: 'audio/sfx/creak.mp3', volume: 0.3 }
   ```

2. Add to `story.ni`:
   ```inform7
   issue sound command "SFX:creak";
   ```

3. Drop the audio file in `web/audio/sfx/`
4. Recompile and update web binary (see above)

### Change Volume or Cooldown (No Recompile)

Edit values directly in `sound-config.js`. Volume is 0.0-1.0, multiplied by master volume.

## File Locations

| File | Location | Purpose |
|------|----------|---------|
| I7 compiler | `/c/Program Files/Inform7IDE/Compilers/inform7.exe` | Compiles .ni → .i6 |
| I6 compiler | `/c/Program Files/Inform7IDE/Compilers/inform6.exe` | Compiles .i6 → .ulx |
| Internal | `/c/Program Files/Inform7IDE/Internal` | Extensions, templates |
| Setup script | `tools/web/setup_web.py` | Bootstrap web player |
| Play template | `tools/web/play-template.html` | Single template for all play pages (projects + hub) |
| Web validator | `tools/validate_web.py` | Post-build validation (7 checks) |
| Deploy scripts | `tools/deploy/*.py` | Asset copying + page generation (Python) |
| Publisher | `tools/publish.py` | Deploys game to GitHub Pages |
| Game registry | `site/games.json` | Game metadata, deploy paths, hub UI config |
| Sound editing guide | `reference/sound.md` | Trigger modes, architecture, editing |

## Related Documentation

- `CLAUDE.md` — Project conventions, compiler details, Parchment troubleshooting
- `reference/sound.md` — Sound architecture, trigger editing guide, decision record
- `site/README.md` — IF Hub deployment details, games.json schema, sound wiring
