"""Exercise the real supply-finder filtering and sight ray. Run in WSL with the engine path."""
import os
import tempfile
import subprocess
import sys
from pathlib import Path

source = (Path(sys.argv[1]) / "src/Main/jkRpg.c").read_text()
start = source.index("static int jkRpg_IsVisiblePickup(const SithThing* item)")
code = source[start:source.index("static void jkRpg_DrawSupplyFinder(", start)]
harness = r'''
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <strings.h>
#define __strnicmp strncasecmp
typedef double flex_t;
typedef struct {double x,y,z;} rdVector3;
typedef struct {unsigned renderTick;} SithSector;
typedef struct {char aName[40];} Script;
typedef struct {Script* pScript; int flags;} Cog;
typedef struct SithThing {
    int type, flags, collide; SithSector* sector; Cog* pCog;
    struct {int type; void* model3; int desiredGeoMode;} renderData;
    unsigned renderFrame; rdVector3 position;
} SithThing;
typedef struct {SithSector* sector; rdVector3 lookPos;} SithCamera;
typedef struct {int type; SithThing* pThingCollided;} SithCollision;
enum {SITH_THING_ITEM=5, SITH_COLLIDE_NONE=0, RD_THING_MODEL3=1, RD_GEOMETRY_NONE=0,
      SITH_TF_DISABLED=1, SITH_TF_10=2, SITH_TF_DESTROYED=4, SITH_COG_DISABLED=8,
      SITHCOLLISION_THING=1, SITHCOLLISION_WORLD=2, RAYCAST_100=256, RAYCAST_2=2};
static unsigned sithRender_lastRenderTick=42, jkPlayer_currentTickIdx=30;
static SithThing* sithPlayer_g_pLocalPlayerThing;
static SithCollision hits[4]; static int count,at,stack,searches;
static void rdVector_Sub3(rdVector3* a,const rdVector3* b,const rdVector3* c){*a=(rdVector3){b->x-c->x,b->y-c->y,b->z-c->z};}
static double rdVector_Normalize3Acc(rdVector3* d){double n=sqrt(d->x*d->x+d->y*d->y+d->z*d->z);if(n){d->x/=n;d->y/=n;d->z/=n;}return n;}
static void sithCollision_SearchForCollisions(SithSector* s,SithThing* moving,const rdVector3* p,const rdVector3* d,double length,double radius,int flags){
    // A moving player invokes callbacks that truncate the ray at actors and pickup spheres.
    assert(s && !moving && length==2 && radius==0 && flags==(RAYCAST_100|RAYCAST_2));
    at=0; stack++; searches++;
}
static SithCollision* sithCollision_PopStack(void){return at<count?&hits[at++]:NULL;}
static void sithCollision_DecreaseStackLevel(void){stack--;}
'''
checks = r'''
int main(void){
    SithSector sector={42}; Script script={"pow_energy.cog"}; Cog cog={&script,0};
    SithThing item={.type=5,.collide=1,.sector=&sector,.pCog=&cog,.renderData={1,&script,4},.renderFrame=30,.position={0,2,0}};
    assert(jkRpg_IsVisiblePickup(&item));
    for(int flag=1;flag<=4;flag*=2){item.flags=flag;assert(!jkRpg_IsVisiblePickup(&item));} item.flags=0;
    item.type=7;assert(!jkRpg_IsVisiblePickup(&item));item.type=5;
    item.collide=0;assert(!jkRpg_IsVisiblePickup(&item));item.collide=1;
    item.sector=NULL;assert(!jkRpg_IsVisiblePickup(&item));item.sector=&sector;
    item.pCog=NULL;assert(!jkRpg_IsVisiblePickup(&item));item.pCog=&cog;
    cog.pScript=NULL;assert(!jkRpg_IsVisiblePickup(&item));cog.pScript=&script;
    cog.flags=8;assert(!jkRpg_IsVisiblePickup(&item));cog.flags=0;
    script.aName[0]='x';assert(!jkRpg_IsVisiblePickup(&item));script.aName[0]='p';
    item.renderData.model3=NULL;assert(!jkRpg_IsVisiblePickup(&item));item.renderData.model3=&script;
    item.renderData.type=0;assert(!jkRpg_IsVisiblePickup(&item));item.renderData.type=1;
    item.renderData.desiredGeoMode=0;assert(!jkRpg_IsVisiblePickup(&item));item.renderData.desiredGeoMode=4;
    sector.renderTick--;assert(!jkRpg_IsVisiblePickup(&item));sector.renderTick++;
    item.renderFrame--;assert(!jkRpg_IsVisiblePickup(&item));item.renderFrame++;
    SithThing player={0}, door={0}, actor={0};sithPlayer_g_pLocalPlayerThing=&player;
    SithCamera camera={&sector,{0,0,0}};
    assert(jkRpg_CanSee(&camera,&item) && !stack); // unobstructed centre
    hits[0]=(SithCollision){1,&player};hits[1]=(SithCollision){1,&item};count=2;
    assert(jkRpg_CanSee(&camera,&item) && !stack);
    // Even when the target's collision sphere is in front of the wall, the centre is hidden.
    hits[2]=(SithCollision){2,NULL};count=3;
    assert(!jkRpg_CanSee(&camera,&item) && !stack);
    hits[0]=(SithCollision){2,NULL};count=1;assert(!jkRpg_CanSee(&camera,&item) && !stack);
    hits[0]=(SithCollision){1,&door};assert(!jkRpg_CanSee(&camera,&item) && !stack);
    hits[0]=(SithCollision){1,&actor};assert(!jkRpg_CanSee(&camera,&item) && !stack);
    int before=searches;camera.lookPos=item.position;assert(jkRpg_CanSee(&camera,&item) && searches==before && !stack);
    puts("Supply finder: real rendered pickups, full sight ray, walls, doors and occluders passed");
}
'''
scratch = Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-finder-check"
scratch.mkdir(parents=True, exist_ok=True)
cfile, binary = scratch / "finder.c", scratch / "finder"
try:
    cfile.write_text(harness + code + checks)
    subprocess.run(["cc", "-std=c99", "-Wall", str(cfile), "-lm", "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
finally:
    cfile.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)
