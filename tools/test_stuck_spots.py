"""Check precise campaign removals, including old saves and reused slots.

Run in WSL: python3 tools/test_stuck_spots.py ~/src/OpenJKDF2
The walk-out scenario is documented in DEVELOPING.md.
"""
from pathlib import Path
import subprocess
import sys
import tempfile

source = (Path(sys.argv[1]) / "src/Main/jkRpg.c").read_text()
start = source.index("static void jkRpg_FixBaronsCrate(void)")
function = source[start:source.index("\n}", start) + 2]
assert "    jkRpg_FixBaronsCrate();" in source
start = source.index("static void jkRpg_ThinReservoirEncounter(void)")
encounter = source[start:source.index("\n}", start) + 2]
assert "    jkRpg_ThinReservoirEncounter();" in source
start = source.index("static void jkRpg_RemoveCargoLiftOfficer(void)")
cargo = source[start:source.index("\n}", start) + 2]
assert "    jkRpg_RemoveCargoLiftOfficer();" in source
start = source.index("static void jkRpg_ThinTowerBacta(void)")
bacta = source[start:source.index("\n}", start) + 2]
assert "    jkRpg_ThinTowerBacta();" in source
start = source.index("static void jkRpg_ThinTempleDragons(void)")
dragons = source[start:source.index("\n}", start) + 2]
assert "    jkRpg_ThinTempleDragons();" in source
harness = r'''
#include <assert.h>
#include <math.h>
#include <string.h>
#include <strings.h>
#define __strcmpi strcasecmp
#define SITH_THING_ITEM 5
#define SITH_THING_FREE 0
#define SITH_THING_ACTOR 2
#define SITH_TF_DEAD 1
#define SITH_TF_DESTROYED 2
#define SITHAI_MODE_ACTIVE 4
#define SITHAI_MODE_ATTACKING 8
typedef double flex_t;
typedef struct Thing {
    int type, guid, flags;
    struct { int flags; }* actor;
    struct Thing* pTemplate;
    const char* aName;
    struct { double x,y,z; } position;
    struct { double health; } actorParams;
} SithThing;
typedef struct {
    const char* map_jkl_fname;
    int numThingsLoaded;
    SithThing aThings[316];
} SithWorld;
static SithWorld world, *sithWorld_g_pCurrentWorld = &world;
static SithThing tpl = {.aName="woodcrate3"};
static int removed;
static void sithThing_DestroyThing(SithThing* p) {
    assert(p == &world.aThings[15] || p == &world.aThings[313] || p == &world.aThings[116] || p == &world.aThings[266] || p == &world.aThings[183] || p == &world.aThings[185] || p == &world.aThings[227] || p == &world.aThings[228]);
    p->flags |= SITH_TF_DESTROYED;
    removed++;
}
static void reset(void) {
    memset(&world, 0, sizeof(world));
    sithWorld_g_pCurrentWorld = &world;
    world.map_jkl_fname="06abarons.jkl";
    world.numThingsLoaded=316;
    world.aThings[313]=(SithThing){.type=7,.guid=313,.pTemplate=&tpl,
        .position={2.253900,28.735487,0.165738}};
    removed=0;
}
'''
checks = r'''
static void reservoir(void) {
    reset(); world.map_jkl_fname="04escapehouse.jkl";
    static SithThing gun={.aName="tuskangun"}, melee={.aName="tuskanbh"};
    world.aThings[116]=(SithThing){.type=SITH_THING_ACTOR,.guid=116,.pTemplate=&gun,
        .position={19.448936,1.575512,-4.523130},.actorParams={50}};
    world.aThings[115]=(SithThing){.type=SITH_THING_ACTOR,.guid=115,.pTemplate=&melee,
        .position={20.214664,1.461402,-4.496383},.actorParams={60}};
}
int main(void) {
    static SithThing dragon={.aName="kelldragon"};
    reset(); world.map_jkl_fname="19b.jkl";
    world.aThings[14]=(SithThing){.type=SITH_THING_ACTOR,.guid=14,.pTemplate=&dragon,.actorParams={500}};
    world.aThings[15]=world.aThings[14]; world.aThings[15].guid=15;
    jkRpg_ThinTempleDragons(); assert(removed==1 && !world.aThings[14].flags);
    jkRpg_ThinTempleDragons(); assert(removed==1);
    world.aThings[15].flags=0; world.aThings[15].guid+=65536;
    jkRpg_ThinTempleDragons(); assert(removed==1);
    world.aThings[15].guid=15; world.map_jkl_fname="19a.jkl";
    jkRpg_ThinTempleDragons(); assert(removed==1);
    world.map_jkl_fname="19b.jkl"; world.numThingsLoaded=15;
    jkRpg_ThinTempleDragons(); assert(removed==1);
    world.numThingsLoaded=316; world.aThings[15].pTemplate=&tpl;
    jkRpg_ThinTempleDragons(); assert(removed==1);
    world.aThings[15].pTemplate=0; jkRpg_ThinTempleDragons(); assert(removed==1);
    world.aThings[15].pTemplate=&dragon; world.aThings[15].type=SITH_THING_FREE;
    jkRpg_ThinTempleDragons(); assert(removed==1);
    world.aThings[15].type=SITH_THING_ACTOR; world.aThings[15].actorParams.health=0;
    jkRpg_ThinTempleDragons(); assert(removed==2);
    sithWorld_g_pCurrentWorld=0; jkRpg_ThinTempleDragons(); assert(removed==2);

    static SithThing tank={.aName="bactatank"};
    reset(); world.map_jkl_fname="14tower.jkl";
    for(int i=182;i<=185;i++) world.aThings[i]=(SithThing){.type=SITH_THING_ITEM,.guid=i,.pTemplate=&tank};
    for(int i=227;i<=228;i++) world.aThings[i]=(SithThing){.type=SITH_THING_ITEM,.guid=i,.pTemplate=&tank};
    jkRpg_ThinTowerBacta();assert(removed==4);
    assert(world.aThings[227].flags && world.aThings[228].flags);
    assert(!world.aThings[182].flags && !world.aThings[184].flags);
    jkRpg_ThinTowerBacta();assert(removed==4);
    world.aThings[183].flags=0;world.aThings[183].guid+=65536;
    jkRpg_ThinTowerBacta();assert(removed==4); // reused slot
    world.aThings[183].guid=183;world.aThings[183].pTemplate=&tpl;
    jkRpg_ThinTowerBacta();assert(removed==4);
    world.aThings[183].pTemplate=&tank;world.aThings[183].type=SITH_THING_FREE;
    jkRpg_ThinTowerBacta();assert(removed==4); // already collected
    world.aThings[183].type=SITH_THING_ITEM;world.map_jkl_fname="another.jkl";
    jkRpg_ThinTowerBacta();assert(removed==4);
    world.map_jkl_fname="14tower.jkl";world.numThingsLoaded=183;
    jkRpg_ThinTowerBacta();assert(removed==4);
    world.numThingsLoaded=316;jkRpg_ThinTowerBacta();assert(removed==5); // old save
    sithWorld_g_pCurrentWorld=0;jkRpg_ThinTowerBacta();assert(removed==5);

    static SithThing officer={.aName="iofficer2"};
    for (int health=0; health<=30; health+=30) {
        reset(); world.map_jkl_fname="10cargo.jkl";
        world.aThings[266]=(SithThing){.type=SITH_THING_ACTOR,.guid=266,.pTemplate=&officer,
            .position={1.620309,1.853165,-3.156306},.actorParams={health}};
        world.aThings[263]=world.aThings[266]; world.aThings[263].guid=263;
        jkRpg_RemoveCargoLiftOfficer(); assert(removed==1);
        assert(world.aThings[266].actorParams.health==health && !world.aThings[263].flags);
        jkRpg_RemoveCargoLiftOfficer(); assert(removed==1);
        world.aThings[266].flags=0; world.aThings[266].guid=65802;
        jkRpg_RemoveCargoLiftOfficer(); assert(removed==1);
        world.aThings[266].guid=266; world.map_jkl_fname="09fuelstation.jkl";
        jkRpg_RemoveCargoLiftOfficer(); assert(removed==1);
        world.map_jkl_fname="10cargo.jkl"; world.numThingsLoaded=266;
        jkRpg_RemoveCargoLiftOfficer(); assert(removed==1);
        world.numThingsLoaded=316; world.aThings[266].pTemplate=&tpl;
        jkRpg_RemoveCargoLiftOfficer(); assert(removed==1);
        world.aThings[266].pTemplate=0;
        jkRpg_RemoveCargoLiftOfficer(); assert(removed==1);
        world.aThings[266].pTemplate=&officer; world.aThings[266].type=SITH_THING_FREE;
        jkRpg_RemoveCargoLiftOfficer(); assert(removed==1);
        world.aThings[266].type=5; // an old-save corpse keeps its original identity
        jkRpg_RemoveCargoLiftOfficer(); assert(removed==2);
        sithWorld_g_pCurrentWorld=0; jkRpg_RemoveCargoLiftOfficer(); assert(removed==2);
    }
    reset(); jkRpg_FixBaronsCrate(); assert(removed==1);
    jkRpg_FixBaronsCrate(); assert(removed==1);
    reset(); jkRpg_FixBaronsCrate(); assert(removed==1); // old save or new mission
    reset(); world.map_jkl_fname="another.jkl"; jkRpg_FixBaronsCrate(); assert(!removed);
    reset(); world.numThingsLoaded=313; jkRpg_FixBaronsCrate(); assert(!removed);
    reset(); world.aThings[313].type=0; jkRpg_FixBaronsCrate(); assert(!removed);
    reset(); world.aThings[313].guid=65849; jkRpg_FixBaronsCrate(); assert(!removed);
    reset(); world.aThings[313].pTemplate=0; jkRpg_FixBaronsCrate(); assert(!removed);
    reset(); SithThing other={.aName="woodcrate"}; world.aThings[313].pTemplate=&other;
    jkRpg_FixBaronsCrate(); assert(!removed);
    reset(); world.aThings[313].position.x+=0.1; jkRpg_FixBaronsCrate(); assert(!removed);
    reset(); world.aThings[313].position.y+=0.1; jkRpg_FixBaronsCrate(); assert(!removed);
    reset(); world.aThings[313].position.z+=0.1; jkRpg_FixBaronsCrate(); assert(!removed);
    reset(); sithWorld_g_pCurrentWorld=0; jkRpg_FixBaronsCrate(); assert(!removed);
    reservoir(); jkRpg_ThinReservoirEncounter(); assert(removed==1);
    assert(!world.aThings[115].flags && world.aThings[115].actorParams.health==60);
    assert(world.aThings[116].actorParams.health==50); // removal, not a damaging/killing hit
    jkRpg_ThinReservoirEncounter(); assert(removed==1); // pending destruction is idempotent
    reservoir(); // actual reported old-save position after the gunman moved
    world.aThings[116].position.x=19.565426;
    world.aThings[116].position.y=1.472686;
    world.aThings[116].position.z=-4.523121;
    jkRpg_ThinReservoirEncounter(); assert(removed==1);
    world.aThings[116].type=SITH_THING_FREE; jkRpg_ThinReservoirEncounter(); assert(removed==1);
    reservoir(); world.map_jkl_fname="03katarn.jkl"; jkRpg_ThinReservoirEncounter(); assert(!removed);
    reservoir(); world.numThingsLoaded=116; jkRpg_ThinReservoirEncounter(); assert(!removed);
    reservoir(); world.aThings[116].type=5; jkRpg_ThinReservoirEncounter(); assert(!removed);
    // Never in the middle of a fight, such as an old save where he walked back to his post.
    struct { int flags; } fighting = {SITHAI_MODE_ATTACKING};
    reservoir(); world.aThings[116].actor=(void*)&fighting; jkRpg_ThinReservoirEncounter(); assert(!removed);
    fighting.flags=0; jkRpg_ThinReservoirEncounter(); assert(removed==1); world.aThings[116].actor=0;
    reservoir(); world.aThings[116].guid=65652; jkRpg_ThinReservoirEncounter(); assert(!removed);
    reservoir(); world.aThings[116].flags=SITH_TF_DEAD; jkRpg_ThinReservoirEncounter(); assert(!removed);
    reservoir(); world.aThings[116].actorParams.health=0; jkRpg_ThinReservoirEncounter(); assert(!removed);
    reservoir(); world.aThings[116].pTemplate=0; jkRpg_ThinReservoirEncounter(); assert(!removed);
    reservoir(); world.aThings[116].pTemplate=world.aThings[115].pTemplate; jkRpg_ThinReservoirEncounter(); assert(!removed);
    reservoir(); world.aThings[116].position.x+=1.01; jkRpg_ThinReservoirEncounter(); assert(!removed);
    reservoir(); world.aThings[116].position.y+=1.01; jkRpg_ThinReservoirEncounter(); assert(!removed);
    reservoir(); world.aThings[116].position.z+=0.36; jkRpg_ThinReservoirEncounter(); assert(!removed);
    reservoir(); sithWorld_g_pCurrentWorld=0; jkRpg_ThinReservoirEncounter(); assert(!removed);
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix="jk-stuck-check-") as tmp:
    path = Path(tmp)
    (path / "check.c").write_text(harness + function + encounter + cargo + bacta + dragons + checks)
    subprocess.run(["cc", "-std=c99", "-Wall", "-Werror", str(path / "check.c"),
                    "-o", str(path / "check")], check=True)
    subprocess.run([str(path / "check")], check=True)
print("Crate/encounter removal: fresh placement, old saves, remaining guard, repeat calls and exclusions passed")
