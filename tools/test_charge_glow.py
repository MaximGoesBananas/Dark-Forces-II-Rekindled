"""Compile the real bowcaster charge share behind the green barrel glow; check where it is drawn."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

src = Path(sys.argv[1]) / "src"
weapons = (src / "Main/jkRpgWeapons.c").read_text()
pov = (src / "World/jkPlayer.c").read_text()
share = ""
for name in ("static flex_t jkRpg_BowChargeShare(", "static flex_t jkRpg_RifleFlashShare("):
    start = weapons.index(name)
    share += weapons[start:weapons.index("\n}\n", start) + 3]
# Lights are drawn on top of the barrel (no depth test), so its tip cannot darken them.
glow = weapons[weapons.index("void jkRpg_DrawChargeGlow("):]
assert glow.index("rdSetZBufferMethod(RD_ZBUFFER_NOREAD_NOWRITE);") < glow.index("rdThing_Draw(&jkRpg_aGlowThing[kind], &place);")
# Drawn after the first-person model, reading its depth without writing it, like the saber blade.
draw = pov.index("jkRpg_DrawChargeGlow(&playerThings[playerThingIdx].povModel, &orient);")
assert pov.rindex("rdThing_Draw(&playerThings[playerThingIdx].povModel, &orient);", 0, draw) < draw
assert pov.rindex("rdSetZBufferMethod(RD_ZBUFFER_READ_NOWRITE);", 0, draw) > pov.rindex("rdCache_Flush();", 0, draw) - 200
assert "jkRpg_FreeChargeGlow();" in weapons[weapons.index("void jkRpg_WeaponsResetSession("):]

code = r'''
#include <assert.h>
#include <math.h>
#include <stdio.h>
typedef double flex_t;
typedef struct { int unused; } SithThing;
typedef struct { double charge; int bolts; } jkRpgMods;
enum { RPG_RIFLE = 3, RPG_BOWCASTER = 5 };
#define RPG_FLASH_TIME 0.09
static double jkRpg_rifleShot = -1;
#define RPG_BOW_STAGE 0.6
static SithThing player; static int active = 1, held = RPG_BOWCASTER, rank3;
static double sithWeapon_8BD0A0[2] = {-1, -1}, sithTime_g_secGameTime = 10, chargeRate = 1;
static int jkRpg_IsActive(SithThing* p) { return active; }
static int jkRpg_CurWeapon(SithThing* p) { return held; }
static void jkRpg_GetMods(SithThing* p, int w, jkRpgMods* m) { m->charge = chargeRate; m->bolts = rank3 ? 7 : 5; }
''' + share + r'''
int main(void) {
    assert(jkRpg_BowChargeShare(&player) == -1);                       // not charging: no glow
    sithWeapon_8BD0A0[0] = 10; assert(jkRpg_BowChargeShare(&player) == 0);
    sithTime_g_secGameTime = 10.6; assert(fabs(jkRpg_BowChargeShare(&player) - 0.5) < 1e-9);   // three bolts
    sithTime_g_secGameTime = 11.25; assert(jkRpg_BowChargeShare(&player) == 1);                // five bolts: full
    rank3 = 1; assert(fabs(jkRpg_BowChargeShare(&player) - 1.25 / 1.8) < 1e-9);                 // Full spread: seven
    chargeRate = 2; assert(jkRpg_BowChargeShare(&player) == 1); chargeRate = 1; rank3 = 0;   // Fast charge
    held = 3; assert(jkRpg_BowChargeShare(&player) == -1); held = RPG_BOWCASTER;            // other weapons
    active = 0; assert(jkRpg_BowChargeShare(&player) == -1); active = 1;
    // The rifle's flash: full just after a shot, gone after 0.09 s, only with the rifle in hand.
    held = RPG_RIFLE; sithTime_g_secGameTime = 20; assert(jkRpg_RifleFlashShare(&player) == -1);   // no shot yet
    jkRpg_rifleShot = 20; assert(jkRpg_RifleFlashShare(&player) == 1);
    sithTime_g_secGameTime = 20.045; assert(fabs(jkRpg_RifleFlashShare(&player) - 0.5) < 1e-9);
    sithTime_g_secGameTime = 20.1; assert(jkRpg_RifleFlashShare(&player) == -1);
    sithTime_g_secGameTime = 19; assert(jkRpg_RifleFlashShare(&player) == -1);                     // a loaded earlier time
    sithTime_g_secGameTime = 20.01; held = RPG_BOWCASTER; assert(jkRpg_RifleFlashShare(&player) == -1);
    puts("Muzzle lights: the bowcaster's charge light grows with its volley stages (Fast charge, Full spread), the rifle's flash fades within 0.09 s, both drawn on top of the first-person weapon passed");
}
'''
scratch = Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-charge-glow"
scratch.mkdir(parents=True, exist_ok=True)
cfile, binary = scratch / "glow.c", scratch / "glow"
try:
    cfile.write_text(code)
    subprocess.run(["cc", "-std=gnu99", "-Wall", str(cfile), "-lm", "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
finally:
    cfile.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)
