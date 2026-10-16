"""Compile actual weapon input handling and test primary/secondary transitions."""
import os
import tempfile
import subprocess
import sys
from pathlib import Path

src = Path(sys.argv[1]) / "src"
weapon = (src / "World/sithWeapon.c").read_text()
rpg = (src / "Main/jkRpg.c").read_text()

def function(source, signature):
    start = source.index(signature)
    return source[start:source.index("\n}\n", start) + 3]

code = r"""
#include <assert.h>
#include <stdio.h>
#include <string.h>
typedef double flex_t;
typedef double flex_d_t;
enum { SITH_THING_PLAYER=10, SITH_TF_DEAD=1, SITH_WF_EMITAITARGETEDEVENT=2,
    INPUT_FUNC_FIRE1=10, INPUT_FUNC_FIRE2=11, INPUT_FUNC_ACTIVATE=12,
    INPUT_FUNC_SELECT1=13, INPUT_FUNC_SELECT0=22, INPUT_FUNC_NEXTWEAPON=23,
    INPUT_FUNC_PREVWEAPON=24, SITH_MESSAGE_ACTIVATE=1, SITH_MESSAGE_DEACTIVATED=2,
    SITH_MESSAGE_FIRE=3, SITH_MESSAGE_SELECTED=4, ITEMINFO_WEAPON=1,
    SENDERTYPE_SYSTEM=1, SENDERTYPE_THING=2,
    SITHBIN_FISTS=1, SITHBIN_BRYARPISTOL=2, SITHBIN_STORMTROOPER_RIFLE=3, SITHBIN_CONCUSSION_RIFLE=9, SITHBIN_LIGHTSABER=10 };
typedef struct { int id; } sithCog;
typedef struct { sithCog* cog; int flags; } SithInventoryType;
typedef struct { int type,flags,idx; struct {int flags;} weaponParams;
    struct {void* pPlayer;} actorParams; } SithThing;
static SithThing player;
static SithThing* sithPlayer_g_pLocalPlayerThing=&player;
static int sithNet_isMulti, Main_bMotsCompat;
static flex_t sithTime_g_secGameTime=10, sithWeapon_secMountWait;
static int sithWeapon_mots_5a3258, sithWeapon_motsAConv[10], sithWeapon_8BD024=-1;
static int sithWeapon_a8BD030[2], held[32], pressed[32], current;
static sithCog cog={1};
static SithInventoryType inventory={&cog,ITEMINFO_WEAPON};
static struct {int message,mode;} events[128];
static int sithWeapon_CurWeaponMode=-1, sithWeapon_8BD05C, sithWeapon_senderIndex;
static flex_t sithWeapon_fireWait, sithWeapon_fireRate, sithWeapon_LastFireTimeSecs;
static int eventCount, selections, saberOwned=1, saberAvailable=1, saberControls=1;
// The RPG saber controls (tools/test_saber_guard.py) own both buttons of the selected saber.
static int jkRpg_SaberControls(SithThing* p) { return saberControls && current==SITHBIN_LIGHTSABER; }
static int sithControl_GetKey(int key,int* edge) { *edge=pressed[key];pressed[key]=0;return held[key]; }
static int sithThing_MotsTick(int a,int b,flex_t c) {return 1;}
static int sithInventory_SelectWeaponFollowing(int n) {return n;}
static int sithInventory_GetCurrentWeapon(SithThing* p) {return current;}
static int sithInventory_GetInventory(SithThing* p,int n) {return n==10?saberOwned:1;}
static int sithInventory_IsInventoryAvailable(SithThing* p,int n) {return n==10?saberAvailable:1;}
static SithInventoryType* sithInventory_GetType(int n) {assert(n>=1 && n<=10);return &inventory;}
static int sithWeapon_SelectWeapon(SithThing* p,int n,int mode) {selections++;current=n;return 1;}
static void sithWeapon_SelectNextWeapon(SithThing* p) {current=current%10+1;}
static void sithWeapon_SelectPreviousWeapon(SithThing* p) {current=current==1?10:current-1;}
static void sithCog_SendMessage(sithCog* c,int message,int sender,int mode,int type,int idx,int unused) {
    assert(c==&cog && mode>=0 && mode<=1 && eventCount<128);
    events[eventCount].message=message;events[eventCount++].mode=mode;
}
static void sithCog_SendMessageEx(sithCog* c,int message,int sender,int mode,int type,int idx,int unused,double a,double b,double d,double e) {
    sithCog_SendMessage(c,message,sender,mode,type,idx,unused);
}
""" + function(rpg, "int jkRpg_IsActive(") + function(weapon, "void sithWeapon_UpdateActorWeaponState(") + function(weapon, "int sithWeapon_ProcessWeaponControls(") + r"""
static void reset(int bin) {
    player=(SithThing){.type=SITH_THING_PLAYER,.idx=7,.actorParams={&player}};
    sithPlayer_g_pLocalPlayerThing=&player;
    sithNet_isMulti=Main_bMotsCompat=0;current=bin;eventCount=selections=0;saberOwned=saberAvailable=1;
    memset(held,0,sizeof(held));memset(pressed,0,sizeof(pressed));
    memset(sithWeapon_a8BD030,0,sizeof(sithWeapon_a8BD030));
}
static void tick(void) {sithWeapon_ProcessWeaponControls(&player,.016);}
static void event(int i,int message,int mode) {
    assert(i<eventCount && events[i].message==message && events[i].mode==mode);
}
int main(void) {
    // SELECT1 is a bound action, not a hardcoded physical key. Before the saber it selects fists.
    for(int missing=0;missing<2;missing++) {
        reset(3);if(missing) saberAvailable=0;else saberOwned=0;
        pressed[INPUT_FUNC_SELECT1]=1;tick();assert(current==1 && selections==1);
    }
    // From any weapon it prefers the owned saber; repeated presses keep fists available.
    for(int bin=1;bin<=10;bin++) {
        reset(bin);pressed[INPUT_FUNC_SELECT1]=held[INPUT_FUNC_SELECT1]=1;tick();
        assert(current==(bin==10?1:10) && selections==1);
        tick();tick();assert(selections==1); // holding the key never toggles again
        pressed[INPUT_FUNC_SELECT1]=1;tick();assert(current==(bin==10?10:1) && selections==2);
        pressed[INPUT_FUNC_SELECT1]=1;tick();assert(current==(bin==10?1:10) && selections==3);
    }
    // Direct saber and the other number actions retain their original targets.
    for(int action=INPUT_FUNC_SELECT1+1;action<=INPUT_FUNC_SELECT0;action++) {
        reset(1);pressed[action]=1;tick();assert(current==action-INPUT_FUNC_ACTIVATE && selections==1);
    }
    // Unbound SELECT1 has no event; custom mappings supply the same action event without rebinding.
    reset(3);tick();assert(current==3 && !selections);
    for(int excluded=0;excluded<3;excluded++) {
        reset(3);if(excluded==0) player.actorParams.pPlayer=NULL;
        if(excluded==1) sithPlayer_g_pLocalPlayerThing=NULL;
        if(excluded==2) sithNet_isMulti=1;
        pressed[INPUT_FUNC_SELECT1]=1;tick();assert(current==1);
    }

    // The selected saber's buttons go to the RPG saber controls, never to its stock script.
    reset(10);held[INPUT_FUNC_FIRE1]=held[INPUT_FUNC_FIRE2]=1;tick();tick();
    held[INPUT_FUNC_FIRE1]=held[INPUT_FUNC_FIRE2]=0;tick();
    assert(eventCount==0 && !sithWeapon_a8BD030[0] && !sithWeapon_a8BD030[1]);
    // A button still active from another weapon is released when the saber takes over.
    reset(4);held[INPUT_FUNC_FIRE2]=1;tick();current=10;tick();
    assert(eventCount==2 && !sithWeapon_a8BD030[1]);event(1,SITH_MESSAGE_DEACTIVATED,1);
    // Without the RPG controls (MotS, multiplayer) the saber keeps both stock attacks.
    saberControls=0;
    for(int bin=1;bin<=10;bin++) {
        reset(bin);held[INPUT_FUNC_FIRE1]=1;tick();
        assert(eventCount==1 && sithWeapon_a8BD030[0]==1);event(0,SITH_MESSAGE_ACTIVATE,0);
        tick();tick();assert(eventCount==1); // held primary never restarts its script
        held[INPUT_FUNC_FIRE1]=0;tick();assert(eventCount==2 && !sithWeapon_a8BD030[0]);
        event(1,SITH_MESSAGE_DEACTIVATED,0);
        reset(bin);held[INPUT_FUNC_FIRE2]=1;tick();tick();tick();
        if(bin<=3 || bin==9) assert(eventCount==0 && !sithWeapon_a8BD030[1]);
        else {assert(eventCount==1 && sithWeapon_a8BD030[1]);event(0,SITH_MESSAGE_ACTIVATE,1);}
        held[INPUT_FUNC_FIRE2]=0;tick();
        assert(eventCount==((bin<=3 || bin==9)?0:2) && !sithWeapon_a8BD030[1]);
        if(bin>3 && bin!=9) event(1,SITH_MESSAGE_DEACTIVATED,1);
    }
    saberControls=1;
    // Adding/releasing a blocked secondary never interrupts a held primary.
    for(int b=0;b<4;b++) {
        int bin=(int[]){1,2,3,9}[b];
        reset(bin);held[INPUT_FUNC_FIRE1]=1;tick();held[INPUT_FUNC_FIRE2]=1;tick();tick();
        held[INPUT_FUNC_FIRE2]=0;tick();assert(eventCount==1 && sithWeapon_a8BD030[0]);
        held[INPUT_FUNC_FIRE1]=0;tick();assert(eventCount==2);event(1,SITH_MESSAGE_DEACTIVATED,0);
        reset(bin);held[INPUT_FUNC_FIRE1]=held[INPUT_FUNC_FIRE2]=1;tick();
        assert(eventCount==1 && sithWeapon_a8BD030[0] && !sithWeapon_a8BD030[1]);
        event(0,SITH_MESSAGE_ACTIVATE,0);
    }
    // Distinct alternate modes preserve original handover and resume behavior.
    reset(4);held[INPUT_FUNC_FIRE1]=1;tick();held[INPUT_FUNC_FIRE2]=1;tick();
    assert(eventCount==3);event(1,SITH_MESSAGE_DEACTIVATED,0);event(2,SITH_MESSAGE_ACTIVATE,1);
    held[INPUT_FUNC_FIRE2]=0;tick();assert(eventCount==5);
    event(3,SITH_MESSAGE_DEACTIVATED,1);event(4,SITH_MESSAGE_ACTIVATE,0);
    held[INPUT_FUNC_FIRE1]=0;tick();assert(eventCount==6);event(5,SITH_MESSAGE_DEACTIVATED,0);
    // Existing active secondary state is released if the selected weapon now blocks it.
    reset(4);held[INPUT_FUNC_FIRE2]=1;tick();current=3;tick();
    assert(eventCount==2 && !sithWeapon_a8BD030[1]);event(1,SITH_MESSAGE_DEACTIVATED,1);
    tick();assert(eventCount==2);current=4;tick();
    assert(eventCount==3 && sithWeapon_a8BD030[1]);event(2,SITH_MESSAGE_ACTIVATE,1);
    held[INPUT_FUNC_FIRE2]=0;tick();assert(eventCount==4);event(3,SITH_MESSAGE_DEACTIVATED,1);
    // Primary resumes after a mode becomes blocked; no stuck activation on release.
    reset(4);held[INPUT_FUNC_FIRE1]=1;tick();held[INPUT_FUNC_FIRE2]=1;tick();current=2;tick();
    assert(eventCount==5 && sithWeapon_a8BD030[0] && !sithWeapon_a8BD030[1]);
    event(3,SITH_MESSAGE_DEACTIVATED,1);event(4,SITH_MESSAGE_ACTIVATE,0);
    held[INPUT_FUNC_FIRE1]=held[INPUT_FUNC_FIRE2]=0;tick();assert(eventCount==6);
    // RPG-inactive, remote-player, multiplayer and MotS inputs retain stock secondary.
    for(int b=0;b<4;b++) for(int excluded=0;excluded<4;excluded++) {
        int bin=(int[]){1,2,3,9}[b];
        reset(bin);
        if(excluded==0) player.actorParams.pPlayer=NULL;
        if(excluded==1) sithPlayer_g_pLocalPlayerThing=NULL;
        if(excluded==2) sithNet_isMulti=1;
        if(excluded==3) Main_bMotsCompat=1;
        held[INPUT_FUNC_FIRE2]=1;tick();assert(eventCount==1);event(0,SITH_MESSAGE_ACTIVATE,1);
        held[INPUT_FUNC_FIRE2]=0;tick();assert(eventCount==2);event(1,SITH_MESSAGE_DEACTIVATED,1);
    }
    reset(4);held[INPUT_FUNC_FIRE2]=1;tick();player.weaponParams.flags=SITH_WF_EMITAITARGETEDEVENT;tick();
    assert(eventCount==2 && !sithWeapon_a8BD030[1]);event(1,SITH_MESSAGE_DEACTIVATED,1);
    // A saved active concussion secondary is canceled before it can fire again.
    for(int mounted=0;mounted<=1;mounted++) {
        reset(9);sithWeapon_CurWeaponMode=1;sithWeapon_8BD05C=mounted;
        sithWeapon_fireRate=1;sithWeapon_fireWait=0;
        sithWeapon_a8BD030[0]=sithWeapon_a8BD030[1]=1;
        sithWeapon_UpdateActorWeaponState(&player);
        assert(eventCount==1 && sithWeapon_CurWeaponMode==-1);
        event(0,SITH_MESSAGE_DEACTIVATED,1);
        held[INPUT_FUNC_FIRE1]=held[INPUT_FUNC_FIRE2]=1;tick();
        assert(eventCount==2);event(1,SITH_MESSAGE_ACTIVATE,0);
    }
    puts("Weapon modes: saber controls own its buttons; all primaries; blocked/retained secondaries; holds, transitions, cleanup and exclusions passed");
}
"""
scratch = Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-fire-modes"
scratch.mkdir(parents=True, exist_ok=True)
cfile, binary = scratch / "fire_modes.c", scratch / "fire_modes"
try:
    cfile.write_text(code)
    subprocess.run(["cc", "-std=gnu99", str(cfile), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
finally:
    cfile.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)
