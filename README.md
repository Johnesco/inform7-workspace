# Inform 7 workspace

Tooling for the Inform 7 and Z-machine games shown on [IF Hub](https://johnesco.github.io/ifhub/). Each game is its own repository that sits next to this one on disk (ignored here); this repo holds only what builds them.

```bash
python tools/build.py <game>        # compile, test, Parchment player, tests.html
```

`build.py` compiles `story.ni` with the system Inform 7 compiler, runs the walkthrough and regression tests with the bundled `glulxe` and `dfrotz` interpreters, renders a test report with [ifPlayer](https://github.com/Johnesco/ifplayer), and wraps the story in a [Parchment](https://github.com/curiousdannii/parchment) web player. Stories marked `engine = zmachine` are wrapped without compiling. The finished game folder is then published by IF Hub's `ship.py`.

- `tools/` — `build.py`, `compile.py`, the test runners, `web/` (player templates and Parchment), `interpreters/`, `lib/`
- `reference/` — Inform 7 language notes, the handbook PDFs, sound and Parchment troubleshooting
- `CLAUDE.md` — authoring rules and the full command list

The folder contract a game must meet is documented in the ifhub repo under `docs/publishing.md`.
