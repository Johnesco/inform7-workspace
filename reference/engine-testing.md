# Engine Testing Reference

What testing means for each engine, what tools exist, and what's planned.

## Test Capabilities by Engine

| Engine | CLI Tests | Browser Tests | Test Runner | Walkthrough Format | Status |
|--------|-----------|---------------|-------------|-------------------|--------|
| **Inform 7** | Yes | No | `glulxe.exe` / `dfrotz.exe` | Plain text (one command/line) | Full pipeline |
| **Z-machine** | Yes | No | `dfrotz.exe` | Plain text (one command/line) | Full pipeline |
| **Ink** | No | Planned | — | — | No testing yet |
| **wwwBASIC** | No | Planned | — | — | No testing yet |
| **qbjc** | No | Planned | — | — | No testing yet |
| **Applesoft** | No | Planned | — | — | No testing yet |
| **bwBASIC** | No | Planned | — | — | No testing yet |
| **jsdos** | No | No | — | — | Not feasible (DOS emulation) |
| **Rez** | No | Planned | — | — | No testing yet |
| **Twine** | No | Planned | — | — | No testing yet |

## Inform 7 / Z-machine Testing (Full Pipeline)

**Tools** (at `/c/code/text-games/i7/tools/`):
- `run_walkthrough.py` — feeds commands to native interpreter, captures transcript
- `run_tests.py` — runs `.regtest` scenario files
- `generate-guide.py` — pairs commands with responses, generates annotated guide
- `find_seeds.py` — RNG seed sweep for deterministic testing
- `regtest.py` — core regtest engine
- `ifhub/tools/extract_commands.py` — extracts walkthrough from `Test me with` blocks in story.ni (stays in ifhub, used by compile.py)

**Artifacts:**
- `tests/walkthrough.txt` — input commands (one per line)
- `tests/inform7/walkthrough.txt` — legacy location (I7 specific)
- `tests/inform7/walkthrough_output.txt` — interpreter transcript (generated)
- `tests/inform7/walkthrough-guide.txt` — annotated guide (generated)
- `tests/seeds.conf` — golden seeds for deterministic RNG
- `tests/*.regtest` — regression test scenarios

**Interpreters:**
- `tools/interpreters/glulxe.exe` — Glulx interpreter (native Windows, built via MSYS2)
- `tools/interpreters/dfrotz.exe` — Z-machine interpreter (native Windows)

**Config:** `tests/project.conf` — full config with engine paths, score patterns, seed flags.

**Flow:** Compile → run walkthrough → check score/death/won patterns → generate guide → run regtests

## Future: Browser-Based Testing (All Web Engines)

**Approach:** Playwright or Puppeteer driving the game's `play.html` in a headless browser.

**Would enable testing for:** Ink, BASIC (all dialects), Rez, Twine.

**Walkthrough format:** Same plain text commands (one per line) stored in `tests/walkthrough.txt`. The browser test runner would type each command into the game's input field and capture the response.

**Not yet implemented.** When built, this would:
1. Start a local HTTP server serving the game
2. Launch headless browser → navigate to play.html
3. For each command: type into input, press Enter, wait for response
4. Capture transcript → compare against expected output or just validate no errors
5. Engine-specific adapters for different input mechanisms (text input for parser games, click targets for choice games)

## Adding Testing to a New Engine

1. Define the test runner (CLI interpreter, npm tool, or browser automation)
2. Set `has_cli_tests=True` in `EngineSpec` if CLI-based
3. Add the runner invocation to `pipeline.py` `stage_test()`
4. Update `dashboard.py` `_test_commands()` to generate the right command
5. Store walkthrough commands in `tests/walkthrough.txt` (universal location)
6. Update this document
