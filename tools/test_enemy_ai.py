"""Check the actual enemy tuning: quicker reactions and much better aim, nothing else.
Run in WSL: python3 tools/test_enemy_ai.py ~/src/OpenJKDF2
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

src = Path(sys.argv[1]) / "src"
source = (src / "Main/jkRpg.c").read_text()
start = source.index("#define RPG_AI_REACTION")
code = source[start:source.index("\n}\n", source.index("flex_t jkRpg_AIMoveScale(")) + 3]
assert "flex_t jkRpg_AIAccuracy(" in code
loader = (src / "AI/sithAIClass.c").read_text()
assert "jkRpg_TuneAIClass(pClass, pPath);" in loader, "the AI class loader must call the tuning"
harness = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
typedef double flex_t;
typedef int (*sithAICommandFunc_t)(void);
typedef struct { flex_t fltArg[16]; int32_t intArg[16]; sithAICommandFunc_t func; } SithAIInstinct;
typedef struct { flex_t alignment, accurancy; int32_t numEntries; SithAIInstinct entries[16]; } SithAIClass;
typedef struct SithThing { struct SithThing* pTemplate; char aName[32]; } SithThing;
#include <strings.h>
#define __strcmpi strcasecmp
static int sithNet_isMulti, Main_bMotsCompat;
static int sithAICmd_LookForTarget(void) { return 0; }
static int sithAICmd_PrimaryFire(void) { return 0; }
static int sithAICmd_BlindFire(void) { return 0; }
static int sithAICmd_LobFire(void) { return 0; }
static int sithAICmd_TurretFire(void) { return 0; }
''' + code.replace("entry->func == sithAICmd_", "entry->func == (sithAICommandFunc_t)sithAICmd_") + r'''
static SithAIClass trooper(void)
{
    // stdefault.ai on Medium: accuracy 0.20; LookForTarget 500, 45000; PrimaryFire 2000 ... first shot 300
    SithAIClass c = {-1.0, 0.20, 3};
    c.entries[0].func = (sithAICommandFunc_t)sithAICmd_LookForTarget;
    c.entries[0].fltArg[0] = 500; c.entries[0].intArg[0] = 500; c.entries[0].fltArg[1] = 45000; c.entries[0].intArg[1] = 45000;
    c.entries[1].func = (sithAICommandFunc_t)sithAICmd_PrimaryFire;
    flex_t fire[10] = {2000, 0.8, 5.0, 0.20, 0.0, 300, 0.20, 0, 2, 500};
    for (int i = 0; i < 10; i++) { c.entries[1].fltArg[i] = fire[i]; c.entries[1].intArg[i] = (int32_t)fire[i]; }
    c.entries[2].func = (sithAICommandFunc_t)sithAICmd_BlindFire;
    c.entries[2].fltArg[0] = 1500; c.entries[2].intArg[0] = 1500;
    return c;
}

int main(void)
{
    SithAIClass c = trooper();
    jkRpg_TuneAIClass(&c, "stdefault.ai");
    assert(c.accurancy > 0.79 && c.accurancy < 0.81);                       // 0.20 -> 0.80
    assert(c.entries[0].intArg[0] == 300 && c.entries[0].intArg[1] == 45000); // looks sooner, same give-up time
    assert(c.entries[1].intArg[5] == 180);                                    // first shot sooner
    assert(fabs(c.entries[1].fltArg[0] - 2000 / 1.4) < 1e-9 && c.entries[1].intArg[0] == 1428); // 40% more often
    assert(c.entries[1].intArg[9] == 357 && c.entries[1].fltArg[8] == 2);       // bursts 40% quicker, same size
    assert(c.entries[1].fltArg[3] == 0.20f || c.entries[1].fltArg[3] == 0.20); // same aim error size
    assert(c.entries[2].intArg[0] == 1500);                                   // other instincts untouched
    // Concussion classes get a longer gap; rail-rifle variants and melee keep their own timing.
    const char* names[] = {"misc\\ai\\bodefault.ai", "misc/ai/BOSENTRY.AI", "bldefault.ai", NULL};
    for (int i=0;i<4;i++) {
        SithAIClass gunner=trooper();
        gunner.entries[2].func=(sithAICommandFunc_t)sithAICmd_PrimaryFire;
        gunner.entries[2].fltArg[2]=0.2; gunner.entries[2].fltArg[0]=1500;
        jkRpg_TuneAIClass(&gunner,names[i]);
        assert(fabs(gunner.entries[1].fltArg[0]-(i<2?3500:2000/1.4))<1e-9);
        assert(gunner.entries[1].intArg[0]==(i<2?3500:1428));
        assert(gunner.entries[2].fltArg[0]==1500);
    }
    // Thrown grenades keep the original aim; blaster fire keeps the better one.
    assert(fabs(jkRpg_AIAccuracy(&c, NULL, 2) - 0.20) < 1e-9 && jkRpg_AIAccuracy(&c, NULL, 0) == c.accurancy);
    // Probe droids keep their original aim for direct fire; other templates keep the better aim.
    SithThing droidTpl = {NULL, "probedroid"}, droid = {&droidTpl}, troopTpl = {NULL, "stormtroop"}, troop = {&troopTpl};
    assert(fabs(jkRpg_AIAccuracy(&c, &droid, 0) - 0.20) < 1e-9 && jkRpg_AIAccuracy(&c, &troop, 0) == c.accurancy);
    SithThing bare = {NULL}; assert(jkRpg_AIAccuracy(&c, &bare, 0) == c.accurancy);
    // The stronger setting remains bounded across enemy classes; lobbed aim is preserved.
    for (int i=0;i<=10;i++) {
        SithAIClass aim=trooper();aim.accurancy=i/10.0;
        jkRpg_TuneAIClass(&aim, "stdefault.ai");
        assert(fabs(aim.accurancy-(0.75+0.25*i/10.0))<1e-9);
        assert(fabs(jkRpg_AIAccuracy(&aim,NULL,2)-i/10.0)<1e-9);
    }
    // Only hostile, melee-only classes move faster: the trooper shoots, a Gamorrean only swings.
    assert(jkRpg_AIMoveScale(&c, NULL) == 1.0);
    SithAIClass g = {-1.0, 1.0, 1};
    g.entries[0].func = (sithAICommandFunc_t)sithAICmd_PrimaryFire; g.entries[0].fltArg[2] = 0.25;
    assert(jkRpg_AIMoveScale(&g, NULL) == 1.1);
    SithThing sarissTpl={NULL,"SARISS"},sariss={&sarissTpl};
    assert(jkRpg_AIMoveScale(&g,&sariss)==1.3*1.25);
    assert(jkRpg_BossReactionMs(&sariss)==250);
    SithThing bossTpl={0},boss={&bossTpl};
    const char* bosses[]={"yun","gorc","pic","maw","sariss","yun2","boc","jerec"};
    for(int i=0;i<8;i++) {
        strcpy(bossTpl.aName,bosses[i]);
        assert(jkRpg_BossReactionMs(&boss)==(i==4?250:((i==6 || i==7)?375:500)));
    }
    strcpy(bossTpl.aName,"maw");assert(jkRpg_AIMoveScale(&g,&boss)==1.1);
    assert(jkRpg_BossReactionMs(NULL)==500 && jkRpg_BossReactionMs(&bare)==500);
    sithNet_isMulti=1;assert(jkRpg_BossReactionMs(&sariss)==500);sithNet_isMulti=0;
    Main_bMotsCompat=1;assert(jkRpg_BossReactionMs(&sariss)==500);Main_bMotsCompat=0;
    sithNet_isMulti=1;assert(jkRpg_AIMoveScale(&g,&sariss)==1.0);sithNet_isMulti=0;
    Main_bMotsCompat=1;assert(jkRpg_AIMoveScale(&g,&sariss)==1.0);Main_bMotsCompat=0;
    assert(jkRpg_AIMoveScale(NULL,&sariss)==1.0);
    // Melee attacks and friendly classes keep their pace; only hostile direct fire speeds up.
    SithAIClass gm = g; gm.entries[0].fltArg[0] = 2000; jkRpg_TuneAIClass(&gm, "stdefault.ai"); assert(gm.entries[0].fltArg[0] == 2000);
    SithAIClass f = trooper(); f.alignment = 1.0; jkRpg_TuneAIClass(&f, "stdefault.ai"); assert(f.entries[1].fltArg[0] == 2000);
    g.alignment = 1.0; assert(jkRpg_AIMoveScale(&g, NULL) == 1.0); g.alignment = -1.0;
    g.entries[1].func = (sithAICommandFunc_t)sithAICmd_LobFire; g.numEntries = 2;
    assert(jkRpg_AIMoveScale(&g, NULL) == 1.0);
    SithAIClass m = trooper();
    sithNet_isMulti = 1; jkRpg_TuneAIClass(&m, "stdefault.ai");
    assert(m.accurancy == 0.20 && m.entries[0].intArg[0] == 500 && m.entries[1].fltArg[0] == 2000);
    sithNet_isMulti = 0; SithAIClass mots = trooper(); Main_bMotsCompat = 1; jkRpg_TuneAIClass(&mots, "stdefault.ai");
    assert(mots.accurancy == 0.20 && mots.entries[1].fltArg[0] == 2000 && jkRpg_AIAccuracy(&mots, NULL, 2) == 0.20);
    assert(jkRpg_AIMoveScale(&g, NULL) == 1.0); Main_bMotsCompat = 0; // Mysteries of the Sith keeps its own enemies
    puts("Enemy tuning: quicker reactions, much better aim and 40% more frequent direct fire and bursts, same damage and give-up time; grenades keep the original aim; melee-only enemies faster passed");
    return 0;
}
'''
with tempfile.TemporaryDirectory() as tmp:
    c = Path(tmp) / "t.c"
    c.write_text(harness)
    subprocess.run(["cc", "-std=gnu11", "-Wall", "-Wno-unused-function", "-o", Path(tmp) / "t", c, "-lm"], check=True)
    print(subprocess.run([Path(tmp) / "t"], check=True, capture_output=True, text=True).stdout.strip())

# The real saber path uses the shorter polling interval without shortening swing recovery.
saber = (src / "Main/jkAI.c").read_text()
assert "sithTime_g_msecGameTime + jkRpg_BossReactionMs(actor->thing)" in saber
assert "instinct->nextUpdate = v19 + sithTime_g_msecGameTime;" in saber
assert "if ( actor->attackDistance > (flex_d_t)*v14 )" in saber
assert "jkSaber_Enable(actor->thing, a2a, a3a, 0.0);" in saber
