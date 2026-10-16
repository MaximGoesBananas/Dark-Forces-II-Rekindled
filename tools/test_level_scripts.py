"""Compile the real level rules: no endless replacements, mission 1's explosive crate and gentle opening Rodian."""
import os
import tempfile
from pathlib import Path
import subprocess
import sys

src = Path(sys.argv[1]) / "src"
source = (src / "Main/jkRpg.c").read_text()
create = (src / "Cog/sithCogFunctionThing.c").read_text()


def function(name):
    start = source.index(name)
    return source[start:source.index("\n}\n", start) + 3]


start = create.index("void sithCogFunctionThing_CreateThing(sithCog *pCog)")
assert "jkRpg_ScriptCreate(pCog, sithCogExec_PopTemplate(pCog), v1)" in create[start:create.index("\n}\n", start)]

code = r'''
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <strings.h>
#define __strcmpi strcasecmp
enum { SITH_MT_PATH=2, SITH_MESSAGE_STARTUP = 3, SITH_MESSAGE_KILLED = 6, SITH_THING_ACTOR = 2, SITH_TF_DEAD = 0x200, SITH_TF_DESTROYED = 0x80000000u };
typedef struct { char aName[32]; } sithCogScript;
typedef struct { sithCogScript* pScript; unsigned trigId; } sithCog;
typedef struct { double x, y, z; } rdVector3;
#include <stdint.h>
typedef double flex_t;
typedef struct { int flags; } SithAIControlBlock;
typedef struct SithThing { int guid; struct SithThing* pTemplate; char aName[32]; rdVector3 position;
    int type; unsigned flags; struct { double health, maxHealth; } actorParams;
    int idx, moveType, curframe, goalframe; struct {int loadedFrames,flags;} trackParams; unsigned signature; SithAIControlBlock* actor; sithCog* pCaptureCog; } SithThing;
typedef struct { char map_jkl_fname[32]; int numThingsLoaded, numThings; SithThing aThings[512]; } SithWorld;
enum { SITHAI_MODE_SEARCHING = 0x4, SITHAI_MODE_ACTIVE = 0x200, SITHAI_MODE_UNK100 = 0x100 };
static double sithTime_g_secGameTime; static int events;
static void sithAI_EmitEvent(SithAIControlBlock* a, int event, int old) { assert(event == SITHAI_MODE_UNK100); events++; }
static SithWorld world = {"01narshadda.jkl", 210, 209};
static SithWorld* sithWorld_g_pCurrentWorld = &world;
static int Main_bMotsCompat, sithNet_isMulti;
static SithThing crate62 = {.aName = "crate6_2"}, crateExp = {.aName = "+crate_exp"}, tankExp = {.aName = "+xtank1_exp"},
    rodian = {.aName = "reeyeesfist"}, opener = {.aName = "reeyeesbhgun"}, item = {.aName = "+DBattery"};
static int haveTank = 1;
static SithThing* sithTemplate_GetTemplate(const char* name) { return haveTank && !strcmp(name, "+xtank1_exp") ? &tankExp : NULL; }
'''
static_stub="""
static int doorMoves;
static void sithTrackThing_MoveToFrame(SithThing* t,int frame,double speed){doorMoves++;t->goalframe=frame;t->trackParams.flags=4;}
"""
code += static_stub
for name in ("int jkRpg_PathFrame(", "static void jkRpg_CloseValleyTunnel(", "static int jkRpg_IsScript(", "static int jkRpg_IsExplosiveCrate(", "static void jkRpg_WeakenOpeningRodian(", "#define RPG_REMOTE_PATIENCE", "SithThing* jkRpg_ScriptCreate("):
    code += function(name)
code += r'''
int main(void) {
    sithCogScript replace = {"00_REPLACEENEMY.COG"}, oops = {"14_oopstroop.cog"}, crate = {"actor_cr.cog"}, other = {"00_door.cog"};
    sithCog c = {&replace, SITH_MESSAGE_STARTUP};
    SithThing doorTemplate={.aName="4x4door"};
    SithThing* door=&world.aThings[297];
    *door=(SithThing){.guid=297,.idx=297,.moveType=SITH_MT_PATH,.pTemplate=&doorTemplate,.trackParams={2,0}};
    strcpy(world.map_jkl_fname,"18ascend.jkl");world.numThingsLoaded=512;
    assert(jkRpg_PathFrame(door,0)==1 && jkRpg_PathFrame(door,1)==1);
    jkRpg_CloseValleyTunnel();jkRpg_CloseValleyTunnel();assert(doorMoves==1 && door->goalframe==1);
    door->curframe=1;door->trackParams.flags=0;jkRpg_CloseValleyTunnel();assert(doorMoves==1);
    door->guid=65537;assert(jkRpg_PathFrame(door,0)==0);door->guid=297;
    Main_bMotsCompat=1;assert(jkRpg_PathFrame(door,0)==0);Main_bMotsCompat=0;
    sithNet_isMulti=1;assert(jkRpg_PathFrame(door,0)==0);sithNet_isMulti=0;
    strcpy(world.map_jkl_fname,"01narshadda.jkl");assert(jkRpg_PathFrame(door,0)==0);
    SithThing* at = &world.aThings[13];
    *at = (SithThing){13, &crate62, "", {3.901013, -3.481718, 0.341718}};
    // The replacer keeps its startup enemy and never brings it back; the guard replacer creates nothing.
    assert(jkRpg_ScriptCreate(&c, &rodian, at) == &rodian);
    c.trigId = SITH_MESSAGE_KILLED; assert(!jkRpg_ScriptCreate(&c, &rodian, at));
    c.pScript = &oops; c.trigId = SITH_MESSAGE_STARTUP; assert(!jkRpg_ScriptCreate(&c, &rodian, at));
    // Other scripts, multiplayer and MotS are untouched.
    c.pScript = &other; assert(jkRpg_ScriptCreate(&c, &rodian, at) == &rodian);
    c.pScript = &replace; c.trigId = SITH_MESSAGE_KILLED;
    sithNet_isMulti = 1; assert(jkRpg_ScriptCreate(&c, &rodian, at) == &rodian); sithNet_isMulti = 0;
    Main_bMotsCompat = 1; assert(jkRpg_ScriptCreate(&c, &rodian, at) == &rodian); Main_bMotsCompat = 0;
    // Only that crate's blast becomes the fuel tank's; its item drops and every other crate stay.
    c.pScript = &crate;
    assert(jkRpg_ScriptCreate(&c, &crateExp, at) == &tankExp);
    assert(jkRpg_ScriptCreate(&c, &item, at) == &item);
    world.aThings[12] = *at; world.aThings[12].guid = 12; assert(jkRpg_ScriptCreate(&c, &crateExp, &world.aThings[12]) == &crateExp);
    at->guid = 14; assert(jkRpg_ScriptCreate(&c, &crateExp, at) == &crateExp); at->guid = 13;
    at->position.x += 0.01; assert(jkRpg_ScriptCreate(&c, &crateExp, at) == &crateExp); at->position.x -= 0.01;
    at->pTemplate = &rodian; assert(jkRpg_ScriptCreate(&c, &crateExp, at) == &crateExp); at->pTemplate = &crate62;
    strcpy(world.map_jkl_fname, "02narshadda.jkl"); assert(jkRpg_ScriptCreate(&c, &crateExp, at) == &crateExp);
    strcpy(world.map_jkl_fname, "01NarShadda.jkl"); assert(jkRpg_ScriptCreate(&c, &crateExp, at) == &tankExp);
    world.numThingsLoaded = 13; assert(jkRpg_ScriptCreate(&c, &crateExp, at) == &crateExp); world.numThingsLoaded = 210;
    assert(jkRpg_ScriptCreate(&c, &crateExp, NULL) == &crateExp);
    haveTank = 0; assert(jkRpg_ScriptCreate(&c, &crateExp, at) == &crateExp); haveTank = 1;
    // The opening Rodian starts at half health once; maximum health (his XP) stays, and a hurt,
    // dead or different actor, another map or an already-halved Rodian is left alone.
    SithThing* r = &world.aThings[207];
    *r = (SithThing){207, &opener, "", {0}, SITH_THING_ACTOR, 0, {60, 60}};
    jkRpg_WeakenOpeningRodian(); assert(r->actorParams.health == 30 && r->actorParams.maxHealth == 60);
    jkRpg_WeakenOpeningRodian(); assert(r->actorParams.health == 30);
    r->actorParams.health = 50; jkRpg_WeakenOpeningRodian(); assert(r->actorParams.health == 50);
    r->actorParams.health = 60; r->flags = SITH_TF_DEAD; jkRpg_WeakenOpeningRodian(); assert(r->actorParams.health == 60); r->flags = 0;
    r->guid = 208; jkRpg_WeakenOpeningRodian(); assert(r->actorParams.health == 60); r->guid = 207;
    r->pTemplate = &rodian; jkRpg_WeakenOpeningRodian(); assert(r->actorParams.health == 60); r->pTemplate = &opener;
    strcpy(world.map_jkl_fname, "02narshadda.jkl"); jkRpg_WeakenOpeningRodian(); assert(r->actorParams.health == 60);
    strcpy(world.map_jkl_fname, "01narshadda.jkl"); sithNet_isMulti = 1; jkRpg_WeakenOpeningRodian(); assert(r->actorParams.health == 60);
    sithNet_isMulti = 0; jkRpg_WeakenOpeningRodian(); assert(r->actorParams.health == 30);
    // Mission 4: a training remote still not hunting 8 seconds after it appears is set hunting,
    // once; one already hunting, another script's actor or another map is left alone.
    sithCogScript r1 = {"04_remotes1.cog"}, r3 = {"04_REMOTES3.COG"}; sithCog c1 = {&r1}, c3 = {&r3}, cx = {&other};
    memset(world.aThings, 0, sizeof(world.aThings)); strcpy(world.map_jkl_fname, "04escapehouse.jkl");
    SithAIControlBlock ai[3] = {{0}, {SITHAI_MODE_SEARCHING}, {0}};
    world.aThings[50] = (SithThing){.type = SITH_THING_ACTOR, .idx = 50, .signature = 500, .actor = &ai[0], .pCaptureCog = &c1};
    world.aThings[51] = (SithThing){.type = SITH_THING_ACTOR, .idx = 51, .signature = 510, .actor = &ai[1], .pCaptureCog = &c3};
    world.aThings[52] = (SithThing){.type = SITH_THING_ACTOR, .idx = 52, .signature = 520, .actor = &ai[2], .pCaptureCog = &cx};
    sithTime_g_secGameTime = 100; jkRpg_FreeStuckRemotes();
    sithTime_g_secGameTime = 107.9; jkRpg_FreeStuckRemotes(); assert(ai[0].flags == 0 && !events);   // still flying to its spot
    sithTime_g_secGameTime = 108.1; jkRpg_FreeStuckRemotes(); assert(ai[0].flags == SITHAI_MODE_SEARCHING && events == 1);
    jkRpg_FreeStuckRemotes(); assert(events == 1 && ai[1].flags == SITHAI_MODE_SEARCHING && ai[2].flags == 0);
    ai[0].flags = 0; world.aThings[50].signature = 501; sithTime_g_secGameTime = 120; jkRpg_FreeStuckRemotes();
    sithTime_g_secGameTime = 125; jkRpg_FreeStuckRemotes(); assert(ai[0].flags == 0);          // a new remote waits its own 8 s
    sithTime_g_secGameTime = 50; jkRpg_FreeStuckRemotes(); sithTime_g_secGameTime = 55; jkRpg_FreeStuckRemotes();
    assert(ai[0].flags == 0);                                                                    // a loaded earlier time restarts
    strcpy(world.map_jkl_fname, "03katarn.jkl"); sithTime_g_secGameTime = 200; jkRpg_FreeStuckRemotes(); assert(ai[0].flags == 0);
    strcpy(world.map_jkl_fname, "01narshadda.jkl");
    sithWorld_g_pCurrentWorld = NULL; jkRpg_WeakenOpeningRodian(); assert(jkRpg_ScriptCreate(&c, &crateExp, at) == &crateExp);
    assert(!jkRpg_ScriptCreate(&c, NULL, at));
    puts("Level scripts: no endless replacements, startup enemies kept, mission 1's one explosive crate and half-health opening Rodian and freed stuck training remotes passed");
}
'''
scratch = Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-level-scripts"
scratch.mkdir(parents=True, exist_ok=True)
cfile, binary = scratch / "check.c", scratch / "check"
try:
    cfile.write_text(code)
    subprocess.run(["cc", "-std=gnu99", "-Wall", "-Wno-unused-function", str(cfile), "-lm", "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
finally:
    cfile.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)
