"""Record matched original/mod scenes on already-running isolated Xvfb sessions.

WSL only. See docs/SHOWCASE.md for setup and provenance. Captures actual gameplay;
no captions, painted effects or replacement frames are added to the recordings.
"""
import tempfile
import argparse
import ctypes
import json
import math
import os
from pathlib import Path
import select
import subprocess
import time

PROJECT = Path(__file__).resolve().parents[1]
WORK = Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-release"
SESSION = PROJECT / "tools/test_session.sh"
GRENADE_LOOK = 60       # relative mouse pixels upward before the throw (0.4 sensitivity)
GRENADE_TAKE = 4.3      # charge from 0.2 s; input latency puts the release about 3.1 s into the take
BALANCE_RETAINED = 13.0 # seconds of balance.gif before its grenade scene (crates, rifle, pickup)
GRENADE_START = 2.6     # seconds cut from the start: the end of the charge remains visible
GRENADE_END = 3.8       # the scene ends here, shortly after both throws leave the view

CANDIDATES = ("crates", "grenade", "repeater", "rail", "concussion", "movement",
              "power-limit", "grenade-limit", "energy-pickup", "saber-guard",
              "saber-heavy", "bryar", "bowcaster")

def candidate(scene, output):
    """One fresh matched scene; staged equipment, real mechanics, separate test profiles."""
    if scene not in CANDIDATES:
        raise ValueError(scene)
    feature = "candidate-" + scene
    legacy = "balance-" + scene
    start_campaign(legacy)
    for edition in ("original", "mod"):
        if scene in ("crates", "grenade"):
            record(edition, legacy)
            (WORK / f"{legacy}-{edition}.mp4").replace(WORK / f"{feature}-{edition}.mp4")
            continue
        position = "10.64 -11.95 3.025 0 135 0"
        command(edition, "do", "size 800 600", "console whiteflag 1",
                "console warp " + position, "key Home", "console r_fov 90",
                "console r_gamma 1", "console hud_scale 1.5", "console hud_disableWeaponWaggle 1",
                "console r_fpslimit 60", "console r_enableVsync 0")
        if scene != "energy-pickup":
            command(edition, "do", "key t", "type red5", "key Return")
        else:
            command(edition, "do", "console npc spawn strifle", "hold w 0.6", "key 3",
                    "console warp " + position, "key Home", "console npc spawn energycell")
        weapon = {"repeater": "6", "rail": "7", "concussion": "9",
                  "power-limit": "6", "grenade-limit": "4", "energy-pickup": "3",
                  "saber-guard": "0", "saber-heavy": "0", "bowcaster": "5"}.get(scene, "2")
        command(edition, "key", weapon)
        time.sleep(6)
        actions = []
        duration = 4
        if scene in ("repeater", "rail", "concussion", "bryar"):
            actions = [(0.5, "fire", "2500")]
        elif scene == "movement":
            actions = [(0.5, "hold", "w", "1.2")]
            duration = 3
        elif scene == "energy-pickup":
            actions = [(1, "hold", "w", "0.85")]
        elif scene == "saber-guard":
            actions = [(0.5, "fire", "2000", "3")]
        elif scene == "saber-heavy":
            actions = [(0.5, "fire", "1300")]
        elif scene == "bowcaster":  # a full charge, then the volley: the mod shows the charge at the tip
            actions = [(0.5, "fire", "2200")]
        take(edition, feature, duration, actions)
        command(edition, "shotwin", feature + "-" + edition)
    combine(feature, output)


def command(edition, *args):
    env = dict(os.environ, JKT_TIMEOUT="90", JKT_KEY_DELAY="150", JKT_DISPLAY=":101" if edition == "original" else ":102",
               JKT_ROOT=str(WORK / edition),
               JKT_SRC="/home/maxim/src/OpenJKDF2-showcase-original" if edition == "original" else "/home/maxim/src/OpenJKDF2")
    # The original engine polls controls once per frame. Hold a key through several
    # frames while software rendering and recording; a 30 ms tap can be missed.
    if args[0] == "key": args = ("hold", args[1], "0.15")
    if args[0] == "do": args = ("do", *("hold " + step[4:] + " 0.15" if step.startswith("key ") else step for step in args[1:]))
    return subprocess.check_output(["bash", str(SESSION), *args], env=env, text=True)


def setting(which, value, color=None):
    """Change the real mod Setup slider between takes; never paint a variant."""
    command("mod", "key", "Escape")
    time.sleep(0.5)
    command("mod", "click", "1210", "727")
    time.sleep(0.5)
    # 800x600 window centred at (560,240); menu is scaled from 640x480.
    x = (75 if which == "saber" else 462) + value * 55
    command("mod", "click", str(560 + x), "740" if which == "saber" else "465")
    if color is not None:
        command("mod", "click", str(1022 + color * 55), "603")
    time.sleep(0.3)
    command("mod", "click", "1230", "802")  # OK, then Return to Game.
    time.sleep(0.5)
    if which == "saber":
        saved = json.loads((WORK / "mod/registry.json").read_text())["rpgSaberColor"]
        assert saved == [2, 0, 3, 4, 1][value], (which, value, saved)
    else:
        profile = (WORK / "mod/player/Player/Player.plr").read_text()
        assert f"crosshair {value}" in profile.splitlines(), (which, value)
        if color is not None:
            saved = json.loads((WORK / "mod/registry.json").read_text())["rpgCrosshairColor"]
            assert saved == color, (color, saved)
    command("mod", "click", "820", "565")
    # Let any click carried over from Return to Game and its animation settle.
    time.sleep(1.5)


def start_campaign(feature, level=None):
    level = level or ("06abarons.jkl" if feature == "balance-crates" else "02narshadda.jkl")
    for edition in ("original", "mod"):
        if (WORK / edition / "jkl").exists():
            raise RuntimeError("Remove old loose showcase levels before a campaign capture")
    for edition in ("original", "mod"):
        command(edition, "start", "-autostart", "-sp", "-episode", "JK1", "-map", level)
    command("mod", "enter")
    # Upstream has no RPG readiness events. Its music starts when the briefing closes.
    deadline = time.monotonic() + 90
    while "stdMci: play track" not in (WORK / "original/engine.log").read_text():
        if time.monotonic() > deadline: raise RuntimeError("Original briefing did not close")
        command("original", "key", "Return")
        time.sleep(0.5)


def record(edition, feature):
    if feature == "balance-rifle":
        command(edition, "do", "size 800 600",
                "console warp 10.64 -11.95 3.025 0 135 0", "key Home", "console r_fov 90",
                "console r_gamma 1", "console hud_scale 1.5", "console hud_disableWeaponWaggle 1", "key 3")
        time.sleep(5)
        take(edition, feature, 5, [(0.5, "fire", "3000")])
        return
    if feature == "balance-pickup":
        command(edition, "do", "size 800 600",
                "console warp 10.64 -11.95 3.025 0 135 0", "key Home", "console r_fov 90",
                "console r_gamma 1", "console hud_scale 1.5", "console hud_disableWeaponWaggle 1",
                "key 3", "console npc spawn energycell")
        time.sleep(5)
        take(edition, feature, 5, [(1, "hold", "w", "0.85")])
        return

    if feature == "balance-grenade":
        # The open courtyard; the same relative mouse input raises the aim onto the far wall.
        # Primary throws explode on impact, showing where each one went.
        command(edition, "do", "size 800 600", "console whiteflag 1", "key t", "type red5", "key Return",
                "console warp 10.64 -11.95 3.025 0 135 0", "key Home", "console r_fov 90",
                "console r_gamma 1", "console hud_scale 1.5", "console hud_disableWeaponWaggle 1", "key 4")
        mouse_pan(edition, 0, -GRENADE_LOOK, 0.5)
        time.sleep(6)
        # A full two-second charge, then the release; the combiner keeps only its end and the flight.
        take(edition, feature, GRENADE_TAKE, [(0.2, "fire", "2200")])
        return
    if feature == "balance-crates":
        command(edition, "do", "size 800 600", "console whiteflag 1",
                "console warp 2.053887 28.705482 0.220163 0 -59.408 0", "key Home", "console r_fov 90",
                "console r_gamma 1", "console hud_scale 1.5", "console hud_disableWeaponWaggle 1", "key 2")
        time.sleep(5)
        # A still matched view of the alcove: no movement, jump or camera turn.
        take(edition, feature, 3, [])
        return
    if feature in ("civilians-market", "civilians-bar", "civilians-plaza"):
        position = {"civilians-market": "14.8 38.95 0.9 0 0 0",
                    "civilians-bar": "-10.126884 -4.747793 -1.179877 0 154.201691 0",
                    "civilians-plaza": "20 39.5 0.95 0 0 0"}[feature]
        command(edition, "do", "size 960 540", "console warp " + position, "key Home",
                "console r_fov 90",
                "console whiteflag 1", "console r_gamma 1.0", "console hud_scale 1.5",
                "console hud_disableWeaponWaggle 1", "console r_fpslimit 60",
                "console r_enableVsync 0", "key 2")
        time.sleep(5)
        take(edition, feature, 4, [(0.2, "pan", 16, 0, 1.5),
                                 (2.2, "pan", -16, 0, 1.5)])
        command(edition, "console", "r_fov 90")
        return
    if feature.startswith("sky-"):
        position = "-0.7645 -4.738 -0.2034 0 -90 0" if feature == "sky-landscape" else "10.64 -11.95 3.025 0 135 0"
        command(edition, "do", "console warp " + position, "key Home",
                "console whiteflag 1", "console r_gamma 1.0", "console hud_scale 1.5",
                "console hud_disableWeaponWaggle 1", "console r_fpslimit 60",
                "console r_enableVsync 0", "key 2")
        time.sleep(6)
        take(edition, feature, 6, [(0.15, "pan", 70, -100, 2.5),
                                 (3.15, "pan", -70, 100, 2.5)])
        return
    if feature == "setup":
        # Begin on the main menu. Show the consolidated page beside the old tabs.
        actions = [(0.8, "click", "1240", "740")]
        if edition == "original":
            actions += [(2.0, "click", "660", "365"), (3.1, "click", "1230", "802"),
                        (3.5, "click", "960", "365"), (4.6, "click", "1230", "802"),
                        (5.0, "click", "1110", "365"), (6.1, "click", "1230", "802"),
                        (6.5, "click", "1260", "365")]
        take(edition, feature, 8, actions)
        return
    if edition == "mod" and feature == "weapons":
        setting("crosshair", 1, 0)
    if edition == "mod" and feature in ("saber", "crosshair"):
        setting(feature, 0 if feature == "saber" else 1)
    command(edition, "do", "console warp 10.64 -11.95 3.025 0 135 0", "key Home",
            "console bactame", "console r_gamma 1.0", "console hud_scale 1.5",
            "console hud_disableWeaponWaggle 1", "console r_fpslimit 60", "console r_enableVsync 0",
            "console hud_crosshairScale 1",
            "key " + ("0" if feature == "saber" else "3"))
    if feature == "progression":
        command(edition, "console", "npc spawn reeyeesgun")
        if edition == "mod":
            command(edition, "console", "givexp 94")  # the mission 2 kill gives 6 (60% of 10)
    # Let the actual game notifications and selection overlay expire before the take.
    time.sleep(6)
    actions = {
        "weapons": [(0.4, "key", "3"), (2.1, "key", "5"), (3.8, "key", "6"), (5.5, "key", "9")],
        "saber": [(0.15, "hold", "z", "0.3")],
        "crosshair": [],
        "progression": [(0.6, "fire", "2000"), (4.5, "key", "k"), (6.5, "key", "Right"), (8.5, "key", "Right")],
    }[feature]
    if feature == "progression" and edition == "original": actions = actions[:1]
    duration = 12 if feature == "progression" else 8 if feature == "weapons" else 2.5 if feature == "crosshair" else 7.5
    output = WORK / (feature + "-" + edition + ".mp4")
    if edition == "mod" and feature in ("saber", "crosshair"):
        parts = []
        if feature == "saber":
            parts.append(take(edition, "saber-swing", 2.5, actions))
        variants = [(v, None) for v in range(5)] if feature == "saber" else [(1, 0), (2, 1), (3, 2), (4, 3), (4, 4)]
        for value, color in variants:
            setting(feature, value, color)
            parts.append(take(edition, f"{feature}-{value}-{color}", 1 if feature == "saber" else 0.5, []))
        listing = WORK / (feature + "-parts.txt")
        listing.write_text("".join(f"file '{p.name}'\n" for p in parts))
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat",
                        "-safe", "0", "-i", str(listing), "-c", "copy", str(output)], check=True)
    else:
        take(edition, feature, duration, actions)
    if feature == "progression" and edition == "mod": command(edition, "key", "k")
    print(output, flush=True)


def mouse_pan(edition, dx, dy, duration):
    """Send actual relative mouse input with a gentle start and stop, without warping the view."""
    x11 = ctypes.CDLL("libX11.so.6")
    xtst = ctypes.CDLL("libXtst.so.6")
    x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
    x11.XOpenDisplay.restype = ctypes.c_void_p
    x11.XFlush.argtypes = x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
    xtst.XTestFakeRelativeMotionEvent.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_ulong]
    display = x11.XOpenDisplay(b":101" if edition == "original" else b":102")
    if not display:
        raise RuntimeError("Cannot open capture display")
    try:
        start, previous = time.monotonic(), (0, 0)
        steps = round(duration * 60)
        for step in range(1, steps + 1):
            time.sleep(max(0, start + duration * step / steps - time.monotonic()))
            ease = (1 - math.cos(math.pi * step / steps)) / 2
            target = (round(dx * ease), round(dy * ease))
            xtst.XTestFakeRelativeMotionEvent(display, target[0] - previous[0], target[1] - previous[1], 0)
            x11.XFlush(display)
            previous = target
    finally:
        x11.XCloseDisplay(display)


def take(edition, name, duration, actions):
    display = ":101" if edition == "original" else ":102"
    env = dict(os.environ, DISPLAY=display)
    window = subprocess.check_output(["xdotool", "search", "--name", "OpenJKDF2"], env=env, text=True).splitlines()[0]
    geometry = dict(line.split("=", 1) for line in subprocess.check_output(["xdotool", "getwindowgeometry", "--shell", window], env=env, text=True).splitlines())
    output = WORK / (name + "-" + edition + ".mp4")
    with output.with_suffix(".log").open("w") as log:
        capture = subprocess.Popen(["ffmpeg", "-hide_banner", "-y", "-stats_period", "0.05",
                                    "-f", "x11grab", "-probesize", "32", "-draw_mouse", "0",
                                    "-framerate", "30", "-video_size", geometry["WIDTH"] + "x" + geometry["HEIGHT"],
                                    "-i", display + ".0+" + geometry["X"] + "," + geometry["Y"],
                                    "-vf", "setpts=N/(30*TB)", "-r", "30", "-frames:v", str(round(duration * 30)),
                                    "-an", "-c:v", "libx264rgb", "-preset", "ultrafast", "-tune", "zerolatency", "-crf", "0",
                                    "-video_track_timescale", "15360",
                                    "-pix_fmt", "rgb24", "-progress", "pipe:1", str(output)], stdout=subprocess.PIPE, stderr=log)
        try:
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if select.select([capture.stdout], [], [], 0.2)[0]:
                    line = capture.stdout.readline()
                    if line.startswith(b"frame=") and int(line.split(b"=")[1]) > 0: break
                if capture.poll() is not None: raise RuntimeError("Capture failed; see " + str(log.name))
            else: raise RuntimeError("Capture did not begin")
            start = time.monotonic()
            for at, *action in actions:
                time.sleep(max(0, start + at - time.monotonic()))
                if action[0] == "pan": mouse_pan(edition, *action[1:])
                else: command(edition, *action)
            capture.communicate(timeout=duration + 10)
            if capture.returncode: raise RuntimeError("Capture failed; see " + str(log.name))
            if time.monotonic() - start < duration * 0.7:
                raise RuntimeError("Capture finished too early; inspect frame timing: " + str(log.name))
        finally:
            if capture.poll() is None: capture.terminate(); capture.wait(timeout=5)
    probe = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries",
                       "stream=nb_frames,r_frame_rate", "-of", "json", str(output)]))["streams"][0]
    assert probe["r_frame_rate"] == "30/1" and int(probe["nb_frames"]) == round(duration * 30), probe
    return output


def combine(feature, target=None):
    target = target or PROJECT / "docs/media"
    target.mkdir(exist_ok=True)
    start = {"weapons": 2, "progression": 1, "saber": 0.5, "candidate-grenade": GRENADE_START}.get(feature, 0)
    end = 3.65 if feature == "candidate-grenade" else None
    trim = f"trim=start={start}" + (f":end={end}" if end is not None else "") + ",setpts=PTS-STARTPTS,"
    crop = "crop=320:240:(iw-320)/2:(ih-240)/2," if feature == "crosshair" else ""
    inputs = [WORK / (feature + "-" + edition + ".mp4") for edition in ("original", "mod")]
    prefix = ""
    scenes = {"sky": ("sky-landscape", "sky-space"),
              "civilians": ("civilians-bar", "civilians-market", "civilians-plaza"),
              "balance": ("balance-crates", "balance-rifle", "balance-pickup", "balance-grenade")}.get(feature)
    if scenes:
        inputs = [WORK / (scene + "-" + edition + ".mp4") for edition in ("original", "mod")
                  for scene in scenes]
        n = len(scenes)
        # Retained crate footage can be 400x300 while fresh takes are 800x600.
        # Normalize every scene before concat; apply the same scale to both sides.
        normalise = "scale=400:300:flags=lanczos,setsar=1," if feature == "balance" else ""
        cut = {"balance-grenade": f"trim=start={GRENADE_START}:end={GRENADE_END},setpts=PTS-STARTPTS,"}
        prefix = "".join(f"[{i}:v]{cut.get(scenes[i % n], '')}{normalise}null[s{i}];" for i in range(2 * n))
        prefix += "".join("".join(f"[s{i}]" for i in range(offset, offset+n)) + f"concat=n={n}:v=1:a=0[{name}];" for name, offset in (("original", 0), ("mod", n)))
    left, right = ("original", "mod") if scenes else ("0:v", "1:v")
    size, fps, colors, dither = ("320:240", 10, 256, "none") if feature == "sky" else ("600:450", 12, 256, "bayer:bayer_scale=5")
    if feature in ("civilians", "balance"):
        size, fps, colors, dither = "400:300", 15 if feature == "balance" else 10, 256, "none"
    if feature == "civilians":
        size = "400:225"
    filters = (prefix + f"[{left}]{trim}{crop}fps={fps},scale={size}:flags=lanczos,setsar=1[l];"
               f"[{right}]{trim}{crop}fps={fps},scale={size}:flags=lanczos,setsar=1[r];"
               f"[l][r]hstack=inputs=2,split[a][b];[a]palettegen=stats_mode=full:reserve_transparent=0:max_colors={colors}[p];"
               f"[b][p]paletteuse=dither={dither}:diff_mode=rectangle")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    *(arg for path in inputs for arg in ("-i", str(path))), "-filter_complex", filters,
                    "-loop", "0", str(target / (feature + ".gif"))], check=True)


def append_grenade():
    """Rebuild balance.gif from its published first scenes plus a fresh grenade scene.

    Use when the crate, rifle and pickup raw takes are no longer available."""
    gif = PROJECT / "docs/media/balance.gif"
    side = (f"trim=start={GRENADE_START}:end={GRENADE_END},setpts=PTS-STARTPTS,"
            "fps=15,scale=400:300:flags=lanczos,setsar=1")
    filters = (f"[0:v]trim=end={BALANCE_RETAINED},setpts=PTS-STARTPTS,fps=15,setsar=1[old];"
               f"[1:v]{side}[l];[2:v]{side}[r];[l][r]hstack=inputs=2[new];"
               "[old][new]concat=n=2:v=1:a=0,split[a][b];"
               "[a]palettegen=stats_mode=full:reserve_transparent=0:max_colors=256[p];"
               "[b][p]paletteuse=dither=none:diff_mode=rectangle")
    out = gif.with_name("balance.new.gif")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(gif),
                    *(arg for e in ("original", "mod") for arg in ("-i", str(WORK / f"balance-grenade-{e}.mp4"))),
                    "-filter_complex", filters, "-loop", "0", str(out)], check=True)
    out.replace(gif)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("feature", choices=["weapons", "saber", "crosshair", "progression", "setup", "civilians", "civilians-market", "civilians-bar", "civilians-plaza", "balance", "balance-crates", "balance-rifle", "balance-pickup", "balance-grenade", "sky-landscape", "sky-space", "sky"] + ["candidate-" + s for s in CANDIDATES])
    parser.add_argument("--work-dir", type=Path, help="Isolated test roots and raw captures")
    parser.add_argument("--output-dir", type=Path, help="GIF destination; required for candidate scenes")
    parser.add_argument("--combine-only", action="store_true")
    parser.add_argument("--edition", choices=["original", "mod"])
    args = parser.parse_args()
    if args.work_dir:
        WORK = args.work_dir.resolve()
    if args.feature.startswith("candidate-"):
        if not args.output_dir: parser.error("Candidate scenes require --output-dir")
        args.output_dir.mkdir(parents=True, exist_ok=True)
        if args.combine_only:
            combine(args.feature, args.output_dir)
        else:
            candidate(args.feature.removeprefix("candidate-"), args.output_dir)
        raise SystemExit(0)
    if args.feature in ("sky", "civilians", "balance") and not args.combine_only:
        parser.error("Record the individual scenes first, then use --combine-only")
    if not args.combine_only:
        if args.feature in ("balance-crates", "balance-grenade"): start_campaign(args.feature)
        for edition in ([args.edition] if args.edition else ["original", "mod"]): record(edition, args.feature)
    if args.feature == "balance-grenade" and args.combine_only: append_grenade()
    if args.feature == "civilians-plaza" or not args.feature.startswith(("sky-", "civilians-", "balance-")): combine(args.feature, args.output_dir)
