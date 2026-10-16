"""Compile both real HUD visibility conditions and the shared weapon preference."""
import os
import tempfile
from pathlib import Path
import re
import subprocess
import sys

source = (Path(sys.argv[1]) / "src/Main/jkHud.c").read_text()
start = source.index("BOOL jkHud_shouldCrosshairBeShownForWeapon(")
weapon = source[start:source.index("\n}", start) + 2]
conditions = re.findall(r"    if \(\s+jkPlayer_setCrosshair\b.*?\n\s*\)\s*\{", source, re.S)
assert len(conditions) == 2, "Check both software and GPU HUD paths"
code = r'''
#include <assert.h>
#include <stdio.h>
typedef int BOOL;
typedef struct {int flags;struct {int flags;} actorParams;} SithThing;
static struct {int type;} camera={1}, *sithCamera_g_pCurCamera=&camera;
static SithThing player, *sithPlayer_g_pLocalPlayerThing=&player;
static int currentWeapon=2, mots, jkPlayer_setCrosshair=1;
static int jkPlayer_setCrosshairOnFist=1, jkPlayer_setCrosshairOnLightsaber=1;
enum {SITHBIN_FISTS=1,SITHBIN_LIGHTSABER=10,SITHBIN_MOTS_FISTS=20,SITHBIN_MOTS_LIGHTSABER=21,
      SITH_TF_DEAD=1,SITH_AF_SCOPEHUD=2};
#define QOL_IMPROVEMENTS
#define MOTS_ONLY_FLAG(x) (mots && (x))
#define MOTS_ONLY_COND(x) (!mots || (x))
static int sithInventory_GetCurrentWeapon(SithThing* p) {return currentWeapon;}
''' + weapon
for i, condition in enumerate(conditions):
    code += f"\nstatic int visible{i}(void) {{\n" + condition + "return 1;} return 0;}\n"
code += r'''
int main(void) {
    int (*paths[])(void)={visible0,visible1};
    for(int path=0;path<2;path++) {
        int (*visible)(void)=paths[path];
        for(int style=0;style<=4;style++) for(int type=1;type<=128;type*=2)
        for(int w=1;w<=10;w++) {
            jkPlayer_setCrosshair=style;camera.type=type;currentWeapon=w;
            assert(visible()==(style!=0 && (type==1 || (type==4 && w!=10))));
        }
        jkPlayer_setCrosshair=1;camera.type=4;currentWeapon=3;
        player.flags=SITH_TF_DEAD;assert(!visible());player.flags=0;
        mots=1;player.actorParams.flags=SITH_AF_SCOPEHUD;assert(!visible());
        player.actorParams.flags=0;currentWeapon=SITHBIN_MOTS_LIGHTSABER;assert(!visible());mots=0;
        camera.type=1;currentWeapon=10;assert(visible());
        jkPlayer_setCrosshairOnLightsaber=0;assert(!visible());jkPlayer_setCrosshairOnLightsaber=1;
        currentWeapon=1;jkPlayer_setCrosshairOnFist=0;assert(!visible());jkPlayer_setCrosshairOnFist=1;
    }
    puts("Both HUD paths: camera modes, all weapons/styles, Off, death, scope and saved preferences passed");
}
'''
scratch = Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-ui"
scratch.mkdir(parents=True, exist_ok=True)
cfile, binary = scratch / "visibility.c", scratch / "visibility"
try:
    cfile.write_text(code)
    subprocess.run(["cc", str(cfile), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
finally:
    cfile.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)
