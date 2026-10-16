"""Exercise actual staged autosave, serializer dispatch and write/close tracking."""
import os
import tempfile
import subprocess
import sys
from pathlib import Path
src = Path(sys.argv[1]) / "src"
save = (src / "Dss/sithGamesave.c").read_text()
conf = (src / "General/stdConffile.c").read_text()
comm = (src / "Devices/sithComm.c").read_text()
def function(text, name):
    start = text.index(name)
    return text[start:text.index("\n}\n", start)+3]
code = r"""
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <stdint.h>
#include <string.h>
#include <uchar.h>
#include <unistd.h>
typedef FILE* stdFile_t;
#define _memset memset
#define _strncpy strncpy
#define __strcmpi strcasecmp
#include <strings.h>
#define _strlen strlen
#define __vsnprintf vsnprintf
#define STDCONF_LINEBUFFER_LEN 256
#define COMPAT_SAVE_VERSION 6
#define LEC_PATH_SEPARATOR_CHR '/'
enum {SITH_GS_NONE=0,SITH_GS_SAVE=1,SITH_GS_LOAD=2,SITH_GS_LOAD_DEBUG_NEXTCHECKPOINT=3,SITH_TF_DEAD=512};
typedef struct {float amount;} SithInventoryItem;
typedef float flex32_t;
typedef struct {unsigned flags;struct {float health,maxHealth;} actorParams;} SithThing;
typedef struct {char episodeName[128],map_jkl_fname[128];} SithWorld;
typedef struct {int version;char episodeName[128],jklName[128];float playerHealth,playerMaxHealth;
    float binAmts[2];char16_t saveName[256];} sithGamesave_Header;
static struct {SithInventoryItem aItems[2];} playerItems,*sithPlayer_g_pLocalPlayer=&playerItems;
static SithThing player={.actorParams={100,100}},*sithPlayer_g_pLocalPlayerThing=&player;
static SithWorld world={"jk1","01narshadda.jkl"},*sithWorld_g_pCurrentWorld=&world;
static int sithGamesave_state,sithGamesave_dword_835914,sithComm_version;
static char16_t jkPlayer_playerShortName[32]=u"test",sithGamesave_wsaveName[256];
static char sithGamesave_aCurFilename[256],sithGamesave_autosave_fname[128],sithGamesave_saveName[128],sithGamesave_preAutosave[128];
static sithGamesave_Header sithGamesave_headerTmp;
static int sithMessage_g_outputstream=17,g_sithMode=1,g_submodeFlags,sithSurface_byte_8EE668;
static int g_debugmodeFlags,jkPlayer_setDiff,g_mapModeFlags,sithNet_isMulti,Main_bMotsCompat;
static uint32_t sithTime_g_msecGameTime=1000;
static int sithGamesave_lastWriteSucceeded,stdConffile_writeFailed,stdConffile_writeSucceeded;
static stdFile_t writeFile;
static char stdConffile_aWriteFilename[128],printfBuffer[256];
static int failOpen,failWrite,failClose,failRename,writes,renames;
static FILE* openHook(const char* path,const char* mode) {return failOpen?NULL:fopen(path,mode);}
static size_t writeHook(FILE* file,void* data,size_t size) {
    writes++;if(writes==failWrite) {if(size) fwrite(data,1,size-1,file);return size?size-1:0;}
    return fwrite(data,1,size,file);
}
static int closeHook(FILE* file) {int result=fclose(file);return failClose?-1:result;}
static struct HostServices {FILE*(*fileOpen)(const char*,const char*);size_t(*fileWrite)(FILE*,void*,size_t);int(*fileClose)(FILE*);}
    services={openHook,writeHook,closeHook},*pLowLevelHS=&services,*stdConffile_pHS=&services;
static void stdString_SafeStrCopy(char* out,const char* text,size_t n) {snprintf(out,n,"%s",text);}
static void stdString_WcharToChar(char* out,const char16_t* in,int n) {int i=0;for(;i<n && in[i];i++)out[i]=(char)in[i];out[i]=0;}
static void stdString_CharToWchar(char16_t* out,const char* in,int n) {int i=0;for(;i<n && in[i];i++)out[i]=in[i];out[i]=0;}
static char16_t* _wcsncpy(char16_t* out,const char16_t* in,size_t n) {size_t i=0;for(;i<n && in[i];i++)out[i]=in[i];for(;i<n;i++)out[i]=0;return out;}
static int stdString_snprintf(char* out,size_t n,const char* fmt,...) {va_list ap;va_start(ap,fmt);int result=vsnprintf(out,n,fmt,ap);va_end(ap);return result;}
static int jkCog_strings;
static char16_t* jkGuiTitle_quicksave_related_func1(int* strings,const char* map) {return u"Nar Shaddaa";}
static void jk_snwprintf(char16_t* out,size_t n,const char16_t* fmt,const char16_t* title) {
    const char16_t required[]=u"%s~Autosave";assert(!memcmp(fmt,required,sizeof(required)));
    size_t i=0;while(title[i] && i+1<n) {out[i]=title[i];i++;}
    const char16_t* suffix=u"~Autosave";for(size_t j=0;suffix[j] && i+1<n;j++)out[i++]=suffix[j];out[i]=0;
}
static int stdFileUtil_MkDir(const char* p) {return 1;}
static int stdConffile_OpenReadBypass(char* p) {return 0;}
static void stdConffile_Close(void) {}
static const char* stdFnames_FindMedName(const char* p) {const char* slash=strrchr(p,'/');return slash?slash+1:p;}
static int sithGamesave_RestoreFile(char* p) {assert(0);return 0;}
static int sithGamesave_RestorePending(void) {assert(0);return 0;}
static void sithPlayer_NewPlayer(SithThing* p) {assert(0);}
static void sithMain_set_sithmode_5(void) {assert(0);}
static const char16_t* sithStrTable_GetUniStringWithFallback(const char* s) {return u"Saved";}
static void sithConsole_PrintWString(const char16_t* s) {}
static int publishHook(const char* a,const char* b) {renames++;return failRename?-1:rename(a,b);}
#define MOVEFILE_REPLACE_EXISTING 1
static int MoveFileExA(const char* a,const char* b,int flags) {assert(flags==MOVEFILE_REPLACE_EXISTING);return publishHook(a,b)==0;}
"""
for name in ["int stdConffile_OpenWrite(","void stdConffile_CloseWrite(","int stdConffile_DidWriteSucceed(","int stdConffile_Write(","int stdConffile_Printf("]:
    code += function(conf,name)
code += r"""
typedef struct {struct {int cogMsgId,msg_size;} netMsg;char pktData[5];} SithMessage;
static int sithComm_009a1160;
""" + function(comm,"void sithMessage_FileWrite(")
code += r"""
static int stdConffile_OpenWriteBypass(const char* p) {return stdConffile_OpenWrite(p);}
// Stand in for world enumeration, retaining the actual DSS packet writer.
static int sithGamesave_SaveCurrentWorld(int flags) {
    assert(flags==4);SithMessage msg={{7,5},{'W','O','R','L','D'}};sithMessage_FileWrite(&msg);return 1;
}
static void writeCallback(void) {stdConffile_Write("EXTRA",5);}
static void finishCallback(void) {stdConffile_Printf("%s","TAIL");}
static void (*sithGamesave_funcWrite)(void)=writeCallback;
static void (*sithGamesave_func1)(void)=finishCallback;
"""
code += "\n#define rename publishHook\n"
for name in ["int sithGamesave_GetProfilePath(","int sithGamesave_Save(","int sithGamesave_Process("]:
    code += function(save,name)
code += "\n#define rename publishHook\n" + function(save,"int sithGamesave_Autosave(") + "\n#undef rename\n"
code += r"""
static void contents(const char* name,const char* text) {FILE* f=fopen(name,"wb");assert(f);assert(fwrite(text,1,strlen(text),f)==strlen(text));assert(!fclose(f));}
static void exact(const char* name,const char* expected) {char b[32]={0};FILE* f=fopen(name,"rb");assert(f);size_t n=fread(b,1,sizeof(b),f);fclose(f);assert(n==strlen(expected) && !memcmp(b,expected,n));}
static void reset(void) {
    failOpen=failWrite=failClose=failRename=writes=renames=0;
    sithGamesave_state=SITH_GS_NONE;g_submodeFlags=0;player.flags=0;
    strcpy(sithGamesave_autosave_fname,"_JKAUTO_01narshadda.jks");sithGamesave_preAutosave[0]=0;
    strcpy(sithGamesave_aCurFilename,"prior-manual.jks");
    contents("player/test/autosave.jks","LAST_GOOD");
    contents("player/test/quicksave.jks","MANUAL");
    contents("player/test/_JKAUTO_01narshadda.jks","LEVEL_START");
}
// A published autosave becomes the restart save, remembering the save before it; a failed one changes neither.
static void restartNames(int published) {
    assert(!strcmp(sithGamesave_autosave_fname,published?"autosave.jks":"_JKAUTO_01narshadda.jks"));
    assert(!strcmp(sithGamesave_preAutosave,published?"_JKAUTO_01narshadda.jks":""));
}
static void preserved(void) {
    exact("player/test/quicksave.jks","MANUAL");exact("player/test/_JKAUTO_01narshadda.jks","LEVEL_START");
    assert(!strcmp(sithGamesave_aCurFilename,"prior-manual.jks"));
    assert(sithMessage_g_outputstream==17 && !writeFile && access("player/test/autosave.tmp",F_OK));
}
int main(void) {
    reset();assert(sithGamesave_Autosave()==1);assert(renames==2);preserved();restartNames(1);
    int totalWrites=writes;assert(totalWrites>=12);
    assert(sithGamesave_Autosave()==1);restartNames(1); // a second autosave keeps the save before the first
    FILE* f=fopen("player/test/autosave.jks","rb");assert(f);
    sithGamesave_Header header;assert(fread(&header,1,sizeof(header),f)==sizeof(header));
    assert(header.version==COMPAT_SAVE_VERSION && header.playerHealth==100);
    assert(!strcmp(header.jklName,"01narshadda.jkl"));
    const char16_t expected[]=u"Nar Shaddaa~Autosave";
    assert(!memcmp(header.saveName,expected,sizeof(expected)));fclose(f);
    // A failure at every header, callback, world and trailing write retains last good.
    for(int i=1;i<=totalWrites;i++) {
        reset();failWrite=i;assert(!sithGamesave_Autosave());assert(!renames);
        exact("player/test/autosave.jks","LAST_GOOD");preserved();restartNames(0);
    }
    for(int failure=0;failure<3;failure++) {
        reset();failOpen=failure==0;failClose=failure==1;failRename=failure==2;
        assert(!sithGamesave_Autosave());exact("player/test/autosave.jks","LAST_GOOD");preserved();restartNames(0);
    }
    reset();failWrite=1;assert(!sithGamesave_Autosave());failWrite=0;writes=0;
    assert(sithGamesave_Autosave());preserved();restartNames(1); // error tracking resets for retry
    for(int blocked=0;blocked<5;blocked++) {
        reset();if(blocked==0)sithGamesave_state=SITH_GS_LOAD;
        if(blocked==1)g_submodeFlags=1;if(blocked==2)player.flags=SITH_TF_DEAD;
        if(blocked==3)sithNet_isMulti=1;if(blocked==4)Main_bMotsCompat=1;
        assert(!sithGamesave_Autosave() && !writes && !renames);
        exact("player/test/autosave.jks","LAST_GOOD");preserved();
        sithNet_isMulti=Main_bMotsCompat=0;
    }
    // Every failed manual save preserves its previous file and restart selection.
    for(int failure=0;failure<4;failure++) {
        reset();assert(sithGamesave_Save("quicksave.jks",1,0,u"Quick"));
        failOpen=failure==0;failWrite=failure==1?1:0;failClose=failure==2;failRename=failure==3;
        sithGamesave_Process();assert(!sithGamesave_lastWriteSucceeded);
        exact("player/test/quicksave.jks","MANUAL");restartNames(0);
        assert(access("player/test/quicksave.jks.tmp",F_OK));
    }
    // Preserve the old manual-save behavior and restart selection.
    reset();assert(sithGamesave_Save("quicksave.jks",1,0,u"Quick"));sithGamesave_Process();
    assert(!strcmp(sithGamesave_autosave_fname,"quicksave.jks"));
    puts("Autosave writer: complete publish, every short write, open/close/rename failure, retry, restart save naming and manual slots passed");
}
"""
scratch=Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-autosave-write"
(scratch/"player/test").mkdir(parents=True,exist_ok=True)
cfile,binary=scratch/"writer.c",scratch/"writer"
try:
    cfile.write_text(code)
    for flags in ([],["-DWIN32"]):
        subprocess.run(["cc","-std=gnu11",*flags,str(cfile),"-o",str(binary)],check=True)
        subprocess.run([str(binary)],cwd=scratch,check=True)
finally:
    for name in ("autosave.jks","autosave.tmp","quicksave.jks","_JKAUTO_01narshadda.jks","autosave.tmp.tmp","quicksave.jks.tmp"):
        (scratch/"player/test"/name).unlink(missing_ok=True)
    cfile.unlink(missing_ok=True);binary.unlink(missing_ok=True)
