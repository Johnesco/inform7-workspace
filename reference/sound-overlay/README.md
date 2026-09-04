# Sound Overlay System (Archived)

**Status**: Archived March 2026. Replaced by native Glk/blorb sound in Parchment 2025.1.

## What This Was

A custom JavaScript overlay that added sound to web-based Inform 7 games without modifying the game binary. It worked by observing the interpreter's DOM output (via MutationObserver) and playing HTML5 Audio when specific text or room names appeared.

The system had three components:

1. **sound-engine.js** — Shared engine that watched `.BufferWindow` for text patterns and `Style_user1` spans containing `SFX:` commands. Supported cooldowns, ifhub integration, and standalone mute buttons.

2. **ambient-audio.js** — Room-based background music for Zork I. Watched the `.GridWindow` status bar for room name changes, mapped ~70 rooms to 10 audio zones (forest, cave, water, etc.), and crossfaded between looping ambient tracks.

3. **sound-config.js** — Per-game trigger definitions. Called `SoundEngine.init()` with game-specific regex patterns and audio file paths.

## Why It Was Replaced

In March 2026, Parchment 2025.1's native blorb sound support was validated and integrated into the IF Hub pipeline. Native blorb embeds `.ogg` audio directly in the game binary (`.gblorb`), so the interpreter handles playback via Glk sound channels — no external JavaScript needed.

Advantages of native blorb over the overlay:
- Sound timing controlled by the game engine (precise, not regex-dependent)
- Single self-contained file (no separate `.mp3` assets to serve)
- Works with any Glk-compatible interpreter
- No MutationObserver polling or DOM coupling
- In-game volume/mute control possible via Glk API

The overlay's main advantage — hot-swappable text triggers without recompilation — was not needed once all games had proper sound declarations in `story.ni`.

## Files in This Archive

| File | Description |
|------|-------------|
| `sound-engine.js` | Shared SFX engine (7.7K) — MutationObserver, Style_user1 + text matching, ifhub API |
| `ambient-audio.js` | Zork I room-based crossfade (16K) — 10 zones, 70 room mappings |
| `sound-config-zork1.js` | Zork I triggers (2.6K) — 16 text-matching SFX triggers |
| `sound-config-feverdream.js` | Fever Dream triggers (416B) — 1 Style_user1 SFX trigger |
| `sound-standalone.html` | Loader snippet (706B) — injected into standalone play pages |
| `soundoverlay.html` | Full architecture documentation page (27K) — diagrams, zone maps, trigger tables |

## Audio Files (Not Archived)

The `.mp3` audio files (~46 MB per game copy) are not included in this archive. They were CC0-licensed ambient recordings and sound effects sourced from [BigSoundBank](https://bigsoundbank.com).

### Ambient loops (Zork I)

| File | Zone | BigSoundBank # | Description |
|------|------|----------------|-------------|
| `forest.mp3` | forest | — | Birds, wind through trees |
| `house.mp3` | house | — | Quiet indoor ambience |
| `cave.mp3` | cave | — | Underground dripping, echoes |
| `water.mp3` | water | — | Gentle flowing water |
| `rapids.mp3` | rapids | — | Rushing water, falls |
| `loud.mp3` | loud | — | Intense reverberation |
| `hades.mp3` | hades | — | Eerie, otherworldly drone |
| `mine.mp3` | mine | — | Deep underground ambience |
| `machinery.mp3` | machinery | — | Mechanical hum, dam equipment |

### Sound effects (Zork I)

| File | Trigger | BigSoundBank # | Description |
|------|---------|----------------|-------------|
| `sfx/bird.mp3` | Songbird | #1667 | Robin chirping (2s) |
| `sfx/creak.mp3` | Mailbox | #0302 | Hinge creak (2s) |
| `sfx/window.mp3` | Window | #0039 | Window sliding open (5s) |
| `sfx/trapdoor.mp3` | Trap door | #3207 | Heavy door creak (6s) |
| `sfx/bell.mp3` | Exorcism bell | #3446 | Bell toll (7s) |
| `sfx/spirits.mp3` | Spirits | #1796 | Ghostly whoosh (1s) |
| `sfx/bat.mp3` | Bat swoops | #0458 | Bat wing flapping (13s) |
| `sfx/footsteps.mp3` | Cyclops flees | #0514 | Running footsteps (10s) |
| `sfx/machine.mp3` | Machine rumble | #0709 | Mechanical rumble (9s) |
| `sfx/inflate.mp3` | Boat inflating | #1129 | Air pump (9s) |
| `sfx/coffin.mp3` | Gold coffin | #0580 | Stone scraping (23s) |
| `sfx/match.mp3` | Match strike | #1271 | Match ignition (10s) |
| `sfx/grue.mp3` | Grue death | #2110 | Growling creature (4s) |
| `sfx/flood.mp3` | Dam flood | #0507 | Rushing water (28s) |
| `sfx/sword.mp3` | Sword glow | #2079 | Chime tone (2s) |
| `sfx/laugh.mp3` | Thief laugh | #0490 | Deep quiet laugh (7s) |

### Sound effects (Fever Dream)

| File | Trigger | Description |
|------|---------|-------------|
| `sfx/glass.mp3` | Glass breaking (Style_user1) | Glass shatter |

## See Also

- `reference/sound.md` — Full technical documentation of both sound approaches
- `CLAUDE.md` — Pipeline documentation including `compile.py --sound`
