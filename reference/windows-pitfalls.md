# Windows / Git Bash Pitfalls

> **Note**: The IF Hub toolchain has been migrated from bash to Python. The bash-specific pitfalls below (grep -oP, pipe subshells) are no longer relevant to the toolchain itself, but remain documented for reference when writing any ad-hoc shell scripts.

## grep -oP (PCRE) Does Not Work

Git Bash's `grep` does not support `-P` (Perl-compatible regex). The toolchain uses `tools/lib/regex.py` for all PCRE operations (no shell grep needed).

## Pipe to `while read` Creates Subshell

Variables set inside a `while read` loop fed by a pipe are lost (subshell). Not relevant to the Python toolchain.

## Native Interpreters (Preferred)

Native Windows CLI interpreters (`glulxe.exe`, `dfrotz.exe`) are built from source via MSYS2 and live at `tools/interpreters/`. They support piped I/O and `--rngseed` for deterministic testing — no WSL required.

**First-time setup**:
1. Install MSYS2: `winget install MSYS2.MSYS2`
2. Open MSYS2 UCRT64 terminal
3. Install tools: `pacman -S --needed mingw-w64-ucrt-x86_64-gcc make git`
4. Build: `cd /c/code/ifhub/tools/interpreters && bash build.sh`

The build script handles three MSYS2/UCRT compatibility patches automatically:
- CheapGlk `bzero` → `memset` (UCRT has no `bzero`)
- Frotz `strndup` → `strdup` (UCRT has no `strndup`)
- Frotz `-fcommon` (GCC 10+ defaults to `-fno-common`)

The Windows GUI `glulxe.exe` at `C:\Program Files\Inform7IDE\Interpreters\` does **not** support piped I/O and cannot be used for automated testing.

## WSL Fallback

If native interpreters are not built, the test framework falls back to WSL with Linux-native interpreters. The Python config parser auto-detects the platform and selects the right interpreter path.

If WSL is unresponsive (`wsl -e echo` hangs), common fixes: `wsl --shutdown` from PowerShell, then retry. WSL2 is known to hang after sleep/hibernate due to Hyper-V architectural issues.
