"""Compile actual death-save selection/queue/fallback and explicit quickload routing.

Death reloads the save last made or loaded; an autosave is used only while it is that save."""
import os
import tempfile
import subprocess
import sys
from pathlib import Path

src = Path(sys.argv[1]) / "src"
source = (src / "Dss/sithGamesave.c").read_text()
control = (src / "Main/jkControl.c").read_text()
player = (src / "Gameplay/sithPlayer.c").read_text()

def function(text, name):
    start = text.index(name)
    return text[start:text.index("\n}\n", start) + 3]

code = r'''
#include <assert.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <strings.h>
#include <stdlib.h>
#include <uchar.h>
#include <sys/stat.h>
#include <utime.h>
#include <math.h>
#define _strncpy strncpy
#define __strcmpi strcasecmp
#define stdString_snprintf snprintf
#define LEC_PATH_SEPARATOR_CHR '/'
typedef FILE* stdFile_t;
typedef struct {int32_t version;char episodeName[128],jklName[128];float playerHealth,playerMaxHealth;
 float binAmts[200];char16_t saveName[256];} sithGamesave_Header;
typedef struct {char episodeName[128],map_jkl_fname[128];} SithWorld;
static SithWorld world={"jk1","01narshadda.jkl"},*sithWorld_g_pCurrentWorld=&world;
static char16_t jkPlayer_playerShortName[32]=u"test";
static int sithNet_isMulti,Main_bMotsCompat,sithGamesave_dword_835914,sithGamesave_state;
enum {SITH_GS_LOAD=2,SITH_GS_LOAD_DEBUG_NEXTCHECKPOINT=3};
static char sithGamesave_autosave_fname[128],sithGamesave_aCurFilename[128];
static char sithGamesave_restartFallback[2][128],sithGamesave_preAutosave[128];
static int loads,failures,notices,quickSame,quickOther;
static char attempts[4][128];
static FILE* config;
static int sithGamesave_RestoreFile(char* path) {
 assert(loads<4);snprintf(attempts[loads++],128,"%s",path);
 // Real loader failure can close the world. Fallback must not consult it.
 if (failures) {failures--;sithWorld_g_pCurrentWorld=NULL;return 0;}
 return 1;
}
static int stdConffile_OpenReadBytesBypass(char* path) {config=fopen(path,"rb");return config!=NULL;}
static void stdConffile_Close(void) {fclose(config);config=NULL;}
static void stdString_WcharToChar(char* out,const char16_t* in,int n) {int i=0;for(;i<n&&in[i];i++)out[i]=(char)in[i];out[i]=0;}
static void stdString_SafeStrCopy(char* out,const char* in,int n) {snprintf(out,n,"%s",in);}
static void stdFnames_ChangeExt(char* path,const char* ext) {char* dot=strrchr(path,'.');assert(dot);strcpy(dot+1,ext);}
static size_t readFile(FILE* f,void* out,size_t len) {return fread(out,1,len,f);}
static struct {FILE*(*fileOpen)(const char*,const char*);size_t(*fileRead)(FILE*,void*,size_t);int(*fileClose)(FILE*);}
 services={fopen,readFile,fclose},*pLowLevelHS=&services;
static void sithConsole_PrintString(const char* s) {notices++;}
static void jkPlayer_LoadSave(char* s) {assert(!strcmp(s,"quicksave.jks"));quickSame++;}
static void jkMain_sub_4034D0(char* ep,char* s,char* map,char16_t* name) {assert(!strcmp(s,"quicksave.jks"));quickOther++;}
static char16_t* __wcschr(char16_t* s,char32_t c) {while(*s&&*s!=c)s++;return *s?s:NULL;}
'''
for name in ["int sithGamesave_GetProfilePath(", "const char* sithGamesave_AutosaveMapName(",
             "int sithGamesave_Restore(", "static int sithGamesave_CanRestartAutosave(",
             "static int sithGamesave_IsSameMapSave(", "int sithGamesave_Restart(", "static int sithGamesave_RestorePending("]:
    code += function(source, name)
code += function(control, "static void jkControl_QuickLoad(")
code += r'''
static sithGamesave_Header header;
static const char* autoPath="player/test/autosave.jks";
static const char* checkpointPath="player/test/_JKAUTO_01narshadda.jks";
static void save(const char* path,int full,time_t when) {
 FILE* f=fopen(path,"wb");assert(f);fwrite(&header,1,full?sizeof(header):7,f);
 if(full)fputs("WORLD",f);fclose(f);struct utimbuf times={when,when};assert(!utime(path,&times));
}
static void reset(void) {
 memset(&header,0,sizeof(header));header.version=6;strcpy(header.episodeName,"jk1");strcpy(header.jklName,"01narshadda.jkl");
 header.playerHealth=80;header.playerMaxHealth=100;
 sithWorld_g_pCurrentWorld=&world;sithNet_isMulti=Main_bMotsCompat=loads=failures=notices=quickSame=quickOther=0;
 memset(sithGamesave_restartFallback,0,sizeof(sithGamesave_restartFallback));
 strcpy(sithGamesave_autosave_fname,"autosave.jks");strcpy(sithGamesave_preAutosave,"quicksave.jks");
 save(checkpointPath,1,100);save("player/test/quicksave.jks",1,150);save(autoPath,1,200);
}
static void choice(const char* basename) {
 assert(sithGamesave_Restart());char expected[128];snprintf(expected,128,"player/test/%s",basename);
 assert(!strcmp(sithGamesave_aCurFilename,expected));assert(sithGamesave_state==SITH_GS_LOAD);
}
int main(void) {
 reset();choice("autosave.jks");assert(sithGamesave_RestorePending());assert(loads==1&&!strcmp(attempts[0],autoPath));
 reset();failures=1;choice("autosave.jks");assert(sithGamesave_RestorePending());assert(loads==2&&!strcmp(attempts[1],"player/test/quicksave.jks"));
 reset();failures=2;choice("autosave.jks");assert(sithGamesave_RestorePending());assert(loads==3&&!strcmp(attempts[2],checkpointPath));
 reset();failures=3;choice("autosave.jks");assert(!sithGamesave_RestorePending());assert(loads==3);
 reset();sithGamesave_preAutosave[0]=0;failures=1;choice("autosave.jks");assert(sithGamesave_RestorePending());assert(loads==2&&!strcmp(attempts[1],checkpointPath));
 // The save before the autosave is a fallback only on this map: never a mid-frame load of another level.
 reset();strcpy(header.jklName,"02another.jkl");save("player/test/quicksave.jks",1,150);failures=1;choice("autosave.jks");
 assert(sithGamesave_RestorePending());assert(loads==2&&!strcmp(attempts[1],checkpointPath));
 reset();remove(autoPath);choice("quicksave.jks");
 reset();save(autoPath,0,200);choice("quicksave.jks");
 reset();header.version=17;save(autoPath,1,200);choice("quicksave.jks");
 reset();header.playerHealth=0;save(autoPath,1,200);choice("quicksave.jks");
 reset();header.playerHealth=NAN;save(autoPath,1,200);choice("quicksave.jks");
 reset();header.playerHealth=header.playerMaxHealth=INFINITY;save(autoPath,1,200);choice("quicksave.jks");
 reset();header.playerHealth=101;save(autoPath,1,200);choice("quicksave.jks");
 reset();strcpy(header.episodeName,"other");save(autoPath,1,200);choice("quicksave.jks");
 reset();strcpy(header.jklName,"02another.jkl");save(autoPath,1,200);choice("quicksave.jks");
 reset();memset(header.episodeName,'x',sizeof(header.episodeName));save(autoPath,1,200);choice("quicksave.jks");
 reset();save(checkpointPath,1,300);choice("quicksave.jks"); // New playthrough on same map.
 reset();sithGamesave_preAutosave[0]=0;save(checkpointPath,1,300);choice("_JKAUTO_01narshadda.jks");
 // A quicksave loaded (even an older one) or made after the autosave is the restart point:
 // dying never jumps ahead to the autosave's progress, and falls back to the level start.
 reset();strcpy(sithGamesave_autosave_fname,"quicksave.jks");save("player/test/quicksave.jks",1,50);choice("quicksave.jks");
 assert(!sithGamesave_restartFallback[0][0]&&!sithGamesave_restartFallback[1][0]);
 reset();strcpy(sithGamesave_autosave_fname,"quicksave.jks");save("player/test/quicksave.jks",1,250);choice("quicksave.jks");
 reset();strcpy(sithGamesave_autosave_fname,"quicksave.jks");remove("player/test/quicksave.jks");choice("_JKAUTO_01narshadda.jks");
 reset();strcpy(sithGamesave_autosave_fname,"_JKAUTO_01narshadda.jks");choice("_JKAUTO_01narshadda.jks");
 reset();sithNet_isMulti=1;choice("quicksave.jks");
 reset();Main_bMotsCompat=1;choice("quicksave.jks");
 reset();remove(autoPath);remove("player/test/quicksave.jks");choice("_JKAUTO_01narshadda.jks");
 reset();choice("autosave.jks");assert(sithGamesave_restartFallback[1][0]);
 assert(sithGamesave_Restore("quicksave.jks",0,0));assert(!sithGamesave_restartFallback[1][0]);
 failures=1;assert(!sithGamesave_RestorePending());assert(loads==1); // Manual failure cannot inherit death fallback.
 reset();jkControl_QuickLoad();assert(quickSame==1&&!quickOther);
 strcpy(header.jklName,"02another.jkl");save("player/test/quicksave.jks",1,150);jkControl_QuickLoad();assert(quickOther==1);
 remove("player/test/quicksave.jks");jkControl_QuickLoad();assert(notices==1);
 reset();jkPlayer_playerShortName[0]='x';assert(!sithGamesave_Restart());jkPlayer_playerShortName[0]='t';
 puts("Death restart: current profile/episode/map, living save, new-run fence, queued fallback failures and explicit F9 passed");
}
'''
assert "sithGamesave_Restart();" in function(player, "void sithPlayer_debug_loadauto(")
assert "sithGamesave_RestorePending()" in function(source, "int sithGamesave_Process(")
autosave = function(source, "int sithGamesave_Autosave(")
published = autosave[autosave.index("if (!published) remove(temporary);"):]
assert published.index("memcpy(sithGamesave_preAutosave, restart") < published.index('"autosave.jks", sizeof(sithGamesave_autosave_fname)')
assert 'if (__strcmpi(restart, "autosave.jks"))' in published  # a second autosave keeps the save before the first
assert "jkControl_QuickLoad();" in control
scratch = Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-death-restart"
(scratch / "player/test").mkdir(parents=True, exist_ok=True)
cfile, binary = scratch / "restart.c", scratch / "restart"
try:
    cfile.write_text(code)
    subprocess.run(["cc", "-std=gnu11", str(cfile), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], cwd=scratch, check=True)
finally:
    for name in ("autosave.jks", "quicksave.jks", "_JKAUTO_01narshadda.jks"):
        (scratch / "player/test" / name).unlink(missing_ok=True)
    cfile.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)
