# Bash Pitfalls (Windows / Git Bash)

globs: ["**/*.sh", "**/project.conf", "tools/**"]

## Quick Checklist

The IF Hub toolchain has been migrated from bash to Python. These pitfalls apply to any remaining shell scripts (e.g., `tools/interpreters/build.sh`):

1. **No `grep -oP`** — Git Bash lacks PCRE. The Python toolchain uses `tools/lib/regex.py` instead
2. **No pipe to `while read`** — Variables set in the loop are lost (subshell). Use `mapfile` + `for`
3. **Native interpreters** — `tools/interpreters/glulxe.exe` and `dfrotz.exe` preferred over WSL
4. **WSL fallback** — If native not built, tests auto-fall back to WSL. `wsl --shutdown` fixes hangs

See `reference/windows-pitfalls.md` for full details and MSYS2 build instructions.
