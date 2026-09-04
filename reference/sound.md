# Sound in Inform 7 Web Games

Research into browser-based sound for Inform 7 games. All IF Hub sound games now use **native Glk/blorb sound** via Parchment 2025.1. The previous JavaScript overlay system (sound-engine.js, ambient-audio.js, sound-config.js) has been archived to `reference/sound-overlay/` — see its README for what it was and why it was replaced. This document retains the full technical reference for both approaches.

## Context

IF Hub games originally used a custom JavaScript overlay for sound — a shared engine plus per-game config that sat outside the interpreter, watched the DOM via MutationObserver, and played HTML5 Audio. As of March 2026, all sound games have been converted to native blorb and the overlay code has been removed from active use (archived at `reference/sound-overlay/`).

**Date**: February 2026 (overlay evaluation), March 2026 (native blorb migration, overlay archived)

## The Landscape: What Exists

### 1. Parchment (curiousdannii) — Native Blorb Sound Works

**Repo**: github.com/curiousdannii/parchment (MIT license)

The Jan 2025 release (2025.1.14) was a major architectural overhaul:
- Replaced Quixe/ZVM with **Glulxe** (WASM) + **Bocfel** via Emglken
- Uses **RemGlk-rs** (Rust port of RemGlk) as the Glk layer
- Uses **AsyncGlk** (TypeScript Glk library) for the browser-side UI

**Sound status (updated March 2026)**: The browser-side sound plumbing **is functional**. Parchment 2025.1 can play sounds natively when the game binary is a `.gblorb` (Glulx blorb) with embedded audio resources. The AudioContext-based playback, Blorb parser, and sound channel management all work end-to-end in the browser.

**However**, two upstream bugs in the Inform 7 toolchain prevent this from working out of the box:
1. **Colon in title bug**: `Release.blurb` generates a `storyfile leafname` containing colons from the game title, producing an invalid filename on Windows (e.g., `"Zork I - The Great Underground E.gblorb"`)
2. **ULX-instead-of-gblorb bug**: The `base64` line in `Release.blurb` encodes `output.ulx` (the naked binary without sounds) instead of `output.gblorb` (the full blorb with embedded audio), so the web player gets a game file with no sound resources

**Workaround**: Generate the `.blurb` file manually with `generate_blurb.py`, run `inblorb` to create the `.gblorb`, then base64-encode the `.gblorb` instead of the `.ulx`. This is automated via `compile.py --sound`.

**Assessment**: **Native blorb sound works today** with the CLI workaround. When the upstream bugs are fixed, the standard IDE Release pipeline will produce correct blorb-encoded web players automatically.

### 2. Quixe (erkyrath) — Stalled

**Repo**: github.com/erkyrath/quixe (MIT license)

- PR #3 ("Implement graphics and sound" by eevee) has been **open since 2014**
- Graphics were merged in 2015 (Quixe 2.1.0), but sound was deferred
- The GlkOte companion PR #1 has a partial Web Audio API implementation (AudioChannel, volume control, multi-sound playback) but is also **open since 2014**
- Sound notifications, Vorbis decoding, and MOD format are unimplemented
- Last activity: 2015

**Assessment**: Dead end. The PRs have been open for 10+ years. Quixe is being superseded by the Glulxe-via-WASM approach in new Parchment anyway.

### 3. Bisquixe (mathbrush/Brian Rushton) — Works But IDE-Only

- Enhanced Quixe with full Glk sound functions (channels, volume, notifications)
- Uses "Simple Multimedia Effects" Inform 7 extension
- Implements all standard Glk sound including `sound-notify` and `volume-notify` events
- **Actually works** — the game "Transparent" plays online with sound via Bisquixe

**But**:
- Requires the **Inform IDE** — activated via `Release along with the 'Bisquixe' interpreter`
- Audio files need **dual format** (`.ogg` in materials/Sounds, `.mp3` in release/Sounds)
- No evidence of CLI compilation support — designed around IDE "Release" workflow
- Replaces our entire Parchment-based pipeline
- Not clear where the source code lives (no obvious GitHub repo found)
- Single-developer project, unclear maintenance status

**Assessment**: Proves the concept works, but the IDE dependency and pipeline incompatibility make it impractical for our CLI-based workflow.

### 4. Vorple — Mature But Different Architecture

**Repo**: github.com/vorple/inform7 (MIT license)

- Complete multimedia toolkit with its own custom interpreter
- Rich sound API: `play music file`, `play sound effect`, playlists, looping, volume, status queries
- Compatible with our Inform 7 v10.1.2
- Well documented, actively maintained

**But**:
- Requires **replacing Parchment entirely** with the Vorple interpreter
- Designed around IDE "Release" workflow
- Sound is authored in `story.ni` — couples audio to game source
- Zone-based ambient crossfading still needs custom logic regardless
- Would require reworking the entire web player pipeline

**Assessment**: Best existing solution for sound-in-source, but wrong architecture for our needs. We'd be trading one custom system for a larger dependency.

## Summary Matrix

| System | Sound Works? | Open Source? | CLI Compatible? | Our Pipeline? | Active? |
|--------|-------------|-------------|----------------|--------------|---------|
| **Parchment 2025.1 (native blorb)** | Yes (with workaround) | MIT | Yes | Yes | Active |
| **Quixe** | No (PRs stalled 10yr) | MIT | Yes | Yes | Stalled |
| **Bisquixe** | Yes | Unknown | No (IDE-only) | No | Unclear |
| **Vorple** | Yes | MIT | No (IDE "Release") | No | Active |
| **Our custom overlay** | Yes | N/A | Yes | Yes | Ours |

## Decision (Updated March 2026)

**All sound games now use native Glk/Blorb sound.** As of March 2026, zork1 (v3) and feverdream have been converted from the JS overlay to native blorb. The JS overlay infrastructure is retained for potential future use — set `"sound": "overlay"` in `games.json` to activate it for a new game.

**Two sound approaches are available**, both integrated into our pipeline:

### 1. Native Blorb Sound (Parchment 2025.1)

Parchment's built-in sound works when the game binary is a `.gblorb` with embedded audio. The game's `story.ni` declares sounds via standard Inform 7 syntax (`Sound of X is the file "Y.ogg"`), and the interpreter handles playback via AudioContext.

**Use when**: The game has Inform 7 sound declarations and you want embedded audio with no external JS dependencies.

**CLI command**: `python tools/compile.py zork1 --sound`

**Tradeoffs**:
- Larger file size (~25MB for zork1 with 25 sounds vs ~1.3MB without)
- Requires `.ogg` sound files in `project/Sounds/`
- Sound timing is controlled by the game engine (Glk sound channels)
- Workaround needed for two upstream Inform 7 bugs (automated by `generate_blurb.py`)

### 2. Custom JavaScript Overlay (sound-engine.js)

Our MutationObserver-based approach watches the DOM and plays HTML5 Audio independently of the interpreter.

**Use when**: No source changes needed, hot-swappable triggers, fine-grained control over timing/volume/zones, or the game doesn't have Inform 7 sound declarations.

**CLI command**: `python tools/compile.py zork1` (then add sound-config.js manually)

**Tradeoffs**:
- Requires per-game JavaScript configuration
- Text-matching triggers can misfire on similar text
- Sound files served separately (not embedded in game binary)

### When to use which

**Native blorb is the default** for all sound games. Use the JS overlay only when you need hot-swappable text-matching triggers or standalone ambient crossfading without game source changes.

| Criterion | Native Blorb | JS Overlay |
|---|---|---|
| Sound declarations in story.ni | Required | Not needed |
| File format | .ogg (embedded in .gblorb) | .mp3 (separate files) |
| Total file size | Larger (~25MB) | Smaller (~1.3MB + audio) |
| Trigger precision | Engine-controlled | Regex or Style_user1 |
| Hot-swappable without recompile | No | Yes (text triggers) |
| Zone-based ambient crossfading | Built in (Glk channels) | Yes (ambient-audio.js) |
| Works offline (single file) | Yes (all embedded) | No (needs audio files) |
| games.json sound value | `"blorb"` | `"overlay"` |
| Hub deployment config needed | No | Yes (legacy) |

Both approaches can coexist in the same project. The JS overlay will work regardless of whether the game binary is `.ulx` or `.gblorb`.

### Future

When the two upstream Inform 7 bugs are fixed:
1. The colon-in-title filename bug
2. The ULX-encoded-instead-of-gblorb bug

...the manual `generate_blurb.py` + `inblorb` steps become unnecessary. The standard IDE Release pipeline will encode the `.gblorb` automatically, and `compile.py --sound` can be simplified to just pass the IDE-generated blorb to `setup_web.py`.

## Native Blorb Sound Architecture

### How It Works

1. **story.ni** declares sounds: `Sound of forest-ambient is the file "forest.ogg".`
2. **inform7** compiles the declarations into Glk sound opcodes in the game binary
3. **generate_blurb.py** parses story.ni, assigns resource IDs (starting from 3), generates a `.blurb` file
4. **inblorb** packages the `.ulx` game binary + `.ogg` sound files into a single `.gblorb` blorb file
5. **setup_web.py --blorb** base64-encodes the `.gblorb` into a `.gblorb.js` file
6. **Parchment 2025.1** loads the blorb, parses the resource map, and plays sounds via AudioContext when the game issues Glk sound channel calls

### Upstream Bugs (Inform 7 v10.1.2)

**Bug 1: Colon in title produces invalid filename**

The `Release.blurb` file uses `storyfile leafname` with the game title, which may contain colons. On Windows, colons are illegal in filenames. Example: `"Zork I - The Great Underground E.gblorb"` causes the release to fail.

**Workaround**: Use `generate_blurb.py` which generates a sanitized blurb without the leafname directive.

**Bug 2: ULX encoded instead of gblorb**

The `base64` line in `Release.blurb` encodes `output.ulx` (the naked game binary) instead of `output.gblorb` (the full blorb with embedded sounds). The resulting `.gblorb.js` file contains only the game code with no sound resources.

```
# What Release.blurb generates (BROKEN):
base64 "zork1.inform\Build\output.ulx" to "...\Zork I - The Great Underground E.gblorb.js"

# What it should generate:
base64 "zork1.inform\Build\output.gblorb" to "...\zork1.gblorb.js"
```

**Workaround**: `compile.py --sound` runs `generate_blurb.py` + `inblorb` + `setup_web.py --blorb` to produce a correct blorb-encoded web player.

### Resource ID Mapping

Sound resource IDs are assigned by the Inform 7 compiler based on declaration order in `story.ni`. IDs 1 and 2 are reserved (cover image and small cover). Sound IDs start at 3.

The `generate_blurb.py` script parses declarations in source order to match the compiler's assignment. This has been validated against the IDE-generated `Release.blurb` — the IDs match exactly.

### File Size Impact

Blorb-encoded games are significantly larger because all sound files are embedded:

| Game | .ulx | .gblorb | .gblorb.js (base64) |
|---|---|---|---|
| zork1 (25 sounds) | ~1.3 MB | ~23 MB | ~31 MB |

## Our Sound Architecture (JS Overlay)

The custom overlay consists of independent JavaScript modules that observe the DOM and play HTML5 Audio. The shared sound engine lives at `tools/web/sound-engine.js` and is copied into each project. Each game provides its own `sound-config.js` with trigger definitions.

### sound-engine.js — Shared Sound Effects Engine

**Source of truth**: `tools/web/sound-engine.js` (copied to each project's `web/lib/`)

Supports two trigger modes:

| Mode | Trigger | Best For |
|------|---------|----------|
| **Style_user1** | `<span class="Style_user1">SFX:id</span>` in DOM | Precise, author-controlled triggers from `story.ni` |
| **Text matching** | Regex patterns against `.BufferWindow` text | Ambient/incidental sounds tied to prose |

Features:
- MutationObserver on `.BufferWindow` (game text output)
- Per-trigger cooldown to prevent spam (text triggers)
- ifhub integration (`window.SOUND_AUDIO_BASE`, `window.ifhubSfx` API)
- Standalone mute button with localStorage persistence (hidden in ifhub mode)

### sound-config.js — Per-Game Trigger Definitions

The only file that differs between games. Calls `SoundEngine.init()` with game-specific triggers:

```javascript
SoundEngine.init({
  storageKey: 'mygame-audio-muted',

  // Style_user1 triggers (precise, from story.ni via Glulx Text Effects)
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

#### Editing Sound Triggers

**To add a new text-matching trigger**, add an entry to the `textTriggers` array:

```javascript
{ id: 'unique-id',              // Used for cooldown tracking
  pattern: /regex pattern/i,    // Matched against game output text
  src: 'audio/sfx/file.mp3',   // Path to audio file (relative to web/)
  volume: 0.3,                  // 0.0–1.0 (scaled by master volume)
  cooldownMs: 5000 }            // Minimum ms between plays (prevents spam)
```

Tips for text triggers:
- Use case-insensitive patterns (`/i` flag) — game output capitalization varies
- Match the most specific phrase possible to avoid false positives
- Use longer cooldowns (10000–30000ms) for triggers that could fire repeatedly
- One sound plays per DOM node — if multiple patterns match the same text, only the first wins

**To add a new Style_user1 trigger**, add an entry to the `sfx` object and emit the command from `story.ni`:

```javascript
// In sound-config.js:
sfx: {
  glass: { src: 'audio/sfx/glass.mp3', volume: 0.4 },
  creak: { src: 'audio/sfx/creak.mp3', volume: 0.3 }
}
```

```inform7
[In story.ni — requires Glulx Text Effects extension:]
Include Glulx Text Effects by Emily Short.

To issue sound command (T - text):
	say "[first custom style][T][roman type]".

Instead of opening the door:
	issue sound command "SFX:creak";
	say "The door creaks open."
```

The `SFX:` prefix is required. The id after it must match a key in the `sfx` object. The CSS rule `.Style_user1 { display: none; }` must be present in `play.html` to hide the command text.

Style_user1 triggers have no cooldown — they fire every time the game emits the command. This is intentional: since the game author controls when they fire, spam prevention is the author's responsibility.

**To change volume or cooldown**, edit the values directly in `sound-config.js`. No recompilation needed (these are JavaScript-side settings). Volume values are 0.0–1.0 and are multiplied by the master volume (set by ifhub's volume slider or defaulting to 1.0).

**To remove a trigger**, delete its entry from the config. For Style_user1 triggers, also remove the `issue sound command` call from `story.ni` (optional — orphaned commands are silently ignored).

#### Audio File Guidelines

- **Format**: MP3 (universal browser support)
- **License**: CC0 recommended. [BigSoundBank](https://bigsoundbank.com) and [Freesound](https://freesound.org) are good sources
- **Location**: `project/web/audio/sfx/` for sound effects, `project/web/audio/` for ambient loops
- **Size**: Keep effects short (1–5 seconds). Ambient loops can be longer but compress well
- **Naming**: Use descriptive lowercase names matching the trigger id (e.g., `glass.mp3` for trigger id `glass`)

### ambient-audio.js — Room-Based Background Music (Optional)

Per-game module (not shared). Only Zork1 v3 uses this currently.

- **Trigger**: MutationObserver on `.GridWindow` (GlkOte status bar) detects room name changes
- **Behavior**: Maps room names to audio zones, crossfades between zones on room transitions
- **Features**: 1-second fade transitions, autoplay-block recovery, localStorage-persisted mute, ifhub API mode

### Why MutationObserver?

The overlay approach observes Parchment's DOM output rather than hooking into the interpreter. This gives us:
- **Interpreter independence**: Works with Quixe, Glulxe, or any future Parchment backend
- **Flexible coupling**: Text triggers need no source changes; Style_user1 triggers give precise control when needed
- **Hot-swappable**: Audio config can change without recompiling (for text triggers)
- **Graceful degradation**: Missing audio files don't crash the game

### Adding Sound to a New Project

1. Copy the sound engine: `python tools/web/setup_web.py --sound ...` (or manually copy `tools/web/sound-engine.js` to `project/web/lib/`)
2. Create `project/web/lib/sound-config.js` with trigger definitions (see template above)
3. Create audio assets in `project/web/audio/sfx/`
4. Add to `play.html`:
   - CSS: `.Style_user1 { display: none; }` (in `<style>` block)
   - Scripts: `<script src="lib/sound-engine.js"></script>` and `<script src="lib/sound-config.js"></script>` before `</body>`
5. If using Style_user1 triggers: add `Include Glulx Text Effects by Emily Short` and the `issue sound command` phrase to `story.ni`
6. For ifhub deployment: set `"sound": "overlay"` in `games.json`

### File Locations

```
tools/web/
└── sound-engine.js              ← Source of truth for the shared engine

projects/<game>/
├── audio/                       ← Ambient loops (optional)
│   └── sfx/                     ← Sound effects
├── lib/
│   ├── sound-engine.js          ← Copied from tools/web/
│   ├── sound-config.js          ← Game-specific triggers (EDIT THIS)
│   └── ambient-audio.js         ← Room-based music (optional, per-game)
└── play.html                    ← Loads sound scripts after Parchment
```

## Interpreter Compatibility

Our overlay watches `.GridWindow`, `.BufferWindow`, and `.Style_user1` — CSS classes produced by the GlkOte and AsyncGlk display libraries. Both libraries produce identical class names, confirmed in source:

```javascript
// GlkOte (erkyrath/glkote, glkote.js)
if (win.type == 'grid')    typeclass = 'GridWindow';
if (win.type == 'buffer')  typeclass = 'BufferWindow';
// Style mapping: 'user1' → 'Style_user1', 'user2' → 'Style_user2'

// AsyncGlk (curiousdannii/asyncglk, windows.ts)
const window_types = { buffer: 'BufferWindow', grid: 'GridWindow', graphics: 'GraphicsWindow' }
// Style mapping: identical to GlkOte
```

Any interpreter using either display layer will work with the overlay:

| Engine / Platform | Display Layer | Compatible? | Active? |
|---|---|---|---|
| **Parchment (current)** | AsyncGlk | Yes | Active (Jan 2025 overhaul) |
| **Parchment (older / our local copy)** | GlkOte | Yes | Superseded but still deployed |
| **Quixe (standalone)** | GlkOte (bundled) | Yes | Active (June 2025 update) |
| **Bisquixe** | GlkOte (via Quixe) | Yes | Active |
| **iplayif.com** | AsyncGlk (is Parchment) | Yes | Active |
| **Borogove IDE preview** (non-Vorple) | Parchment | Yes | Active |
| **All Emglken interpreters** (Bocfel, Glulxe, Git, Hugo, Scare, TADS) | AsyncGlk | Yes | Active |
| **Vorple** | Haven (own classes) | No | Active |
| **HugoJS (standalone)** | Haven | No | Maintained |
| **Ink / inkjs** | Own HTML (choice-based) | No | Active |
| **TADS native Web UI** | Own framework | No | Maintained |

The incompatible interpreters all use their own display libraries with different CSS classes. Vorple games already have their own multimedia system, so the gap is not a practical concern.

## Style_user1 Sound Commands

Glk defines two custom text styles (`user1`, `user2`) reserved for application use. Both GlkOte and AsyncGlk render them as `<span class="Style_user1">`. This enables **explicit sound commands from game logic** — invisible to the player, detectable by the overlay.

**Status**: Infrastructure available but no games currently use it. Fever Dream was converted to native blorb sound in March 2026 (previously used Style_user1). Zork1 was converted from text-matching overlay to native blorb. Both trigger modes remain functional in the shared sound engine for future use.

### How It Works

**In `story.ni`** (using the "Glulx Text Effects" extension by Emily Short):
```inform7
Include Glulx Text Effects by Emily Short.

To issue sound command (T - text):
	say "[first custom style][T][roman type]".

Instead of opening the coffin:
	issue sound command "SFX:coffin-creak";
	say "The lid groans open."
```

**In CSS** (hide from player):
```css
.Style_user1 { display: none; }
```

**In sound-config.js** (map command to audio):
```javascript
sfx: {
  'coffin-creak': { src: 'audio/sfx/coffin.mp3', volume: 0.3 }
}
```

The CSS `display: none` hides the text before it renders — no flash. The MutationObserver catches the DOM node regardless of visibility.

### What This Enables

- **Precise triggers**: Fire sounds at exact narrative moments, not via fragile regex
- **Metadata the status bar can't express**: e.g., "Frigid River but rapids are getting louder" (currently indistinguishable from calm river)
- **Volume/fade instructions**: Could extend the command format (e.g., `AMBIENT:volume:0.5`)
- **Zone overrides**: Signal a zone change without waiting for a room transition

### When to Use Each Mode

| | Text matching | Style_user1 |
|---|---|---|
| Sound logic lives in | JavaScript only | Split: triggers in story.ni, playback in JS |
| Recompile to change triggers? | No | Yes |
| Precision | Pattern-matching (can misfire) | Exact (author-controlled) |
| Volume/cooldown tuning | Edit sound-config.js (no recompile) | Edit sound-config.js (no recompile) |
| Best for | Incidental sounds, ambient triggers | Key narrative moments, unique events |

Use text matching as the default — it's simpler and doesn't require source changes. Use Style_user1 when a trigger needs to be precise (the same text appears in multiple contexts, or the trigger must fire at a specific point in a multi-paragraph response).

### Compatibility

Style_user1 has the **same compatibility as the overlay itself** — it's just another CSS class from the same GlkOte/AsyncGlk code path. Every interpreter in the "Yes" column above will render `.Style_user1`.

In non-browser interpreters (terminal), the player would see the raw command text. Guard with a conditional if needed, or accept it as a browser-only feature.

## Troubleshooting: Sound Not Playing

If you see `[Sound effect number N here.]` text instead of hearing audio, work through this checklist in order:

### 1. Wrong JS entry point (most common)

**Symptom**: Game loads and runs fine, but prints `[Sound effect number 13 here.]` instead of playing sound.

**Cause**: `play.html` loads `main.js` instead of `parchment.js`. Parchment 2025.1 ships two JS files:
- **`parchment.js`** (134KB) — Full engine with AudioContext, Glk sound channels, `gestalt_Sound=1`. **Use this.**
- **`main.js`** (176KB) — AsyncGlk standalone build with stub `glk_schannel_*` functions (all throw errors) and hardcoded `gestalt_Sound=0`. **Do NOT use for sound games.**

When `gestalt_Sound` returns 0, the Inform 7 runtime disables sound and prints text fallback instead.

**Fix**: In your play.html, change `<script src="...main.js">` to `<script src="...parchment.js">`. The `setup_web.py` script now validates this and warns if the wrong file is referenced.

### 2. Colon in story title

**Symptom**: `inblorb` fails or produces a corrupt blorb. On Windows, you may see file-not-found errors mentioning truncated filenames.

**Cause**: Inform 7 derives filenames from the title in line 1 of `story.ni`. Colons (`:`) are illegal in Windows filenames. The title `"Zork I: The Great Underground Empire"` produces `Zork I: The Great Underground E.gblorb` which cannot be written.

**Fix**: Replace `:` with `-` in the title: `"Zork I - The Great Underground Empire"`. The `compile.py` script now checks for this before compilation and exits with a clear error.

### 3. Sounds/ directory not at project root

**Symptom**: `compile.py --sound` fails at the "Generating blurb" step, or `generate_blurb.py` reports "Sounds directory not found".

**Cause**: `compile.py` looks for `.ogg` files at `projects/<name>/Sounds/`. If your sound files are in `<name>.materials/Sounds/` (the Inform 7 IDE convention), they won't be found.

**Fix**: Copy the sounds to the project root:
```bash
cp -r projects/myproject/myproject.materials/Sounds projects/myproject/Sounds
```
Do NOT symlink — the sound directories may diverge between projects.

### 4. Browser serving cached old JS

**Symptom**: You changed `main.js → parchment.js` in the template, recompiled, but sound still doesn't work.

**Cause**: The browser cached the old JavaScript files. HTTP servers like `python -m http.server` don't set cache-control headers, so browsers aggressively cache `.js` files.

**Fix**: Hard refresh with Ctrl+Shift+R, or open in an incognito/private window. `setup_web.py` and `compile.py` append `?v=<timestamp>` cache-busting params to all `.js` and `.css` references to prevent this.

### 5. Binary is .ulx instead of .gblorb

**Symptom**: Game loads but has no sound. No errors in console. The `.js` file is suspiciously small (1-2 MB instead of 19+ MB for a game with 25 sounds).

**Cause**: The base64-encoded file contains a naked `.ulx` binary (no embedded audio resources) instead of a `.gblorb` (blorb with sounds).

**Fix**: Recompile with `compile.py <name> --sound` which automatically encodes the `.gblorb` via `setup_web.py --blorb`. Check that the output says "Encoding name.gblorb" not "Encoding name.ulx".

### 6. Missing `story_name` in parchment_options

**Symptom**: Page shows `TypeError: Cannot read properties of undefined (reading 'substring')` instead of loading the game.

**Cause**: `parchment.js` calls `.substring()` on `parchment_options.story_name` to detect the file type (`.ulx.js`, `.gblorb.js`, `.z3.js`). If `story_name` is missing or undefined, the call crashes.

**Fix**: Add `story_name` to `parchment_options` in every play page:
```javascript
parchment_options = {
    default_story: ['path/to/game.gblorb.js'],
    lib_path: 'lib/parchment/',
    story_name: 'game.gblorb.js',    // ← REQUIRED by parchment.js
    use_proxy: 0,
    do_vm_autosave: 1,
};
```
For dynamic pages where the binary path comes from a URL parameter, derive it:
```javascript
story_name: binaryPath.split('/').pop()
```

### 7. Autoplay blocked by browser

**Symptom**: Game loads, first sound doesn't play, but subsequent sounds (after typing a command) work fine.

**Cause**: Browsers block AudioContext until user interaction. The first sound may be issued before the user types anything.

**Fix**: This is expected browser behavior. Parchment handles it — once the user types their first command (which counts as interaction), AudioContext is unlocked and all subsequent sounds play normally.

## Sources

- Parchment releases — github.com/curiousdannii/parchment/releases
- Async Parchment update — intfiction.org/t/async-parchment-update-live-on-iplayif-com-jan-2025/71463
- Parchment template "not updated with sound support yet" — intfiction.org/t/is-the-update-to-informs-parchment-able-to-do-graphics-and-sounds/75268/3
- Quixe PR #3 — github.com/erkyrath/quixe/pull/3
- GlkOte PR #1 — github.com/erkyrath/glkote/pull/1
- AsyncGlk glkaudio decoder — github.com/curiousdannii/asyncglk
- Emglken — github.com/curiousdannii/emglken
- Bisquixe — intfiction.org/t/the-bisquixe-interpreter-for-inform-7-and-inform-10-styling-new-full-sound-internal-links/66166
- Vorple Multimedia — vorple-if.com/docs/extension-multimedia.html
- Glulx interpreters with sound (2024) — intfiction.org/t/glulx-interpreters-that-support-sound-2024-edition/69761
