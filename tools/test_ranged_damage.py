"""Exercise the real post-shield damage hook; preserve melee, shields and outgoing upgrades."""
import os
import tempfile
from pathlib import Path
import subprocess
import sys

root = Path(sys.argv[1]) / 'src'
source = (root / 'Main/jkRpgWeapons.c').read_text()
start = source.index('flex_t jkRpg_ModifyDamage(')
function = source[start:source.index('\n}', start) + 2]
start = source.index('static int jkRpg_IsTemplate(')
identity = source[start:source.index('\n}', start) + 2]
start = source.index('static int jkRpg_IsCampaignBoss(')
boss_identity = source[start:source.index('\n}', start) + 2]
start = source.index('static flex_t jkRpg_RangedShare(')
phases = source[start:source.index('\n}', start) + 2]
helpers = ''.join(source[source.index(name):source.index('\n}', source.index(name)) + 2] + '\n'
                  for name in ('static int jkRpg_IsSequencerBlast(', 'static int jkRpg_IsForceShot(',
                               '#define RPG_ENEMY_DETONATOR', 'flex_t jkRpg_WeaponProtection('))
actor = (root / 'World/sithActor.c').read_text()
start = actor.index('flex_t sithActor_DamageActor(')
actor = actor[start:actor.index('\n}', start) + 2]
assert actor.index('sithInventory_BroadcastMessage(') < actor.index('jkRpg_ModifyDamage(') < actor.index('health -= damage')
harness = r'''
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <strings.h>
#define __strcmpi strcasecmp
#define __strnicmp strncasecmp
typedef double flex_t;
typedef struct SithThing { int type; struct SithThing* pTemplate; char aName[32]; struct SithThing* pParent; } SithThing;
static struct { char map_jkl_fname[32]; } world,*sithWorld_g_pCurrentWorld=&world;
static int Main_bMotsCompat;
typedef struct { double damage, selfBlast, mineBlast, guard; } jkRpgMods;
enum { SITH_THING_ACTOR=2, SITH_THING_WEAPON=3, SITH_THING_EXPLOSION=6,
SITH_DAMAGE_IMPACT=1, SITH_DAMAGE_ENERGY=2, SITH_DAMAGE_FIRE=4, SITH_DAMAGE_FORCE=8, SITH_DAMAGE_SABER=16,
SITHBIN_LIGHTSABER=10, RPG_THERMAL=4, RPG_SEQUENCER=8, RPG_CONCUSSION=9 };
static SithThing player={10}, enemy={2}, bolt={3}, blast={6}, other={5};
static SithThing* sithPlayer_g_pLocalPlayerThing=&player;
static SithThing enemyThermalTemplate, playerThermalTemplate, mineTemplate, droidTemplate, enemyRailTemplate, enemyRailBlastTemplate;
static SithThing* sithTemplate_GetTemplate(const char* name){
    return !strcmp(name,"+egrenade_exp") ? &enemyThermalTemplate : !strcmp(name,"+esequencer_exp") ? &mineTemplate
        : !strcmp(name,"+eraildet") ? &enemyRailTemplate : !strcmp(name,"+eraildet_exp") ? &enemyRailBlastTemplate : NULL;
}
static int active=1;
static int jkRpg_IsActive(SithThing* p){return active;}
static int tag=3, modsWeapon;
static double damageUpgrade=1.25;
static SithThing heldShotTemplate, destructTemplate;
static int jkRpg_TagOf(SithThing* p){return tag;}
static int held=3;
static int jkRpg_CurWeapon(SithThing* p){return held;}
static SithThing* sithThing_GetThingParent(SithThing* t){return t->pParent?t->pParent:t;}
static int jkRpg_IsWeaponShot(int weapon,SithThing* t){return weapon==3 && t==&heldShotTemplate;}
static SithThing heldBlastTemplate;
static int jkRpg_IsWeaponBlast(int weapon,SithThing* t){return weapon==3 && t==&heldBlastTemplate;}
static void jkRpg_GetMods(SithThing* p,int weapon,jkRpgMods* m){modsWeapon=weapon;m->damage=damageUpgrade;m->selfBlast=m->mineBlast=1;m->guard=weapon==SITHBIN_LIGHTSABER?0.75:1;}
'''
checks = r'''
int main(void){
    for (int kind=0;kind<2;kind++) {
        SithThing* shot=kind?&blast:&bolt;
        for(int type=1;type<=64;type*=2) {
            double expected=(type==2 || type==4)?30:40;
            assert(jkRpg_ModifyDamage(&player,shot,&enemy,40,type)==expected);
        }
        // Only the remainder reaching health is scaled; full shielding stays zero.
        assert(jkRpg_ModifyDamage(&player,shot,&enemy,8,2)==6);
        assert(jkRpg_ModifyDamage(&player,shot,&enemy,0,2)==0);
        assert(jkRpg_ModifyDamage(&player,shot,&player,40,2)==40);
        assert(jkRpg_ModifyDamage(&player,shot,NULL,40,2)==40);
        assert(jkRpg_ModifyDamage(&player,shot,&other,40,2)==40);
        assert(jkRpg_ModifyDamage(&enemy,shot,&enemy,40,2)==40);
        assert(jkRpg_ModifyDamage(&enemy,shot,&player,40,2)==50);
        assert(jkRpg_ModifyDamage(&enemy,shot,&player,40,8)==40);
    }
    // Direct actor contact, environmental sources and mixed melee flags get no discount.
    assert(jkRpg_ModifyDamage(&player,&enemy,&enemy,40,2)==40);
    assert(jkRpg_ModifyDamage(&player,NULL,&enemy,40,2)==40);
    assert(jkRpg_ModifyDamage(&player,&bolt,&enemy,40,18)==40);
    // Both enemy grenade variants share this exact blast template. Template identity
    // survives loading existing projectiles; no newly fired projectile tag is required.
    blast.pTemplate=&enemyThermalTemplate;
    assert(fabs(jkRpg_ModifyDamage(&player,&blast,&enemy,50,4)-24.375)<1e-9);
    assert(fabs(jkRpg_ModifyDamage(&player,&blast,&enemy,8,4)-3.9)<1e-9);
    assert(jkRpg_ModifyDamage(&player,&blast,&enemy,0,4)==0);
    assert(jkRpg_ModifyDamage(&player,&blast,&player,50,4)==50); // self damage
    assert(jkRpg_ModifyDamage(&enemy,&blast,&player,40,4)==50); // outgoing upgrade
    assert(jkRpg_ModifyDamage(&player,&blast,NULL,50,4)==50); // no enemy ownership
    assert(jkRpg_ModifyDamage(&player,&blast,&enemy,50,8)==50); // not Force
    assert(jkRpg_ModifyDamage(&player,&blast,&enemy,50,1)==50); // not melee
    SithThing* unchanged[]={&playerThermalTemplate,&mineTemplate,&droidTemplate,NULL};
    for(int i=0;i<4;i++) {
        blast.pTemplate=unchanged[i];
        assert(jkRpg_ModifyDamage(&player,&blast,&enemy,40,4)==30);
    }
    bolt.pTemplate=&enemyThermalTemplate; // cannot misclassify a direct projectile hit
    assert(jkRpg_ModifyDamage(&player,&bolt,&enemy,40,4)==30);
    active=0;blast.pTemplate=&enemyThermalTemplate;
    assert(jkRpg_ModifyDamage(&player,&blast,&enemy,50,4)==50);
    assert(jkRpg_ModifyDamage(&player,&bolt,&enemy,40,2)==40);
    active=1;
    const char* maps[]={"07yun.jkl","11gorc.jkl","11gorc.jkl","15maw.jkl","17asarris.jkl","17bsarris.jkl","20aboc.jkl","20bboc.jkl","21ajerec.jkl","21bjerec.jkl"};
    const char* names[]={"yun","gorc","pic","maw","sariss","yun2","boc","boc","jerec","jerec"};
    SithThing bossTemplate={0};enemy.pTemplate=&bossTemplate;
    for(int i=0;i<10;i++) {
        strcpy(world.map_jkl_fname,maps[i]);strcpy(bossTemplate.aName,names[i]);
        assert(jkRpg_IsCampaignBoss(&enemy));
        double bonus=i==2?1.5/0.9:i==3?1.25:i==4?2.0:1.5; // Maw +20%, Sariss -25% effective health.
        damageUpgrade=1;
        assert(jkRpg_ModifyDamage(&enemy,&player,&player,60,16)==60*bonus); // guarded heavy keeps the boss bonus
        assert(jkRpg_ModifyDamage(&enemy,&player,&player,100,16)==100*bonus); // unguarded heavy
        damageUpgrade=1.25;
        assert(jkRpg_ModifyDamage(&enemy,&player,&player,50,16)==50*bonus*1.25); // boss and weapon upgrade
        assert(jkRpg_ModifyDamage(&enemy,&player,&player,40,8)==40*bonus); // Force also uses the boss balance
        assert(jkRpg_ModifyDamage(&player,&enemy,&enemy,40,16)==(i==4?62.5:50));
        assert(jkRpg_ModifyDamage(&player,&enemy,&enemy,40,1)==(i==4?62.5:50));
        assert(jkRpg_ModifyDamage(&player,&enemy,&enemy,8,16)==(i==4?12.5:10)); // only remainder after shields
        assert(jkRpg_ModifyDamage(&player,&enemy,&enemy,120,8)==120); // Force remains original
        assert(jkRpg_ModifyDamage(&enemy,&enemy,&enemy,40,16)==40); // no extra AI damage to each other
        Main_bMotsCompat=1;assert(!jkRpg_IsCampaignBoss(&enemy));Main_bMotsCompat=0;
        active=0;assert(jkRpg_ModifyDamage(&enemy,&player,&player,50,16)==50);active=1;
    }
    strcpy(world.map_jkl_fname,"17asarris.jkl");strcpy(bossTemplate.aName,"sariss");
    assert(jkRpg_ModifyDamage(&player,&enemy,&enemy,0,16)==0);
    active=0;assert(jkRpg_ModifyDamage(&player,&enemy,&enemy,40,16)==40);active=1;
    Main_bMotsCompat=1;assert(jkRpg_ModifyDamage(&player,&enemy,&enemy,40,16)==40);Main_bMotsCompat=0;
    strcpy(bossTemplate.aName,"SARISS");assert(jkRpg_ModifyDamage(&player,&enemy,&enemy,40,16)==62.5);
    damageUpgrade=1;
    assert(fabs((1900/jkRpg_ModifyDamage(&enemy,&player,&player,40,16))/(1900/60.0)-0.75)<1e-9);
    // Each original Maw stage takes exactly 20% more player damage, including Force.
    strcpy(world.map_jkl_fname,"15MAW.JKL");strcpy(bossTemplate.aName,"MAW");
    damageUpgrade=1;
    const double stages[]={900,630,360,0};
    for(int type=1;type<=16;type*=2) {
        double hit=jkRpg_ModifyDamage(&enemy,&player,&player,40,type);
        for(int stage=0;stage<3;stage++)
            assert(fabs((stages[stage]-stages[stage+1])/hit /
                        ((stages[stage]-stages[stage+1])/60)-1.2)<1e-9);
    }
    damageUpgrade=1.25;
    strcpy(world.map_jkl_fname,"01narshadda.jkl");assert(!jkRpg_IsCampaignBoss(&enemy));
    strcpy(world.map_jkl_fname,"21ajerec.jkl");strcpy(bossTemplate.aName,"stormtrooper");assert(!jkRpg_IsCampaignBoss(&enemy));
    assert(!jkRpg_IsCampaignBoss(NULL));enemy.pTemplate=NULL;assert(!jkRpg_IsCampaignBoss(&enemy));
    // Untagged damage: a Force projectile (Destruction's impact) never takes the held weapon's
    // rules, while the held weapon's own untagged shot, sabers and blasts keep theirs.
    tag=0;SithThing destruct={3,&destructTemplate};
    modsWeapon=-1;assert(jkRpg_ModifyDamage(&enemy,&destruct,&player,20,2)==20 && modsWeapon==-1);
    destruct.pTemplate=NULL;assert(jkRpg_ModifyDamage(&enemy,&destruct,&player,20,2)==20 && modsWeapon==-1);
    destruct.pTemplate=&heldShotTemplate;assert(jkRpg_ModifyDamage(&enemy,&destruct,&player,20,2)==25 && modsWeapon==3);
    assert(jkRpg_ModifyDamage(&enemy,&player,&player,40,16)==50 && modsWeapon==SITHBIN_LIGHTSABER);
    blast.pTemplate=&heldBlastTemplate;assert(jkRpg_ModifyDamage(&enemy,&blast,&player,40,4)==50 && modsWeapon==3);
    // A blast that lost its tag to a reload (an old mine) does not take the held weapon's rules.
    modsWeapon=-1;blast.pTemplate=NULL;assert(jkRpg_ModifyDamage(&enemy,&blast,&player,40,4)==40 && modsWeapon==-1);
    tag=3;
    // A boss's Destruction projectile is Force, not blaster fire: no ranged share on the player.
    SithThing forceTemplate={0,NULL,"+force_dest_p1"}, forceShot={3,&forceTemplate};
    assert(jkRpg_ModifyDamage(&player,&forceShot,&enemy,40,2)==40);
    // A placed enemy mine has no owner; its blast still counts as an enemy blast.
    SithThing mineBlast={6,&mineTemplate};
    assert(jkRpg_ModifyDamage(&player,&mineBlast,&mineBlast,40,4)==30 && jkRpg_ModifyDamage(&player,&mineBlast,NULL,40,4)==30);
    assert(jkRpg_ModifyDamage(&player,&mineBlast,&player,40,4)==40); // the player's own mine stays full
    // Campaign phases: very little, little, a bit, some. Boss duels and other maps keep 0.75,
    // enemy grenades keep their extra 0.65 in every phase and melee stays full everywhere.
    const char* phaseMaps[]={"01narshadda.jkl","04ESCAPEHOUSE.JKL","06abarons.jkl","06bbarons.jkl","10cargo.jkl",
        "12escape.jkl","14tower.jkl","16aescapeship.jkl","16bescapeship.jkl","19b.jkl",
        "07yun.jkl","11gorc.jkl","15maw.jkl","17bsarris.jkl","20aboc.jkl","21bjerec.jkl","test.jkl"};
    const double shares[]={0.5,0.5,0.6,0.6,0.6,0.7,0.7,0.8,0.8,0.8,0.75,0.75,0.75,0.75,0.75,0.75,0.75};
    SithThing grunt={2};
    for(int i=0;i<17;i++) {
        strcpy(world.map_jkl_fname,phaseMaps[i]);
        assert(fabs(jkRpg_ModifyDamage(&player,&bolt,&grunt,40,2)-40*shares[i])<1e-9);
        blast.pTemplate=&enemyThermalTemplate;
        assert(fabs(jkRpg_ModifyDamage(&player,&blast,&grunt,40,4)-40*shares[i]*0.65)<1e-9);
        assert(jkRpg_ModifyDamage(&player,&grunt,&grunt,40,1)==40);
        assert(jkRpg_ModifyDamage(&player,&bolt,&grunt,40,16)==40);
    }
    sithWorld_g_pCurrentWorld=NULL;
    assert(jkRpg_ModifyDamage(&player,&bolt,&grunt,40,2)==30);
    sithWorld_g_pCurrentWorld=&world;
    // Before shields: enemy detonators (the rail detonator's direct hit and both enemy blasts) lose a
    // quarter, shields and health alike; one the player sent back is the player's own.
    SithThing railShot={3,&enemyRailTemplate,"",&enemy}, railBlast={6,&enemyRailBlastTemplate,"",&enemy}, grenade={6,&enemyThermalTemplate,"",&enemy};
    assert(jkRpg_WeaponProtection(&player,&railShot,20,2)==15 && jkRpg_WeaponProtection(&player,&railBlast,40,4)==30);
    assert(jkRpg_WeaponProtection(&player,&grenade,40,4)==30);
    railShot.pParent=&player; assert(jkRpg_WeaponProtection(&player,&railShot,20,2)==20); railShot.pParent=&enemy;
    SithThing trooperBolt={3,&droidTemplate,"",&enemy};
    assert(jkRpg_WeaponProtection(&player,&trooperBolt,12,2)==12);
    // Blaster protection (the drawn saber) cuts blaster bolts by a quarter, never a Force projectile.
    held=SITHBIN_LIGHTSABER; assert(jkRpg_WeaponProtection(&player,&trooperBolt,12,2)==9);
    SithThing bossForce={3,&forceTemplate,"",&enemy}; assert(jkRpg_WeaponProtection(&player,&bossForce,20,2)==20);
    assert(jkRpg_WeaponProtection(&player,&railShot,20,2)==11.25); held=3;
    puts("Enemy detonators and Blaster protection before shields, campaign phases, enemy ranged health damage, weapon-independent Force projectiles, all ten campaign boss variants, preserved Force attacks and outgoing upgrades passed");
}
'''
scratch = Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-ranged-check"
scratch.mkdir(parents=True, exist_ok=True)
c, exe = scratch/'check.c', scratch/'check'
try:
    c.write_text(harness+identity+'\n'+helpers+boss_identity+'\n'+phases+'\n'+function+checks)
    subprocess.run(['cc',str(c),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
finally:
    c.unlink(missing_ok=True)
    exe.unlink(missing_ok=True)
