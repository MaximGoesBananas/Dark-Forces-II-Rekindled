"""Compile the actual crowd population code against a small synthetic world.

Run in WSL: python3 tools/test_crowds.py ~/src/OpenJKDF2
Geometry is separately checked in the running campaign; this checks population,
save markers, exclusions, placement failures and object/AI capacity reserves.
"""
import os
import tempfile
import re
import subprocess
import sys
from pathlib import Path

source = (Path(sys.argv[1]) / "src/Main/jkRpg.c").read_text()
ai_source = (Path(sys.argv[1]) / "src/AI/sithAICmd.c").read_text()
flee_start = ai_source.index("int sithAICmd_Flee(")
flee_end = ai_source.index("\n}", flee_start)
assert ai_source.count("jkRpg_CivilianFleeSpeed(") == 1
assert "jkRpg_CivilianFleeSpeed(pLocal->thing, 2.5)" in ai_source[flee_start:flee_end]
assert "    jkRpg_FixBaronsPatron(p);" in source
assert source.index("    jkRpg_ThinDenseCrowds(p);") < source.index("    jkRpg_ClearCrowdObstructions(p);")
assert '"rpg_crowds", 0, 3,' in source


def function(name):
    start = re.search(r"(?:static (?:int|void)|flex_t) " + name + r"\([^;]*?\)\n\{", source)
    end = source.index("\n}", start.end()) + 2
    return source[start.start():end]


harness = r'''
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <strings.h>
#include <stdint.h>
#define SITHAI_MAX_ACTORS 256
#define SITH_THING_ACTOR 2
#define SITH_TF_DEAD 1
#define SITH_TF_DISABLED 2
#define SITH_TF_DESTROYED 4
#define SITHBIN_PEDS_TOTAL 73
#define RPG_BIN_CROWDS 137
#define RPG_BIN_STARTAMMO 139
#define RPG_BIN_CROWDFIX 182
#define __strcmpi strcasecmp
#define stdPlatform_Printf(...) ((void)0)
typedef double flex_t;
typedef struct { double x,y,z; } rdVector3;
typedef struct { int unused; } rdMatrix34;
typedef struct { int id; } SithSector;
typedef struct { const char* aName; } Script;
typedef struct { Script* pScript; } Cog;
typedef Cog sithCog;
typedef struct SithThing {
    int type, flags, idx, guid, supported; Cog* pCog; void* actor; SithSector* sector;
    rdVector3 position; struct { void* model3; void* puppet; } renderData; struct SithThing* pTemplate;
    const char* aName; void* pPuppetClass; void* pSoundClass; void* puppet; double health;
} SithThing;
typedef struct { int numThingsLoaded, numThings; SithThing aThings[512]; const char* map_jkl_fname; } SithWorld;
static SithWorld world, *sithWorld_g_pCurrentWorld = &world;
static SithSector sector;
static Script scripts[] = {{"actor_mn.cog"},{"actor_fn.cog"},{"actor_ug.cog"},{"actor_wg.cog"},{"actor_st.cog"},{"actor_bt.cog"}};
static Cog cogs[] = {{&scripts[0]},{&scripts[1]},{&scripts[2]},{&scripts[3]},{&scripts[4]},{&scripts[5]}};
static SithThing templates[3];
static SithThing enemyTemplate;
static SithThing repeaterTemplate;
static SithThing templeTemplates[4];
static SithThing energyTemplate;
static SithThing womanTemplate;
static int sithNet_isMulti, modelChanges, trackResets;
static void sithPuppet_ResetTrack(SithThing* p) { trackResets++; }
static int sithThing_SetThingModel(SithThing* p, void* model) { p->renderData.model3=model; modelChanges++; return 1; }
static int ammoAdded, missingAmmo, badSector;
static uint32_t clockMs;
static uint32_t stdPlatform_GetTimeMsec(void) { return clockMs += 1000; }
static int marker, spawns, reject, failSpawn, fixed, moved, population, destroyed;
static void sithThing_DestroyThing(SithThing* p) { p->flags |= SITH_TF_DESTROYED; destroyed++; }
static void sithInventory_ChangeInventory(SithThing* p, int bin, int n) { assert(bin==SITHBIN_PEDS_TOTAL); population+=n; }
static uint32_t jkRpg_crowdTrimStarted;
static int jkRpg_StandsSupported(SithThing* p) { return p->supported; }
static void jkRpg_MoveActor(SithThing* p, rdVector3 pos, SithSector* sec) { p->position=pos; p->sector=sec; p->supported=1; moved++; }
static int jkRpg_Get(SithThing* p, int bin) { return bin==RPG_BIN_CROWDFIX ? fixed : bin==RPG_BIN_STARTAMMO ? ammoAdded : marker; }
static void sithInventory_SetInventory(SithThing* p, int bin, int n) { if (bin==RPG_BIN_CROWDFIX) fixed=n; else if (bin==RPG_BIN_STARTAMMO) ammoAdded=n; else marker=n; }
static SithSector* sithSector_FindSectorAtPos(SithWorld* w, rdVector3* p) { return badSector ? NULL : &sector; }
static void rdMatrix_BuildRotate34(rdMatrix34* m, rdVector3* r) {}
static void rdMatrix_Identity34(rdMatrix34* m) {}
static SithThing* sithTemplate_GetTemplate(const char* name) {
    if (!strcmp(name,"woman1")) return &womanTemplate;
    if (!strcmp(name,"stormtroop2")) return &enemyTemplate;
    if (!strcmp(name,"stormtroop3")) return &repeaterTemplate;
    const char* templeNames[]={"stormtroop4","iofficer2","icommandorpt","icommando"};
    for(int i=0;i<4;i++) if(!strcmp(name,templeNames[i])) {
        templeTemplates[i]=(SithThing){.type=SITH_THING_ACTOR,.aName=templeNames[i]};return &templeTemplates[i];
    }
    if (!strcmp(name,"energycell")) return missingAmmo ? NULL : &energyTemplate;
    if (!strcmp(name,"reeyeesbhfist")) return &enemyTemplate;
    if (!strcmp(name,"nman1")) return &templates[0];
    if (!strcmp(name,"nwoman1")) return &templates[1];
    if (!strcmp(name,"ug")) return &templates[2];
    return NULL;
}
static SithSector* jkRpg_CrowdPosition(SithThing* seed, SithThing* tpl, rdVector3* p, flex_t spacingMargin) {
    return reject == 1 || (reject == 2 && seed->idx == 0) ? NULL : &sector;
}
static SithThing* sithThing_CreateThingAtPos(SithThing* tpl, rdVector3* p, rdMatrix34* m, SithSector* sec, void* parent) {
    if (failSpawn==1 || (failSpawn==2 && spawns==2)) return NULL;
    for (int i=0; i<world.numThingsLoaded; i++) if (!world.aThings[i].type) {
        world.aThings[i]=*tpl; world.aThings[i].idx=i; world.aThings[i].position=*p;
        if (i>world.numThings) world.numThings=i;
        spawns++; return &world.aThings[i];
    }
    return NULL;
}
static void reset(int people, int others) {
    memset(&world,0,sizeof(world)); world.numThingsLoaded=512; world.map_jkl_fname="test.jkl";
    marker=spawns=reject=failSpawn=fixed=moved=destroyed=0; population=36;
    ammoAdded=missingAmmo=badSector=0; energyTemplate=(SithThing){.type=5};
    womanTemplate=(SithThing){0};modelChanges=trackResets=sithNet_isMulti=0;
    for (int i=0;i<3;i++) templates[i]=(SithThing){.type=2,.pCog=&cogs[i],.actor=&sector,.sector=&sector,.renderData={&scripts[i]}};
    for (int i=0;i<people+others;i++) {
        world.aThings[i]=templates[0];world.aThings[i].idx=world.aThings[i].guid=i;
        if (i>=people) world.aThings[i].pCog=&cogs[4];
    }
    world.numThings=people+others-1;
}
static int jkRpg_PlaceBarActor(SithThing* thing, rdVector3 pos, flex_t yaw) {
    if (reject) return 0;
    for (int i=0; i<=world.numThings; i++) {
        rdVector3 other=world.aThings[i].position;
        if (other.x==pos.x && other.y==pos.y) return 0;
    }
    thing->position=pos; return 1;
}
'''
checks = r'''
int main(void) {
    SithThing player={0};
    reset(0,0); world.map_jkl_fname="18ascend.jkl";
    enemyTemplate.type=SITH_THING_ACTOR;
    jkRpg_AddValleyTroopers(&player); assert(ammoAdded==10 && spawns==10);
    int first=0,second=0;
    for(int i=0;i<10;i++) {first+=world.aThings[i].position.y<0;second+=world.aThings[i].position.y>0;}
    assert(first==6 && second==4);
    world.aThings[0].type=0; // death/slot reuse and restored marker must not respawn anyone
    jkRpg_AddValleyTroopers(&player);assert(spawns==10);
    reset(0,0);world.map_jkl_fname="18ascend.jkl";failSpawn=2;
    jkRpg_AddValleyTroopers(&player);assert(ammoAdded==2 && spawns==2);
    failSpawn=0;jkRpg_AddValleyTroopers(&player);assert(ammoAdded==10 && spawns==10);
    reset(0,0);world.map_jkl_fname="18ascend.jkl";reject=1;
    jkRpg_AddValleyTroopers(&player);assert(!ammoAdded && !spawns);
    reset(0,0);world.map_jkl_fname="18ascend.jkl";world.numThingsLoaded=32;
    jkRpg_AddValleyTroopers(&player);assert(!spawns);
    reset(0,224);world.map_jkl_fname="18ascend.jkl";
    jkRpg_AddValleyTroopers(&player);assert(!spawns);
    reset(0,0);jkRpg_AddValleyTroopers(&player);assert(!spawns);
    reset(0,0);world.map_jkl_fname="19b.jkl";
    enemyTemplate.aName="stormtroop2";
    repeaterTemplate=(SithThing){.type=SITH_THING_ACTOR,.aName="stormtroop3"};
    jkRpg_AddValleyTroopers(&player);assert(spawns==7 && ammoAdded==7);
    for(int i=0;i<3;i++)assert(!strcmp(world.aThings[i].aName,i==2?"stormtroop3":"stormtroop2"));
    for(int i=3;i<5;i++)assert(world.aThings[i].position.z < -24 && world.aThings[i].position.z > -24.5);
    assert(!strcmp(world.aThings[5].aName,"icommandorpt") && !strcmp(world.aThings[6].aName,"icommandorpt"));
    world.aThings[0].type=0;jkRpg_AddValleyTroopers(&player);assert(spawns==7);
    reset(0,0);world.map_jkl_fname="19b.jkl";failSpawn=2;
    jkRpg_AddValleyTroopers(&player);assert(spawns==2 && ammoAdded==2);
    failSpawn=0;jkRpg_AddValleyTroopers(&player);assert(spawns==7 && ammoAdded==7);
    reset(0,0);world.map_jkl_fname="19b.jkl";reject=1;
    jkRpg_AddValleyTroopers(&player);assert(!spawns && !ammoAdded);
    reset(2,0); marker=1; world.map_jkl_fname="06abarons.jkl";
    SithThing male={.aName="man1"};
    womanTemplate=(SithThing){.aName="woman1",.pCog=&cogs[1],.pPuppetClass=&sector,
        .pSoundClass=&sector,.renderData={&cogs[1]}};
    SithThing* patron=&world.aThings[1];
    patron->guid=65537;patron->position=(rdVector3){6.497,40.2425,0.3787};
    patron->pTemplate=&male;patron->health=23;patron->puppet=patron->renderData.puppet=&sector;
    world.aThings[0]=*patron;world.aThings[0].idx=world.aThings[0].guid=0;
    SithThing original=world.aThings[0];
    jkRpg_FixBaronsPatron(&player);
    assert(marker==2 && modelChanges==1 && trackResets==1 && patron->pTemplate==&womanTemplate);
    assert(patron->guid==65537 && patron->health==23 && patron->position.x==6.497 && !spawns);
    assert(patron->pCog==womanTemplate.pCog && patron->pPuppetClass==womanTemplate.pPuppetClass);
    assert(!memcmp(&original,&world.aThings[0],sizeof(original)));
    jkRpg_FixBaronsPatron(&player);assert(modelChanges==1);
    patron->pTemplate=&male;marker=1;patron->flags=SITH_TF_DEAD;
    jkRpg_FixBaronsPatron(&player);assert(modelChanges==1 && patron->pTemplate==&male);
    marker=1;patron->flags=0;patron->position.z=0.8;
    jkRpg_FixBaronsPatron(&player);assert(modelChanges==1);
    marker=1;patron->position.z=0.3787;world.map_jkl_fname="custom.jkl";
    jkRpg_FixBaronsPatron(&player);assert(marker==1 && modelChanges==1);
    world.map_jkl_fname="06abarons.jkl";womanTemplate.renderData.model3=0;
    jkRpg_FixBaronsPatron(&player);assert(marker==1 && modelChanges==1);
    const char* panicScripts[]={"actor_mn.cog","actor_fn.cog","actor_pm.cog","actor_pf.cog"};
    for(int i=0;i<4;i++) {
        Script panicScript={panicScripts[i]};Cog panicCog={&panicScript};
        SithThing pedestrian={.type=SITH_THING_ACTOR,.pCog=&panicCog};
        assert(jkRpg_CivilianFleeSpeed(&pedestrian,2.5)==1.25);
        assert(jkRpg_CivilianFleeSpeed(&pedestrian,1.25)==0.625);
        sithNet_isMulti=1;assert(jkRpg_CivilianFleeSpeed(&pedestrian,2.5)==2.5);sithNet_isMulti=0;
    }
    for(int i=2;i<6;i++) {
        SithThing other={.type=SITH_THING_ACTOR,.pCog=&cogs[i]};
        assert(jkRpg_CivilianFleeSpeed(&other,2.5)==2.5); // workers, story roles, enemies, bartender
    }
    assert(jkRpg_CivilianFleeSpeed(NULL,2.5)==2.5);
    assert(jkRpg_CivilianFleeSpeed(&player,2.5)==2.5);
    puts("Bar patron appearance preserves identity/counts; ordinary panic speed halved; scripted roles excluded");
    reset(32,0); world.map_jkl_fname="09fuelstation.jkl";
    jkRpg_PopulateCivilians(&player); assert(spawns==32 && marker==2);
    fixed=2; jkRpg_ThinFuelStation(&player); assert(!destroyed);
    jkRpg_PopulateCivilians(&player); assert(spawns==32);
    reset(96,0); marker=1; world.map_jkl_fname="09fuelstation.jkl"; population=96;
    for(int i=32;i<96;i++) world.aThings[i].guid=65536+i;
    jkRpg_ThinFuelStation(&player); assert(!destroyed && marker==1);
    fixed=2; jkRpg_ThinFuelStation(&player);
    assert(destroyed==32 && population==64 && marker==2);
    for(int i=0;i<32;i++) assert(!world.aThings[i].flags);
    jkRpg_ThinFuelStation(&player); assert(destroyed==32 && population==64);
    for(int excluded=0;excluded<5;excluded++) {
        reset(4,0); marker=1; fixed=2; world.map_jkl_fname="09fuelstation.jkl";
        for(int i=0;i<4;i++) world.aThings[i].guid=65536+i;
        if(excluded==0) world.map_jkl_fname="06abarons.jkl";
        for(int i=0;i<4;i++) {
            if(excluded==1)world.aThings[i].flags=SITH_TF_DEAD;
            if(excluded==2)world.aThings[i].flags=SITH_TF_DISABLED;
            if(excluded==3)world.aThings[i].flags=SITH_TF_DESTROYED;
            if(excluded==4)world.aThings[i].pCog=&cogs[4];
        }
        jkRpg_ThinFuelStation(&player);assert(!destroyed);
    }
    puts("Fuel Station targets 2x; older crowds halve only surviving additions once");
    reset(0,4); jkRpg_PopulateCivilians(&player); assert(marker==1 && spawns==0);
    reset(2,0); jkRpg_PopulateCivilians(&player); assert(spawns==4);
    jkRpg_PopulateCivilians(&player); assert(spawns==4); // persisted marker: no duplicates
    reset(2,0); marker=1; jkRpg_PopulateCivilians(&player); assert(spawns==0);
    reset(2,0); reject=2; jkRpg_PopulateCivilians(&player); assert(spawns==4); // use roomier area
    reset(2,0); reject=1; jkRpg_PopulateCivilians(&player); assert(spawns==0 && marker==1);
    reset(2,0); failSpawn=1; jkRpg_PopulateCivilians(&player); assert(spawns==0);
    reset(2,222); jkRpg_PopulateCivilians(&player); assert(spawns==0); // AI reserve
    reset(2,0); world.numThingsLoaded=34; jkRpg_PopulateCivilians(&player); assert(spawns==0); // object reserve
    reset(2,0); world.aThings[0].flags=SITH_TF_DEAD; world.aThings[1].pCog=&cogs[3];
    jkRpg_PopulateCivilians(&player); assert(spawns==0); // dead civilian and story droid
    reset(1,0); world.aThings[0]=templates[2]; jkRpg_PopulateCivilians(&player); assert(spawns==2);
    assert(world.aThings[1].pCog==&cogs[2] && world.aThings[2].pCog==&cogs[2]); // workers stay workers
    reset(7,0); marker=1;
    world.aThings[0].position=(rdVector3){-8.3,-4.97,-1.17};
    world.aThings[1].position=(rdVector3){-8.82,-4.83,-1.17};
    world.aThings[2].position=(rdVector3){-9.0,-5.89,-1.08};
    world.aThings[3].position=(rdVector3){-8.3,-5.86,-1.12};
    world.aThings[4].position=(rdVector3){-10.35,-5.35,-1.12}; // starting booth
    world.aThings[5].position=(rdVector3){-9.18,-4.94,-1.17};
    world.aThings[5].pCog=&cogs[5]; // bartender script kind 3
    world.aThings[6].position=(rdVector3){-9,-5.56,-1.17}; // patron floor
    world.aThings[208]=(SithThing){.type=2,.guid=208,.pTemplate=&enemyTemplate,.position={-8.91,-5.25,-1.17}};
    world.numThings=208;
    jkRpg_FixOpeningBar(&player); assert(marker==1); // another map untouched
    world.map_jkl_fname="01narshadda.jkl";
    reject=1; jkRpg_FixOpeningBar(&player); assert(marker==1 && world.aThings[0].position.x==-8.3);
    reject=0; jkRpg_FixOpeningBar(&player); assert(marker==2 && spawns==0);
    for (int i=0;i<4;i++) {
        rdVector3 pos=world.aThings[i].position;
        assert(pos.x < -10.57 || (pos.x > -10.13 && pos.x < -9.77));
    }
    assert(world.aThings[4].position.x==-10.35 && world.aThings[5].position.x==-9.18);
    assert(world.aThings[6].position.x==-9 && world.aThings[208].position.x==-8);
    world.aThings[0].position=(rdVector3){-8.3,-4.97,-1.17};
    jkRpg_FixOpeningBar(&player); assert(world.aThings[0].position.x==-8.3); // saved correction never repeats
    // Only the original enemy 208 moves: a reused slot with another identity stays.
    marker=1; world.aThings[208].position=(rdVector3){-8.91,-5.25,-1.17}; world.aThings[208].guid=5000;
    jkRpg_FixOpeningBar(&player); assert(marker==2 && world.aThings[208].position.x==-8.91);
    marker=1; world.aThings[208].guid=208;
    world.aThings[208].flags=SITH_TF_DEAD;
    jkRpg_FixOpeningBar(&player); assert(marker==2 && world.aThings[208].position.x==-8.91);
    puts("Opening bar relocation, occupied destinations, save versions and dead enemy preservation passed");
    // The reported man and fresh booth placement are the same narrow correction.
    SithThing boothTemplate={.aName="nman1"};
    const rdVector3 boothPositions[]={{-10.634983,-5.366392,-1.121291},{-10.67,-5.18,-1.10}};
    for (int placement=0;placement<2;placement++) {
        reset(2,0);marker=2;fixed=2;world.map_jkl_fname="01narshadda.jkl";
        SithThing* target=&world.aThings[0];
        target->guid=65548;target->pTemplate=&boothTemplate;target->position=boothPositions[placement];
        world.aThings[1]=*target;world.aThings[1].idx=1;world.aThings[1].guid=65545;
        world.aThings[1].position=(rdVector3){-10.865002,-5.400971,-1.121292};
        world.aThings[2]=(SithThing){.type=5,.idx=2,.guid=2,.position=boothPositions[placement]};
        world.numThings=2;
        SithThing companion=world.aThings[1],shield=world.aThings[2];
        fixed=1;jkRpg_ClearCrowdObstructions(&player);
        assert(marker==2 && !destroyed && population==36); // COG count not ready
        fixed=2;jkRpg_ClearCrowdObstructions(&player);
        assert(marker==3 && destroyed==1 && population==35);
        assert(target->flags&SITH_TF_DESTROYED);
        assert(!memcmp(&companion,&world.aThings[1],sizeof(companion)));
        assert(!memcmp(&shield,&world.aThings[2],sizeof(shield)));
        target->flags=0; // simulate loaded/reused slot: saved marker prevents another removal
        jkRpg_ClearCrowdObstructions(&player);assert(destroyed==1 && population==35);
    }
    for (int excluded=0;excluded<8;excluded++) {
        reset(1,0);marker=2;fixed=2;world.map_jkl_fname="01narshadda.jkl";
        SithThing* target=&world.aThings[0];
        target->guid=65548;target->pTemplate=&boothTemplate;target->position=boothPositions[0];
        if (excluded==0) target->guid=target->idx; // stock authored actor
        if (excluded==1) target->flags=SITH_TF_DEAD;
        if (excluded==2) target->flags=SITH_TF_DISABLED;
        if (excluded==3) target->flags=SITH_TF_DESTROYED;
        if (excluded==4) target->position.x=-10.83; // other man at fresh placement
        if (excluded==5) target->pTemplate=&male; // different template
        if (excluded==6) target->type=5; // pickup even at matching location
        if (excluded==7) target->pTemplate=NULL;
        jkRpg_ClearCrowdObstructions(&player);
        assert(marker==3 && !destroyed && population==36);
    }
    reset(1,0);marker=2;fixed=2;
    world.aThings[0].guid=65548;world.aThings[0].pTemplate=&boothTemplate;
    world.aThings[0].position=boothPositions[0];
    jkRpg_ClearCrowdObstructions(&player);assert(marker==2 && !destroyed); // other map
    world.map_jkl_fname="01narshadda.jkl";marker=1;
    jkRpg_ClearCrowdObstructions(&player);assert(marker==1 && !destroyed); // placement still pending
    puts("Shield booth: fresh/old placement removes exactly one added man; pickup, companion, counts and saves preserved");
    SithThing walkwayTemplate={.aName="nwoman2"};
    const rdVector3 walkwayPositions[]={{0.056840,-0.043673,-4.798007},{-0.088578,-0.129723,-4.797990}};
    for (int placement=0;placement<2;placement++) {
        reset(2,0);marker=1;fixed=2;world.map_jkl_fname="02narshadda.jkl";
        SithThing* target=&world.aThings[0];
        target->guid=65548;target->pTemplate=&walkwayTemplate;target->position=walkwayPositions[placement];
        world.aThings[1]=*target;world.aThings[1].idx=1;world.aThings[1].guid=65549;
        world.aThings[1].position.y=.6;
        SithThing neighbor=world.aThings[1];
        jkRpg_ClearCrowdObstructions(&player);
        assert(marker==3 && destroyed==1 && population==35);
        assert(!memcmp(&neighbor,&world.aThings[1],sizeof(neighbor)));
        target->flags=0;jkRpg_ClearCrowdObstructions(&player);
        assert(destroyed==1 && population==35); // saved removal never repeats
    }
    for (int excluded=0;excluded<5;excluded++) {
        reset(1,0);marker=1;fixed=2;world.map_jkl_fname="02narshadda.jkl";
        SithThing* target=&world.aThings[0];
        target->guid=65548;target->pTemplate=&walkwayTemplate;target->position=walkwayPositions[0];
        if(excluded==0)target->guid=target->idx;
        if(excluded==1)target->flags=SITH_TF_DEAD;
        if(excluded==2)target->pTemplate=&boothTemplate;
        if(excluded==3)target->position.z=-2.27;
        if(excluded==4)fixed=1;
        jkRpg_ClearCrowdObstructions(&player);assert(!destroyed && population==36);
    }
    puts("Cargo walkway: reported woman removed once; nearby people, authored actors and population preserved");
    reset(0,0); jkRpg_AddOpeningAmmo(&player); assert(ammoAdded==0 && spawns==0);
    world.map_jkl_fname="01narshadda.jkl";
    missingAmmo=1; jkRpg_AddOpeningAmmo(&player); assert(ammoAdded==0);
    missingAmmo=0; badSector=1; jkRpg_AddOpeningAmmo(&player); assert(ammoAdded==0);
    badSector=0; failSpawn=2; jkRpg_AddOpeningAmmo(&player); assert(ammoAdded==2 && spawns==2);
    failSpawn=0; jkRpg_AddOpeningAmmo(&player); assert(ammoAdded==4 && spawns==4);
    for(int i=0;i<4;i++) {
        rdVector3 pos=world.aThings[i].position;
        assert(fabs(pos.x-(-8.855+i*.07))<1e-6 && pos.y==-5.96 && pos.z==-1.177565);
        world.aThings[i].type=0; // collected pickups stay gone, including on save/load
    }
    jkRpg_AddOpeningAmmo(&player); assert(ammoAdded==4 && spawns==4);
    reset(0,0); world.map_jkl_fname="01narshadda.jkl";
    jkRpg_AddOpeningAmmo(&player); assert(ammoAdded==4 && spawns==4); // fresh mission or pre-feature save
    puts("Opening ammo: four pickups, partial creation recovery, missing resources and no refill passed");
    reset(8,1); world.map_jkl_fname="02narshadda.jkl";
    // Original, added ordinary, worker, bartender, story actor, dead, supported, disabled, enemy.
    for(int i=1;i<9;i++) world.aThings[i].guid=65536+i;
    world.aThings[2].pCog=&cogs[2]; world.aThings[3].pCog=&cogs[5];
    world.aThings[4].pCog=&cogs[3]; world.aThings[5].flags=SITH_TF_DEAD;
    world.aThings[6].supported=1; world.aThings[7].flags=SITH_TF_DISABLED;
    SithThing snapshot[9]; memcpy(snapshot,world.aThings,sizeof(snapshot));
    jkRpg_FixUnsupportedCivilians(&player);
    assert(fixed==1 && moved==2 && spawns==0);
    for(int i=0;i<9;i++) {
        if(i==1 || i==2) {
            assert(world.aThings[i].guid==snapshot[i].guid && world.aThings[i].pCog==snapshot[i].pCog);
            assert(world.aThings[i].supported && world.aThings[i].position.x==0.3);
        } else assert(!memcmp(&world.aThings[i],&snapshot[i],sizeof(SithThing)));
    }
    jkRpg_FixUnsupportedCivilians(&player); assert(moved==2); // saved repair never repeats
    reset(1,0); world.map_jkl_fname="02narshadda.jkl"; world.aThings[0].guid=65536; reject=1;
    snapshot[0]=world.aThings[0]; jkRpg_FixUnsupportedCivilians(&player);
    assert(fixed==1 && !moved && !memcmp(snapshot,world.aThings,sizeof(SithThing)));
    reset(1,0); world.aThings[0].guid=65536; jkRpg_FixUnsupportedCivilians(&player); assert(!moved);
    puts("Crowd repair preserves originals, story actors, enemies, dead/supported actors and failed placements");
    Script tuskenScript={"actor_tk.cog"}; Cog tuskenCog={&tuskenScript};
    reset(1,0); world.map_jkl_fname="04escapehouse.jkl";
    SithThing* guard=&world.aThings[0];guard->pCog=&tuskenCog;
    guard->position=(rdVector3){1.1,2.4,0.02};guard->guid=4321;
    jkRpg_FixPoolGuards();assert(moved==1 && guard->position.z>0.6 && guard->guid==4321);
    jkRpg_FixPoolGuards();assert(moved==1);
    guard->position=(rdVector3){1.1,2.4,0.02};reject=1;
    jkRpg_FixPoolGuards();assert(moved==1 && guard->position.z==0.02);reject=0;
    guard->flags=SITH_TF_DEAD;jkRpg_FixPoolGuards();assert(moved==1);guard->flags=0;
    world.map_jkl_fname="custom.jkl";jkRpg_FixPoolGuards();assert(moved==1);
    world.map_jkl_fname="04escapehouse.jkl";guard->position.x=10;jkRpg_FixPoolGuards();assert(moved==1);
    guard->position.x=1.1;guard->pCog=&cogs[0];jkRpg_FixPoolGuards();assert(moved==1);
    guard->pCog=&tuskenCog;jkRpg_FixPoolGuards();assert(moved==2);
    puts("Reservoir repair preserves identity, retries blocked banks and excludes other actors/maps/areas");
    puts("Crowd population, save marker, exclusions, failures and capacity reserves passed");
}
'''
scratch = Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-crowds"
scratch.mkdir(parents=True, exist_ok=True)
cfile, binary = scratch / "crowd_check.c", scratch / "crowd_check"
try:
    cfile.write_text(harness + function("jkRpg_CivilianKind") + "\n" +
                     function("jkRpg_PopulateCivilians") + "\n" + function("jkRpg_FixOpeningBar") + "\n" +
                     function("jkRpg_AddValleyTroopers") + function("jkRpg_AddOpeningAmmo") + "\n" + function("jkRpg_IsAuthored") + "\n" +
                     function("jkRpg_ThinFuelStation") + function("jkRpg_ClearCrowdObstructions") + "\n" + function("jkRpg_IsCrowdMap") + function("jkRpg_FixUnsupportedCivilians") + function("jkRpg_IsScript") +
                     function("jkRpg_FixPoolGuards") + function("jkRpg_FixBaronsPatron") +
                     function("jkRpg_CivilianFleeSpeed") + checks)
    subprocess.run(["cc", "-std=gnu99", str(cfile), "-lm", "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
finally:
    cfile.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)

# Exercise the actual floor/ray code against simple geometric scenes, including the
# narrow ledge that the previous centre-only test accepted.
geometry = r'''
#include <assert.h>
#include <math.h>
#include <stddef.h>
#include <stdio.h>
typedef double flex_t;
typedef struct { double x,y,z; } rdVector3;
typedef struct { int flags; } SithSector;
typedef struct { SithSector* sector; } Adjoin;
typedef struct { int flags; Adjoin* pAdjoin; } Surface;
typedef struct { int type; Surface* surface; rdVector3 hitNorm; double distance; } SithCollision;
#define SITH_SECTOR_UNDERWATER 1
#define SITH_SECTOR_USETHRUST 2
#define SITH_SURFACE_COG_LINKED 1
#define SITH_SURFACE_WATER 2
#define SITH_SURFACE_VERYDEEPWATER 4
#define SITHCOLLISION_WORLD 1
#define SITHCOLLISION_ADJOINCROSS 2
#define RAYCAST_1 1
#define RAYCAST_10 16
static SithSector sector, across;
static Adjoin adjoin={&across};
static Surface surface, boundary;
static void* sithWorld_g_pCurrentWorld;
static int scene, pending, stack;
static SithCollision hit;
static SithSector* sithSector_FindSectorAtPos(void* w, const rdVector3* p) { return scene==8 ? NULL : &sector; }
static void rdVector_Sub3(rdVector3* d,const rdVector3* a,const rdVector3* b) { *d=(rdVector3){a->x-b->x,a->y-b->y,a->z-b->z}; }
static void rdVector_Add3Acc(rdVector3* a,const rdVector3* b) { a->x+=b->x; a->y+=b->y; a->z+=b->z; }
static double rdVector_Normalize3Acc(rdVector3* v) {
    double d=sqrt(v->x*v->x+v->y*v->y+v->z*v->z);
    if(d) { v->x/=d; v->y/=d; v->z/=d; } return d;
}
static void sithCollision_SearchForCollisions(SithSector* sec, void* thing,const rdVector3* from,const rdVector3* dir,double depth,double radius,int flags) {
    assert(!thing && !radius && !stack); stack++; pending=0;
    if(flags & RAYCAST_10) {
        double z=scene==2 ? .4*from->x : 0;
        if((scene==1 && fabs(from->x)>.04) || (scene==7 && fabs(from->y)>.04)) z=-1;
        if(scene==3 && from->x>.04) z=-.03; // small step, safe
        if(scene==4 && from->x>.04) z=-.08; // drop, unsafe
        double d=from->z-z;
        if(d>=0 && d<=depth+1e-8) {
            hit=(SithCollision){SITHCOLLISION_WORLD,&surface,scene==2 ? (rdVector3){-.37139,0,.928477} : (rdVector3){0,0,1},d}; pending=1;
        }
    } else if(dir->x>0 && (scene==5 || scene==6 || scene==9)) {
        boundary.pAdjoin=scene==5 ? NULL : &adjoin;
        hit=(SithCollision){scene==9 ? SITHCOLLISION_ADJOINCROSS : SITHCOLLISION_WORLD,&boundary,{0,0,0},depth*.5}; pending=1;
    }
}
static SithCollision* sithCollision_PopStack(void) { if(pending) { pending=0; return &hit; } return NULL; }
static void sithCollision_DecreaseStackLevel(void) { assert(stack==1); stack--; }
'''
geometry_checks = r'''
int main(void) {
    rdVector3 p={0,0,.15}; flex_t floor;
    for(scene=0;scene<10;scene++) {
        int okay=jkRpg_CrowdFloor(&p,.1,&floor)!=NULL;
        int expected=scene==0 || scene==2 || scene==3 || scene==5 || scene==9;
        assert(okay==expected && !stack);
    }
    scene=0;
    for(int flag=1;flag<=4;flag*=2) { surface.flags=flag; assert(!jkRpg_CrowdFloor(&p,.1,&floor)); }
    surface.flags=0; surface.pAdjoin=&adjoin; assert(!jkRpg_CrowdFloor(&p,.1,&floor));
    surface.pAdjoin=NULL;
    sector.flags=SITH_SECTOR_UNDERWATER; assert(!jkRpg_CrowdFloor(&p,.1,&floor));
    sector.flags=SITH_SECTOR_USETHRUST; assert(!jkRpg_CrowdFloor(&p,.1,&floor));
    assert(!stack);
    puts("Crowd floor: broad ground, slopes, steps, walls and open passages pass; thin ledges, drops, closed passages, water and scripted floors fail");
}
'''
a=source.index('static flex_t jkRpg_FloorBelow(')
b=source.index('\nstatic SithSector* jkRpg_CrowdPosition(', a)
geometry_functions=source[a:b]
try:
    cfile.write_text(geometry + geometry_functions + geometry_checks)
    subprocess.run(['cc', '-std=gnu99', str(cfile), '-lm', '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
finally:
    cfile.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)
