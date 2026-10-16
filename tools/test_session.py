"""Check that inherited WSLg settings cannot send test input to the desktop."""
from pathlib import Path
import os
import subprocess
import tempfile

script=Path(__file__).with_suffix(".sh").resolve()
with tempfile.TemporaryDirectory(prefix="jk-test-display-") as tmp:
    root=Path(tmp)
    (root/"pgrep").write_text('#!/bin/sh\n[ "$TEST_SCREEN" = 1 ]\n')
    (root/"xdotool").write_text('#!/bin/sh\nprintf "%s %s %s %s\\n" "$DISPLAY" "$SDL_VIDEODRIVER" "$SDL_VIDEO_DRIVER" "${WAYLAND_DISPLAY-unset}" >> "$TEST_LOG"\n[ "$1" != search ] || echo 123\n')
    for p in root.iterdir(): p.chmod(0o755)
    log=root/"input.log"
    env=dict(os.environ,PATH=str(root)+":"+os.environ["PATH"],TEST_LOG=str(log),TEST_SCREEN="1",
             DISPLAY=":0",WAYLAND_DISPLAY="wayland-0",SDL_VIDEODRIVER="wayland",SDL_VIDEO_DRIVER="wayland")
    def run(display):
        return subprocess.run(["bash",str(script),"key","Return"],env=dict(env,JKT_DISPLAY=display),capture_output=True,text=True)
    for display in (":0",":00","localhost:0",":99.0"):
        assert run(display).returncode and not log.exists()
    env["TEST_SCREEN"]="0"
    assert run(":99").returncode and not log.exists()
    env["TEST_SCREEN"]="1"
    assert run(":99").returncode==0
    assert log.read_text().splitlines()==[":99 x11 x11 unset"]*2
print("Test input rejects desktop/missing virtual displays and overrides inherited Wayland drivers")
