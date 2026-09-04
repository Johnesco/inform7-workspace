#!/bin/bash
# Build native Windows CLI interpreters (glulxe.exe + dfrotz.exe)
# from source using MSYS2 UCRT64.
#
# Prerequisites:
#   1. Install MSYS2: https://www.msys2.org/
#   2. Open "MSYS2 UCRT64" terminal
#   3. Install build tools:
#        pacman -S --needed mingw-w64-ucrt-x86_64-gcc make git
#   4. Run this script from the MSYS2 UCRT64 terminal:
#        cd /c/code/ifhub/tools/interpreters
#        bash build.sh
#
# Output:
#   tools/interpreters/glulxe.exe   — Glulx CLI interpreter
#   tools/interpreters/dfrotz.exe   — Z-machine CLI interpreter
#
# These are gitignored. Each developer builds locally.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"

echo "=== Building native interpreters ==="
echo "Build dir: $BUILD_DIR"
echo ""

mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# --- CheapGlk (required by glulxe) ---
echo "--- CheapGlk ---"
if [[ ! -d cheapglk ]]; then
    git clone https://github.com/erkyrath/cheapglk.git
else
    echo "  (already cloned)"
fi
cd cheapglk
make clean 2>/dev/null || true
# UCRT doesn't provide bzero(); patch cgdate.c to use memset instead
if grep -q 'bzero' cgdate.c 2>/dev/null; then
    sed -i 's/bzero(tm, sizeof(\*tm))/memset(tm, 0, sizeof(*tm))/' cgdate.c
    echo "  (patched bzero -> memset in cgdate.c)"
fi
make
cd "$BUILD_DIR"

# --- Glulxe ---
echo ""
echo "--- Glulxe ---"
if [[ ! -d glulxe ]]; then
    git clone https://github.com/erkyrath/glulxe.git
else
    echo "  (already cloned)"
fi
cd glulxe

# Glulxe Makefile expects GLKINCLUDEDIR and GLKLIBDIR
# Override OPTIONS: use -DOS_WINDOWS (Makefile defaults to -DOS_MAC)
make clean 2>/dev/null || true
make GLKINCLUDEDIR="$BUILD_DIR/cheapglk" GLKLIBDIR="$BUILD_DIR/cheapglk" \
    OPTIONS="-g -Wall -Wmissing-prototypes -Wno-unused -DOS_WINDOWS"

cp glulxe.exe "$SCRIPT_DIR/glulxe.exe"
echo "  -> Copied glulxe.exe to $SCRIPT_DIR/"
cd "$BUILD_DIR"

# --- Frotz (dfrotz) ---
echo ""
echo "--- Frotz (dfrotz) ---"
if [[ ! -d frotz ]]; then
    git clone https://github.com/DavidGriffith/frotz.git
else
    echo "  (already cloned)"
fi
cd frotz

# Build dumb terminal frotz (no curses needed)
# UCRT doesn't provide strndup; patch dumb_init.c to use strdup instead
# (strndup with PATH_MAX is effectively strdup for all practical paths)
if grep -q 'strndup' src/dumb/dumb_init.c 2>/dev/null; then
    sed -i 's/strndup(zoptarg, PATH_MAX)/strdup(zoptarg)/' src/dumb/dumb_init.c
    echo "  (patched strndup -> strdup in dumb_init.c)"
fi
make clean 2>/dev/null || true
# GCC 10+ defaults to -fno-common; frotz headers define globals in multiple TUs
make dfrotz CFLAGS="-Wall -std=c99 -D_POSIX_C_SOURCE=200809L -g -fPIC -fpic -fcommon"

cp dfrotz.exe "$SCRIPT_DIR/dfrotz.exe"
echo "  -> Copied dfrotz.exe to $SCRIPT_DIR/"
cd "$BUILD_DIR"

echo ""
echo "=== Build complete ==="
echo "  glulxe.exe:  $SCRIPT_DIR/glulxe.exe"
echo "  dfrotz.exe:  $SCRIPT_DIR/dfrotz.exe"
echo ""
echo "Smoke test:"
echo "  echo 'look' | $SCRIPT_DIR/glulxe.exe path/to/game.ulx"
