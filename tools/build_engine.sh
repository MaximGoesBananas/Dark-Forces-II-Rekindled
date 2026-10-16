#!/bin/bash
# Build the RPG engine (OpenJKDF2 + engine/*.patch) for Windows inside WSL and copy it to the game's rpg folder.
# Usage: wsl -d Ubuntu-24.04 -- bash /mnt/d/Dev/Games/jk-rpg/tools/build_engine.sh
# One-time setup (as root): see README.md.
set -e
case "${1:-}" in
    "") export RPG_DEVELOPMENT_REPORTS=1 ;;
    --release) export RPG_DEVELOPMENT_REPORTS=0 ;;
    *) echo "usage: build_engine.sh [--release]" >&2; exit 2 ;;
esac
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$HOME/.local/bin
PROJECT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${JKRPG_ENGINE:-$HOME/src/OpenJKDF2}"
BASE=9c0844d1   # upstream commit the patches apply to
GAME="/mnt/d/SteamLibrary/steamapps/common/Star Wars Jedi Knight"

if [ ! -d "$SRC" ]; then
    git clone -q https://github.com/shinyquagsire23/OpenJKDF2.git "$SRC"
    git -C "$SRC" checkout -q -b rpg "$BASE"
    git -C "$SRC" submodule update --init -q
    git -C "$SRC" apply --index "$PROJECT/engine/rekindled.patch"
    git -C "$SRC" commit -qm Rekindled
fi

cd "$SRC"
# Build only committed engine source: the install and engine/*.patch must describe the same code,
# and the patch must reproduce that source tree.
if [ -n "$(git status --porcelain --ignore-submodules=all)" ]; then
    git status --short --ignore-submodules=all | head -20
    echo "Commit the engine branch first (git -C $SRC commit), then run this again." >&2
    exit 3
fi
# The Linux test engine needs Linux development packages; keep pkg-config from offering them to
# the Windows cross-build (they broke it with Linux-only headers such as PipeWire's).
export PKG_CONFIG_LIBDIR=/usr/x86_64-w64-mingw32/lib/pkgconfig PKG_CONFIG_PATH=
# The script's last step copies MinGW DLLs from macOS paths and fails here; we copy them below.
./build_win64.sh > /tmp/build_win64.log 2>&1 || true
grep -q "Built target openjkdf2-64" /tmp/build_win64.log || { grep -E "error:|undefined reference" /tmp/build_win64.log | head -40; exit 1; }
# Export the complete mod diff without development commit messages.
git diff --binary "$BASE" HEAD > "$PROJECT/engine/rekindled.patch"
if [ "$RPG_DEVELOPMENT_REPORTS" = 0 ]; then
    echo "built release $(git rev-parse --short HEAD); development install unchanged"
    exit 0
fi
if /mnt/c/Windows/System32/tasklist.exe 2>/dev/null | grep -qi openjkdf2-64; then
    echo "Built, but the game is running: run tools/close_game.ps1 first, then build again to install."
    exit 2
fi
mkdir -p "$GAME/rpg"
cp build_win64/openjkdf2-64.exe build_win64/*.dll "$GAME/rpg/"
cp /usr/lib/gcc/x86_64-w64-mingw32/13-posix/{libstdc++-6,libgcc_s_seh-1}.dll /usr/x86_64-w64-mingw32/lib/libwinpthread-1.dll "$GAME/rpg/"
# Menu and HUD artwork, including cleaned official weapon pictures, goes to rpg/art.
mkdir -p "$GAME/rpg/art" && cp "$PROJECT"/art/*.bmp "$GAME/rpg/art/"
# Ship only the mod's reviewed sky images and their existing JKGM metadata.
SKY="$PROJECT/jkgm/materials/rekindled-sky"
if [ -f "$SKY/metadata.json" ]; then
    mkdir -p "$GAME/rpg/jkgm/materials/rekindled-sky"
    cp "$SKY"/*.png "$SKY/metadata.json" "$GAME/rpg/jkgm/materials/rekindled-sky/"
fi

echo "built $(git rev-parse --short HEAD)"
