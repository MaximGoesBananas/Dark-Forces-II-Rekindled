"""Compile actual heavy-slash setup and timed deflects (returned bolts hit 50% harder once); untimed blocks glance bolts aside and wear the guard."""
import os
import tempfile
from pathlib import Path
import re
import subprocess
import sys

root = Path(sys.argv[1]) / "src"
weapons = (root / "Main/jkRpgWeapons.c").read_text()
saber = (root / "Gameplay/jkSaber.c").read_text()
header = (root / "Main/jkRpg.h").read_text()


def function(source, name):
    start = source.index("void " + name + "(")
    return source[start:source.index("\n}", start) + 2]


harness = r'''
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#define _memset memset
typedef double flex_t;
typedef struct {double x,y,z;} rdVector3;
typedef struct {struct {double damage,bladeLength,stunDelay;int field_1A4,numDamagedThings,numDamagedSurfaces;
void* damagedThings[16];void* damagedSurfaces[16];} saberCollideInfo;int lastSparkSpawnMs;} jkPlayerInfo;
typedef struct SithThing {int type,flags,signature,parentSignature;struct SithThing* pParent;
rdVector3 position;struct {rdVector3 vel;} physicsParams;struct {double damage, rate;} weaponParams;jkPlayerInfo* playerInfo;struct SithThing* pTemplate;} SithThing;
typedef struct {int deflect;} jkRpgMods;
enum {SITH_THING_WEAPON=11,SITH_THING_ACTOR=2,SITH_THING_PLAYER=10,SITHBIN_LIGHTSABER=10,SITH_TF_DEAD=1,SITH_TF_DESTROYED=2};
static SithThing player,enemy,bolt,boltTemplate;
static int active=1,weapon=10,upgrade=0,Main_bMotsCompat,rolls;
static double sithTime_g_secGameTime=20,randomValues[3]={.5,.5,.5};
static int jkRpg_IsActive(SithThing* p){return active && p==&player;}
static int jkRpg_CurWeapon(SithThing* p){return weapon;}
static void jkRpg_GetMods(SithThing* p,int w,jkRpgMods* m){m->deflect=upgrade;}
static double _frand(void){return randomValues[rolls++ % 3];}
static void rdVector_Sub3(rdVector3* o,const rdVector3* a,const rdVector3* b){*o=(rdVector3){a->x-b->x,a->y-b->y,a->z-b->z};}
static double rdVector_Len3(const rdVector3* v){return sqrt(v->x*v->x+v->y*v->y+v->z*v->z);}
static double rdVector_Normalize3Acc(rdVector3* v){double n=rdVector_Len3(v);if(n){v->x/=n;v->y/=n;v->z/=n;}return n;}
static void rdVector_Scale3(rdVector3* o,const rdVector3* a,double s){*o=(rdVector3){a->x*s,a->y*s,a->z*s};}
static rdVector3 lastTurn; static int turns, strains; static double strained;
static void jkRpg_OnGuardBlow(SithThing* p,double damage){assert(p==&player);strains++;strained=damage;}
static void rdVector_Rotate3Acc(rdVector3* v,const rdVector3* pyr){lastTurn=*pyr;turns++;
    double r=pyr->y*M_PI/180,x=v->x*cos(r)-v->y*sin(r),y=v->x*sin(r)+v->y*cos(r);v->x=x;v->y=y;}
'''
checks = r'''
static double angleToShooter(void){
    rdVector3 aim; rdVector_Sub3(&aim,&enemy.position,&bolt.position); rdVector_Normalize3Acc(&aim);
    rdVector3 v=bolt.physicsParams.vel; rdVector_Normalize3Acc(&v);
    return acos(fmin(1,aim.x*v.x+aim.y*v.y+aim.z*v.z))*180/M_PI;
}
static void deflect(double sinceRaised){
    bolt.physicsParams.vel=(rdVector3){0,5,0}; bolt.weaponParams.damage=12; bolt.weaponParams.rate=10; turns=0; rolls=0; strains=0;
    jkRpg_saber.guard=1; jkRpg_saber.raised=sithTime_g_secGameTime-sinceRaised;
    jkRpg_OnDeflect(&bolt,&player);
}
int main(void){
    jkPlayerInfo info={0};player.playerInfo=&info;
    const double normal[]={0,40,50,60};
    for(int i=0;i<4;i++){jkSaber_Enable(&player,normal[i],.25,.7);assert(info.saberCollideInfo.damage==normal[i]);}
    jkSaber_Enable(&player,160,.3,1.2);
    assert(info.saberCollideInfo.damage==RPG_SABER_HEAVY && info.saberCollideInfo.bladeLength==.3 && info.saberCollideInfo.stunDelay==1.2);
    assert(info.saberCollideInfo.field_1A4 && !info.saberCollideInfo.numDamagedThings);
    Main_bMotsCompat=1;jkSaber_Enable(&player,160,.3,1.2);assert(info.saberCollideInfo.damage==160);Main_bMotsCompat=0;
    active=0;jkSaber_Enable(&player,160,.3,1.2);assert(info.saberCollideInfo.damage==160);active=1;
    enemy.playerInfo=&info;jkSaber_Enable(&enemy,160,.3,1.2);assert(info.saberCollideInfo.damage==160);
    jkSaber_Enable(NULL,160,.3,1.2);

    enemy.type=SITH_THING_ACTOR;enemy.signature=42;enemy.position=(rdVector3){3,4,0};
    bolt.pParent=&enemy;bolt.parentSignature=42;bolt.type=SITH_THING_WEAPON;boltTemplate.weaponParams.damage=12;bolt.pTemplate=&boltTemplate;
    // A guard raised just in time returns the bolt exactly to its shooter at the same speed.
    deflect(0.1); assert(angleToShooter()<1e-6 && fabs(rdVector_Len3(&bolt.physicsParams.vel)-5)<1e-9 && !turns && !strains);
    // It hits 50% harder, once: a rally cannot keep raising it, and a bolt without a template keeps its damage.
    assert(bolt.weaponParams.damage==18 && bolt.weaponParams.rate==0); // keeps the bonus for the whole flight back
    // A bolt that already lost damage over distance still returns with its original damage plus the bonus.
    deflect(0.1); bolt.weaponParams.damage=5; jkRpg_saber.raised=sithTime_g_secGameTime-0.1; jkRpg_OnDeflect(&bolt,&player);
    assert(bolt.weaponParams.damage==18);
    jkRpg_saber.raised=sithTime_g_secGameTime-0.1; jkRpg_OnDeflect(&bolt,&player); assert(bolt.weaponParams.damage==18);
    bolt.pTemplate=NULL; deflect(0.1); assert(bolt.weaponParams.damage==12 && angleToShooter()<1e-6); bolt.pTemplate=&boltTemplate;
    // Too late without the upgrade: the bolt glances 20-45 degrees aside instead.
    deflect(RPG_PARRY_WINDOW+0.05); assert(turns==1 && fabs(lastTurn.y)>=RPG_GLANCE_MIN && fabs(lastTurn.y)<=RPG_GLANCE_MAX);
    assert(strains==1 && strained==12 && bolt.weaponParams.damage==12 && bolt.weaponParams.rate==10); // untimed: wears the guard, no bonus
    assert(fabs(lastTurn.x)<=RPG_GLANCE_PITCH && fabs(rdVector_Len3(&bolt.physicsParams.vel)-5)<1e-9);
    // Accurate deflection widens the timing.
    upgrade=1; deflect(RPG_PARRY_WINDOW+0.05); assert(!turns && !strains && angleToShooter()<1e-6 && bolt.weaponParams.damage==18);
    deflect(RPG_PARRY_UPGRADED+0.05); assert(turns==1); upgrade=0;
    // Both glance directions occur; extremes stay within the limits.
    for(int i=0;i<2;i++){randomValues[0]=i?.9:.1;randomValues[1]=i?.999:0;randomValues[2]=i?1:0;
        deflect(5); assert(turns==1 && (i?lastTurn.y>0:lastTurn.y<0));
        assert(fabs(lastTurn.y)>=RPG_GLANCE_MIN-1e-9 && fabs(lastTurn.y)<=RPG_GLANCE_MAX+1e-9);}
    randomValues[0]=randomValues[1]=randomValues[2]=.5;
    // A dead, missing or mismatched shooter cannot be targeted: a timed block glances instead.
    enemy.flags=SITH_TF_DEAD; deflect(0.1); assert(turns==1 && !strains && bolt.weaponParams.damage==12); enemy.flags=0; // timing still spares the guard
    bolt.parentSignature=41; deflect(0.1); assert(turns==1); bolt.parentSignature=42;
    bolt.pParent=NULL; deflect(0.1); assert(turns==1); bolt.pParent=&enemy;
    // Other weapons, other blockers and MotS-less inactive play keep the stock reflection.
    weapon=2; deflect(0.1); assert(!turns && !strains && bolt.physicsParams.vel.y==5 && bolt.weaponParams.damage==12); weapon=10;
    active=0; deflect(0.1); assert(!turns && bolt.physicsParams.vel.y==5); active=1;
    puts("Heavy slash, unchanged primary/reach/timing, timed deflect window and 50% return damage, upgrade, glancing blocks and bolt strain passed");
}
'''
scratch = Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-saber-balance"
scratch.mkdir(parents=True, exist_ok=True)
cfile, binary = scratch / "saber.c", scratch / "saber"
try:
    heavy = re.search(r"^#define RPG_SABER_HEAVY\s+.*$", header, re.M)[0]
    rules = weapons[weapons.index("// ---- Lightsaber controls: pure rules"):weapons.index("// ---- End of lightsaber control rules. ----")]
    state = re.search(r"^static jkRpgSaber jkRpg_saber .*$", weapons, re.M)[0]
    cfile.write_text(harness + heavy + "\n" + rules + state + "\n" + function(saber, "jkSaber_Enable") + "\n"
                     + function(weapons, "jkRpg_OnDeflect") + checks)
    subprocess.run(["cc", "-std=gnu99", "-Wno-unused-function", str(cfile), "-lm", "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
finally:
    cfile.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)
