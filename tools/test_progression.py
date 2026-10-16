"""Compile and exercise the actual engine XP functions, with inventory/sound stubs.

Run in WSL: python3 tools/test_progression.py ~/src/OpenJKDF2
Only the temporary C harness/binary are written under Helm scratch.
"""
import os
import tempfile
import re
import subprocess
import sys
from pathlib import Path

from campaign_xp import BOSS_XP, placed_enemies, xp_for_level

# Synthetic level data only: inheritance, instance overrides, difficulty and civilians.
level_text = """Section: TEMPLATES
world templates 4
base none type=actor health=40 maxhealth=40 thingflags=0
guard base maxhealth=60
civilian base cog=civilian.cog
end
Section: Things
world things 5
0: guard test 0 0 0 0 0 0 0
1: guard test 0 0 0 0 0 0 0 maxhealth=100
2: guard test 0 0 0 0 0 0 0 thingflags=0x2000
3: guard test 0 0 0 0 0 0 0 thingflags=0x10000
4: civilian test 0 0 0 0 0 0 0
end
"""
assert placed_enemies(level_text, {"cog\\civilian.cog": "ChangeInv(player, 72, 1);"}) == (2, 32)

assert placed_enemies(level_text.replace("guard base maxhealth=60", "guard base maxhealth=60 cog=actor_tk.cog"),
                      {"cog\\civilian.cog": "ChangeInv(player, 72, 1);"}) == (2, 35)

for escape in ("16aescapeship.jkl", "16BESCAPESHIP.JKL"):
    assert placed_enemies(level_text, {"cog\\civilian.cog": "ChangeInv(player, 72, 1);"}, escape) == (2, 0)
for route in ("a", "b"):
    duel = ("17asarris.jkl", "sariss") if route == "a" else ("17bsarris.jkl", "yun2")
    assert (BOSS_XP[duel] - 700) + (BOSS_XP[("20" + route + "boc.jkl", "boc")] - 300) + 306 == 406

source = (Path(sys.argv[1]) / "src/Main/jkRpg.c").read_text()
# Saves from the old level-50 cap keep their levels and points: those bins must not clamp them.
for bin_name in ("LEVEL", "POINTS"):
    limit = re.search(r"RegisterType\(RPG_BIN_" + bin_name + r", NULL, names\[\d\], 0, (\w+),", source).group(1)
    assert int(re.search(r"#define " + limit + r"\s+(\d+)", source).group(1)) >= 50, bin_name
# The balancing tool's curve and mission-16 bosses must match the game's.
same_curve = "".join(f"assert(jkRpg_XpForLevel({level})=={xp_for_level(level)});" for level in range(0, 52))
assert BOSS_XP[("17bsarris.jkl", "yun2")] == BOSS_XP[("17asarris.jkl", "sariss")] == 600


def function(name, source=source):
    match = re.search(r"(?:static )?(?:int|void) " + name + r"\([^;]*?\)\n\{", source)
    end = source.index("\n}", match.end()) + 2
    return source[match.start():end]


cause = "\n".join(re.findall(r"^(?:#define RPG_CAUSE_TAGS .*|static uint32_t jkRpg_aCauseSig\[.*)$", source, re.M)) + "\n" + "".join(
    function(name) + "\n" for name in ("jkRpg_SetOffByPlayer", "jkRpg_CausedByPlayer", "jkRpg_OnThingDamaged", "jkRpg_OnThingCreated"))
defines = "\n".join(re.findall(r"^#define RPG_(?:BIN_\w+|MAX_LEVEL|SAVED_LEVEL_MAX|SCRIPT_ENEMY_XP)\s+\d+.*$|^#define RPG_MISSION6_MAP .*$", source, re.M))
harness = r'''
#include <assert.h>
#include <stdio.h>
#include <stdint.h>
#include <strings.h>
#include <string.h>
#define __strcmpi strcasecmp
typedef struct { const char* aName; } Script;
typedef struct { Script* pScript; } Cog;
typedef Cog sithCog;
typedef struct { int field_18; } Puppet;
typedef struct SithThing { struct { float health, maxHealth; int flags; void* pExplodeTemplate; } actorParams;
    Cog* pCog; Cog* pCaptureCog; int type,flags,position,orient,msecLifeLeft; void* sector; void* pPuppetClass; Puppet* puppet;
    struct { int flags; float buoyancy; } physicsParams;
    struct SithThing* pTemplate; char aName[32]; int idx, guid; uint32_t signature; struct SithThing* pParent;
} SithThing;
#define SITH_THING_WEAPON 11
#define SITH_THING_PLAYER 10
#define SITH_DAMAGE_IMPACT 1
#define SITH_DAMAGE_ENERGY 2
#define SITH_THING_ACTOR 2
#define SITHBIN_PEDS_KILLED 72
typedef double flex_t;
static int bins[200], jkRpg_numUndo;
static SithThing* sithPlayer_g_pLocalPlayerThing;
static int jkRpg_IsActive(SithThing* p) { return p != NULL; }
static SithThing* sithThing_GetThingParent(SithThing* p) { return p; }
static int sithInventory_GetInventory(SithThing* p,int b) { return bins[b]; }
static int jkRpg_Get(SithThing* p, int b) { return bins[b]; }
static void sithInventory_SetInventory(SithThing* p, int b, int n) { bins[b] = n; }
static void sithInventory_ChangeInventory(SithThing* p, int b, int n) { bins[b] += n; }
static void jkRpg_Print(const char* s, ...) {}
static const char* jkRpg_MenuHint(void) { return "PRESS K"; }
#define stdString_snprintf snprintf
#define RPG_SOUND_LEVELUP 0
static void sithConsole_PrintString(const char* s) {}
static int sounds;
static void jkRpg_PlaySound(int sound) { sounds++; }
static struct { void* pCameraFocusThing; char map_jkl_fname[32]; } world, *sithWorld_g_pCurrentWorld=&world;
static int flashes;
static void sithPlayer_AddDynamicTint(float r, float g, float b) { assert(r>0.299 && r<0.301 && g==0.25 && b==0); flashes++; }
'''
death_stubs = r'''
#define SITH_TF_DEAD 1
#define SITH_TF_CAPTURED 2
#define SITH_TF_DESTROYED 4
#define SITH_TF_WATER 8
#define SITH_THING_PLAYER 10
#define SITH_PF_CROUCHING 2
#define SITH_PF_FLY 1
#define SITH_AF_EXPLODE_WHEN_KILLED 1
#define SITH_AF_BREATHEUNDERWATER 2
#define SITH_MESSAGE_KILLED 12
#define Main_bMotsCompat 0
#define sithSoundClass_StopSound(...) ((void)0)
#define sithSoundClass_PlayModeRandom(...) ((void)0)
#define sithActor_SetHeadPYR(...) ((void)0)
#define sithAIAwareness_CreateTransmittingEvent(...) ((void)0)
#define sithPlayer_PlayerKilledAction(...) ((void)0)
#define sithCamera_SetCurrentCamera(...) ((void)0)
#define sithPuppet_ResetTrack(...) ((void)0)
#define sithPuppet_PlayMode(...) 0
#define sithThing_CreateThingAtPos(...) ((void)0)
static void sithThing_DestroyThing(SithThing* p) { p->flags|=SITH_TF_DESTROYED; }
static void sithActor_DestroyActor(SithThing* p) { p->flags|=SITH_TF_DEAD;p->type=5; }
static void sithCog_ThingSendMessage(SithThing* p,SithThing* k,int msg) {
    if (p->pCog && !strcmp(p->pCog->pScript->aName,"civilian.cog")) bins[72]++;
}
static double jkRpg_PedsKilled(void) { return bins[72]; }
'''

checks = r'''
int main(void) {
    assert(RPG_MAX_LEVEL == 40 && RPG_SAVED_LEVEL_MAX == 50);
    SAME_CURVE
    assert(jkRpg_XpForLevel(1) == 0);
    assert(jkRpg_XpForLevel(2) == 100);
    assert(jkRpg_XpForLevel(3) == 300);
    assert(jkRpg_XpForLevel(4) == 505);
    // Added valley guards increase the available XP without changing existing level thresholds.
    assert(jkRpg_XpForLevel(40) == 17117);
    for (int l=2;l<=10;l++) { // Levels 1-10 are unchanged, so saves from missions 1-3 are unaffected.
        int n=l-2; assert(jkRpg_XpForLevel(l)==100+200*n+5*n*(n-1)/2);
    }
    for (int l=12;l<=40;l++) // Each later level costs 12-13 XP more than the one before.
        assert(jkRpg_XpForLevel(l)-2*jkRpg_XpForLevel(l-1)+jkRpg_XpForLevel(l-2) >= 12);
    Script fly={"actor_mailoc.cog"}; Cog flyCog={&fly};
    SithThing flier={.actorParams={40,40},.pCog=&flyCog,.type=SITH_THING_ACTOR};
    assert(jkRpg_KillXp(&flier)==5);
    Script bow={"actor_tk.cog"}, rifle={"actor_tb.cog"}; Cog c={&bow};
    SithThing enemy={.actorParams={50,50},.pCog=&c};
    assert(jkRpg_KillXp(&enemy)==15);
    enemy.actorParams.maxHealth=60; assert(jkRpg_KillXp(&enemy)==15);
    enemy.actorParams.maxHealth=100; assert(jkRpg_KillXp(&enemy)==20);
    c.pScript=&rifle; enemy.actorParams.maxHealth=60; assert(jkRpg_KillXp(&enemy)==12);
    enemy.pCog=NULL; enemy.actorParams.maxHealth=40; assert(jkRpg_KillXp(&enemy)==8);
    enemy.actorParams.maxHealth=1; assert(jkRpg_KillXp(&enemy)==5);
    SithThing p = {{20, 100}};
    sithPlayer_g_pLocalPlayerThing=&p;
    flier.physicsParams.flags=SITH_PF_FLY;flier.flags=SITH_TF_CAPTURED;
    sithActor_KillActor(&flier,&p,0);
    assert(bins[RPG_BIN_XP]==5 && flier.type==5);
    sithActor_KillActor(&flier,&p,0);assert(bins[RPG_BIN_XP]==5); // Corpse cannot pay twice.
    flier.type=SITH_THING_ACTOR;flier.flags=SITH_TF_CAPTURED;
    sithActor_KillActor(&flier,&flier,0);assert(bins[RPG_BIN_XP]==5);
    Script civ={"civilian.cog"};flyCog.pScript=&civ;
    flier.type=SITH_THING_ACTOR;flier.flags=SITH_TF_CAPTURED;
    sithActor_KillActor(&flier,&p,0);assert(bins[RPG_BIN_XP]==5 && bins[72]==1);
    bins[72]=0;bins[RPG_BIN_XP]=0;
    enemy.pCog=&c; c.pScript=&bow;enemy.type=SITH_THING_ACTOR;enemy.actorParams.maxHealth=50;
    jkRpg_OnKill(&enemy,&p,0);assert(bins[RPG_BIN_XP]==15);
    jkRpg_OnKill(&enemy,&enemy,0);assert(bins[RPG_BIN_XP]==15); // Other killers give no XP.
    bins[72]=1;jkRpg_OnKill(&enemy,&p,0);assert(bins[RPG_BIN_XP]==15); // Civilian exclusion stays first.
    // A tank the player sets off credits its blast's kills; untouched blasts and reused slots never do.
    bins[72]=0;
    SithThing tank={{0}}, blast={{0}}, other={{0}}, bolt={{0}};
    tank.idx=5;tank.signature=50;tank.type=6;blast.idx=6;blast.signature=60;blast.type=6;other.idx=7;other.signature=70;other.type=6;
    jkRpg_OnKill(&enemy,&blast,0);assert(bins[RPG_BIN_XP]==15);
    jkRpg_OnThingDamaged(&tank,&enemy,SITH_DAMAGE_ENERGY);jkRpg_OnThingCreated(&blast,&tank);
    jkRpg_OnKill(&enemy,&blast,0);assert(bins[RPG_BIN_XP]==15);          // an enemy's shot sets off nothing
    jkRpg_OnThingDamaged(&tank,&p,SITH_DAMAGE_IMPACT);jkRpg_OnThingCreated(&blast,&tank);
    jkRpg_OnKill(&enemy,&blast,0);assert(bins[RPG_BIN_XP]==15);          // bumping or punching does not
    jkRpg_OnThingDamaged(&tank,&p,SITH_DAMAGE_ENERGY);
    jkRpg_OnThingCreated(&other,&enemy);jkRpg_OnKill(&enemy,&other,0);assert(bins[RPG_BIN_XP]==15);
    jkRpg_OnThingCreated(&blast,&tank);jkRpg_OnKill(&enemy,&blast,0);assert(bins[RPG_BIN_XP]==30);
    jkRpg_OnThingDamaged(&other,&blast,SITH_DAMAGE_ENERGY);assert(jkRpg_CausedByPlayer(&other)); // chain reactions
    blast.signature=61;assert(!jkRpg_CausedByPlayer(&blast));            // a reused slot is not credited
    bolt.idx=8;bolt.signature=80;bolt.type=SITH_THING_WEAPON;bolt.pParent=&enemy;jkRpg_OnThingDamaged(&bolt,&p,SITH_DAMAGE_ENERGY);
    assert(!jkRpg_CausedByPlayer(&bolt));                                 // fired projectiles are never tagged
    SithThing mine={{0}};mine.idx=10;mine.signature=100;mine.type=SITH_THING_WEAPON;
    jkRpg_OnThingDamaged(&mine,&p,SITH_DAMAGE_ENERGY);assert(jkRpg_CausedByPlayer(&mine)); // a placed mine the player sets off
    enemy.idx=9;enemy.signature=90;jkRpg_OnThingDamaged(&enemy,&p,SITH_DAMAGE_ENERGY);
    assert(!jkRpg_CausedByPlayer(&enemy));                               // characters are never tagged
    bins[RPG_BIN_XP]=15;
    bins[72]=0;bins[RPG_BIN_XP]=0;bins[RPG_BIN_MISSIONXP]=0;
    bins[RPG_BIN_LEVEL] = 1;
    flashes=0;
    for (int level = 2; level <= 40; level++) {
        int needed = jkRpg_XpForLevel(level) - bins[RPG_BIN_XP];
        jkRpg_AddXp(&p, needed - 1);
        assert(bins[RPG_BIN_LEVEL] == level - 1 && flashes == level - 2);
        jkRpg_AddXp(&p, 1);
        assert(bins[RPG_BIN_LEVEL] == level && flashes == level - 1);
        assert(bins[RPG_BIN_POINTS] == level - 1);
        assert(p.actorParams.health == 100);
    }
    jkRpg_AddXp(&p, 10000);
    assert(bins[RPG_BIN_LEVEL] == 40 && bins[RPG_BIN_POINTS] == 39 && flashes==39);
    // A save above 40 from the old level-50 cap keeps its level and points and gains no more.
    bins[RPG_BIN_LEVEL] = 47; bins[RPG_BIN_POINTS] = 3;
    jkRpg_AddXp(&p, 10000);
    assert(bins[RPG_BIN_LEVEL] == 47 && bins[RPG_BIN_POINTS] == 3);
    // An older save may have a level ahead of its XP under the new early curve.
    bins[RPG_BIN_LEVEL] = 3; bins[RPG_BIN_XP] = 245; bins[RPG_BIN_POINTS] = 2;
    jkRpg_AddXp(&p, 5);
    assert(bins[RPG_BIN_LEVEL] == 3 && bins[RPG_BIN_POINTS] == 2);
    // A level-20 save from the old curve (4,465 XP) is ahead of the new one: it keeps its level
    // and points and levels again at the new level-21 threshold, without repeating earlier points.
    bins[RPG_BIN_LEVEL] = 20; bins[RPG_BIN_XP] = 4465; bins[RPG_BIN_POINTS] = 4;
    jkRpg_AddXp(&p, jkRpg_XpForLevel(21) - 4465 - 1);
    assert(bins[RPG_BIN_LEVEL] == 20 && bins[RPG_BIN_POINTS] == 4);
    jkRpg_AddXp(&p, 1);
    assert(bins[RPG_BIN_LEVEL] == 21 && bins[RPG_BIN_POINTS] == 5);
    // Later old saves catch up once, without awarding already-earned points again.
    bins[RPG_BIN_LEVEL] = 20; bins[RPG_BIN_XP] = 10000; bins[RPG_BIN_POINTS] = 4;
    jkRpg_AddXp(&p, 5);
    int level = bins[RPG_BIN_LEVEL], points = bins[RPG_BIN_POINTS];
    assert(level > 20 && points == 4 + level - 20);
    jkRpg_AddXp(&p, 0);
    assert(bins[RPG_BIN_LEVEL] == level && bins[RPG_BIN_POINTS] == points);
    // Missions 1 and 2 pay 60% before the minimum of 5; bosses pay fixed amounts in their maps.
    strcpy(world.map_jkl_fname, "01NarShadda.jkl"); enemy.pCog=NULL;
    enemy.actorParams.maxHealth=100; assert(jkRpg_KillXp(&enemy)==12);
    enemy.actorParams.maxHealth=59; assert(jkRpg_KillXp(&enemy)==6); // 11 XP, not 59 * 12%.
    enemy.actorParams.maxHealth=40; assert(jkRpg_KillXp(&enemy)==5);
    strcpy(world.map_jkl_fname, "02narshadda.jkl"); enemy.actorParams.maxHealth=200; assert(jkRpg_KillXp(&enemy)==24);
    strcpy(world.map_jkl_fname, "03katarn.jkl"); assert(jkRpg_KillXp(&enemy)==40);
    SithThing tpl={0}; enemy.pTemplate=&tpl; enemy.actorParams.maxHealth=500;
    const struct { const char* map; const char* boss; int xp; } bosses[] = {
        {"07yun.jkl","yun",200},{"11gorc.jkl","gorc",300},{"11gorc.jkl","pic",200},{"15maw.jkl","maw",400},
        {"17asarris.jkl","sariss",600},{"17bsarris.jkl","yun2",600},
        {"20aboc.jkl","boc",500},{"20bboc.jkl","boc",500}};
    for (int i=0;i<8;i++) {
        strcpy(world.map_jkl_fname, bosses[i].map); strcpy(tpl.aName, bosses[i].boss);
        assert(jkRpg_KillXp(&enemy)==bosses[i].xp);
        strcpy(tpl.aName, "stormtroop"); assert(jkRpg_KillXp(&enemy)==100); // Others in the map are unchanged.
    }
    strcpy(tpl.aName, "yun"); strcpy(world.map_jkl_fname, "17bsarris.jkl"); assert(jkRpg_KillXp(&enemy)==100);
    // 600 XP never grants two levels from any XP position at level 31 or later.
    // Purchased upgrade bins are untouched; this is future reward behavior, not save migration.
    for(int level=31;level<40;level++) for(int xp=jkRpg_XpForLevel(level);xp<jkRpg_XpForLevel(level+1);xp++) {
        bins[RPG_BIN_XP]=xp;bins[RPG_BIN_LEVEL]=level;bins[RPG_BIN_POINTS]=2;bins[140]=3;
        jkRpg_AddXp(&p,600);
        assert(bins[RPG_BIN_LEVEL]<=level+1 && bins[RPG_BIN_POINTS]<=3 && bins[140]==3);
    }
    bins[RPG_BIN_XP]=11238;bins[RPG_BIN_LEVEL]=31;bins[RPG_BIN_POINTS]=0;
    jkRpg_AddXp(&p,600);assert(bins[RPG_BIN_XP]==11838 && bins[RPG_BIN_LEVEL]==32 && bins[RPG_BIN_POINTS]==1);
    const char* lateMaps[]={"18ASCEND.JKL","19a.jkl","19b.jkl","14tower.jkl"};
    const char* troopers[]={"stormtroop","stormtroop2","stormtroop3","STORMTROOP4","icommandorpt","iofficer"};
    enemy.actorParams.maxHealth=70;
    for(int m=0;m<4;m++) for(int t=0;t<6;t++) {
        strcpy(world.map_jkl_fname,lateMaps[m]);strcpy(tpl.aName,troopers[t]);
        assert(jkRpg_KillXp(&enemy)==(m<3 && t<4?16:14));
    }
    // The timed escape pays nothing for any enemy, including old-save actors and indirect kills.
    const char* escapes[]={"16aescapeship.jkl","16BESCAPESHIP.JKL"};
    enemy.type=SITH_THING_ACTOR;bins[72]=0;
    for(int i=0;i<2;i++) {
        strcpy(world.map_jkl_fname,escapes[i]);
        int xp=bins[RPG_BIN_XP],mission=bins[RPG_BIN_MISSIONXP],level=bins[RPG_BIN_LEVEL],points=bins[RPG_BIN_POINTS];
        for(int health=1;health<=2000;health+=199) {
            enemy.actorParams.maxHealth=health;
            assert(jkRpg_KillXp(&enemy)==0);
            jkRpg_OnKill(&enemy,&p,0);
            jkRpg_OnKill(&enemy,&mine,0);
        }
        enemy.pCog=&flyCog;flyCog.pScript=&fly;
        assert(jkRpg_KillXp(&enemy)==0);enemy.pCog=NULL;
        assert(bins[RPG_BIN_XP]==xp && bins[RPG_BIN_MISSIONXP]==mission);
        assert(bins[RPG_BIN_LEVEL]==level && bins[RPG_BIN_POINTS]==points);
    }
    // Jerec's duel ends the game: he gives nothing on either route, and the kill awards no XP.
    enemy.actorParams.maxHealth=2000; enemy.type=SITH_THING_ACTOR; bins[72]=0;
    const char* finals[] = {"21ajerec.jkl","21BJEREC.JKL"};
    for (int i=0;i<2;i++) {
        strcpy(world.map_jkl_fname, finals[i]); strcpy(tpl.aName, "jerec"); assert(jkRpg_KillXp(&enemy)==0);
        int xp=bins[RPG_BIN_XP], mission=bins[RPG_BIN_MISSIONXP];
        jkRpg_OnKill(&enemy,&p,0); assert(bins[RPG_BIN_XP]==xp && bins[RPG_BIN_MISSIONXP]==mission);
        strcpy(tpl.aName, "stormtroop"); assert(jkRpg_KillXp(&enemy)==400); // Only Jerec.
    }
    strcpy(world.map_jkl_fname, "20aboc.jkl"); strcpy(tpl.aName, "jerec"); assert(jkRpg_KillXp(&enemy)==400);
    // Enemies the level's replacement scripts create (no longer endlessly) give normal XP.
    Script replacer={"00_REPLACEENEMY.COG"}; Cog rc={&replacer};
    strcpy(world.map_jkl_fname, "14tower.jkl"); strcpy(tpl.aName, "reeyeesfist"); enemy.actorParams.maxHealth=60;
    enemy.pCaptureCog=&rc; assert(jkRpg_KillXp(&enemy)==12); enemy.pCaptureCog=NULL;
    // Mission 6's three remaining walkers share the five walkers' 400 XP: 133 + 133 + 134.
    strcpy(world.map_jkl_fname, "06bbarons.jkl"); strcpy(tpl.aName, "iatst"); enemy.actorParams.maxHealth=400;
    int walkers=0; const int remaining[3]={91,93,308};
    for (int i=0;i<3;i++) { enemy.guid=remaining[i]; walkers+=jkRpg_KillXp(&enemy); }
    assert(walkers==400 && jkRpg_KillXp(&enemy)==134);
    strcpy(tpl.aName, "stormtroop"); enemy.actorParams.maxHealth=60; assert(jkRpg_KillXp(&enemy)==12);
    strcpy(world.map_jkl_fname, "09fuelstation.jkl"); strcpy(tpl.aName, "iatst"); enemy.actorParams.maxHealth=400;
    assert(jkRpg_KillXp(&enemy)==80); // walkers elsewhere are unchanged
    // Level-ups in boss maps keep the message and point but not the fanfare.
    const char* duels[] = {"07yun.jkl","11gorc.jkl","15maw.jkl","17asarris.jkl","17bsarris.jkl","20aboc.jkl","20bboc.jkl"};
    for (int i=0;i<7;i++) {
        strcpy(world.map_jkl_fname, duels[i]);
        bins[RPG_BIN_LEVEL]=1; bins[RPG_BIN_XP]=0; bins[RPG_BIN_POINTS]=0; sounds=0; flashes=0;
        jkRpg_AddXp(&p, 300); assert(bins[RPG_BIN_LEVEL]==3 && bins[RPG_BIN_POINTS]==2 && sounds==0 && flashes==1);
    }
    strcpy(world.map_jkl_fname, "12escape.jkl");
    bins[RPG_BIN_LEVEL]=1; bins[RPG_BIN_XP]=0; sounds=0;
    jkRpg_AddXp(&p, 300); assert(bins[RPG_BIN_LEVEL]==3 && sounds==2);
    puts("XP thresholds, 39 points, cap 40, Jerec without XP, healing and old-save handling passed");
}
'''
scratch = Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-xp"
scratch.mkdir(parents=True, exist_ok=True)
cfile = scratch / "progression_check.c"
binary = scratch / "progression_check"
try:
    cfile.write_text(defines + harness + function("jkRpg_XpForLevel") + "\n" +
                     function("jkRpg_BossXp") + "\n" + function("jkRpg_AddXp") + "\n" + function("jkRpg_IsScript") + "\n" + function("jkRpg_WalkerXp") + "\n" + function("jkRpg_KillXp") + "\n" + cause + function("jkRpg_OnKill") + death_stubs + function("sithActor_KillActor", (Path(sys.argv[1]) / "src/World/sithActor.c").read_text())
                     + checks.replace("SAME_CURVE", same_curve))
    subprocess.run(["cc", "-std=c99", str(cfile), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
finally:
    cfile.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)
