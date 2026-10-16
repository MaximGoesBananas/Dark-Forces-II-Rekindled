"""Compile the actual contact slash: bounded visual only, with safe missing-resource paths."""
import os
import tempfile
from pathlib import Path
import subprocess
import sys

source = (Path(sys.argv[1]) / "src/Gameplay/jkSaber.c").read_text()
start = source.index("static void jkSaber_Slash(")
function = source[start:source.index("\n}\n", start) + 3]
harness = r'''
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
typedef double flex_t;
typedef struct { double x,y,z; } rdVector3;
typedef struct { rdVector3 lvec,scale; } rdMatrix34;
enum { SITH_THING_ACTOR=2,SITH_THING_PLAYER=10,SITH_THING_PARTICLE=8,SITH_MT_NONE=0,
SITH_TF_DEAD=1,SITH_TF_DESTROYED=2,SITHPARTICLE_FLAG_EMIT_LIGHT=16,SITHPARTICLE_FLAG_FADE_OUT_OVER_TIME=8 };
typedef struct { int num_texinfo; } rdMaterial;
typedef struct { int numVertices; double cloudRadius; rdMaterial* material; rdVector3 aVertices[24]; int aVertMatCelNums[24]; } rdParticle;
typedef int SithSector;
typedef struct SithThing { int type,flags,moveType,msecLifeLeft; struct {double health;} actorParams;
struct {int flags,count; double size,range,rate; rdMaterial* material;} particleParams;
struct {rdParticle* particlecloud;} renderData; struct SithThing* pTemplate; } SithThing;
typedef struct {SithThing* actorThing; int bHasLastJointMat; rdMatrix34 lastSaberJointMat;} jkPlayerInfo;
static SithThing player,victim,source,spawned,*sithPlayer_g_pLocalPlayerThing=&player;
static rdMaterial material={8}; static rdParticle cloud; static rdMatrix34 rdroid_identMatrix34;
static int sithNet_isMulti,missing,full,empty,spawns,destroys;
static SithThing* sithTemplate_GetTemplate(const char* name) {assert(!strcmp(name,"+sspks_wall"));return missing?NULL:&source;}
static SithThing* sithThing_CreateThingAtPos(SithThing* t,const rdVector3* p,const rdMatrix34* m,SithSector* s,SithThing* parent) {
    assert(t->moveType==SITH_MT_NONE && t->msecLifeLeft<=150 && t->particleParams.count==24);
    assert(parent==&player);if(full)return NULL;spawns++;spawned=*t;
    cloud.numVertices=t->particleParams.count;cloud.material=t->particleParams.material;
    spawned.renderData.particlecloud=empty?NULL:&cloud;return &spawned;
}
static void sithThing_DestroyThing(SithThing* t){destroys++;}
static void rdVector_ScaleAdd3Acc(rdVector3* a,const rdVector3* b,double s){a->x+=b->x*s;a->y+=b->y*s;a->z+=b->z*s;}
static void rdVector_Sub3(rdVector3* o,const rdVector3* a,const rdVector3* b){*o=(rdVector3){a->x-b->x,a->y-b->y,a->z-b->z};}
static double rdVector_Dot3(const rdVector3* a,const rdVector3* b){return a->x*b->x+a->y*b->y+a->z*b->z;}
static void rdVector_Normalize3Acc(rdVector3* a){double n=sqrt(rdVector_Dot3(a,a));if(n){a->x/=n;a->y/=n;a->z/=n;}}
static void rdVector_Scale3(rdVector3* o,const rdVector3* a,double s){*o=(rdVector3){a->x*s,a->y*s,a->z*s};}
'''
checks = r'''
int main(void){
    jkPlayerInfo info={.actorThing=&player};rdVector3 pos={0,0,0},blade={0,1,0};SithSector sector=1;
    source.type=SITH_THING_PARTICLE;source.particleParams.material=&material;
    victim.type=SITH_THING_ACTOR;victim.actorParams.health=50;
    for(int previous=0;previous<2;previous++) {
        info.bHasLastJointMat=previous;info.lastSaberJointMat.scale=(rdVector3){-.1,0,0};
        jkSaber_Slash(&info,&victim,&pos,&blade,0,&sector);
        assert(spawned.pTemplate==&source && victim.actorParams.health==50);
        for(int i=0;i<24;i++) {
            assert(rdVector_Dot3(&cloud.aVertices[i],&cloud.aVertices[i])<=cloud.cloudRadius*cloud.cloudRadius);
            assert(cloud.aVertMatCelNums[i]>=0 && cloud.aVertMatCelNums[i]<material.num_texinfo);
            if(previous) assert(cloud.aVertices[i].y==0);else assert(cloud.aVertices[i].x==0);
        }
    }
    int before=spawns;
    missing=1;jkSaber_Slash(&info,&victim,&pos,&blade,0,&sector);missing=0;
    full=1;jkSaber_Slash(&info,&victim,&pos,&blade,0,&sector);full=0;
    sithNet_isMulti=1;jkSaber_Slash(&info,&victim,&pos,&blade,0,&sector);sithNet_isMulti=0;
    victim.flags=SITH_TF_DEAD;jkSaber_Slash(&info,&victim,&pos,&blade,0,&sector);victim.flags=0;
    victim.actorParams.health=0;jkSaber_Slash(&info,&victim,&pos,&blade,0,&sector);victim.actorParams.health=50;
    victim.type=99;jkSaber_Slash(&info,&victim,&pos,&blade,0,&sector);victim.type=SITH_THING_ACTOR;
    info.actorThing=&victim;jkSaber_Slash(&info,&victim,&pos,&blade,0,&sector);info.actorThing=&player;
    assert(spawns==before);
    empty=1;jkSaber_Slash(&info,&victim,&pos,&blade,0,&sector);assert(destroys==1);
    puts("Contact slash direction, bounds, no damage, exclusions and allocation failures passed");
}
'''
scratch = Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-saber-hit-check"
scratch.mkdir(parents=True, exist_ok=True)
cfile, exe = scratch / "check.c", scratch / "check"
try:
    cfile.write_text(harness + function + checks)
    subprocess.run(["cc", str(cfile), "-lm", "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
finally:
    cfile.unlink(missing_ok=True)
    exe.unlink(missing_ok=True)
