"""Run the actual autosave scheduler through deadlines, blocked states and retries."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

src=Path(sys.argv[1])/"src"
rpg=(src/"Main/jkRpg.c").read_text()
def function(signature):
    start=rpg.index(signature)
    return rpg[start:rpg.index("\n}\n",start)+3]
main=(src/"Main/sithMain.c").read_text()
tick=main.index("jkRpg_AutosaveTick();")
assert main.index("sithThing_Update(")<tick
assert main.rindex("sithCog_ProcessCogs();",0,tick)<tick<main.index("sithGamesave_Process();",tick)
restore=(src/"Dss/sithGamesave.c").read_text()
assert restore.index("jkRpg_OnRestoreStart();")<restore.index("stdConffile_OpenReadBytesBypass(fpath)",restore.index("jkRpg_OnRestoreStart();"))
code=r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
typedef double flex_t;
enum {SITH_THING_PLAYER=1,SITH_TF_DEAD=1,SITH_TF_DESTROYED=2,SITH_TF_DISABLED=4,SITH_TF_WATER=8,
 SITH_AF_CONTROLSDISABLED=16,SITH_GS_NONE=0,RPG_BIN_DATAVER=0,RPG_BIN_LIGHTGAP,RPG_BIN_CROWDS,RPG_BIN_STARTAMMO,
 RPG_BIN_CROWDFIX,RPG_BIN_PEDFIX,RPG_BIN_BACTACOOL,RPG_BIN_BACTAHEAL,RPG_BIN_REGENWAIT};
typedef struct {int type,flags;struct {double health,maxHealth;int flags;void* pPlayer;} actorParams;void* sector;} SithThing;
typedef struct {int placeholder;} SithWorld;
static SithThing player,otherPlayer,*sithPlayer_g_pLocalPlayerThing;
static SithWorld world,otherWorld,*sithWorld_g_pCurrentWorld;
static int sithNet_isMulti,Main_bMotsCompat,sithMain_bEndLevel,g_sithMode,g_submodeFlags,jkRpg_bMenuOpen,sithGamesave_state;
static double sithTime_g_secGameTime;
static int registryValue=5,registryReads,attempts,messages,saveResult=1;
static int wuRegistry_GetInt(const char* name,int fallback) {registryReads++;return registryValue;}
static void wuRegistry_SaveInt(const char* name,int value) {registryValue=value;}
static int sithGamesave_Autosave(void) {attempts++;return saveResult;}
static void sithConsole_PrintString(const char* text) {messages++;}
static int jkRpg_bRestoring,jkRpg_bWorldFromSave,jkRpg_bRestorePedCount,jkRpg_crowdTrimStarted,sessionResets;
static struct {struct {double amount;} aItems[64];} jkPlayer_playerInfos[1];
static void jkRpg_ResetSession(void) {sessionResets++;}
'''
code+=function("int jkRpg_IsActive(")
a=rpg.index("// Timed saves")
code+=rpg[a:rpg.index("// Level and load events",a)]
code+=function("void jkRpg_OnRestoreStart(")
code+=r'''
static void tick(double now) {sithTime_g_secGameTime=now;jkRpg_AutosaveTick();}
static void fresh(void) {
 player=(SithThing){.type=SITH_THING_PLAYER,.actorParams={100,100,0,&player},.sector=&world};otherPlayer=player;
 sithPlayer_g_pLocalPlayerThing=&player;sithWorld_g_pCurrentWorld=&world;
 sithNet_isMulti=Main_bMotsCompat=sithMain_bEndLevel=g_sithMode=g_submodeFlags=jkRpg_bMenuOpen=sithGamesave_state=0;
 attempts=messages=0;saveResult=1;jkRpg_autosaveMinutes=1;jkRpg_ResetAutosave();tick(0);
}
static void block(int why,int enabled) {
 switch(why) {
 case 0:sithMain_bEndLevel=enabled;break;
 case 1:g_sithMode=enabled?2:0;break;
 case 2:g_submodeFlags=enabled;break;
 case 3:jkRpg_bMenuOpen=enabled;break;
 case 4:sithGamesave_state=enabled;break;
 case 5:player.flags=enabled?SITH_TF_DEAD:0;break;
 case 6:player.flags=enabled?SITH_TF_DESTROYED:0;break;
 case 7:player.flags=enabled?SITH_TF_DISABLED:0;break;
 case 8:player.actorParams.flags=enabled?SITH_AF_CONTROLSDISABLED:0;break;
 case 9:player.actorParams.health=enabled?0:100;break;
 case 10:player.sector=enabled?NULL:&world;break;
 }
}
int main(void) {
 jkRpg_autosaveMinutes=-1;assert(jkRpg_GetAutosaveMinutes()==5);int reads=registryReads;
 assert(jkRpg_GetAutosaveMinutes()==5 && registryReads==reads);
 registryValue=-1;jkRpg_autosaveMinutes=-1;assert(jkRpg_GetAutosaveMinutes()==0);
 registryValue=99;jkRpg_autosaveMinutes=-1;assert(jkRpg_GetAutosaveMinutes()==15);
 fresh();jkRpg_SetAutosaveMinutes(-1);tick(10000);assert(!attempts && !jkRpg_autosaveWorld);
 jkRpg_SetAutosaveMinutes(99);tick(10000);tick(10899.5);assert(!attempts);tick(10900);assert(attempts==1);
 fresh();tick(59);jkRpg_SetAutosaveMinutes(1);tick(60);assert(attempts==1);
 fresh();tick(59);jkRpg_SetAutosaveMinutes(2);tick(60);tick(179.5);assert(!attempts);tick(180);assert(attempts==1);
 // Fifteen minutes without new pickups/kills/areas must yield fifteen saves, not one stale checkpoint.
 fresh();for(int second=1;second<=900;second++) {tick(second);assert(attempts==second/60);}
 // Damage, healing, low health and swimming must not silently postpone the selected interval.
 fresh();player.flags=SITH_TF_WATER;
 for(int second=1;second<=900;second++) {
  player.actorParams.health=1+second%24;tick(second);assert(attempts==second/60);
 }
 for(int reason=0;reason<11;reason++) {
  fresh();block(reason,1);tick(60);tick(900);assert(!attempts);
  block(reason,0);tick(901);assert(attempts==1);tick(960.9);assert(attempts==1);tick(961);assert(attempts==2);
 }
 for(int mode=0;mode<2;mode++) {
  fresh();if(mode)Main_bMotsCompat=1;else sithNet_isMulti=1;
  tick(60);tick(120);assert(!attempts && !jkRpg_autosaveWorld);
  Main_bMotsCompat=sithNet_isMulti=0;tick(121);tick(180.9);assert(!attempts);tick(181);assert(attempts==1);
 }
 for(int reason=0;reason<4;reason++) {
  fresh();tick(59);
  if(reason==0)sithWorld_g_pCurrentWorld=&otherWorld;
  if(reason==1)sithPlayer_g_pLocalPlayerThing=&otherPlayer;
  if(reason==2)jkRpg_OnRestoreStart();
  double start=reason==3?10:60;tick(start);tick(start+59.9);assert(!attempts);tick(start+60);assert(attempts==1);
 }
 fresh();sithWorld_g_pCurrentWorld=NULL;tick(60);assert(!attempts);
 sithWorld_g_pCurrentWorld=&world;sithPlayer_g_pLocalPlayerThing=NULL;tick(61);assert(!attempts);
 fresh();saveResult=0;tick(60);assert(attempts==1 && messages==1);
 tick(89.9);assert(attempts==1);saveResult=1;tick(90);assert(attempts==2 && messages==2);
 tick(149.9);assert(attempts==2);tick(150);assert(attempts==3);
 sithPlayer_g_pLocalPlayerThing=NULL;sessionResets=0;
 jkPlayer_playerInfos[0].aItems[RPG_BIN_CROWDS].amount=3;jkRpg_OnRestoreStart();
 assert(!jkPlayer_playerInfos[0].aItems[RPG_BIN_CROWDS].amount && sessionResets==1 && jkRpg_bRestoring && jkRpg_bWorldFromSave);
 puts("Autosave honors fifteen consecutive deadlines, gameplay changes, suspended states, restore, settings and write retries");
}
'''
scratch=Path(os.environ.get("JK_SCRATCH",tempfile.gettempdir()))/"jk-rpg-autosave-check"
scratch.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(dir=scratch) as work:
    cfile,binary=Path(work)/"check.c",Path(work)/"check"
    cfile.write_text(code)
    subprocess.run(["cc","-std=gnu99",str(cfile),"-o",str(binary)],check=True)
    subprocess.run([str(binary)],check=True)
