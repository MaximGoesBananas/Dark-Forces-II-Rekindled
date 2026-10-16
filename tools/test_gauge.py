"""Check actual arc selection against the player's original ring artwork, read-only.
Run in WSL: python3 tools/test_gauge.py ~/src/OpenJKDF2
"""
import ctypes
import math
import re
import struct
import subprocess
import sys
from pathlib import Path

from gob import read_index

root = Path(sys.argv[1]) / "src"
source = (root / "Main/jkRpg.c").read_text()
constants = "\n".join(re.findall(r"^#define RPG_RING_.*$", source, re.M))
functions = []
for name in ("jkRpg_IsOuterArc", "jkRpg_RingSource"):
    start = source.index("static int " + name + "(")
    functions.append(source[start:source.index("\n}", start) + 2])
hud = (root / "Main/jkHud.c").read_text()
ratio = re.search(r"jkRpg_DrawGaugeRings\(jkHud_pStShieldBm, rpgXp,\s*(.*?)\s*,", hud, re.S).group(1)
ratio = ratio.replace("sithInventory_g_aTypes[SITHBIN_SHIELDS].max", "maximum")
code = "#include <stdint.h>\n#include <math.h>\ntypedef double flex_t;\n" + constants
code += "\n" + "\n".join(functions)
code += "\nint selectPixel(int x,int y,double xp,double shield) {return jkRpg_RingSource(x,y,xp,shield);}\n"
code += "double fraction(int v10,double maximum) {return " + ratio + ";}\n"
scratch = Path("/mnt/d/Dev/helm/scratch/jk-rpg-shields")
scratch.mkdir(parents=True, exist_ok=True)
cfile, library = scratch / "check.c", scratch / "check.so"
try:
    cfile.write_text(code)
    subprocess.run(["cc", "-shared", "-fPIC", str(cfile), "-lm", "-o", str(library)], check=True)
    lib = ctypes.CDLL(str(library))
    lib.selectPixel.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_double, ctypes.c_double]
    lib.fraction.argtypes = [ctypes.c_int, ctypes.c_double]
    lib.fraction.restype = ctypes.c_double
    archive = Path("/mnt/d/SteamLibrary/steamapps/common/Star Wars Jedi Knight/Resource/Res1hi.gob")
    entry = next(e for e in read_index(archive) if e[0].lower().endswith("stshield16.bm"))
    with archive.open("rb") as f:
        f.seek(entry[1])
        data = f.read(entry[2])
    mips, pos = [], 128
    for _ in range(11):
        w, h = struct.unpack_from("<II", data, pos)
        pos += 8
        mips.append(struct.unpack_from(f"<{w*h}H", data, pos))
        pos += w * h * 2
    inner = [(i % w, i // w) for i, (a, b) in enumerate(zip(mips[5], mips[10])) if a != b]
    outer = [(i % w, i // w) for i, (a, b) in enumerate(zip(mips[0], mips[5])) if a != b]
    previous = set()
    for percent in range(101):
        filled = {p for p in inner if lib.selectPixel(*p, .37, percent / 100) == 0}
        assert previous <= filled
        previous = filled
        if percent == 0:
            assert not filled
        if percent == 50:
            assert abs(len(filled) / len(inner) - .5) < .04
        if percent == 100:
            assert len(filled) == len(inner)
    for maximum in (100, 120, 140, 160, 180, 200):
        assert lib.fraction(maximum // 2, maximum) == .5
        assert lib.fraction(maximum, maximum) == 1
        assert lib.fraction(0, maximum) == 0
    assert lib.fraction(0, 0) == 0
    for p in inner:
        assert lib.selectPixel(*p, 0, .5) == lib.selectPixel(*p, 1, .5)
        assert lib.selectPixel(*p, .5, -1) == 3
        assert lib.selectPixel(*p, .5, float("nan")) == 3
        assert lib.selectPixel(*p, .5, 2) == 0
    for p in outer:
        angle = math.degrees(math.atan2(p[1] + .5 - 23, p[0] + .5 - 15))
        for xp in (0, .25, .5, 1):
            expected = 1 if (41.5 - angle) / 175 <= xp else 2
            assert lib.selectPixel(*p, xp, 0) == lib.selectPixel(*p, xp, 1) == expected
    print("Shield arc empty/half/full, all upgrade maxima, monotonic fill and unchanged XP passed")
finally:
    cfile.unlink(missing_ok=True)
    library.unlink(missing_ok=True)
