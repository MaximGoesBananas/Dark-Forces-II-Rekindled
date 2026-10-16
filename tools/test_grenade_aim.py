"""Compile thermal aiming, its real launch pipeline and twin-throw routing.

Run in WSL: python3 tools/test_grenade_aim.py ~/src/OpenJKDF2
"""
import os
import tempfile
import re
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1]) / "src"


def function(path, name):
    source = (root / path).read_text()
    match = re.search(r"^(?:static )?[\w* ]+\b" + name + r"\([^;]*?\)\n\{", source, re.M)
    return source[match.start():source.index("\n}", match.end()) + 2] + "\n"


harness = r'''
#include <assert.h>
#include <math.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef double flex_t;
typedef double flex_d_t;
typedef struct { double x,y,z; } rdVector3;
typedef struct { rdVector3 rvec,lvec,uvec,scale; } rdMatrix34;
typedef int sithSound;
typedef struct SithThing {
    int moveType, msecLifeLeft, controlType, actor;
    void *sector, *pPuppetClass;
    double userval;
    rdVector3 position;
    struct { rdVector3 vel, deltaVelocity; int flags; } physicsParams;
    struct { double damage,unk8; int flags; } weaponParams;
} SithThing;
typedef struct {int type; SithThing* pThingCollided;} SithCollision;
typedef struct {int unused;} jkRpgMods;
enum { RPG_THERMAL=4, SITH_MT_PHYSICS=1, SITH_WF_EMITAITARGETEDEVENT=2,
       RAYCAST_2=2, SITHCOLLISION_THING=1, SITH_CT_AI=1, SITHAI_MODE_SLEEPING=1,
       SITHSOUNDFLAG_FOLLOWSTHING=1,SITHSOUNDFLAG_HIGHPRIO=2 };
#define NO_ALIAS
#define RPG_TWIN_SPREAD 3.0
#define SITHLOG_ERROR(...) ((void)0)
#define _memcpy memcpy
static int active=1, weapon=RPG_THERMAL, Main_bMotsCompat, sithNet_isMulti, jkPlayer_setDiff;
static int spawnedCount, sweeps, bounce, rounds=10, prepared;
static SithThing player, grenade[2], other, spawned[4];
static SithThing* sithPlayer_g_pLocalPlayerThing=&player;
static int jkRpg_IsActive(SithThing* p){return active && p==&player;}
static int jkRpg_CurWeapon(SithThing* p){return weapon;}
static SithThing* sithTemplate_GetTemplate(const char* n){
    if(!strcmp(n,"+grenade1"))return &grenade[0];
    if(!strcmp(n,"+grenade2"))return &grenade[1];
    return &other;
}
static double rdVector_Len3(const rdVector3* v){return sqrt(v->x*v->x+v->y*v->y+v->z*v->z);}
static double rdVector_Normalize3Acc(rdVector3* v){double n=rdVector_Len3(v);if(n){v->x/=n;v->y/=n;v->z/=n;}return n;}
static double rdVector_Normalize3(rdVector3* out,const rdVector3* in){*out=*in;return rdVector_Normalize3Acc(out);}
static void rdVector_Scale3(rdVector3* out,const rdVector3* in,double s){*out=(rdVector3){in->x*s,in->y*s,in->z*s};}
static void rdVector_Scale3Acc(rdVector3* v,double s){rdVector_Scale3(v,v,s);}
static void rdVector_Copy3(rdVector3* out,const rdVector3* in){*out=*in;}
static void rdVector_Sub3(rdVector3* out,const rdVector3* a,const rdVector3* b){*out=(rdVector3){a->x-b->x,a->y-b->y,a->z-b->z};}
static int rdVector_IsZero3(const rdVector3* v){return v->x==0 && v->y==0 && v->z==0;}
static void rdVector_Rotate3Acc(rdVector3* v,const rdVector3* pyr){
    assert(pyr->x==0 && pyr->z==0);
    double a=pyr->y*acos(-1)/180, x=v->x,y=v->y;
    v->x=x*cos(a)-y*sin(a);v->y=x*sin(a)+y*cos(a);
}
static void rdMatrix_PreRotate34(rdMatrix34* m,const rdVector3* pyr){rdVector_Rotate3Acc(&m->lvec,pyr);}
static double stdMath_ArcTan1(double y,double z){return atan2(z,y)*180/acos(-1);}
static void rdMatrix_ExtractAngles34(rdMatrix34* m,rdVector3* pyr){*pyr=(rdVector3){asin(m->lvec.z)*180/acos(-1),0,0};}
static SithThing* sithThing_CreateThingAtPos(SithThing* t,const rdVector3* pos,const rdMatrix34* m,void* sector,SithThing* parent){
    assert(spawnedCount<4);
    SithThing* p=&spawned[spawnedCount++];*p=*t;p->position=*pos;
    rdVector3 v=t->physicsParams.vel;
    p->physicsParams.vel=(rdVector3){m->rvec.x*v.x+m->lvec.x*v.y+m->uvec.x*v.z,
        m->rvec.y*v.x+m->lvec.y*v.y+m->uvec.y*v.z,
        m->rvec.z*v.x+m->lvec.z*v.y+m->uvec.z*v.z};
    return p;
}
static void sithCollision_MoveThing(SithThing* p,rdVector3* dir,double distance,int flags){
    sweeps++;assert(distance>0);
    // A wall hit during the body-to-hand sweep may legitimately change velocity.
    if(bounce)p->physicsParams.vel=(rdVector3){-3,2,-1};
}
static void sithPhysics_UpdateThing(SithThing* p,double dt){assert(0);}
static void sithCollision_SearchForCollisions(void*a,SithThing*b,rdVector3*c,rdVector3*d,double e,double f,int g){assert(0);}
static SithCollision* sithCollision_PopStack(void){assert(0);return NULL;}
static void sithCollision_DecreaseStackLevel(void){assert(0);}
static void sithAI_EmitEvent(int actor,int event,long value){assert(0);}
static void sithSoundMixer_PlaySoundThing(sithSound*a,SithThing*b,double c,double d,double e,int f){assert(0);}
static void sithPuppet_PlayMode(SithThing*a,int b,int c){assert(0);}
static void jkRpg_PrepareProjectile(SithThing*p,int w,const jkRpgMods*m){assert(p && w==RPG_THERMAL);prepared++;}
static double sithInventory_GetInventory(SithThing*p,int bin){assert(p==&player && bin==RPG_THERMAL);return rounds;}
static void sithInventory_ChangeInventory(SithThing*p,int bin,double d){rounds+=(int)d;}
static int near(double a,double b){return fabs(a-b)<1e-9;}
static int equal(rdVector3 a,rdVector3 b){return near(a.x,b.x)&&near(a.y,b.y)&&near(a.z,b.z);}
'''

checks = r'''
static SithThing* launch(int mode,rdVector3 dir,double charge){
    rdVector3 hand={.05,0,0};
    return sithWeapon_WeaponFireProjectile(&player,&grenade[mode],&dir,&hand,NULL,-1,charge,1,0,0);
}
int main(void){
    for(int mode=0;mode<2;mode++){
        grenade[mode].moveType=SITH_MT_PHYSICS;
        grenade[mode].physicsParams.vel=(rdVector3){0,2,1.5};
        grenade[mode].msecLifeLeft=mode?3000:10000;
        grenade[mode].weaponParams.flags=mode?0x40309:0x4030d;
        grenade[mode].weaponParams.damage=75;
    }
    SithThing originals[2];memcpy(originals,grenade,sizeof(grenade));
    double charges[]={.25,.7,1,2};
    for(int mode=0;mode<2;mode++)for(int pitch=-89;pitch<=89;pitch++)for(int yaw=0;yaw<360;yaw+=45)
    for(int c=0;c<4;c++){
        double p=pitch*acos(-1)/180,y=yaw*acos(-1)/180;
        rdVector3 dir={-sin(y)*cos(p),cos(y)*cos(p),sin(p)};
        spawnedCount=sweeps=0;SithThing* f=launch(mode,dir,charges[c]);
        rdVector3 expected;rdVector_Scale3(&expected,&dir,2.5*charges[c]);
        assert(equal(f->physicsParams.vel,expected) && sweeps==1);
        assert(f->msecLifeLeft==originals[mode].msecLifeLeft);
        assert(f->weaponParams.flags==originals[mode].weaponParams.flags && f->weaponParams.damage==75);
        assert(!memcmp(originals,grenade,sizeof(grenade)));
    }
    // The helper normalizes imperfect input, but leaves an invalid zero direction unchanged.
    SithThing f=grenade[0];rdVector3 dir={0,3,0},before=f.physicsParams.vel;
    jkRpg_AimThermal(&player,&grenade[0],&f,&dir);assert(equal(f.physicsParams.vel,(rdVector3){0,2.5,0}));
    dir=(rdVector3){0,0,0};f.physicsParams.vel=before;
    jkRpg_AimThermal(&player,&grenade[0],&f,&dir);assert(equal(f.physicsParams.vel,before));
    dir=(rdVector3){0,1,0};
    for(int reason=0;reason<8;reason++){
        f=grenade[0];active=reason!=0;Main_bMotsCompat=reason==1;weapon=reason==2?2:RPG_THERMAL;
        if(reason==3)f.moveType=0;
        jkRpg_AimThermal(reason==4?NULL:reason==5?&other:&player,reason==6?NULL:reason==7?&other:&grenade[0],&f,&dir);
        assert(equal(f.physicsParams.vel,before));
    }
    active=1;Main_bMotsCompat=0;weapon=RPG_THERMAL;
    jkRpg_AimThermal(&player,&grenade[0],NULL,&dir);
    rdVector3 hand={.05,0,0};spawnedCount=0;
    assert(!sithWeapon_WeaponFireProjectile(&player,&grenade[0],NULL,&hand,NULL,-1,1,1,0,0));
    assert(!sithWeapon_WeaponFireProjectile(NULL,&grenade[0],&dir,&hand,NULL,-1,1,1,0,0));
    assert(spawnedCount==0);
    // Correction precedes the real launch function's collision sweep, never overwriting its bounce.
    spawnedCount=sweeps=0;bounce=1;SithThing* hit=launch(0,dir,.7);
    assert(sweeps==1 && equal(hit->physicsParams.vel,(rdVector3){-3,2,-1}));bounce=0;
    // The real twin helper uses the same low-level path for its second grenade.
    for(int mode=0;mode<2;mode++){
        dir=(rdVector3){0,.6,.8};rdVector3 hand={.05,0,0};jkRpgMods mods={0};
        spawnedCount=sweeps=prepared=0;rounds=2;SithThing* first=launch(mode,dir,2);
        jkRpg_TwinThrow(&player,&grenade[mode],first,&dir,&hand,2,1,0,&mods);
        assert(spawnedCount==2 && sweeps==2 && prepared==1 && rounds==1);
        for(int i=0;i<2;i++){
            assert(near(rdVector_Len3(&spawned[i].physicsParams.vel),5));
            assert(near(spawned[i].physicsParams.vel.z,4));
            assert(spawned[i].msecLifeLeft==grenade[mode].msecLifeLeft);
            assert(spawned[i].weaponParams.flags==grenade[mode].weaponParams.flags);
        }
        assert(near(spawned[0].physicsParams.vel.x,-spawned[1].physicsParams.vel.x));
        assert(spawned[0].physicsParams.vel.x!=0);
        spawnedCount=sweeps=0;first=launch(mode,dir,.7);rdVector3 single=first->physicsParams.vel;
        jkRpg_TwinThrow(&player,&grenade[mode],first,&dir,&hand,.7,1,0,&mods);
        assert(spawnedCount==1 && rounds==1 && equal(single,first->physicsParams.vel));
    }
    assert(!memcmp(originals,grenade,sizeof(grenade)));
    puts("Thermal launch: full pitch/yaw sweep, both modes, charge, exclusions, wall bounce and twin throws passed");
}
'''

scratch = Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-grenade-aim"
scratch.mkdir(parents=True, exist_ok=True)
cfile, binary = scratch / "grenade.c", scratch / "grenade"
try:
    cfile.write_text(harness
        + function("Primitives/rdMatrix.c", "rdMatrix_BuildFromLook34")
        + function("Main/jkRpgWeapons.c", "jkRpg_IsTemplate")
        + re.search(r"^static const char\* jkRpg_aShots\[11\]\[3\] = \{.*?^\};\n", (root / "Main/jkRpgWeapons.c").read_text(), re.M | re.S).group(0)
        + function("Main/jkRpgWeapons.c", "jkRpg_IsWeaponShot")
        + function("Main/jkRpgWeapons.c", "jkRpg_AimThermal")
        + function("World/sithWeapon.c", "sithWeapon_WeaponFireProjectile")
        + function("Main/jkRpgWeapons.c", "jkRpg_FireExtra")
        + function("Main/jkRpgWeapons.c", "jkRpg_TwinThrow") + checks)
    subprocess.run(["cc", "-std=c99", "-w", str(cfile), "-lm", "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
finally:
    cfile.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)
