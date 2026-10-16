# Developing Rekindled

Rekindled extends OpenJKDF2. The repository contains the engine patch, launcher,
artwork and tests. The source download also includes the patched engine and its
libraries. Player-facing features are described in [README.md](README.md).

## Engine source

`engine/rekindled.patch` applies to OpenJKDF2 commit `9c0844d1`.
For a repository checkout:

```sh
git clone https://github.com/shinyquagsire23/OpenJKDF2.git ~/src/OpenJKDF2
cd ~/src/OpenJKDF2
git checkout -b rekindled 9c0844d1
git submodule update --init --recursive
git apply --index /path/to/Rekindled/engine/rekindled.patch
git commit -m "Rekindled"
```

The engine in the source download already has the patch applied. Do not apply it
again. Keep third-party copyright and license notices when redistributing sources.

## Windows build

The build uses Ubuntu 24.04 under WSL and the POSIX-threaded MinGW compiler.
Install the build dependencies:

```sh
sudo apt-get install git build-essential cmake python3 bison flex imagemagick \
  protobuf-compiler zsh libpng-dev clang mingw-w64 pipx
sudo update-alternatives --set x86_64-w64-mingw32-gcc /usr/bin/x86_64-w64-mingw32-gcc-posix
sudo update-alternatives --set x86_64-w64-mingw32-g++ /usr/bin/x86_64-w64-mingw32-g++-posix
pipx install cogapp
```

From the project directory, build without installing into a game folder:

```sh
JKRPG_ENGINE=~/src/OpenJKDF2 bash tools/build_engine.sh --release
```

The helper excludes Linux-only pkg-config paths from the Windows build. The upstream
script's final DLL-copy step uses macOS paths; the helper checks that the executable
was built before accepting that step's failure. See [packaging](release/README.md)
for the launcher and matching source download.

## Code map

| Source | Responsibility |
|---|---|
| `src/Main/jkRpg.c` | Progression, upgrade effects, pickups and campaign encounters |
| `src/Main/jkRpgWeapons.c` | Weapon upgrades, saber controls and combat timing |
| `src/Main/jkRpgMenu.c` | Upgrade menu, HUD and asset fallbacks |
| `src/Main/jkRpgOutfits.c` | Clothing recoloring during level loading |
| `src/Main/jkRpgCrash.c` | Bounded Windows crash reports |
| `src/Main/jkRpg.h`, `jkRpgInternal.h` | Engine hooks and shared mod declarations |
| `launcher/Installer.cs` | Installation, integrity, repair and removal |
| `launcher/Program.cs` | Launcher interface and game discovery |
| `art/tools/` | Asset conversion and atlas layout |
| `tools/test_*.py` | Focused regression checks |

The `src/` paths are relative to OpenJKDF2. Hooks in its actor, inventory, physics,
weapon, save, GUI and rendering code call the mod modules. Include the declaring
header when adding a hook; implicit C declarations can truncate pointers on 64-bit builds.

## Tests and saves

Run [the test suite](docs/TESTING.md) before packaging. Use isolated profiles for
in-game checks; never overwrite a player's saves or close an unrelated game process.
Changes to rendering also need inspection at the affected resolutions and aspect ratios.

Progression uses inventory bins registered by `jkRpg_Register`. Persistent upgrade
changes must preserve XP, purchases, unspent points and mission purchase limits.
When changing the save layout, increment `RPG_DATA_VERSION` and test migration plus
repeated save/load. Refund only an affected purchase when necessary. The engine retains
compatibility readers for older data layouts; those are part of save support.

Update the [upgrade reference](docs/UPGRADES.md) and relevant feature documentation
when changing gameplay. Describe the resulting behavior and its limits.

## Runtime diagnostics

Windows crashes append the exception, module offsets, build revision and level position
to `rpg/reports/crash-log.txt`. The log is bounded to 32 KB and trimmed to 16 KB.
`tools/crash_addr.sh` resolves addresses against the matching executable. Library aborts
without an unhandled exception may only appear in Windows' Application event log.

Development builds enable F12 location reports with `RPG_DEVELOPMENT_REPORTS=1`.
Release builds disable that collector and retain ordinary screenshots.
`tools/read_report.py` reads position and camera metadata from a development screenshot.

## References

- [Progression and XP](docs/PROGRESSION.md)
- [Upgrades and combat](docs/UPGRADES.md)
- [Crowds and clothing](docs/CIVILIANS.md)
- [Sky materials and inspection positions](docs/SKIES.md)
- [Artwork and atlas processing](art/README.md)
- [Launcher packaging](release/README.md)
