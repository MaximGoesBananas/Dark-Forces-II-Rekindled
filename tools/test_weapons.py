"""Compile the actual weapon reminder: ownership, bindings, timing and narrow screens.
Run in WSL: python3 tools/test_weapons.py ~/src/OpenJKDF2
"""
import os
import tempfile
import re
import subprocess
import sys
from pathlib import Path

source = (Path(sys.argv[1]) / "src/Main/jkRpg.c").read_text()
start = source.index("static void jkRpg_DrawWeapons(")
function = source[start:source.index("\n}", start) + 2]
settings = source[source.index("static int jkRpg_weaponSwitcher"):start]
setup = (Path(sys.argv[1]) / "src/Gui/jkGUISetup.c").read_text()
elements = setup.split("static jkGuiElement jkGuiSetup_aRpgElements[] = {", 1)[1].split("\n};", 1)[0]
hint = re.search(r'\{ELEMENT_TEXT, 0, 0, 0, 3, \{([^}]+)\}, (\d+)', elements)
height = re.search(r'#define RPGSETUP_CHECK.*?\{x, y, 270, (\d+)\}', setup).group(1)
slider_offset, slider_width, slider_height = map(int, re.search(
    r"#define RPGSETUP_SLIDER.*?\{x - (\d+), y, (\d+), (\d+)\}", setup).groups())
sliders = re.findall(r"RPGSETUP_SLIDER\([^,]+, (\d+), (\d+)\)", elements)
boxes = re.findall(r'RPGSETUP_CHECK\("[^"]+", (\d+), (\d+)\)', elements)
layout = "static jkGuiElement layout[]={" + f"{{1,{hint[2]},{{{hint[1]}}}}}," + "".join(
    f"{{1,1,{{{x},{y},270,{height}}}}}," for x,y in boxes) + "".join(
    f"{{1,1,{{{int(x)-slider_offset},{y},{slider_width},{slider_height}}}}}," for x,y in sliders) + "{0}};\n"
render = (Path(sys.argv[1]) / "src/Gui/jkGUIRend.c").read_text()
hint_index = re.search(r'jkGuiSetup_rpgMenu = \{jkGuiSetup_aRpgElements, (-?\d+)', setup).group(1)
hint_start = render.index("void jkGuiRend_UpdateDrawMenu(")
hint_update = render[hint_start:render.index("\n}", hint_start)+2]
hit_start = render.index("void jkGuiRend_MouseMovedCallback(")
hit_test = render[hit_start:render.index("\n}", hit_start)+2]
harness = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define stdString_snprintf snprintf
enum { ELEMENT_END=0 };
typedef struct {int x,y,width,height;} rdRect;
typedef struct {int type,bIsVisible;rdRect rect; const char* hintText; const char* str; int enableHover;} jkGuiElement;
typedef struct {jkGuiElement* lastMouseOverClickable; jkGuiElement* paElements; int clickableIdxIdk;} jkGuiMenu;
static int g_app_suspended=1, jkGuiRend_bIsSurfaceValid, hintRedraws;
static void jkGuiRend_UpdateAndDrawClickable(jkGuiElement* e,jkGuiMenu* menu,int redraw) {hintRedraws++;}
static void jkGuiRend_ClickableMouseover(jkGuiMenu* menu,jkGuiElement* e) {menu->lastMouseOverClickable=e;}
typedef float flex_t;
typedef int SithThing;
typedef int stdFont;
enum { INPUT_FUNC_SELECT1=13, INPUT_FUNC_SELECT0=22, SITHBIN_LIGHTSABER=10, UP_WEAPON0=9 };
static struct { int width,height; } Video_format={640,480};
static uint32_t sithTime_g_msecGameTime=10000;
static int weapon=2, available[11]={0,1,1}, amount[16]={0,1,1};
static const int jkRpg_aAmmoBin[11]={0,0,11,11,4,12,12,15,8,12,0};
static int bindingIds[16], sharedUnbound;
static int cells, highlights, icons, labels, bindingCalls, rebound, ammoLabels, unlimited, melee;
static int savedSetting=-1, settingReads;
static int wuRegistry_GetInt(const char* name,int fallback) {
    assert(!strcmp(name,"rpgWeaponSwitcher"));settingReads++;
    return savedSetting<0 ? fallback : savedSetting;
}
static void wuRegistry_SaveInt(const char* name,int value) {
    assert(!strcmp(name,"rpgWeaponSwitcher"));savedSetting=value;
}
static int sithInventory_GetCurrentWeapon(SithThing* p) {return weapon;}
static int sithInventory_IsInventoryAvailable(SithThing* p,int b) {return available[b];}
static int sithInventory_GetInventory(SithThing* p,int b) {return amount[b];}
static int stdFont_GetHeight(stdFont* f) {return 12;}
static void jkRpg_Rect(int x,int y,int w,int h,int r,int g,int b,int a) {
    assert(x>=0 && x+w<=Video_format.width && y>=0 && y+h<Video_format.height/3);
    if(a==190) cells++; else highlights++;
}
static void jkRpg_DrawWeaponIcon(int bin,int x,int y,int w,int h) {assert(bin>=1 && bin<=10);icons++;}
static const char* jkRpg_BindingName(int f) {
    assert(f>=13 && f<=22 && bindingCalls<16);bindingIds[bindingCalls++]=f;
    if(rebound==2 || (sharedUnbound && f==INPUT_FUNC_SELECT1)) return NULL;
    return rebound ? "Mouse Button 4" : "2";
}
static int jkRpg_TextWidth(stdFont* f,flex_t s,const char* t) {return strlen(t)*8*s;}
static void jkRpg_Text(stdFont* f,int x,int y,flex_t s,const char* t) {
    assert(x>=0 && x+jkRpg_TextWidth(f,s,t)<=Video_format.width); labels++;
    if (!strcmp(t,"Unlimited")) unlimited++;
    if (!strcmp(t,"Melee")) melee++;
    if (!strcmp(t,"48") || !strcmp(t,"73") || !strcmp(t,"91")) ammoLabels++;
}
static void reset(void) {cells=highlights=icons=labels=bindingCalls=ammoLabels=unlimited=melee=0;}
'''
checks = r'''
int main(void) {
    int p=0,f=0;
    jkGuiMenu menu={0,layout,SETUP_HINT_INDEX};
    for(int i=1;layout[i].type!=ELEMENT_END;i++) {
        // Every slider and checkbox fits above the buttons without overlapping another control.
        rdRect r=layout[i].rect;
        assert(r.x>=0 && r.y>=0 && r.x+r.width<=640 && r.y+r.height<=430);
        for(int j=1;j<i;j++) {
            rdRect q=layout[j].rect;
            assert(r.x+r.width<=q.x || q.x+q.width<=r.x || r.y+r.height<=q.y || q.y+q.height<=r.y);
        }
        // Actual menu hit testing must reach each control, including the bottom row.
        jkGuiRend_MouseMovedCallback(&menu,layout[i].rect.x+8,layout[i].rect.y+8);
        assert(menu.lastMouseOverClickable==&layout[i]);
        jkGuiRend_UpdateDrawMenu(&menu);
    }
    assert(hintRedraws==0); // Hovering any setting must not clear the hidden bottom strip.
    menu.clickableIdxIdk=0;jkGuiRend_UpdateDrawMenu(&menu);assert(hintRedraws==1);
    assert(jkRpg_GetWeaponSwitcher()==1 && jkRpg_GetWeaponSwitcher()==1 && settingReads==1);
    jkRpg_DrawWeapons(&p,&f);assert(cells==2 && highlights==2 && icons==2 && labels==5 && bindingCalls==2);
    assert(unlimited==1 && melee==1);
    reset();sithTime_g_msecGameTime+=2200;jkRpg_DrawWeapons(&p,&f);assert(!cells && !labels);
    for(int i=1;i<=10;i++) available[i]=amount[i]=1;
    amount[11]=48;amount[12]=73;amount[15]=91;
    for(int i=1;i<=10;i++) {
        reset();weapon=i;rebound=i%3;sithTime_g_msecGameTime++;
        jkRpg_DrawWeapons(&p,&f);assert(cells==10 && highlights==2 && icons==10 && bindingCalls==(rebound==2?11:10));
        assert(bindingIds[0]==INPUT_FUNC_SELECT1 && bindingIds[9]==INPUT_FUNC_SELECT1);
        assert(ammoLabels==5 && unlimited==1 && melee==2);
    }
    reset();rebound=0;sharedUnbound=1;weapon=1;sithTime_g_msecGameTime++;
    jkRpg_DrawWeapons(&p,&f);assert(bindingCalls==11 && bindingIds[10]==INPUT_FUNC_SELECT0);
    sharedUnbound=0;
    jkRpg_SetWeaponSwitcher(0);assert(savedSetting==0);
    jkRpg_weaponSwitcher=-1;assert(jkRpg_GetWeaponSwitcher()==0); // Process restart.
    reset();weapon=5;sithTime_g_msecGameTime++;
    jkRpg_DrawWeapons(&p,&f);assert(!cells && !icons && !labels && weapon==5);
    jkRpg_SetWeaponSwitcher(1);assert(savedSetting==1);
    jkRpg_weaponSwitcher=-1;assert(jkRpg_GetWeaponSwitcher()==1);
    jkRpg_DrawWeapons(&p,&f);assert(cells==10 && icons==10);
    reset();weapon=1;Video_format.width=320;Video_format.height=240;
    jkRpg_DrawWeapons(&p,&f);assert(cells==10 && icons==10);
    reset();weapon=2;available[3]=0;amount[4]=0;
    jkRpg_DrawWeapons(&p,&f);assert(cells==8 && bindingCalls==8);
    reset();weapon=0;jkRpg_DrawWeapons(&p,&f);assert(!cells);
    puts("Weapon switcher default/persistence/on/off, icons/keys, timing and bounds passed");
}
'''
scratch = Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-weapons"
scratch.mkdir(parents=True, exist_ok=True)
cfile, binary = scratch / "check.c", scratch / "check"
try:
    cfile.write_text(harness + layout + hint_update + hit_test + settings + function + checks.replace("SETUP_HINT_INDEX", hint_index))
    subprocess.run(["cc", str(cfile), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
finally:
    cfile.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)
