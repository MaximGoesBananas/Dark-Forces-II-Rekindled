"""Check one-time 20% thinning of compact crowds above ten civilians."""
import subprocess
import sys
import tempfile
from pathlib import Path

source = (Path(sys.argv[1]) / "src/Main/jkRpg.c").read_text()
def function(signature):
    start = source.index(signature)
    return source[start:source.index("\n}\n", start) + 3]

assert '"rpg_crowdfix", 0, 2,' in source
assert "jkRpg_ThinDenseCrowds(p);" in source
assert "jkRpg_crowdTrimStarted = 0;" in function("void jkRpg_OnRestoreStart(")
code = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <strings.h>
#include <math.h>
#define __strcmpi strcasecmp
#define SITHAI_MAX_ACTORS 256
#define SITH_THING_ACTOR 2
#define SITH_TF_DEAD 1
#define SITH_TF_DISABLED 2
#define SITH_TF_DESTROYED 4
#define RPG_BIN_CROWDFIX 182
#define SITHBIN_PEDS_TOTAL 73
#define stdPlatform_Printf(...) ((void)0)
typedef struct { double x,y,z; } rdVector3;
typedef struct { const char* aName; } Script;
typedef struct { Script* pScript; } Cog;
typedef struct { int unused; } SithSector;
typedef struct { int type, flags, idx, guid; Cog* pCog; SithSector* sector;
    rdVector3 position; int health; } SithThing;
typedef struct { const char* map_jkl_fname; int numThings; SithThing aThings[256]; } SithWorld;
static SithWorld world, *sithWorld_g_pCurrentWorld=&world;
static SithSector sector;
static Script script={"actor_mn.cog"}; static Cog cog={&script};
static uint32_t clockMs, jkRpg_crowdTrimStarted;
static int marker,total,removed,walls,killed;
#define sithTime_g_msecGameTime clockMs
static int jkRpg_Get(SithThing* p,int bin) { assert(bin==182); return marker; }
static void sithInventory_SetInventory(SithThing* p,int bin,int n) { assert(bin==182); marker=n; }
static void sithInventory_ChangeInventory(SithThing* p,int bin,int n) { assert(bin==73); total+=n; }
static void sithThing_DestroyThing(SithThing* p) {
    assert(p->guid!=p->idx && !(p->flags&7)); p->flags|=4; removed++;
}
static void rdVector_Sub3(rdVector3* d,const rdVector3* a,const rdVector3* b) {
    d->x=a->x-b->x;d->y=a->y-b->y;d->z=a->z-b->z;
}
static SithSector* jkRpg_CrowdProbe(SithSector* s,const rdVector3* a,const rdVector3* b,int* wall) {
    return walls && a->x*b->x<0 ? NULL : s;
}
''' + function("static int jkRpg_CivilianKind(") + function("static int jkRpg_IsAuthored(") + function("static int jkRpg_IsCrowdMap(") + function("static void jkRpg_ThinDenseCrowds(") + r'''
static void reset(int n,int originals) {
    memset(&world,0,sizeof(world));world.map_jkl_fname="06abarons.jkl";world.numThings=n-1;
    marker=1; total=n+3; killed=3; removed=walls=0;clockMs=100;jkRpg_crowdTrimStarted=0;
    for(int i=0;i<n;i++) world.aThings[i]=(SithThing){.type=2,.idx=i,
        .guid=i<originals?i:65536+i,.pCog=&cog,.sector=&sector,.health=50};
}
static void run(void) {
    SithThing player={0};jkRpg_ThinDenseCrowds(&player);assert(!removed);
    clockMs+=1499;jkRpg_ThinDenseCrowds(&player);assert(!removed);
    clockMs++;jkRpg_ThinDenseCrowds(&player);
}
int main(void) {
    int sizes[]={0,10,11,12,13,15,20,30};
    for(unsigned i=0;i<sizeof(sizes)/sizeof(*sizes);i++) {
        int n=sizes[i], want=n>10?(n+2)/5:0;reset(n,n/3);run();
        assert(removed==want && total==n+3-want && killed==3 && marker==2);
        for(int j=0;j<n;j++) { assert(world.aThings[j].health==50); if(j<n/3) assert(!world.aThings[j].flags); }
        SithThing player={0};jkRpg_crowdTrimStarted=0;clockMs+=5000;
        jkRpg_ThinDenseCrowds(&player);assert(removed==want); // saved marker never repeats
    }
    reset(15,15);run();assert(!removed); // never remove original characters
    reset(15,14);run();assert(removed==1); // only as many added actors as exist
    reset(20,4);for(int i=10;i<20;i++)world.aThings[i].position.x=8;
    run();assert(!removed); // two separate groups of ten
    reset(12,4);walls=1;for(int i=0;i<12;i++)world.aThings[i].position.x=i<6?-.5:.5;
    run();assert(!removed); // six in each room, separated by a wall
    reset(12,4);for(int i=6;i<12;i++)world.aThings[i].position.z=1;
    run();assert(!removed); // floors do not combine
    reset(20,4);for(int i=0;i<20;i++)world.aThings[i].position.x=i;
    run();assert(!removed); // a long sparse street is not a dense area
    reset(12,4);world.aThings[10].flags=1;world.aThings[11].flags=2;
    run();assert(!removed); // ten living, enabled civilians
    reset(12,4);world.aThings[10].type=0;world.aThings[11].pCog=NULL;
    run();assert(!removed);
    reset(20,4);world.map_jkl_fname="custom.jkl";run();assert(!removed && marker==1);
    puts("Dense crowds: >10 only, rounded 20%, separated rooms/floors, originals, morality and saved one-time marker preserved");
}
'''
with tempfile.TemporaryDirectory() as tmp:
    c = Path(tmp) / "density.c"; c.write_text(code)
    exe = Path(tmp) / "density"
    subprocess.run(["cc", "-std=gnu11", "-Wall", "-Werror", str(c), "-lm", "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
