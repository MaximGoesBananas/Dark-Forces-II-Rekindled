#!/bin/bash
# Background test session: runs the Linux test engine on an invisible screen (Xvfb :99) with its own
# test profile, so testing never takes the player's screen, keyboard or saves.
# Game data comes read-only from the Steam folder; profiles, settings and saves live in ~/jktest.
#
#   test_session.sh start [engine args]   e.g. start -autostart -sp -episode JK1 -map 01narshadda.jkl
#   test_session.sh key <keysym>...        e.g. key Return, key k, key shift+Escape
#   test_session.sh type <text>
#   test_session.sh hold <keysym> <seconds> e.g. hold Next 2 (look down with Page Down)
#   test_session.sh click <x> <y>          screen pixels on the 1920x1080 test screen
#   test_session.sh fire <ms>              hold the left mouse button
#   test_session.sh shot <name>            saves the game window as D:/Dev/helm/scratch/jk-rpg-shots/<name>.png
#   test_session.sh size <w> <h>           resizes the game window (centred), e.g. size 1920 1080 for 16:9
#   test_session.sh shotwin <name>         like shot, but at the window's current size and position
#   test_session.sh console <command>      runs a console command, e.g. console givexp 160
#   test_session.sh enter                  wait for briefing, accept, then wait for gameplay
#   test_session.sh load                   F9, then wait for a confirmed restore
#   test_session.sh expect <text>          require text in the latest command output
#   test_session.sh wait <seconds>
#   test_session.sh do "<step>" "<step>"... runs several steps in one call, e.g. do "key k" "wait 1" "shot menu"
#   test_session.sh stop
# Run from Windows as: wsl -d Ubuntu-24.04 -- bash /mnt/d/Dev/Games/jk-rpg/tools/test_session.sh ...
# Parallel sessions: give each its own JKT_DISPLAY (e.g. :101), JKT_ROOT (profile/saves folder) and
# JKT_SRC (engine checkout); defaults are :99, ~/jktest and ~/src/OpenJKDF2.
set -e
export DISPLAY="${JKT_DISPLAY:-:99}"
[[ "$DISPLAY" =~ ^:[1-9][0-9]*$ ]] || { echo "Refusing non-test display $DISPLAY" >&2; exit 1; }
# DISPLAY alone does not isolate SDL: WSLg's inherited Wayland socket bypasses Xvfb.
export SDL_VIDEODRIVER=x11 SDL_VIDEO_DRIVER=x11
unset WAYLAND_DISPLAY
GAME="/mnt/d/SteamLibrary/steamapps/common/Star Wars Jedi Knight"
ROOT="${JKT_ROOT:-$HOME/jktest}"
ENGINE="${JKT_SRC:-$HOME/src/OpenJKDF2}/build_linux64"
SHOTS="${JKT_SHOTS:-/mnt/d/Dev/helm/scratch/jk-rpg-shots}"
WIN() { xdotool search --name OpenJKDF2 | head -1; }
virtual_screen() { pgrep -f "^Xvfb $DISPLAY " >/dev/null; }

wait_log() {
    local pattern="$1" offset="${2:-1}" deadline=$((SECONDS + ${JKT_TIMEOUT:-30}))
    while ! tail -c +"$offset" "$ROOT/engine.log" 2>/dev/null | grep -Eq "$pattern"; do
        if ((SECONDS >= deadline)); then
            echo "Timed out waiting for $pattern; see $ROOT/engine.log" >&2
            return 1
        fi
        sleep 0.1
    done
}
stop_game() {
    local window pid executable
    pid=$(cat "$ROOT/engine.pid" 2>/dev/null || true)
    if ! [[ "$pid" =~ ^[0-9]+$ ]] || ! kill -0 "$pid" 2>/dev/null; then
        window=$(WIN 2>/dev/null)
        pid=$([ -z "$window" ] || xdotool getwindowpid "$window")
    fi
    if [ -n "$pid" ]; then
        # Restrict termination to this display's test engine, never another session.
        executable=$(readlink /proc/"$pid"/exe)
        if [ "${executable% (deleted)}" != "$ENGINE/openjkdf2" ] ||
            ! tr '\0' '\n' < "/proc/$pid/environ" | grep -Fxq "OPENJKDF2_ROOT=$ROOT"; then
            echo "Unexpected test window process $pid" >&2; return 1
        fi
        kill "$pid"
        for i in $(seq 1 50); do kill -0 "$pid" 2>/dev/null || break; sleep 0.1; done
    fi
    rm -f "$ROOT/engine.pid"
}
run() {
case "$1" in
start)
    shift
    mkdir -p "$ROOT/player" "$SHOTS"
    for d in Resource Episode MUSIC; do [ -e "$ROOT/$d" ] || ln -s "$GAME/$d" "$ROOT/$d"; done
    # The engine checks for resource/jk_.cd; the symlinked folders keep their Windows names.
    [ -e "$ROOT/resource" ] || ln -s "$GAME/Resource" "$ROOT/resource"
    [ -e "$ROOT/episode" ] || ln -s "$GAME/Episode" "$ROOT/episode"
    # The mod's own menu and HUD art from this checkout, as build_engine.sh installs it.
    # A root whose rpg/art already is (or links to) this checkout's art keeps it as it is.
    mkdir -p "$ROOT/rpg/art"
    for art in "$(dirname "$0")"/../art/*.bmp; do
        [ "$art" -ef "$ROOT/rpg/art/${art##*/}" ] || cp "$art" "$ROOT/rpg/art/"
    done
    SKY="$(dirname "$0")/../jkgm/materials/rekindled-sky"
    if [ -f "$SKY/metadata.json" ]; then
        mkdir -p "$ROOT/rpg/jkgm/materials/rekindled-sky"
        for asset in "$SKY"/*.png "$SKY/metadata.json"; do
            [ "$asset" -ef "$ROOT/rpg/jkgm/materials/rekindled-sky/${asset##*/}" ] || cp "$asset" "$ROOT/rpg/jkgm/materials/rekindled-sky/"
        done
    fi
    # setsid detaches both from this shell; otherwise WSL ends them when the calling command returns.
    virtual_screen || { setsid -f Xvfb "$DISPLAY" -screen 0 "${JKT_SCREEN:-1920x1080x24}" -nolisten tcp >"$ROOT/xvfb.log" 2>&1; sleep 1; }
    virtual_screen && xdotool getdisplaygeometry >/dev/null 2>&1 || { echo "Virtual screen unavailable; refusing to launch the game" >&2; exit 1; }
    stop_game
    cd "$ROOT"
    # Silence: WSL forwards Linux audio to the Windows speakers, so mute every path the engine has
    # (SDL, OpenAL Soft and PulseAudio); keep test audio isolated from the desktop.
    OPENJKDF2_ROOT="$ROOT" SDL_AUDIODRIVER=dummy SDL_AUDIO_DRIVER=dummy ALSOFT_DRIVERS=null \
        PULSE_SERVER=unix:/nonexistent LD_LIBRARY_PATH="$ENGINE" \
        setsid -f bash -c 'echo "$$" > "$1"; shift; exec "$@"' bash "$ROOT/engine.pid" \
        stdbuf -oL -eL "$ENGINE/openjkdf2" "$@" >"$ROOT/engine.log" 2>&1  # line-buffered log
    for i in $(seq 1 60); do [ -n "$(WIN)" ] && break; sleep 0.5; done
    [ -n "$(WIN)" ] && echo "test game running" || { echo "test game did not open; see $ROOT/engine.log"; tail -20 "$ROOT/engine.log"; stop_game; exit 1; }
    ;;
key)  shift; for k in "$@"; do xdotool key --window "$(WIN)" --delay "${JKT_KEY_DELAY:-30}" "$k"; sleep 0.05; done ;;
hold) xdotool keydown --window "$(WIN)" "$2"; sleep "$3"; xdotool keyup --window "$(WIN)" "$2" ;;
type) shift; xdotool type --window "$(WIN)" --delay 2 "$*" ;;
click) xdotool mousemove "$2" "$3" click 1 ;;
down) xdotool mousedown "${2:-1}" ;;  # hold a mouse button across later steps, e.g. a saber guard
up) xdotool mouseup "${2:-1}" ;;
fire) xdotool mousedown "${3:-1}"; sleep "$(printf '%d.%03d' "$(( $2 / 1000 ))" "$(( $2 % 1000 ))")"; xdotool mouseup "${3:-1}" ;;
shot) run shotwin "$2" ;;
size) read -r screen_w screen_h <<< "$(xdotool getdisplaygeometry)"; xdotool windowsize --sync "$(WIN)" "$2" "$3"; xdotool windowmove "$(WIN)" $(( (screen_w - $2) / 2 )) $(( (screen_h - $3) / 2 )); sleep 1 ;;
shotwin) eval "$(xdotool getwindowgeometry --shell "$(WIN)")"
    xwd -root -silent | convert xwd:- -crop "${WIDTH}x${HEIGHT}+${X}+${Y}" +repage "$SHOTS/$2.png" && echo "$SHOTS/$2.png" ;;
console) shift
    # Keep the output boundary for an optional assertion on this command alone.
    wc -c < "$ROOT/engine.log" > "$ROOT/command-offset"
    run key shift+Escape; sleep 0.15; run type "$*"; run key Return shift+Escape
    if tail -c +"$(( $(cat "$ROOT/command-offset") + 1 ))" "$ROOT/engine.log" | grep -Fq 'Position not in world'; then
        echo "Warp failed: $*" >&2; return 1
    fi ;;
expect) shift
    local offset=$(( $(cat "$ROOT/command-offset") + 1 ))
    if ! tail -c +"$offset" "$ROOT/engine.log" | grep -Fq -- "$*"; then
        echo "Expected command output missing: $*" >&2; return 1
    fi ;;
enter)
    wait_log 'RPG (briefing ready|gameplay ready)'
    local state offset
    state=$(grep -E 'RPG (briefing ready|gameplay ready)' "$ROOT/engine.log" | tail -1)
    if [[ "$state" == *'briefing ready'* ]]; then
        offset=$(( $(wc -c < "$ROOT/engine.log") + 1 ))
        run key Return
        wait_log 'RPG gameplay ready' "$offset"
    fi ;;
load)
    local offset=$(( $(wc -c < "$ROOT/engine.log") + 1 )) previous restored
    previous=$(grep -E 'RPG (save restored|gameplay ready):' "$ROOT/engine.log" | tail -1)
    run key F9
    wait_log 'RPG save restored:' "$offset"
    restored=$(tail -c +"$offset" "$ROOT/engine.log" | grep 'RPG save restored:' | tail -1)
    if [ "${previous##*: }" != "${restored##*: }" ]; then
        # Cross-map restores can stop at the destination's briefing after reading the save.
        wait_log 'RPG (briefing ready|gameplay ready)' "$offset"
        run enter
    fi
    # Wait one input frame after the restore callback returns.
    sleep 0.05 ;;
wait) sleep "$2" ;;
do) shift; for step in "$@"; do read -r -a parts <<< "$step"; run "${parts[@]}"; done ;;
stop) stop_game; pkill -f "^Xvfb $DISPLAY " || true; echo "test game stopped" ;;
*) echo "usage: start|key|hold|type|click|down|up|fire|shot|size|shotwin|console|expect|enter|load|wait|do|stop"; exit 2 ;;
esac

}
if [ "${1:-}" != start ] && [ "${1:-}" != stop ]; then
    virtual_screen || { echo "Virtual screen unavailable; refusing test input" >&2; exit 1; }
fi
run "$@"
