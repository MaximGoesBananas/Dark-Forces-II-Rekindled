"""Exercise the engine's upgrade-menu input and prompts with real binding lookup.

Run in WSL: python3 tools/test_bindings.py ~/src/OpenJKDF2
Also check rebinding and profile persistence in-game as described in DEVELOPING.md.
Add --windows to cross-compile and run the same checks as a native Windows executable.
"""
import os
import tempfile
import re
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1]) / "src"
assert '"USEVISION"       0 "Toggle field light"' in (root.parent / "resource/ui/openjkdf2.uni").read_text()


def function(file, name):
    source = (root / file).read_text()
    start = re.search(r"^(?:static )?(?:const char\*|int|void) " + name + r"\([^;]*?\)\n\{", source, re.M)
    return source[start.start():source.index("\n}", start.end()) + 2]


harness = r'''
#define QOL_IMPROVEMENTS
#define AXIS_MOUSE_X 0
#define AXIS_MOUSE_Y 1
#define AXIS_MOUSE_Z 2
#define INPUT_MAPPING_FLAG_AXIS_REVERSED 4
#define INPUT_MAPPING_FLAG_RAW_AXIS 8
#define KEY_MOUSE_B1 280
#define KEY_MOUSE_B2 281
#define KEY_MOUSE_B3 282
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint16_t char16_t;
typedef struct { int flags; unsigned dxKeyNum; float binaryAxisVal; } stdControlKeyInfoEntry;
typedef struct { unsigned numEntries; stdControlKeyInfoEntry aEntries[8]; } stdControlKeyInfo;
enum { INPUT_FUNC_UPGRADEMENU, INPUT_FUNC_FIRE1, INPUT_FUNC_FIRE2, INPUT_FUNC_JUMP, INPUT_FUNC_TURN, INPUT_FUNC_PITCH, INPUT_FUNC_MAX, INPUT_MAPPING_FLAG_DXKEY = 2,
       JK_EXTENDED_KEY_START = 256, JK_NUM_AXES=2, JK_TOTAL_NUM_KEYS=6 };
typedef struct { uint32_t val; const char* pStr; } stdControlDikStrToNum;
static const char* stdControl_aAxisNames[3]={"Mouse X","Mouse Y"," "};
static const stdControlDikStrToNum stdControl_aDikNumToStr[6]={
    {1,"Escape"},{3,"2"},{4,"3"},{37,"K"},{22,"U"},{68,"F10"}};
static stdControlKeyInfo sithControl_aInputFuncToKeyinfo[INPUT_FUNC_MAX];
static int sithWeapon_controlOptions, held[512], presses[512];
static stdControlKeyInfoEntry axes[3];
static stdControlKeyInfoEntry* sithControl_BindAxis(int func,int key,int flags) { return &axes[key]; }
static void sithControl_DefaultHelper(int func,int key,int flags) {
    stdControlKeyInfo* k=&sithControl_aInputFuncToKeyinfo[func];
    k->aEntries[k->numEntries++]=(stdControlKeyInfoEntry){flags,key,0};
}
#define SITH_ASSERTREL assert
#define KEY_IS_MOUSE(k) ((k) >= 256 && (k) < 264)
#define stdString_snprintf snprintf
static int stdControl_ReadKey(int key, int* count) {
    if (count) *count += presses[key];
    return held[key];
}
static char16_t* jkStrings_GetUniStringWithFallback(const char* id) {
    static char16_t text[16];
    for (int i = 0; (text[i] = id[i]); i++) {}
    return text;
}
static void stdString_WcharToChar(char* out, const char16_t* in, int n) {
    for (int i = 0; i < n; i++) if (!(out[i] = in[i])) break;
}
'''
checks = r'''
int main(void) {
    assert(!strcmp(jkGuiKeyboard_DIKNumToStr(3,0),"2"));
    assert(!strcmp(jkGuiKeyboard_DIKNumToStr(4,0),"3"));
    assert(!strcmp(jkGuiKeyboard_DIKNumToStr(9999,0),"KEY_UNKNOWN"));
    assert(!strcmp(jkGuiKeyboard_DIKNumToStr(0,1),"Mouse X"));
    assert(!strcmp(jkGuiKeyboard_DIKNumToStr(JK_NUM_AXES,1),"AXIS_UNKNOWN"));
    stdControlKeyInfo* keys = &sithControl_aInputFuncToKeyinfo[INPUT_FUNC_UPGRADEMENU];
    assert(!jkRpg_MenuKeyName());
    assert(!strcmp(jkRpg_MenuHint(), "BIND UPGRADE MENU IN SETUP"));
    keys->numEntries = 1;
    keys->aEntries[0] = (stdControlKeyInfoEntry){2, 37};
    assert(!strcmp(jkRpg_MenuHint(), "PRESS K"));
    presses[37] = held[37] = 1; assert(jkRpg_MenuPressed());
    presses[37] = 0; assert(!jkRpg_MenuPressed()); // Holding must not close it again.
    keys->aEntries[0].dxKeyNum = 22;
    presses[37] = 1; assert(!jkRpg_MenuPressed()); // Old key no longer opens it.
    presses[22] = 1; assert(jkRpg_MenuPressed());
    assert(!strcmp(jkRpg_MenuHint(), "PRESS U"));
    keys->numEntries = 2;
    keys->aEntries[1] = (stdControlKeyInfoEntry){2, 68};
    presses[22] = 0; presses[68] = 1; assert(jkRpg_MenuPressed());
    assert(!strcmp(jkRpg_MenuKeyName(), "U")); // First binding is the displayed hint.
    keys->aEntries[0] = keys->aEntries[1]; keys->numEntries = 1;
    assert(!strcmp(jkRpg_MenuHint(), "PRESS F10"));
    keys->numEntries = 0;
    assert(!jkRpg_MenuPressed() && !jkRpg_MenuKeyName());
    sithControl_RegisterMouseBindings();
    assert(axes[AXIS_MOUSE_X].binaryAxisVal == 0.04f && axes[AXIS_MOUSE_Y].binaryAxisVal == 0.04f);
    assert(sithControl_aInputFuncToKeyinfo[INPUT_FUNC_FIRE1].aEntries[0].dxKeyNum==KEY_MOUSE_B1);
    assert(sithControl_aInputFuncToKeyinfo[INPUT_FUNC_FIRE2].aEntries[0].dxKeyNum==KEY_MOUSE_B2);
    assert(!sithControl_aInputFuncToKeyinfo[INPUT_FUNC_JUMP].numEntries);
    puts("Menu rebinding, held keys, alternate bindings, unbound hints and Mouse2 secondary defaults passed");
}
'''
scratch = Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-bindings"
scratch.mkdir(parents=True, exist_ok=True)
cfile, binary = scratch / "bindings.c", scratch / "bindings"
windows = "--windows" in sys.argv
if windows:
    binary = binary.with_suffix(".exe")
try:
    cfile.write_text(harness + function("Gui/jkGUIKeyboard.c", "jkGuiKeyboard_DIKNumToStr") + "\n" +
                     function("Devices/sithControl.c", "sithControl_GetKey") + "void sithControl_BindDefaultMouseButtons(void);\n" +
                     function("Devices/sithControl.c", "sithControl_RegisterMouseBindings") +
                     function("Devices/sithControl.c", "sithControl_BindDefaultMouseButtons") +
                     "\n" + "\n".join(function("Main/jkRpg.c", name) for name in
                     ("jkRpg_BindingName", "jkRpg_MenuKeyName", "jkRpg_MenuHint", "jkRpg_MenuPressed")) + checks)
    compiler = "x86_64-w64-mingw32-gcc" if windows else "cc"
    subprocess.run([compiler, "-std=c99", str(cfile), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
    # Exercise the actual enumeration used by keyboard, mouse and joystick Setup.
    # Menu filtering must never erase bindings or hide still-useful Force actions.
    enums = {}
    for name, value in re.findall(r"\b(INPUT_FUNC_\w+) = (\d+)", (root / "types_enums.h").read_text()):
        enums.setdefault(name, value)  # QOL definitions precede stock fallbacks.
    control = (root / "Devices/sithControl.c").read_text()
    start = control.index("stdControlKeyInfo* sithControl_EnumBindings(")
    enumeration = control[start:control.index("\n}", start) + 2]
    cfile.write_text(r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#define QOL_IMPROVEMENTS
#define KEY_IS_MOUSE(k) ((k) >= 280 && (k) < 288)
enum { INPUT_MAPPING_FLAG_AXIS=1, INPUT_MAPPING_FLAG_DXKEY=2, JK_EXTENDED_KEY_START=256, AXIS_MOUSE_X=12 };
enum { SITHINVENTORY_NUM_POWERKEYBINDS=20, SITHBIN_BACTATANK=40, SITHBIN_IRGOGGLES=41, SITHBIN_FIELDLIGHT=42 };
enum { ''' + ",".join(f"{k}={v}" for k, v in enums.items()) + r''' };
typedef int BOOL;
typedef int Darray;
typedef struct { int flags; unsigned dxKeyNum; float binaryAxisVal; } stdControlKeyInfoEntry;
typedef struct { unsigned numEntries; stdControlKeyInfoEntry aEntries[8]; } stdControlKeyInfo;
typedef int (*sithControlEnumFunc_t)(int,const char*,int,unsigned,int,int,stdControlKeyInfoEntry*,Darray*);
static stdControlKeyInfo sithControl_aInputFuncToKeyinfo[INPUT_FUNC_MAX];
static int sithControl_inputFuncToControlType[INPUT_FUNC_MAX], Main_bMotsCompat, seen[INPUT_FUNC_MAX];
static const char* sithControl_aFunctionStrs[INPUT_FUNC_MAX];
static struct { int enabled, binding, idk; } sithInventory_powerKeybinds[SITHINVENTORY_NUM_POWERKEYBINDS];
static int visit(int f,const char*s,int flags,unsigned idx,int key,int opts,stdControlKeyInfoEntry* entry,Darray*d) {
    assert(f >= 0 && f < INPUT_FUNC_MAX); seen[f]++; return 1;
}
''' + enumeration + r'''
int main(void) {
    for(int f=0;f<INPUT_FUNC_MAX;f++) {
        sithControl_inputFuncToControlType[f]=5;
        sithControl_aInputFuncToKeyinfo[f].numEntries=1;
        sithControl_aInputFuncToKeyinfo[f].aEntries[0]=(stdControlKeyInfoEntry){2,37,.75f};
    }
    stdControlKeyInfo before[INPUT_FUNC_MAX];
    memcpy(before,sithControl_aInputFuncToKeyinfo,sizeof(before));
    // Reordered item registrations prove this follows the inventory table, not fixed action numbers.
    for(int i=0;i<SITHINVENTORY_NUM_POWERKEYBINDS;i++) {
        sithInventory_powerKeybinds[i].enabled=1;
        sithInventory_powerKeybinds[i].binding=i+20;
    }
    sithInventory_powerKeybinds[3].binding=SITHBIN_BACTATANK;
    sithInventory_powerKeybinds[15].binding=SITHBIN_IRGOGGLES;
    sithInventory_powerKeybinds[18].binding=SITHBIN_FIELDLIGHT;
    sithInventory_powerKeybinds[19].binding=SITHBIN_IRGOGGLES;
    sithInventory_powerKeybinds[19].enabled=0; // Stale disabled slots must not hide another action.
    for(Main_bMotsCompat=0;Main_bMotsCompat<=1;Main_bMotsCompat++) {
        for(int device=0;device<3;device++) {
            memset(seen,0,sizeof(seen));
            sithControl_EnumBindings(visit,device==0,device==1,device==2,0);
            for(int f=0;f<INPUT_FUNC_MAX;f++) {
                int hidden=!Main_bMotsCompat && (f==INPUT_FUNC_NEXTINV || f==INPUT_FUNC_PREVINV || f==INPUT_FUNC_USEINV || f==INPUT_FUNC_TALLY
                    || f==INPUT_FUNC_USELASTSELECTED
                    || f==INPUT_FUNC_ACTIVATE3 || f==INPUT_FUNC_ACTIVATE15 || f==INPUT_FUNC_ACTIVATE18);
                assert((seen[f]==0)==hidden);
            }
            assert(!memcmp(before,sithControl_aInputFuncToKeyinfo,sizeof(before)));
        }
    }
    puts("All remapping lists hide obsolete item/score controls, preserve other actions and keep custom bindings intact");
}
''')
    subprocess.run([compiler, "-std=c99", str(cfile), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
finally:
    cfile.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)
