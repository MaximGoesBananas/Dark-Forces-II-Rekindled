# Testing Rekindled

Run the checks from WSL with the engine source directory:

```sh
python3 tools/run_checks.py ~/src/OpenJKDF2 --windows
```

The runner executes the available `test_*.py` files sequentially and exits nonzero
on failure. `--windows` includes native Windows binding and controller checks. To select checks,
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

## Controllers

`test_controller.py` exercises the actual button migration, custom-binding preservation,
look sensitivity, inversion, menu selection and Back release handling. `test_ui.py`
also checks upgrade navigation and purchases using controller buttons and stick input.

For an isolated SDL input test on Linux, compile `tools/test_gamepad_device.c` with
`cc -o <test-folder>/gamepad tools/test_gamepad_device.c`. Run it as root with a
state-file path and the test user's numeric UID. It creates one virtual Xbox controller,
grants only that user access, and removes it on exit or after ten minutes. Each state
file contains ten integers: sequence, LX, LY, RX, RY, LT, RT, hat X, hat Y, button mask.
Use a new sequence for each change. Sticks range from -32768 to 32767, triggers from
0 to 255, and hats from -1 to 1. Button bits 0-10 are A, B, X, Y, LB, RB, Back, Start,
Guide, left-stick click and right-stick click. A negative sequence stops the device.

Check movement, looking, jumping, triggers, neutral-stick drift, menus, save/load,
upgrade purchases and refunds, sensitivity, inversion and unplug/reconnect. Inspect
actual screenshots and compare camera angles at different sensitivity settings.
Repeat with a physical controller on Windows before publishing controller support.
A Linux input test does not establish SteamOS or Proton compatibility.

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

The launcher UI check also loads the form from the supplied EXE and exercises twelve
simulated desktop and scaling combinations, from 640x480 at 100% through 4K at 300%
and 5120x1440 at 125%. It checks that folder selection and action buttons remain
reachable by scrolling and that button and heading text fit. The test uses the
release DPI manifest and does not change the user's display settings. These layout
checks do not reproduce switching between physical monitors with different DPI.
