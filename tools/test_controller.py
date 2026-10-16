"""Compile the controller bindings, look scaling and menu actions from the engine."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(sys.argv[1]) / "src"


def function(file, signature):
    source = (root / file).read_text()
    start = source.index(signature + "\n{")
    return source[start:source.index("\n}", start) + 2] + "\n"


code = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <math.h>
#include <string.h>
typedef double flex_t;
typedef double flex_d_t;
enum {INPUT_FUNC_TURN,INPUT_FUNC_PITCH,INPUT_FUNC_FORWARD,INPUT_FUNC_JUMP,
      INPUT_FUNC_USELASTSELECTED,INPUT_FUNC_USESKILL,INPUT_FUNC_USEINV,INPUT_FUNC_MAP,
      INPUT_FUNC_NEXTINV,INPUT_FUNC_PREVINV,INPUT_FUNC_USEBACTA,INPUT_FUNC_USEVISION,
      INPUT_FUNC_UPGRADEMENU,INPUT_FUNC_MAX};
enum {KEY_JOY1_B1=256,KEY_JOY1_B4,KEY_JOY1_B8,KEY_JOY1_HUP,KEY_JOY1_HDOWN,KEY_JOY1_B5};
enum {INPUT_MAPPING_FLAG_AXIS=1,INPUT_MAPPING_FLAG_DXKEY=2,
      INPUT_MAPPING_FLAG_AXIS_REVERSED=4,INPUT_MAPPING_FLAG_RAW_AXIS=8,AXIS_MOUSE_X=12,JK_EXTENDED_KEY_START=256};
#define KEY_IS_MOUSE(k) ((k)>=280 && (k)<288)
#define SITH_ASSERTREL assert
typedef struct {int flags;unsigned dxKeyNum;double binaryAxisVal;} stdControlKeyInfoEntry;
typedef struct {unsigned numEntries;stdControlKeyInfoEntry aEntries[8];} stdControlKeyInfo;
static stdControlKeyInfo sithControl_aInputFuncToKeyinfo[INPUT_FUNC_MAX];
static int Main_bMotsCompat,sithNet_isMulti,sithWeapon_controlOptions,inverted;
static double sensitivity=.04;
static double sithControl_GetMouseSensitivity(void){return sensitivity;}
static int sithControl_GetMouseInverted(void){return inverted;}
static double stdControl_ReadAxis(int key){return .5;}
static double stdControl_ReadKeyAsAxis(int key){return .25;}
static void sithControl_BindControl(int func,int key,int flags){
    for(int f=0;f<INPUT_FUNC_MAX;f++) {
        stdControlKeyInfo* info=&sithControl_aInputFuncToKeyinfo[f];
        for(unsigned j=0;j<info->numEntries;j++)
            if((info->aEntries[j].flags&2) && info->aEntries[j].dxKeyNum==key)
                info->aEntries[j--]=info->aEntries[--info->numEntries];
    }
    stdControlKeyInfo* info=&sithControl_aInputFuncToKeyinfo[func];
    info->aEntries[info->numEntries++]=(stdControlKeyInfoEntry){2,key,0};
}
static int assigned(int key){
    for(int f=0;f<INPUT_FUNC_MAX;f++) for(unsigned j=0;j<sithControl_aInputFuncToKeyinfo[f].numEntries;j++)
        if(sithControl_aInputFuncToKeyinfo[f].aEntries[j].dxKeyNum==key)return f;
    return -1;
}
enum {ELEMENT_TEXTBUTTON,ELEMENT_PICBUTTON,ELEMENT_TEXT,ELEMENT_CHECKBOX,ELEMENT_LISTBOX,
      ELEMENT_TEXTBOX,ELEMENT_SLIDER,ELEMENT_CUSTOM,ELEMENT_8,ELEMENT_END};
typedef struct {int x,y,width,height;} Rect;
typedef struct {int type,bIsVisible;Rect rect;} jkGuiElement;
typedef struct {jkGuiElement *paElements,*focusedElement,*lastMouseOverClickable,*pReturnKeyShortcutElement;} jkGuiMenu;
static jkGuiElement* clicked;
static void jkGuiRend_ClickableMouseover(jkGuiMenu* menu,jkGuiElement* e){menu->lastMouseOverClickable=e;}
static void jkGuiRend_UpdateAndDrawClickable(jkGuiElement* e,jkGuiMenu* menu,int redraw){}
static void jkGuiRend_InvokeClicked(jkGuiElement* e,jkGuiMenu* menu,int x,int y,int redraw){clicked=e;}
enum {SDL_GAMEPAD_BUTTON_START,SDL_GAMEPAD_BUTTON_BACK};
static int menuActive,jkCutscene_isRendering,stdControl_bControllerEscapeKey;
static int jkGuiRend_IsMenuActive(void){return menuActive;}
'''
window = (root / "Win95/Window.c").read_text()
start = window.index("if (event.gbutton.button == SDL_GAMEPAD_BUTTON_START")
end = window.index("\n                    }", start) + len("\n                    }")
code += "static void escape(int button, int down) {\nstruct {struct {int button,down;} gbutton;} event={{button,down}};\n" + window[start:end] + "\n}\n"
for file, signature in [
    ("Devices/sithControl.c", "static void sithControl_RekindledControllerBindings(void)"),
    ("Devices/sithControl.c", "static flex_t sithControl_ControllerLookScale(int funcId, const stdControlKeyInfoEntry* entry)"),
    ("Devices/sithControl.c", "flex_t sithControl_GetKeyAsAxis(int axisId)"),
    ("Gui/jkGUIRend.c", "static void jkGuiRend_ControllerFocusStep(jkGuiMenu* menu, int step)"),
    ("Gui/jkGUIRend.c", "static void jkGuiRend_ControllerAccept(jkGuiMenu* menu)"),
]:
    code += function(file, signature)
code += r'''
int main(void){
    escape(SDL_GAMEPAD_BUTTON_BACK,1);assert(!stdControl_bControllerEscapeKey);
    menuActive=1;escape(SDL_GAMEPAD_BUTTON_BACK,1);assert(stdControl_bControllerEscapeKey);
    menuActive=0;escape(SDL_GAMEPAD_BUTTON_BACK,0);assert(!stdControl_bControllerEscapeKey);
    escape(SDL_GAMEPAD_BUTTON_START,1);assert(stdControl_bControllerEscapeKey);
    escape(SDL_GAMEPAD_BUTTON_START,0);assert(!stdControl_bControllerEscapeKey);
    sithControl_BindControl(INPUT_FUNC_USELASTSELECTED,KEY_JOY1_B1,0);
    sithControl_BindControl(INPUT_FUNC_JUMP,KEY_JOY1_B4,0);
    sithControl_BindControl(INPUT_FUNC_USEINV,KEY_JOY1_B8,0);
    sithControl_BindControl(INPUT_FUNC_NEXTINV,KEY_JOY1_HUP,0);
    sithControl_BindControl(INPUT_FUNC_FORWARD,KEY_JOY1_HDOWN,0);
    sithControl_RekindledControllerBindings();
    assert(assigned(KEY_JOY1_B1)==INPUT_FUNC_JUMP);
    assert(assigned(KEY_JOY1_B4)==INPUT_FUNC_USESKILL);
    assert(assigned(KEY_JOY1_B8)==INPUT_FUNC_MAP);
    assert(assigned(KEY_JOY1_HUP)==INPUT_FUNC_USEBACTA);
    assert(assigned(KEY_JOY1_HDOWN)==INPUT_FUNC_FORWARD);
    assert(assigned(KEY_JOY1_B5)==INPUT_FUNC_UPGRADEMENU);
    stdControlKeyInfo saved[INPUT_FUNC_MAX];memcpy(saved,sithControl_aInputFuncToKeyinfo,sizeof(saved));
    sithControl_RekindledControllerBindings();assert(!memcmp(saved,sithControl_aInputFuncToKeyinfo,sizeof(saved)));
    for(int mode=0;mode<2;mode++){
        memset(sithControl_aInputFuncToKeyinfo,0,sizeof(saved));
        Main_bMotsCompat=!mode;sithNet_isMulti=mode;
        sithControl_RekindledControllerBindings();assert(assigned(KEY_JOY1_B1)==-1);
    }
    Main_bMotsCompat=sithNet_isMulti=0;
    for(int f=0;f<=INPUT_FUNC_FORWARD;f++){
        stdControlKeyInfo* info=&sithControl_aInputFuncToKeyinfo[f];
        info->numEntries=1;info->aEntries[0]=(stdControlKeyInfoEntry){1,0,1.5};
    }
    sensitivity=.0025;assert(fabs(sithControl_GetKeyAsAxis(INPUT_FUNC_TURN)-.15)<.0001);
    sensitivity=.04;assert(fabs(sithControl_GetKeyAsAxis(INPUT_FUNC_TURN)-.75)<.0001);
    sensitivity=1.28;assert(fabs(sithControl_GetKeyAsAxis(INPUT_FUNC_TURN)-1.5)<.0001);
    assert(fabs(sithControl_GetKeyAsAxis(INPUT_FUNC_FORWARD)-.75)<.0001);
    inverted=1;assert(sithControl_GetKeyAsAxis(INPUT_FUNC_PITCH)==-1.5);
    sensitivity=NAN;assert(sithControl_GetKeyAsAxis(INPUT_FUNC_TURN)==.75);
    sensitivity=.0025;
    sithControl_aInputFuncToKeyinfo[INPUT_FUNC_TURN].aEntries[0].dxKeyNum=AXIS_MOUSE_X;
    assert(sithControl_GetKeyAsAxis(INPUT_FUNC_TURN)==.75);
    sithControl_aInputFuncToKeyinfo[INPUT_FUNC_TURN].aEntries[0]=(stdControlKeyInfoEntry){2,37,1};
    assert(sithControl_GetKeyAsAxis(INPUT_FUNC_TURN)==.25);
    jkGuiElement elements[]={{ELEMENT_TEXT,1},{ELEMENT_TEXTBUTTON,1},{ELEMENT_TEXTBUTTON,0},
        {ELEMENT_SLIDER,1},{ELEMENT_CHECKBOX,1},{ELEMENT_LISTBOX,1},{ELEMENT_END,0}};
    jkGuiMenu menu={.paElements=elements,.pReturnKeyShortcutElement=&elements[1]};
    jkGuiRend_ControllerFocusStep(&menu,1);assert(menu.lastMouseOverClickable==&elements[1]);
    jkGuiRend_ControllerFocusStep(&menu,1);assert(menu.focusedElement==&elements[3]);
    clicked=NULL;jkGuiRend_ControllerAccept(&menu);assert(!clicked);
    jkGuiRend_ControllerFocusStep(&menu,1);jkGuiRend_ControllerAccept(&menu);
    assert(!menu.focusedElement && clicked==&elements[4]);
    jkGuiRend_ControllerFocusStep(&menu,1);assert(menu.focusedElement==&elements[5]);
    jkGuiRend_ControllerFocusStep(&menu,1);assert(menu.lastMouseOverClickable==&elements[1]);
    jkGuiRend_ControllerFocusStep(&menu,-1);assert(menu.focusedElement==&elements[5]);
    puts("Controller defaults, custom bindings, shared sensitivity, inversion and menu focus passed");
}
'''
scratch = Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-controller"
scratch.mkdir(parents=True, exist_ok=True)
cfile, binary = scratch / "controller.c", scratch / "controller"
windows = "--windows" in sys.argv
if windows:
    binary = binary.with_suffix(".exe")
try:
    cfile.write_text(code)
    subprocess.run(["x86_64-w64-mingw32-gcc" if windows else "cc", "-std=c99", str(cfile), "-lm", "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
finally:
    cfile.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)
