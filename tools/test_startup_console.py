"""Compile the real Windows startup console block with observable OS calls."""
from pathlib import Path
import subprocess
import sys
import tempfile

source = (Path(sys.argv[1]) / "src/main.c").read_text()
start = source.index("    // Normal desktop launches need only the game window.")
block = source[start:source.index("    int can_has_crashdumps", start)]
code = r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <strings.h>
#define __strcmpi strcasecmp
static int allocations, redirects, succeeds = 1;
static int AllocConsole(void) { ++allocations; return succeeds; }
static int freopen_s(FILE** output, const char* path, const char* mode, FILE* stream) {
    const int slot = redirects++;
    assert(slot < 3);
    assert(!strcmp(path, slot ? "CONOUT$" : "CONIN$"));
    assert(!strcmp(mode, slot ? "w" : "r"));
    assert(stream == (slot == 0 ? stdin : slot == 1 ? stdout : stderr));
    *output = stream;
    return 0;
}
static void launch(int argc, char** argv) {
    allocations = redirects = 0;
''' + block + r'''
}
int main(void) {
    char* normal[] = {"openjkdf2.exe", "-autostart", "-sp"};
    launch(1, normal); assert(!allocations && !redirects);
    launch(3, normal); assert(!allocations && !redirects);
    char* debug[] = {"openjkdf2.exe", "-console"};
    launch(2, debug); assert(allocations == 1 && redirects == 3);
    debug[1] = "/CONSOLE";
    launch(2, debug); assert(allocations == 1 && redirects == 3);
    debug[1] = "-console-other";
    launch(2, debug); assert(!allocations && !redirects);
    debug[1] = "-console"; succeeds = 0;
    launch(2, debug); assert(allocations == 1 && !redirects);
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix="jk-console-check-") as tmp:
    path = Path(tmp)
    (path / "check.c").write_text(code)
    subprocess.run(["cc", "-std=c99", "-Wall", "-Werror", str(path / "check.c"),
                    "-o", str(path / "check")], check=True)
    subprocess.run([str(path / "check")], check=True)
print("Windows startup: quiet default, explicit console, streams and allocation failure passed")
