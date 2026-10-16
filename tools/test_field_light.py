"""Compile field-light range ownership, camera registration and real model light math."""
import os
import tempfile
import re
import subprocess
import sys
from pathlib import Path
src = Path(sys.argv[1]) / "src"

def function(file, signature):
    source = (src / file).read_text()
    start = source.index(signature)
    return source[start:source.index("\n}\n", start) + 3]

code = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
typedef double flex_t;
typedef double flex_d_t;
typedef struct {double x,y,z;} rdVector3;
typedef struct {int* vertexPosIdx;} rdFace;
typedef struct {int id,type,bEnabled;rdVector3 direction;double intensity;unsigned color;
 double angleX,cosAngleX,angleY,cosAngleY,lux;unsigned dword20,dword24;
 double minRadius,maxRadius,attenuationScale;} rdLight;
#define RDCAMERA_MAX_LIGHTS 64
typedef struct {int numLights;rdLight* aLights[64];rdVector3 aLightPositions[64];double attenuationMin,attenuationMax;} rdCamera;
typedef struct {struct {int flags;} actorParams;} SithThing;
enum {SITH_AF_HEADLIGHT=4,UP_LIGHT=7};
static int Main_bMotsCompat,multi,owned;
static SithThing player,other;
static int jkRpg_IsActive(SithThing* p) {return p==&player&&!multi;}
static int jkRpg_OwnsTier(SithThing* p,int up,int tier) {assert(p==&player&&up==UP_LIGHT&&tier==2);return owned;}
static void rdVector_Copy3(rdVector3* out,const rdVector3* in) {*out=*in;}
static void rdVector_Sub3(rdVector3* out,const rdVector3* a,const rdVector3* b) {*out=(rdVector3){a->x-b->x,a->y-b->y,a->z-b->z};}
static double rdVector_Dot3(const rdVector3* a,const rdVector3* b) {return a->x*b->x+a->y*b->y+a->z*b->z;}
static double rdVector_Len3(const rdVector3* v) {return sqrt(rdVector_Dot3(v,v));}
static double rdVector_Normalize3Acc(rdVector3* v) {double d=rdVector_Len3(v);if(d){v->x/=d;v->y/=d;v->z/=d;}return d;}
static double rdMath_DistancePointToPlane(const rdVector3* a,const rdVector3* n,const rdVector3* p) {rdVector3 d;rdVector_Sub3(&d,a,p);return rdVector_Dot3(&d,n);}
'''
for file, signature in [
    ("Main/jkRpg.c", "flex_t jkRpg_FieldLightRange("),
    ("Engine/rdLight.c", "int rdLight_NewEntry("),
    ("Engine/rdCamera.c", "void rdCamera_SetAttenuation("),
    ("Engine/rdCamera.c", "int rdCamera_AddLight("),
    ("Engine/rdCamera.c", "int rdCamera_AddLightRange("),
    ("Engine/rdCamera.c", "int rdCamera_ClearLights("),
    ("Engine/rdLight.c", "flex_t rdLight_CalcVertexIntensities("),
    ("Engine/rdLight.c", "flex_t rdLight_CalcFaceIntensity("),
]:
    code += function(file, signature)
code += r'''
static double vertex(rdLight* light,double distance) {
 rdLight* lights[]={light};rdVector3 origin={0,0,0},point={distance,0,0},normal={-1,0,0};
 double base=0,out=0;
 rdLight_CalcVertexIntensities(lights,&origin,
#ifdef JKM_LIGHTING
 NULL,
#endif
 1,&normal,&point,&base,&out,1,.5);
 int index=0;rdFace face={&index};
 assert(fabs(out-rdLight_CalcFaceIntensity(lights,&origin,1,&face,&normal,&point,.5))<1e-9);
 return out;
}
int main(void) {
 rdLight light;memset(&light,0xff,sizeof(light));rdLight_NewEntry(&light);assert(light.attenuationScale==1);
 rdCamera camera={.attenuationMin=.5,.attenuationMax=.25};rdVector3 origin={0};
 assert(jkRpg_FieldLightRange(&player)==1);owned=1;assert(jkRpg_FieldLightRange(&player)==1); // off
 player.actorParams.flags=SITH_AF_HEADLIGHT;assert(jkRpg_FieldLightRange(&player)==1.5);
 owned=0;assert(jkRpg_FieldLightRange(&player)==1); // base or refunded tier2 gap
 owned=1;other.actorParams.flags=SITH_AF_HEADLIGHT;assert(jkRpg_FieldLightRange(&other)==1);
 multi=1;assert(jkRpg_FieldLightRange(&player)==1);multi=0;
 Main_bMotsCompat=1;assert(jkRpg_FieldLightRange(&player)==1);Main_bMotsCompat=0;
 rdCamera_AddLight(&camera,&light,&origin);assert(light.minRadius==2&&light.maxRadius==4&&light.intensity==1);
 for(int i=1;i<20;i++)assert(fabs(vertex(&light,i*.1)-(1-i*.05))<1e-9);
 assert(vertex(&light,2.5)==0);
 for(int frame=0;frame<100;frame++) {
  rdCamera_ClearLights(&camera);rdCamera_AddLightRange(&camera,&light,&origin,jkRpg_FieldLightRange(&player));
  assert(light.minRadius==3&&light.maxRadius==6&&light.intensity==1);
  assert(fabs(vertex(&light,1.5)-.5)<1e-9); // Same brightness 50% farther away.
  assert(fabs(vertex(&light,2.5)-(1-2.5/3))<1e-9);assert(vertex(&light,3)==0);
 }
 // Restoring an actor copies no renderer state; re-registration yields the same result.
 SithThing saved=player;player.actorParams.flags=0;assert(jkRpg_FieldLightRange(&player)==1);
 player=saved;rdCamera_ClearLights(&camera);rdCamera_AddLightRange(&camera,&light,&origin,jkRpg_FieldLightRange(&player));
 assert(light.minRadius==3&&light.intensity==1);
 rdCamera_SetAttenuation(&camera,1,.5);assert(light.minRadius==1.5&&light.maxRadius==3);
 rdCamera_SetAttenuation(&camera,.5,.25);assert(light.minRadius==3&&light.maxRadius==6);
 // The reused slot's next ordinary light must keep its original range and brightness.
 rdCamera_ClearLights(&camera);rdCamera_AddLight(&camera,&light,&origin);
 assert(light.attenuationScale==1&&light.minRadius==2&&light.maxRadius==4);
 assert(vertex(&light,2.5)==0&&fabs(vertex(&light,1)-.5)<1e-9);
 for(int invalid=0;invalid<4;invalid++) {
  double scales[]={0,-1,INFINITY,NAN};rdCamera_ClearLights(&camera);
  rdCamera_AddLightRange(&camera,&light,&origin,scales[invalid]);assert(light.attenuationScale==1&&light.minRadius==2);
 }
 camera.numLights=RDCAMERA_MAX_LIGHTS;assert(!rdCamera_AddLightRange(&camera,&light,&origin,1.5));
 assert(light.attenuationScale==1);
 puts("Field light: exclusive owned/on source, 1.5x range, unchanged peak, original other lights, frame reuse and restore passed");
}
'''
render=(src/"Engine/sithRender.c").read_text()
assert render.count("rdCamera_AddLightRange(")==4
assert render.count("jkRpg_FieldLightRange(")==4
assert "attenuationMax * tmpLights[i]->attenuationScale" in render
menu=(src/"Main/jkRpgMenu.c").read_text()
assert "{ART_GLINT, ART_FIELD_RANGE, ART_BATTERY}" in menu
heading=function("Main/jkRpgMenu.c","static void jkRpg_DrawHeading(")
assert "SITHBIN_IRGOGGLES" not in heading
assert "if (tile == UP_LIGHT * TILES_PER_BRANCH + 2) continue;" in function("Main/jkRpgMenu.c", "static void jkRpg_OverlayShippedTiles(uint16_t* px, int stride)\n{")
scratch=Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-field-light"
scratch.mkdir(parents=True,exist_ok=True)
cfile,binary=scratch/"light.c",scratch/"light"
try:
 cfile.write_text(code)
 for flags in ([],["-DJKM_LIGHTING"]):
  subprocess.run(["cc","-std=gnu11",*flags,str(cfile),"-lm","-o",str(binary)],check=True)
  subprocess.run([str(binary)],check=True)
finally:
 cfile.unlink(missing_ok=True);binary.unlink(missing_ok=True)
