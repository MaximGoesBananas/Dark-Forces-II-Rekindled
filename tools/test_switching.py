"""Compile real switching/timer rules; check animation and lockout integration."""
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(sys.argv[1]) / "src"
source = (root / "Main/jkRpgWeapons.c").read_text()
start = source.index("flex_t jkRpg_WeaponSwitchScale(")
end = source.index("\n}", source.index("flex_t jkRpg_ScriptTimer(")) + 2
code = source[start:end]
for file, call in {
    "Cog/jkCog.c": "v6->aTracks[v7].speed /= jkRpg_WeaponSwitchScale(ctx)",
    "Cog/sithCogFunctionThing.c": "puppet->aTracks[track].speed /= jkRpg_WeaponSwitchScale(pCog)",
    "Cog/sithCogFunction.c": "mountWait < 0.0 ? mountWait : mountWait * jkRpg_WeaponSwitchScale(pCog)",
}.items():
    text = (root / file).read_text()
    assert call in text and '#include "Main/jkRpg.h"' in text

harness = r'''
#include <assert.h>
#include <stddef.h>
typedef double flex_t;
typedef struct { int trigId; } sithCog;
typedef struct { int unused; } SithThing;
enum { SITH_MESSAGE_SELECTED=1, SITH_MESSAGE_DESELECTED=2, SITHBIN_FISTS=1, SITHBIN_LIGHTSABER=10 };
static struct { sithCog* cog; } sithInventory_g_aTypes[11];
static SithThing player, *sithPlayer_g_pLocalPlayerThing=&player;
static int active=1, rank=2;
enum { UP_ATHLETICS=2 };
static int jkRpg_Rank(SithThing* p, int up) { return up==UP_ATHLETICS ? rank : 0; }
static int jkRpg_IsActive(SithThing* p) { return p && active; }
'''
checks = r'''
int main(void) {
    sithCog weapons[11]={0}, unrelated={SITH_MESSAGE_SELECTED};
    for(int bin=1;bin<=10;bin++) {
        sithInventory_g_aTypes[bin].cog=&weapons[bin];
        for(int message=1;message<=2;message++) {
            weapons[bin].trigId=message;
            assert(jkRpg_WeaponSwitchScale(&weapons[bin])==0.5);
            assert(jkRpg_ScriptTimer(&weapons[bin],2,0.6)==0.3);
            assert(jkRpg_ScriptTimer(&weapons[bin],1,0.6)==0.3);
        }
        weapons[bin].trigId=3; // fire, charge release, recovery, timer callbacks
        assert(jkRpg_WeaponSwitchScale(&weapons[bin])==1.0);
        assert(jkRpg_ScriptTimer(&weapons[bin],2,0.6)==0.6);
    }
    assert(jkRpg_ScriptTimer(&weapons[10],1,0.6)==0.6); // saber recovery belongs to the manual guard
    // Without Quick draw (second Athletics upgrade) switching keeps the original speed.
    for(rank=0;rank<2;rank++) {
        weapons[3].trigId=1;
        assert(jkRpg_WeaponSwitchScale(&weapons[3])==1.0 && jkRpg_ScriptTimer(&weapons[3],2,0.6)==0.6);
        weapons[10].trigId=3;
        assert(jkRpg_ScriptTimer(&weapons[10],1,0.6)==0.6); // the stock autoblock timer is unchanged
    }
    rank=2;
    assert(jkRpg_WeaponSwitchScale(&unrelated)==1.0);
    assert(jkRpg_WeaponSwitchScale(NULL)==1.0);
    weapons[3].trigId=1; active=0;
    assert(jkRpg_WeaponSwitchScale(&weapons[3])==1.0);
    assert(jkRpg_ScriptTimer(&weapons[3],2,0.6)==0.6);
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix="jk-switch-check-") as tmp:
    path=Path(tmp)
    (path / "check.c").write_text(harness + code + checks)
    subprocess.run(["cc", "-std=c99", str(path / "check.c"), "-o", str(path / "check")], check=True)
    subprocess.run([str(path / "check")], check=True)
print("Switching: Quick draw only, all ten weapons, synchronized timers, unchanged firing/recovery and unrelated scripts passed")
