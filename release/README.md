# Building Rekindled

Source and build instructions for **Dark Forces II Rekindled**. For the game download
and installation instructions, see [the project page](../README.md).

## Build the download

Build the engine as described in [DEVELOPING.md](../DEVELOPING.md), then run
packaging from Windows Python with explicit engine and runtime locations:

```powershell
python tools/build_release.py --version "<version>" --engine "<engine source folder>" --runtime "<runtime DLL folder>"
```

The engine path may be a WSL UNC path, such as
`//wsl.localhost/Ubuntu-24.04/home/<user>/src/OpenJKDF2`. The runtime folder supplies
`libGameNetworkingSockets.dll`, `libstdc++-6.dll`, `libgcc_s_seh-1.dll`,
`libwinpthread-1.dll` and `OpenAL32.dll`. The executable comes from the engine's
`build_win64` directory. `--output` selects a separate package directory.

The builder takes the public executable from the engine build and supporting DLLs
from the installed runtime. It rejects executables containing development location
reports, takes artwork from `art/*.bmp` and the PNGs/metadata in
`jkgm/materials/rekindled-sky/`, embeds a ZIP manifest with SHA-256 hashes, and
compiles the WinForms launcher with Windows' Framework compiler. Its
explicit file list excludes game archives, profiles and saves.

Outputs in `dist/<version>`:

- `Dark-Forces-II-Rekindled-<version>.exe`: launcher and embedded mod.
- `Dark-Forces-II-Rekindled-<version>-source.zip`: matching engine, library, mod and launcher sources.
- `SHA256SUMS.txt`: checksums for both downloads.
- `manifest.json`: version, engine commit and installed file hashes.

The source archive includes the fully patched engine and initialized submodule sources,
including local library build fixes. It excludes private game data and Git history.
Publish it beside the binary. Component notices are in the install's `licenses` folder.
The source archive is built on WSL so Linux links resolve correctly.

The release build leaves the maintainer's installed development game unchanged.
Normal local build helpers enable location reports; the release helper disables them.

## Source archive and rebuilding

`OpenJKDF2/` is the complete working engine source; `jk-rpg/` holds this project.
`ENGINE-COMMIT.txt` and `ENGINE-SUBMODULES.txt` record source revisions. The engine
changes are already applied: do not apply `jk-rpg/engine/*.patch` a second time.

On Ubuntu, install the dependencies in `jk-rpg/DEVELOPING.md`, enter `OpenJKDF2` and
run `bash build_win64.sh` with the MinGW POSIX compiler selected and Linux-only
pkg-config paths excluded as described there. The last upstream macOS DLL copy step
does not apply on Ubuntu: use the built EXE/DLLs and three MinGW runtime DLLs listed
in `tools/build_engine.sh`. Copy `jk-rpg/art/*.bmp` into `rpg/art` beside the runtime.
Copy the PNGs and
`metadata.json` from `jk-rpg/jkgm/materials/rekindled-sky/` into the same relative
folder under `rpg/`. Keep the game archives unchanged.
`build_linux64.sh` builds the Linux test engine. This layout allows replacing and
relinking LGPL components; OpenAL remains a replaceable DLL.

The launcher uses C# and .NET Framework without external NuGet packages. Its exact
compiler invocation is in `tools/build_release.py`. The binary is currently unsigned;
this build does not imply a publisher signature or Windows reputation.
Orbitron Medium is embedded for headings and buttons, without installing a system font.
The original font and its SIL Open Font License are in `launcher/fonts`, from
[The League of Moveable Type](https://github.com/theleagueof/orbitron).

## Installer checks

`tools/test_launcher.py` runs the real C# installer on Windows, including when called
by the WSL check runner. It checks safe paths, integrity, fresh install, interrupted
preparation, update, adoption, collisions, modified files and uninstall against an
isolated fake game with an original save sentinel. The GUI keeps file operations off
its main thread and waits for them before closing. One launcher instance runs at a time.

The launcher owns only files in its installed `rpg/launcher-install.json`. Saves and
the original game stay outside that ownership.

`python tools/test_launcher_ui.py` checks the actual WinForms controls and renders
the launcher without changing the player's installation. Use `--package <launcher.exe>`
to inspect its embedded version. It covers installation states and scrolling at enlarged
scale; this does not replace checking actual Windows DPI settings on other displays.
