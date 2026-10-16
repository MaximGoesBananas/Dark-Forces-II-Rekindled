#!/bin/bash
# Build the Linux copy of the RPG engine used for background testing (tools/test_session.sh).
# Same source as the Windows build (~/src/OpenJKDF2, branch rpg); output build_linux64/openjkdf2.
# Usage: wsl -d Ubuntu-24.04 -- bash /mnt/d/Dev/Games/jk-rpg/tools/build_test_engine.sh
set -e
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$HOME/.local/bin
export CC=clang CXX=clang++
export RPG_DEVELOPMENT_REPORTS=1
# JKT_SRC selects another engine checkout, e.g. one per parallel session (see test_session.sh).
SRC="${JKT_SRC:-$HOME/src/OpenJKDF2}"
cd "$SRC"
# The log lives in $HOME: WSL clears /tmp whenever the distribution stops between calls.
LOG="$HOME/build_linux64$(echo "$SRC" | tr / _).log"
./build_linux64.sh > "$LOG" 2>&1 || true
grep -q "Built target openjkdf2" "$LOG" || { grep -E -A4 "error:|undefined reference|CMake Error" "$LOG" | head -40; exit 1; }
echo "built test engine $(git rev-parse --short HEAD)"
