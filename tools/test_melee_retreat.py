"""Compile the actual ordinary-melee ledge retreat helper and its exclusions."""
import os
import tempfile
import subprocess
import sys
from pathlib import Path
src = Path(sys.argv[1]) / "src"
rpg = (src / "Main/jkRpg.c").read_text()
follow = (src / "AI/sithAICmd.c").read_text()
dss = (src / "Dss/sithDSS.c").read_text()
def function(text, signature):
    start = text.index(signature)
    return text[start:text.index("\n}\n", start)+3]
assert "if (jkRpg_MeleeRetreat(actor, instinct, flags)) return 0;" in function(follow,"int sithAICmd_Follow(")
for param in ("param1", "param2"):
    assert f"NETMSG_PUSHF32(pLocal->aInstinctStates[i].{param})" in dss
    assert f"actor->aInstinctStates[i].{param} = NETMSG_POPF32()" in dss
code = r"""
#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <math.h>
#include <string.h>
#include <strings.h>
#include <stdio.h>
#define __strcmpi strcasecmp
#define RPG_AI_MELEE_REACH 0.5
#define RPG_AI_MELEE_SPEED 1.1
typedef double flex_t;
typedef struct {double x,y,z;} rdVector3;
typedef int (*sithAICommandFunc_t)(void);
enum {SITHAI_MODE_ATTACKING=2,SITHAI_MODE_MOVING=1,SITHAI_MODE_TOUGHSKIN=32,
    SITHAI_MODE_FLEEING=2048,SITHAI_MODE_DISABLED=8192,SITHAI_MODE_ACTIVE=512,
    SITH_MT_PHYSICS=1,SITH_TF_DEAD=512,SITH_TF_DESTROYED=2,SITH_TF_DISABLED=524288,
    SITH_TF_WATER=33554432,SITH_PF_FLY=8192,SITH_AF_BOSS=512,SITH_AF_CONTROLSDISABLED=2097152};
typedef struct {const char* aName;} Script;
typedef struct {Script* pScript;} Cog;
typedef struct SithThing {rdVector3 position;struct {rdVector3 vel;int flags;} physicsParams;
    struct {int flags;} actorParams;int type,flags,moveType,attach_flags;void* sector;
    Cog* pCog;struct {rdVector3 lvec;} orient;double moveSize;struct SithThing* pTemplate;char aName[32];} SithThing;
typedef struct {sithAICommandFunc_t func;double fltArg[16];} Instinct;
typedef struct {double alignment,maxStep;int numEntries;Instinct entries[16];} SithAIClass;
typedef struct {int field_0,nextUpdate;double param0,param1,param2,param3;} SithAIInstinctState;
typedef struct {SithThing* thing;SithAIClass* pClass;SithThing *pMoveThing,*pDistractor;
    int flags;rdVector3 movePos;} SithAIControlBlock;
static int sithNet_isMulti,Main_bMotsCompat;
static SithThing player,*sithPlayer_g_pLocalPlayerThing=&player;
static int active=1;
static int jkRpg_IsActive(SithThing* p) {return active && !sithNet_isMulti && p==&player;}
static int sithAICmd_PrimaryFire(void) {return 0;}
static int sithAICmd_BlindFire(void) {return 0;}
static int sithAICmd_LobFire(void) {return 0;}
static int sithAICmd_TurretFire(void) {return 0;}
static uint32_t sithTime_g_msecGameTime;
static double sithTime_g_secGameTime;
static double rdVector_Normalize3Acc(rdVector3* p) {double n=sqrt(p->x*p->x+p->y*p->y+p->z*p->z);if(n){p->x/=n;p->y/=n;p->z/=n;}return n;}
static void rdVector_ScaleAdd3Acc(rdVector3* p,const rdVector3* v,double a) {p->x+=v->x*a;p->y+=v->y*a;p->z+=v->z*a;}
static int pathMode,floorMode,pathChecks,floorChecks,moves,looks;
static double moveSpeed;
static rdVector3 looked;
static int jkRpg_CrowdPath(SithThing* thing,void* sector,const rdVector3* from,const rdVector3* to,double radius) {
    assert(sector==thing->sector && from==&thing->position && radius==thing->moveSize);
    pathChecks++;
    if(pathMode==1) return 0; // solid wall or occupied corridor
    if(pathMode==2 && pathChecks==1) return 0; // use a sideways exit
    if(pathMode==3 && hypot(to->x-from->x,to->y-from->y)>.61) return 0; // short room
    if(pathMode==4 && pathChecks<=5) return 0; // wall requires wrapping around at135 degrees
    if(pathMode==5 && (to->y!=from->y || to->x<=from->x)) return 0; // exact east tangent in narrow lane
    if(pathMode==6 && hypot(to->x-from->x,to->y-from->y)>.41) return 0; // companion leaves only a short gap
    return 1;
}
static int sithAI_CanWalk(SithAIControlBlock* actor,rdVector3* p,void* out) {
    assert(!out);floorChecks++;
    if(floorMode==1) return 0; // cliff or missing floor
    if(floorMode==2) return 2; // non-walkable slope
    if(floorMode==3 && floorChecks%3==0) return 0; // gap inside route, endpoint alone insufficient
    return 1;
}
static void sithAI_SetMoveThing(SithAIControlBlock* a,rdVector3* p,double speed) {moves++;a->movePos=*p;a->flags|=SITHAI_MODE_MOVING;moveSpeed=speed;}
static void sithAI_SetLookFrame(SithAIControlBlock* a,rdVector3* p) {looks++;looked=*p;}
""" + function(rpg,"flex_t jkRpg_AIMoveScale(") + function(rpg,"static int jkRpg_IsOrdinaryBrawler(") + function(rpg,"int jkRpg_MeleeRetreat(") + r"""
static Script script={"actor_gg.cog"};static Cog cog={&script};
static SithThing enemy;static SithAIClass ai;static SithAIControlBlock actor;static SithAIInstinctState state;
static void reset(void) {
    sithNet_isMulti=Main_bMotsCompat=pathMode=floorMode=pathChecks=floorChecks=moves=looks=0;active=1;
    sithTime_g_secGameTime=10;sithTime_g_msecGameTime=10000;
    player=(SithThing){.position={-3.401696,-11.363347,-3.079895},.attach_flags=1,.sector=&player};
    enemy=(SithThing){.position={-3.347389,-11.476037,-3.665181},.attach_flags=1,.sector=&player,
        .moveType=SITH_MT_PHYSICS,.pCog=&cog,.moveSize=.08,.orient={{0,1,0}}};
    script.aName="actor_gg.cog";
    ai=(SithAIClass){.alignment=-1,.maxStep=.1,.numEntries=1};
    ai.entries[0].func=sithAICmd_PrimaryFire;ai.entries[0].fltArg[2]=.25;
    actor=(SithAIControlBlock){.thing=&enemy,.pClass=&ai,.pMoveThing=&player,.pDistractor=&player,.flags=SITHAI_MODE_ATTACKING};
    state=(SithAIInstinctState){.param0=7,.param3=9};
}
static int tick(double now,int event) {sithTime_g_secGameTime=now;sithTime_g_msecGameTime=(uint32_t)(now*1000);return jkRpg_MeleeRetreat(&actor,&state,event);}
static void retreat(void) {assert(!tick(10,0));assert(!tick(11,0));assert(tick(12.1,0));}
int main(void) {
    for(int target=0;target<2;target++) {
        reset();actor.flags|=SITHAI_MODE_TOUGHSKIN; // ordinary stock actor_gg sets its fire target
        if(target)enemy.position=(rdVector3){-3.506648,-11.456781,-3.665181};
        rdVector3 original=enemy.position;
        retreat();assert(moves==1 && moveSpeed==2.5 && state.param2==1 && floorChecks==6);
        assert(state.param0==7 && state.param3==9 && !(actor.flags&SITHAI_MODE_FLEEING));
        assert(!memcmp(&original,&enemy.position,sizeof(original))); // move normally, never teleport
        assert(hypot(actor.movePos.x-player.position.x,actor.movePos.y-player.position.y)>1);
        assert(actor.movePos.z==original.z);
        assert(tick(13,SITHAI_MODE_ACTIVE) && moves==1); // events cannot redirect retreat under ledge
        enemy.position=actor.movePos;actor.flags&=~SITHAI_MODE_MOVING;
        assert(tick(30,0) && moves==1 && looked.z==player.position.z); // wait after escaping
        SithAIInstinctState saved=state;state=saved;assert(tick(31,0) && moves==1); // restored retreat state
        player.position.z=enemy.position.z;assert(!tick(32,0) && state.param1==0 && state.param2==0);
    }
    reset();retreat();player.position.x+=4;assert(!tick(13,0) && !state.param2);
    reset();retreat();player.attach_flags=0;assert(!tick(13,0) && !state.param2);
    reset();enemy.physicsParams.vel.x=.1;assert(!tick(10,0) && !tick(20,0) && !state.param1 && !moves);
    enemy.physicsParams.vel.x=0;assert(!tick(21,0) && !tick(22,0) && tick(23.1,0)); // stairs keep pursuit while progressing
    reset();assert(!tick(10,0));player.attach_flags=0;assert(!tick(11,0));player.attach_flags=1;
    assert(!tick(12,0) && !tick(13,0) && tick(14.1,0)); // jump interrupts sustained trigger
    reset();player.position.z=enemy.position.z+.3;assert(!tick(10,0) && !tick(15,0) && !moves);
    reset();pathMode=2;retreat();assert(pathChecks==2 && moves==1);
    reset();pathMode=3;retreat();assert(pathChecks==13 && moves==1);
    assert(fabs(hypot(actor.movePos.x-enemy.position.x,actor.movePos.y-enemy.position.y)-.6)<1e-8);
    reset();pathMode=4;retreat();assert(pathChecks==6 && moves==1); // full-circle escape round a wall
    double before=hypot(enemy.position.x-player.position.x,enemy.position.y-player.position.y);
    double after=hypot(actor.movePos.x-player.position.x,actor.movePos.y-player.position.y);
    assert(after>=before+.2);
    reset();pathMode=5;retreat();assert(pathChecks==9 && moves==1); // first cardinal fallback
    assert(actor.movePos.y==enemy.position.y && actor.movePos.x>enemy.position.x);
    reset();pathMode=6;retreat();assert(pathChecks==25 && moves==1);
    assert(fabs(hypot(actor.movePos.x-enemy.position.x,actor.movePos.y-enemy.position.y)-.4)<1e-8);
    for(int blocked=0;blocked<4;blocked++) {
        reset();if(!blocked)pathMode=1;else floorMode=blocked;
        assert(!tick(10,0) && !tick(12.1,0) && !moves && !state.param2);
        assert(pathChecks==32); // 36 candidates; four short routes fail the separation guardint attempts=pathChecks;assert(!tick(13,0) && pathChecks==attempts);
    }
    for(int excluded=0;excluded<15;excluded++) {
        reset();
        if(excluded==0)sithNet_isMulti=1;
        if(excluded==1)Main_bMotsCompat=1;
        if(excluded==2)active=0;
        if(excluded==3)script.aName="actor_st.cog";
        if(excluded==4)script.aName="actor_mn.cog";
        if(excluded==5)actor.flags|=SITHAI_MODE_FLEEING;
        if(excluded==6)enemy.actorParams.flags=SITH_AF_BOSS;
        if(excluded==7)enemy.physicsParams.flags=SITH_PF_FLY;
        if(excluded==8)enemy.flags=SITH_TF_WATER;
        if(excluded==9)ai.alignment=1;
        if(excluded==10)ai.entries[0].fltArg[2]=4;
        if(excluded==11){ai.entries[1].func=sithAICmd_LobFire;ai.numEntries=2;}
        if(excluded==12)actor.pMoveThing=&enemy;
        if(excluded==13)actor.pDistractor=&enemy;
        if(excluded==14)actor.flags|=SITHAI_MODE_DISABLED;
        state.param1=8;state.param2=1;
        assert(!tick(10,0) && !tick(20,0) && !moves && !state.param1 && !state.param2);
    }
    reset();script.aName="actor_rf.cog";ai.maxStep=.5;ai.entries[0].fltArg[2]=.15;
    player.position.z=enemy.position.z+1;retreat();assert(moves==1); // ordinary punching Gran
    reset();player.position.x=enemy.position.x;player.position.y=enemy.position.y;retreat();assert(moves==1);
    puts("Melee ledge retreat: reported guards, bounded safe exits, no cliffs, persistent waiting, prompt pursuit and exclusions passed");
}
"""
scratch=Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-melee-retreat"
scratch.mkdir(parents=True,exist_ok=True)
cfile,binary=scratch/"retreat.c",scratch/"retreat"
try:
    cfile.write_text(code)
    subprocess.run(["cc","-std=gnu11",str(cfile),"-lm","-o",str(binary)],check=True)
    subprocess.run([str(binary)],check=True)
finally:
    cfile.unlink(missing_ok=True);binary.unlink(missing_ok=True)
