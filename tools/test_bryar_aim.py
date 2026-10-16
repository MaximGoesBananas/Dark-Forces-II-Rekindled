"""Check actual Bryar convergence at walls/actors, near cover and steep angles.
Run in WSL: python3 tools/test_bryar_aim.py ~/src/OpenJKDF2
"""
import os
import tempfile
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1]) / "src"
source = (root / "Main/jkRpgWeapons.c").read_text()
start = source.index("void jkRpg_AimBryar(")
code = source[start:source.index("\n}", start) + 2]
# The correction must affect every shot, including low-frame-rate catch-up shots.
fire = (root / "World/sithWeapon.c").read_text()
start = fire.index("SithThing* sithWeapon_FireProjectile(")
fire = fire[start:fire.index("\n}", start) + 2]
assert fire.index("jkRpg_AimBryar") < fire.index("sithWeapon_WeaponFireProjectile")

harness = r'''
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stddef.h>
typedef double flex_t;
typedef struct {double x,y,z;} rdVector3;
typedef struct SithThing {int type,signature,parentSignature;struct SithThing* pParent;} SithThing;
typedef struct {struct {rdVector3 lvec;} orient;rdVector3 lookPos;SithThing* pPrimaryFocusThing;void* sector;} SithCamera;
typedef struct {int type;double distance;} SithCollision;
enum {SITHCOLLISION_WORLD=2,SITHCOLLISION_THING=1};
static SithCamera sithCamera_g_aCameras[2],*sithCamera_g_pCurCamera=&sithCamera_g_aCameras[0];
static int active=1,weapon=2,stack,searches,at,numHits;
static SithCollision hits[3];
static SithThing* bryarTemplate;
static SithThing* sithTemplate_GetTemplate(const char* name){return bryarTemplate;}
static int jkRpg_IsActive(SithThing* p){return active;}
static int jkRpg_CurWeapon(SithThing* p){return weapon;}
static double rdVector_Dot3(const rdVector3* a,const rdVector3* b){return a->x*b->x+a->y*b->y+a->z*b->z;}
static double rdVector_Normalize3Acc(rdVector3* v){double n=sqrt(rdVector_Dot3(v,v));if(n){v->x/=n;v->y/=n;v->z/=n;}return n;}
static void rdVector_ScaleAdd3Acc(rdVector3* a,const rdVector3* b,double s){a->x+=b->x*s;a->y+=b->y*s;a->z+=b->z*s;}
static void rdVector_Sub3(rdVector3* a,const rdVector3* b,const rdVector3* c){*a=(rdVector3){b->x-c->x,b->y-c->y,b->z-c->z};}
static void sithCollision_SearchForCollisions(void* sector,SithThing* shooter,rdVector3* start,rdVector3* dir,double dist,int radius,int flags){assert(sector && shooter && shooter->type==2 && shooter->pParent && shooter->parentSignature==42 && dist==100 && radius==0);stack++;searches++;at=0;}
static SithCollision* sithCollision_PopStack(void){return at<numHits?&hits[at++]:NULL;}
static void sithCollision_DecreaseStackLevel(void){stack--;}
'''
checks = r'''
int main(void){
    SithThing player={.type=1,.signature=42},projectile={.type=2};SithCamera* c=sithCamera_g_pCurCamera;
    bryarTemplate=&projectile;
    c->pPrimaryFocusThing=&player;c->sector=&player;c->lookPos=(rdVector3){1,2,3};
    for(int pitch=-89;pitch<=89;pitch+=1)for(int wall=0;wall<2;wall++)for(int range=0;range<3;range++){
        double angle=pitch*3.141592653589793/180;
        c->orient.lvec=(rdVector3){0,cos(angle),sin(angle)};
        double distance=range==0?.25:range==1?3:40;
        hits[0]=(SithCollision){32,.01};hits[1]=(SithCollision){wall?2:1,distance};hits[2]=(SithCollision){2,distance+1};numHits=3;
        rdVector3 muzzle=c->lookPos;rdVector_ScaleAdd3Acc(&muzzle,&c->orient.lvec,.1624);muzzle.x+=.0135;
        rdVector3 original=muzzle,dir={0,1,0};jkRpg_AimBryar(&player,&projectile,&dir,&muzzle);
        assert(muzzle.x==original.x && muzzle.y==original.y && muzzle.z==original.z && stack==0);
        rdVector3 target=c->lookPos;rdVector_ScaleAdd3Acc(&target,&c->orient.lvec,distance);
        rdVector3 gap;rdVector_Sub3(&gap,&target,&muzzle);double flight=sqrt(rdVector_Dot3(&gap,&gap));
        rdVector_ScaleAdd3Acc(&muzzle,&dir,flight);rdVector_Sub3(&gap,&target,&muzzle);assert(rdVector_Dot3(&gap,&gap)<1e-16);
    }
    c->orient.lvec=(rdVector3){0,1,0};numHits=1;hits[0]=(SithCollision){2,.01};
    rdVector3 muzzle={1.0135,2.1624,3},dir={1,0,0};jkRpg_AimBryar(&player,&projectile,&dir,&muzzle);
    assert(muzzle.x==1 && muzzle.y==2 && muzzle.z==3 && dir.y==1 && stack==0);
    numHits=0;muzzle=(rdVector3){1.0135,2.1624,3};jkRpg_AimBryar(&player,&projectile,&dir,&muzzle);assert(dir.y>.999 && dir.x<0);
    int before=searches;
    SithThing forceProjectile={.type=2};jkRpg_AimBryar(&player,&forceProjectile,&dir,&muzzle);
    weapon=3;jkRpg_AimBryar(&player,&projectile,&dir,&muzzle);weapon=2;
    active=0;jkRpg_AimBryar(&player,&projectile,&dir,&muzzle);active=1;
    sithCamera_g_pCurCamera=&sithCamera_g_aCameras[1];jkRpg_AimBryar(&player,&projectile,&dir,&muzzle);
    sithCamera_g_pCurCamera=NULL;jkRpg_AimBryar(&player,&projectile,&dir,&muzzle);
    sithCamera_g_pCurCamera=c;c->sector=NULL;jkRpg_AimBryar(&player,&projectile,&dir,&muzzle);
    assert(searches==before && stack==0);
    puts("Bryar aim: close/distant targets, walls/actors, steep pitch, cover and exclusions passed");
}
'''
scratch = Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-upgrade-preview"
scratch.mkdir(parents=True, exist_ok=True)
cfile, binary = scratch / "aim.c", scratch / "aim"
try:
    cfile.write_text(harness + code + checks)
    subprocess.run(["cc", "-std=c99", str(cfile), "-lm", "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
finally:
    cfile.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)
