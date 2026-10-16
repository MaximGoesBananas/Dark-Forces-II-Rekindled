"""Run the real saber contact path: guarded heavy hits, open hits and hit deduplication."""
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

root = Path(sys.argv[1]) / "src"
saber = (root / "Gameplay/jkSaber.c").read_text()
weapons = (root / "Main/jkRpgWeapons.c").read_text()
header = (root / "Main/jkRpg.h").read_text()


def function(source, signature):
    start = source.index(signature)
    return source[start:source.index("\n}", start) + 2]


harness = r'''
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
typedef double flex_t;
typedef struct { double x,y,z; } rdVector3;
typedef struct { rdVector3 lvec; } rdMatrix34;
typedef struct SithSector { int unused; } SithSector;
typedef struct { int unused; } jkPlayerInfo;
typedef struct SithThing {
    int type; struct { int flags; double chance,fov; rdVector3 headPYR; } actorParams;
    rdVector3 position; rdMatrix34 orient; jkPlayerInfo* playerInfo; SithSector* sector;
} SithThing;
typedef struct { struct { SithSector* sector; } *pAdjoin; } SithSurface;
typedef struct { int type; double distance; SithThing* pThingCollided; SithSurface* surface; } SithCollision;
typedef struct { double damage,bladeLength; int numDamagedThings,numDamagedSurfaces;
    SithThing* damagedThings[6]; SithSurface* damagedSurfaces[6]; } jkSaberCollide;
enum { SITH_THING_ACTOR=2,SITH_THING_PLAYER=10,SITH_THING_ITEM=5,SITH_THING_EXPLOSION=6,SITH_THING_PARTICLE=8,
    SITH_AF_DROID=1,SITH_AF_BLEEDS=2,SITH_AF_INVISIBLE=4,SITHCOLLISION_ADJOINCROSS=1,SITHCOLLISION_THING=2,
    SITHCOLLISION_WORLD=4,SPARKTYPE_WALL=0,SPARKTYPE_BLOOD=1,SPARKTYPE_SABER=2,
    SITH_DAMAGE_SABER=16,SITH_SC_DEFLECTED=1,SITH_ANIM_BLOCK2=2,SITH_ANIM_BLOCK=1,SITH_MESSAGE_BLOCKED=1 };
static SithThing player,enemy,other;
static SithSector sector;
static SithCollision contact;
static int active=1,Main_bMotsCompat,popped,hits,blocks,strains,slashes,stackEnds;
static double received,roll;
static int jkRpg_IsActive(SithThing* p) { return active && p==&player; }
static int jkRpg_CanBlock(SithThing* p,int stock) { return stock; }
static double jkRpg_GuardCone(SithThing* p) { return p->actorParams.fov; }
static double _frand(void) { return roll; }
static SithSector* sithCollision_FindSectorInRadius(SithSector* s,rdVector3* p,rdVector3* q,double r) { return s; }
static void sithCollision_SearchForCollisions(SithSector* s,SithThing* t,rdVector3* p,rdVector3* d,double l,double r,int f) {}
static SithCollision* sithCollision_PopStack(void) { return popped++ ? NULL : &contact; }
static void sithCollision_DecreaseStackLevel(void) { stackEnds++; }
static void rdVector_Copy3(rdVector3* a,rdVector3* b) { *a=*b; }
static void rdVector_ScaleAdd3Acc(rdVector3* a,rdVector3* b,double n) { a->x+=b->x*n;a->y+=b->y*n;a->z+=b->z*n; }
static void rdVector_Sub3(rdVector3* a,rdVector3* b,rdVector3* c) { *a=(rdVector3){b->x-c->x,b->y-c->y,b->z-c->z}; }
static double rdVector_Dot3(rdVector3* a,rdVector3* b) { return a->x*b->x+a->y*b->y+a->z*b->z; }
static void rdVector_Normalize3Acc(rdVector3* a) { double n=sqrt(rdVector_Dot3(a,a));if(n){a->x/=n;a->y/=n;a->z/=n;} }
static void rdMatrix_Copy34(rdMatrix34* a,rdMatrix34* b) { *a=*b; }
static void rdMatrix_PreRotate34(rdMatrix34* a,rdVector3* b) { assert(b->x==0 && b->y==0 && b->z==0); }
static void jkSaber_SpawnSparks(jkPlayerInfo* p,rdVector3* v,SithSector* s,int type) {}
static void jkSaber_Slash(jkPlayerInfo* p,SithThing* t,rdVector3* v,rdVector3* d,double n,SithSector* s) { slashes++; }
static void sithThing_DamageThing(SithThing* victim,SithThing* attacker,double damage,int type) { hits++;received=damage;assert(type==SITH_DAMAGE_SABER); }
static void sithSoundClass_PlayModeRandom(SithThing* t,int mode) {}
static void sithPuppet_PlayMode(SithThing* t,int mode,int unused) {}
static void sithCog_ThingSendMessage(SithThing* t,int unused,int message) { blocks++; }
static void jkRpg_OnGuardBlow(SithThing* t,double damage) { strains++; }
static void sithSurface_HandleThingImpact(SithSurface* s,SithThing* t,double damage,int type) { received=damage; }
'''
checks = r'''
static jkSaberCollide info;
static rdVector3 pos={0,1,0},dir={0,-1,0};
static void reset(double damage) {
    player=(SithThing){.type=SITH_THING_PLAYER,.sector=&sector};
    enemy=(SithThing){.type=SITH_THING_ACTOR,.actorParams={.flags=SITH_AF_BLEEDS,.chance=1,.fov=.71},.orient={{0,1,0}}};
    other=player;info=(jkSaberCollide){.damage=damage,.bladeLength=.3};
    contact=(SithCollision){.type=SITHCOLLISION_THING,.pThingCollided=&enemy};
    popped=hits=blocks=strains=slashes=stackEnds=0;received=0;roll=.5;active=1;Main_bMotsCompat=0;
}
static void hit(SithThing* attacker) { popped=0;jkSaber_UpdateCollision2(attacker,&pos,&dir,&info); }
int main(void) {
    reset(100);hit(&player);assert(hits==1 && received==60 && !blocks && !strains && slashes==1 && stackEnds==1);
    assert(info.damage==100 && info.numDamagedThings==1); // never lower later contacts of the swing
    hit(&player);assert(hits==1); // the same enemy cannot take repeated damage from one swing
    contact.pThingCollided=&other;hit(&player);assert(hits==2 && received==100 && info.damage==100);
    reset(100);enemy.actorParams.flags=0;hit(&player);assert(hits==1 && received==100);
    reset(100);enemy.orient.lvec.y=-1;hit(&player);assert(hits==1 && received==100); // rear
    reset(100);enemy.orient.lvec=(rdVector3){1,0,0};hit(&player);assert(hits==1 && received==100); // side
    reset(100);enemy.actorParams.chance=.25;hit(&player);assert(hits==1 && received==100); // failed guard
    reset(100);player.actorParams.flags=SITH_AF_INVISIBLE;hit(&player);assert(hits==1 && received==100);
    for(int damage=40;damage<=60;damage+=10) {
        reset(damage);hit(&player);assert(!hits && blocks==1 && strains==1 && !slashes);
        hit(&player);assert(blocks==1 && strains==1);
        reset(damage);enemy.actorParams.flags=0;hit(&player);assert(hits==1 && received==damage);
    }
    reset(100);active=0;hit(&player);assert(!hits && blocks==1);
    reset(100);Main_bMotsCompat=1;hit(&player);assert(!hits && blocks==1);
    reset(100);hit(&other);assert(!hits && blocks==1); // enemy's own heavy attack unchanged
    reset(100);enemy.type=99;hit(&player);assert(hits==1 && received==100);
    reset(100);enemy.type=SITH_THING_ITEM;hit(&player);assert(!hits && info.numDamagedThings==0);
    reset(100);info.numDamagedThings=6;hit(&player);assert(!hits);
    reset(100);player.sector=NULL;hit(&player);assert(!hits && !stackEnds);
    puts("Guarded heavy 60, open heavy 100, normal blocks, direction, chance, exclusions and repeated contacts passed");
}
'''
scratch = Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-saber-collision"
scratch.mkdir(parents=True, exist_ok=True)
cfile, binary = scratch / "collision.c", scratch / "collision"
try:
    constants = "\n".join(re.findall(r"^#define RPG_SABER_(?:HEAVY|GUARDED)\s+.*$", header, re.M))
    cfile.write_text(harness + constants + "\n" + function(weapons, "int jkRpg_SaberBreaksGuard(")
                     + "\n" + function(saber, "void  jkSaber_UpdateCollision2(") + checks)
    subprocess.run(["cc", "-std=gnu99", str(cfile), "-lm", "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
finally:
    cfile.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)
