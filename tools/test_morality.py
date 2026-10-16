"""Compile the real timer, alignment and old-save repair code with minimal stubs.
Run in WSL: python3 tools/test_morality.py ~/src/OpenJKDF2
"""
import os
import tempfile
import re
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1]) / "src"

def function(file, name):
    source = (root / file).read_text()
    start = re.search(r"(?:static )?(?:void|flex_t) " + name + r"\([^;]*?\)\n\{", source)
    return source[start.start():source.index("\n}", start.end()) + 2]

harness = r'''
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <strings.h>
#define __strcmpi strcasecmp
#define SITH_COG_DEBUG 1
#define SITH_COG_TIMER_SET 2
#define SITH_THING_ACTOR 2
#define SITH_THING_CORPSE 5
#define RPG_BIN_PEDFIX 138
#define SITHBIN_PEDS_KILLED 72
#define SITHBIN_PEDS_TOTAL 73
#define SITHBIN_ALIGNMENT 75
typedef double flex_t;
typedef double cog_flex_t;
typedef struct { const char* aName; } Script;
typedef struct { Script* pScript; unsigned stackPos; double stack[4]; int flags,field_20,idx; } sithCog;
typedef struct { double field_14,field_10; int timerIdx,idx; } SithEventParams;
typedef struct { int type; sithCog* pCog; } SithThing;
typedef struct { int numThings; SithThing aThings[4]; } SithWorld;
static SithWorld world, *sithWorld_g_pCurrentWorld=&world;
static int sithTime_g_msecGameTime=100, events, due, choice, jkRpg_bRestorePedCount;
static SithEventParams last;
static double bins[200], stars;
static double sithCogExec_PopFlex(sithCog* c) { assert(c->stackPos); return c->stack[--c->stackPos]; }
static int sithCogExec_PopInt(sithCog* c) { return sithCogExec_PopFlex(c); }
static void sithEvent_CreateEvent(int task, SithEventParams* p, int ms) { assert(task==4); last=*p; due=ms; events++; }
static int jkPlayer_GetChoice(void) { return choice; }
static double jkPlayer_CalcStarsAlign(void) { return stars; }
static double sithPlayer_GetInvItemAmount(int bin) { return bins[bin]; }
static void sithPlayer_SetInvItemAmount(int bin, double n) { bins[bin]=n; }
static int jkRpg_Get(SithThing* p,int bin) { return bins[bin]; }
static double jkRpg_ScriptTimer(sithCog* c,int id,double delay) { return delay; } // weapon upgrades: unchanged here
static double jkRpg_ForceTimer(sithCog* c,int id,double delay) { return delay; } // Force durations: unchanged here
static void sithInventory_SetInventory(SithThing* p,int bin,double n) { bins[bin]=n; }
static void sithInventory_ChangeInventory(SithThing* p,int bin,double n) { bins[bin]+=n; }
'''
checks = r'''
int main(void) {
    Script scripts[]={{"actor_fn.cog"},{"actor_gd.cog"},{"other.cog"}};
    for (int i=0;i<2;i++) {
        sithCog c={.pScript=&scripts[i],.stackPos=4,.stack={1,1,0,0},.idx=7};
        sithCogFunction_SetTimer(&c);
        assert(c.stackPos==0 && events==i+1 && due==1000 && last.timerIdx==1 && last.idx==7);
    }
    for (int i=0;i<3;i++) {
        sithCog c={.pScript=&scripts[i],.stackPos=1,.stack={2}};
        sithCogFunction_SetTimer(&c); assert(c.field_20==2100 && c.flags==SITH_COG_TIMER_SET);
        c.stackPos=1;c.stack[0]=0;sithCogFunction_SetTimer(&c);assert(c.flags==0);
    }
    assert(events==2);
    bins[72]=1; bins[73]=10; double original=jkPlayer_CalcAlignment(0);
    bins[72]=3; bins[73]=30; assert(jkPlayer_CalcAlignment(0)==original);
    bins[72]=10; bins[73]=36; assert(fabs(jkPlayer_CalcAlignment(0)-(20-100*10.0/36))<1e-9);
    bins[72]=36; assert(jkPlayer_CalcAlignment(0)==-80);
    assert(jkPlayer_CalcAlignment(1)==0); // Multiplayer does not use civilian counts.
    bins[73]=0; assert(jkPlayer_CalcAlignment(0)==20);
    choice=1;assert(jkPlayer_CalcAlignment(0)==100);choice=2;assert(jkPlayer_CalcAlignment(0)==-100);choice=0;
    SithThing player={0}; sithCog female={.pScript=&scripts[0]}, other={.pScript=&scripts[2]};
    world.numThings=2;world.aThings[0]=(SithThing){2,&female};world.aThings[1]=(SithThing){2,&other};world.aThings[2]=(SithThing){5,&female};
    bins[73]=10; bins[138]=0;jkRpg_bRestorePedCount=0;
    jkRpg_RepairPedCount(&player);assert(bins[73]==10 && bins[138]==1); // Fresh timers register normally.
    bins[138]=0;jkRpg_bRestorePedCount=1;jkRpg_RepairPedCount(&player);assert(bins[73]==12);
    jkRpg_bRestorePedCount=1;jkRpg_RepairPedCount(&player);assert(bins[73]==12 && !jkRpg_bRestorePedCount);
    puts("Civilian timer repair, proportional alignment and one-time save repair passed");
}
'''
scratch = Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-morality"
scratch.mkdir(parents=True, exist_ok=True)
cfile, binary = scratch / "check.c", scratch / "check"
try:
    code = harness
    for file, name in [("Cog/sithCogFunction.c", "sithCogFunction_SetTimerEx"),
                       ("Cog/sithCogFunction.c", "sithCogFunction_SetTimer"),
                       ("World/jkPlayer.c", "jkPlayer_CalcAlignment"),
                       ("Main/jkRpg.c", "jkRpg_RepairPedCount")]:
        code += function(file, name) + "\n"
    cfile.write_text(code + checks)
    subprocess.run(["cc", "-std=gnu99", str(cfile), "-lm", "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
finally:
    cfile.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)
