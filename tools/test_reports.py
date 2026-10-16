"""Test the actual PNG report writer and reader, including write failures and bad input."""
import os
import tempfile
from pathlib import Path
import struct
import subprocess
import sys

from read_report import read_report
from build_release import validate_release_engine

root = Path(sys.argv[1])
source = (root / "src/Platform/GL/jkgm.cpp").read_text()
start = source.index("int jkgm_write_png_report(")
function = source[start:source.index("\n}\n", start) + 3]
scratch = Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-report-check"
scratch.mkdir(parents=True, exist_ok=True)
cpp, exe, shot, broken = [scratch / n for n in ("check.cpp", "check", "report.png", "broken.png")]
try:
    game = (root / "src/Main/jkGame.c").read_text()
    first = game.index("void jkGame_Screenshot()")
    screenshot = game[first:game.index("\n}", first) + 2]
    # Compile the actual F12 entry point in both configurations. Release saves an
    # ordinary image; only development can request the metadata collector.
    cpp.write_text(r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
typedef int stdFile_t;
static int jkGame_reportPending, Video_dword_5528B0, images, closes;
static int open_file(const char* path,const char* mode) {return !strcmp(path,"SHOT0000.PNG");}
static void close_file(int file) {closes++;}
static struct {int(*fileOpen)(const char*,const char*);void(*fileClose)(int);} host={open_file,close_file}, *pHS=&host;
#define stdString_snprintf snprintf
static void std3D_Screenshot(const char* path) {assert(!strcmp(path,"SHOT0001.PNG"));images++;}
''' + screenshot + r'''
int main() {
    jkGame_Screenshot();
#ifdef RPG_DEVELOPMENT_REPORTS
    assert(jkGame_reportPending==1 && images==0 && closes==0);
#else
    assert(jkGame_reportPending==0 && images==1 && closes==1);
#endif
}
''')
    for flags in ([], ["-DRPG_DEVELOPMENT_REPORTS=1"]):
        subprocess.run(["c++", *flags, str(cpp), "-o", str(exe)], check=True)
        subprocess.run([str(exe)], check=True)
    validate_release_engine(b"ordinary release")
    try:
        validate_release_engine(b"executable\0Jedi Knight RPG location report v1\0")
    except RuntimeError:
        pass
    else:
        raise AssertionError("Development executable accepted for release")
    cpp.write_text("#include <png.h>\n#include <stdio.h>\n#include <stdint.h>\n#include <assert.h>\n" + function + r'''
int main(int argc, char** argv) {
    uint8_t pixels[18]={255,0,0, 0,255,0, 0,0,255, 255,255,255, 32,64,128, 0,0,0};
    assert(!jkgm_write_png_report("/not/a/real/directory/report.png",3,2,pixels,"data"));
    assert(!jkgm_write_png_report(argv[1],0,2,pixels,"data"));
    assert(jkgm_write_png_report(argv[1],3,2,pixels,"map test.jkl\nplayer 1 2 3\nhead_pyr -20 0 0\n"));
}
''')
    # Missing paths and libpng errors must return failure without aborting the game.
    subprocess.run(["c++", str(cpp), "-lpng", "-o", str(exe)], check=True)
    subprocess.run([str(exe), str(shot)], check=True)
    assert read_report(shot) == "map test.jkl\nplayer 1 2 3\nhead_pyr -20 0 0\n"
    data = shot.read_bytes()
    assert struct.unpack_from(">II", data, 16) == (3, 2)  # Odd widths, not only multiples of four.
    for contents in (b"not a png", data[:20], data[:50] + b"x" + data[51:]):
        broken.write_bytes(contents)
        try:
            read_report(broken)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid report accepted")
    clean = bytearray(data[:8])
    pos = 8
    while pos < len(data):
        length, kind = struct.unpack_from(">I4s", data, pos)
        if kind != b"tEXt":
            clean.extend(data[pos:pos + length + 12])
        pos += length + 12
    broken.write_bytes(clean)
    try:
        read_report(broken)
    except ValueError as error:
        assert "no RPG location data" in str(error)
    else:
        raise AssertionError("Ordinary image accepted as a location report")
    print("PNG metadata round-trip, dimensions, write failure, corruption and absent metadata passed")
finally:
    for path in (cpp, exe, shot, broken):
        path.unlink(missing_ok=True)
