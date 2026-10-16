# Testing Rekindled

Run the checks from WSL with the engine source directory:

```sh
python3 tools/run_checks.py ~/src/OpenJKDF2 --windows
```

The runner executes the available `test_*.py` files sequentially and exits nonzero
on failure. `--windows` includes the native Windows binding check. To select checks,
put their names after the engine path, for example `bindings ui --windows`.
The launcher tests require Windows Python and the .NET Framework compiler.

The scripts use the maintainer's Windows/WSL fixture paths. Adjust those paths for
another development environment; they are not required to install or play Rekindled.

## Isolated gameplay

`tools/build_test_engine.sh` builds a Linux test engine. `tools/test_session.sh`
runs it on an Xvfb display with its own profile and muted audio. `JKT_SRC`, `JKT_ROOT`,
`JKT_DISPLAY` and `JKT_SHOTS` select the checkout, profile, display and capture folder.
The helper refuses display `:0`. It must not access the player's active profile.

```sh
bash tools/test_session.sh start -autostart -sp -episode JK1 -map 02narshadda.jkl
bash tools/test_session.sh do "enter" "console whiteflag 1" \
  "console skillinfo" "expect RPG skillinfo:" "shotwin baseline"
bash tools/test_session.sh stop
```

`enter` waits for briefing/gameplay readiness. `load` uses F9 and waits for restore.
`expect` checks the latest console command's output. Failed setup stops the batch.
`shotwin` captures the actual window after resizing. Waiting has a bounded timeout;
read the engine log if it expires.

For campaign progression, start New Game and advance through mission results.
An isolated `-autostart` map does not reproduce episode progression. Scripted openings
can lock input; wait for them to finish before disabling AI or issuing test commands.

## Coverage

Use the focused checks for a change, then run the complete suite before release.
Rendering, artwork, movement and encounter changes also need in-game inspection.
Check save/load twice for persistent features so counters do not duplicate actors,
awards or purchases. Test missing assets and failed writes where applicable.

Build the release engine with `tools/build_engine.sh --release`; it does not install
into the player's game. Test the actual packaged launcher with:

```powershell
python tools/test_launcher.py --package "<launcher.exe>"
python tools/test_launcher_ui.py --package "<launcher.exe>"
```

These tests use isolated game fixtures. Installation, repair, update and uninstall
must preserve saves, settings and unrelated files. Do not use a real player profile
as a fixture.
