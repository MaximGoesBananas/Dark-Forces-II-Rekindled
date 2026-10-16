"""Exercise the shared shot gate and actual BlindFire, including saved cooldown state."""
import subprocess
import sys
import tempfile
from pathlib import Path

src = Path(sys.argv[1]) / "src"
def function(path, signature):
    text = (src / path).read_text()
    start = text.index(signature)
    return text[start:text.index("\n}\n", start) + 3]
fire = function("World/sithWeapon.c", "SithThing* sithWeapon_WeaponFire(")
blind = function("AI/sithAICmd.c", "int sithAICmd_BlindFire(")
# Normal fire and delayed animation callbacks both enter the shared shot function.
ai = (src / "AI/sithAI.c").read_text()
assert 'sithWeapon_WeaponFire(v9, v8,' in ai
saved = (src / "Dss/sithDSS.c").read_text()
assert 'NETMSG_PUSHU32(pLocal->field_288)' in saved and 'actor->field_288 = NETMSG_POPU32()' in saved
code = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <strings.h>
#define __strcmpi strcasecmp
#define SITH_ASSERTREL assert
typedef double flex_t, flex_d_t;
typedef struct { double x,y,z; } rdVector3;
typedef int sithSound;
typedef struct SithThing SithThing;
typedef struct { SithThing* thing; int field_288,flags; SithThing* pDistractor;
    rdVector3 field_1F8,blindAimError; double attackDistance; } SithAIControlBlock;
struct SithThing { int type,guid; SithAIControlBlock* actor; char aName[32];
    void* sector; rdVector3 position; double moveSize;
    struct { SithThing* pWeaponTemplate; SithThing* templateWeapon2; } actorParams; };
typedef struct { double fltArg[16]; int intArg[16]; } SithAIInstinct;
typedef struct { int nextUpdate; } SithAIInstinctState;
enum { SITH_THING_ACTOR=2, SITHAI_MODE_ATTACKING=2, SITH_SC_FIRE1=1, SITH_ANIM_FIRE=1,
    DEBUGFLAG_NO_AI=1, SITH_MESSAGE_FIRE=1 };
static int sithTime_g_msecGameTime,sithMessage_g_outputstream,g_debugmodeFlags,active=1,shots,fail;
static SithThing player,shot,*sithPlayer_g_pLocalPlayerThing=&player;
static int jkRpg_IsActive(SithThing* p) { return active; }
static double _frand(void) { return 0; }
static void sithAIAwareness_CreateTransmittingEvent(void* a,rdVector3* b,int c,double d,SithThing* e) {}
static SithThing* sithWeapon_WeaponFireProjectile(SithThing* a,SithThing* b,rdVector3* c,rdVector3* d,
    sithSound* e,int f,double g,int h,double i,int j) { if(fail)return NULL; shots++; return &shot; }
static void sithDSSThing_Fire(SithThing* a,SithThing* b,rdVector3* c,rdVector3* d,sithSound* e,
    int f,double g,int h,double i,int j,int k,int l,int m) {}
static int sithAI_sub_4EB300(SithThing* a,rdVector3* b,rdVector3* c,double d,double e,double f,
    rdVector3* g,double* distance) { *distance=2; return 0; }
static void sithAI_RandomFireVector(rdVector3* a,double b) {}
static void sithSoundClass_PlayModeFirst(SithThing* a,int b) {}
static void sithCog_ThingSendMessage(SithThing* a,SithThing* b,int c) {}
''' + fire + blind + r'''
static SithThing* shoot(SithThing* actor,SithThing* projectile) {
    rdVector3 zero={0}; return sithWeapon_WeaponFire(actor,projectile,&zero,&zero,NULL,0,1,0,0);
}
int main(void) {
    SithThing rifle={.aName="+econcbullet"}, other={.aName="+elaser"};
    SithAIControlBlock ai={0}; SithThing gunner={.type=2,.actor=&ai};
    ai.thing=&gunner; ai.pDistractor=&player; gunner.actorParams.pWeaponTemplate=&rifle;
    SithAIInstinct instinct={0}; instinct.fltArg[1]=1; instinct.intArg[0]=4000;
    SithAIInstinctState state={0};
    sithTime_g_msecGameTime=1000; assert(shoot(&gunner,&rifle)); assert(ai.field_288==3800);
    // BlindFire and PrimaryFire must share the same firing cooldown.
    sithTime_g_msecGameTime=1100; sithAICmd_BlindFire(&ai,&instinct,&state,0,0); assert(shots==1);
    // A repeated animation callback or a fresh primary schedule cannot bypass the gate either.
    assert(!shoot(&gunner,&rifle)); sithTime_g_msecGameTime=3799; assert(!shoot(&gunner,&rifle));
    // Save/reload retains the deadline through the existing serialized AI field.
    SithAIControlBlock restored=ai; gunner.actor=&restored; assert(!shoot(&gunner,&rifle));
    gunner.actor=&ai; sithTime_g_msecGameTime=3800;
    sithAICmd_BlindFire(&ai,&instinct,&state,0,0); assert(shots==2 && ai.field_288==6600);
    sithTime_g_msecGameTime=3900; assert(!shoot(&gunner,&rifle));
    // Other weapons, player shots, inactive RPG and independent enemies retain their behavior.
    assert(shoot(&gunner,&other)); assert(shoot(&player,&rifle));
    active=0; assert(shoot(&gunner,&rifle)); active=1;
    SithAIControlBlock second={0}; SithThing enemy2={.type=2,.actor=&second}; assert(shoot(&enemy2,&rifle));
    sithTime_g_msecGameTime=6600; fail=1; assert(!shoot(&gunner,&rifle)); assert(ai.field_288==6600);
    fail=0; assert(shoot(&gunner,&rifle));
    puts("Concussion primary/blind/delayed shots share a saved 2.8-second minimum; exclusions and failed spawns passed");
}
'''
scratch = Path("/mnt/d/Dev/helm/temp/rekindled-concussion-review")
with tempfile.TemporaryDirectory(dir=scratch if scratch.is_dir() else None) as tmp:
    path=Path(tmp)/"test.c"
    path.write_text(code)
    subprocess.run(["cc","-std=gnu11","-Wall","-o",str(Path(tmp)/"test"),str(path)],check=True)
    subprocess.run([str(Path(tmp)/"test")],check=True)
