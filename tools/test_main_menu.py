"""Exercise direct single-player routing with the real loop and stubbed episode pickers."""
import os,re,subprocess,sys,tempfile
from pathlib import Path
root=Path(sys.argv[1])/"src"
s=(root/"Gui/jkGUISingleplayer.c").read_text()
start=s.index("int jkGuiSingleplayer_ShowAction(")
s=s[start:s.index("\n}",start)+2]
# Episode setup/debug loading are unchanged; test routing and cancellation around them.
a=s.index("    const char")
b=s.index("    jkGuiRend_MenuSetReturn",a)
s=s[:a]+s[b:]
a=s.index("                case JKGUI_NEWGAME:")
b=s.index("                case JKGUI_LOAD:",a)
s=s[:a]+"                case JKGUI_NEWGAME: clicked=episode_result; ++new_calls; break;\n"+s[b:]
a=s.index("                case JKGUI_DEBUGPLAY:")
b=s.index("\n            }\n            if ( clicked <",a)
s=s[:a]+"                case JKGUI_DEBUGPLAY: clicked=-1; break;"+s[b:]
h=r'''
#include <assert.h>
enum {JKGUI_NEWGAME=100,JKGUI_LOAD=101,JKGUI_DEBUGPLAY=102};
static int jkGuiSingleplayer_menu1,jkGuiSingleplayer_buttons1[7];
static int hub_calls,load_calls,new_calls,load_result,episode_result,hub_result;
#define jkGuiRend_MenuSetReturnKeyShortcutElement(a,b) ((void)0)
#define jkGuiRend_MenuSetEscapeKeyShortcutElement(a,b) ((void)0)
#define jkGui_sub_412E20(a,b,c,d) ((void)0)
#define jkGuiRend_Paint(a) ((void)0)
#define jkGuiRend_UpdateSurface() ((void)0)
static int jkGuiRend_DisplayAndReturnClicked(void* m){++hub_calls;assert(hub_calls<3);return hub_result;}
static int jkGuiSaveLoad_Show(int x){++load_calls;return load_result;}
'''
t=r'''
int main(void){
 hub_result=-1;
 load_result=-1;assert(jkGuiSingleplayer_ShowAction(JKGUI_LOAD)==-1);
 assert(hub_calls==0 && load_calls==1);
 load_result=34;assert(jkGuiSingleplayer_ShowAction(JKGUI_LOAD)==1);
 load_result=1;assert(jkGuiSingleplayer_ShowAction(JKGUI_LOAD)==1);
 episode_result=-1;assert(jkGuiSingleplayer_ShowAction(JKGUI_NEWGAME)==-1);
 episode_result=1;assert(jkGuiSingleplayer_ShowAction(JKGUI_NEWGAME)==1);
 assert(hub_calls==0 && new_calls==2 && load_calls==3);
 assert(jkGuiSingleplayer_ShowAction(0)==-1 && hub_calls==1);
}
'''
scratch=Path(os.environ.get("JK_SCRATCH","/mnt/d/Dev/helm/temp/rekindled-menu-sky"));scratch.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(dir=scratch) as d:
 c=Path(d)/"menu.c";exe=Path(d)/"menu";c.write_text(h+s+t)
 subprocess.run(["cc",str(c),"-o",str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
print("Direct new/load, cancellation, successful restore and legacy hub passed")
