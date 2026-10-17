"""Check mouse buttons on the Key bindings page, the F5/F9 defaults and Force key migration.

Run in WSL: python3 tools/test_mouse_bindings.py ~/src/OpenJKDF2
Compiles the engine's real migration and mouse reset functions against a small binding table.
In-game: bind Mouse Button 4/5 in Setup > Key bindings, confirm the action in a level, restart,
and use Restore Defaults; docs/TESTING.md has the isolated session.
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

root = Path(sys.argv[1]) / "src"


def function(file, name):
    source = (root / file).read_text()
    start = re.search(r"^(?:static )?(?:int|void) " + name + r"\([^;]*?\)\n\{", source, re.M)
    assert start, name
    return source[start.start():source.index("\n}", start.end()) + 2]


keyboard = (root / "Gui/jkGUIKeyboard.c").read_text()
control = (root / "Devices/sithControl.c").read_text()
hud_defaults = function("Main/jkHudInv.c", "jkHudInv_InputInit")
key_defaults = function("Devices/sithControl.c", "sithControl_RegisterKeyboardBindings")

# Fresh profiles and Restore defaults: no Force keys, F5 quicksave, F9 quick load.
assert "ACTIVATE0" not in hud_defaults and not re.search(r"DIK_F[5-8]\b", hud_defaults), hud_defaults
assert "sithControl_BindControl(INPUT_FUNC_GAMESAVE, DIK_F5, 0);" in key_defaults
assert "sithControl_BindControl(INPUT_FUNC_QUICKLOAD, DIK_F9, 0);" in key_defaults
assert 'stdConffile_WriteLine("rpgforcekeys=1\\n");' in control
assert "sithControl_MigrateForceKeys(hasForceKeySetting);" in control

# The Key bindings page lists, captures and resets mouse buttons as well as keys.
assert "sithControl_EnumBindings(jkGuiKeyboard_EnumBindings, 1, 0, 1, pDarr);" in keyboard
assert "(KEY_IS_BUTTON(v4) || KEY_IS_MOUSE(v4))" in keyboard and "!KEY_IS_MOUSE(v4)" not in keyboard
restore = function("Gui/jkGUIKeyboard.c", "jkGuiKeyboard_RestoreDefaultsClicked")
assert "sithControl_RebindMouseButtons();" in restore

harness = r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
#define SITH_ASSERTREL assert
#define DIK_F5 0x3F
#define DIK_F6 0x40
#define DIK_F7 0x41
#define DIK_F8 0x42
#define DIK_F10 0x44
#define DIK_TAB 0x0F
#define KEY_MOUSE_B1 280
#define KEY_MOUSE_B2 281
#define KEY_MOUSE_B3 282
#define KEY_MOUSE_B4 283
#define KEY_MOUSE_B5 284
#define KEY_IS_MOUSE(x) ((x) >= KEY_MOUSE_B1 && (x) <= KEY_MOUSE_B5)
enum { INPUT_FUNC_FIRE1, INPUT_FUNC_FIRE2, INPUT_FUNC_GAMESAVE, INPUT_FUNC_MAP, INPUT_FUNC_ACTIVATE0,
       INPUT_FUNC_MAX = INPUT_FUNC_ACTIVATE0 + 5, INPUT_MAPPING_FLAG_DXKEY = 2 };
typedef struct { int flags; unsigned dxKeyNum; float binaryAxisVal; } stdControlKeyInfoEntry;
typedef struct { unsigned numEntries; stdControlKeyInfoEntry aEntries[8]; } stdControlKeyInfo;
static stdControlKeyInfo sithControl_aInputFuncToKeyinfo[INPUT_FUNC_MAX];
static void add(int func, unsigned key) {
    stdControlKeyInfo* k = &sithControl_aInputFuncToKeyinfo[func];
    k->aEntries[k->numEntries++] = (stdControlKeyInfoEntry){INPUT_MAPPING_FLAG_DXKEY, key, 0};
}
static void sithControl_DefaultHelper(int func, int key, int flags) { add(func, key); }
static stdControlKeyInfoEntry* sithControl_BindControl(int func, int key, int flags) { add(func, key); return 0; }
static int keys(int func) { return sithControl_aInputFuncToKeyinfo[func].numEntries; }
static unsigned key(int func, int i) { return sithControl_aInputFuncToKeyinfo[func].aEntries[i].dxKeyNum; }
static void reset(void) { memset(sithControl_aInputFuncToKeyinfo, 0, sizeof sithControl_aInputFuncToKeyinfo); }
static void stock11(void) {   // what 1.1 saved: Force powers on F5-F8, quicksave lost to them
    reset();
    add(INPUT_FUNC_ACTIVATE0 + 0, DIK_F5); add(INPUT_FUNC_ACTIVATE0 + 1, DIK_F6);
    add(INPUT_FUNC_ACTIVATE0 + 2, DIK_F7); add(INPUT_FUNC_ACTIVATE0 + 3, DIK_F8);
}
void sithControl_UnbindFunctionIndex(int funcId, unsigned int bindIndex);
void sithControl_BindDefaultMouseButtons(void);
'''

checks = r'''
int main(void) {
    stock11();
    sithControl_MigrateForceKeys(0);
    for (int i = 0; i < 4; i++) assert(keys(INPUT_FUNC_ACTIVATE0 + i) == 0);
    assert(keys(INPUT_FUNC_GAMESAVE) == 1 && key(INPUT_FUNC_GAMESAVE, 0) == DIK_F5);

    stock11();   // a profile that already had the offer keeps Force keys chosen later
    sithControl_MigrateForceKeys(1);
    assert(keys(INPUT_FUNC_ACTIVATE0) == 1 && keys(INPUT_FUNC_GAMESAVE) == 0);

    stock11();   // customised Force keys are left alone, and F5 stays with the player's choice
    sithControl_aInputFuncToKeyinfo[INPUT_FUNC_ACTIVATE0 + 1].aEntries[0].dxKeyNum = DIK_F10;
    sithControl_MigrateForceKeys(0);
    assert(keys(INPUT_FUNC_ACTIVATE0) == 1 && key(INPUT_FUNC_ACTIVATE0 + 1, 0) == DIK_F10);
    assert(keys(INPUT_FUNC_GAMESAVE) == 0);

    reset();     // quicksave already bound elsewhere stays there
    add(INPUT_FUNC_GAMESAVE, DIK_F6);
    sithControl_MigrateForceKeys(0);
    assert(keys(INPUT_FUNC_GAMESAVE) == 1 && key(INPUT_FUNC_GAMESAVE, 0) == DIK_F6);

    reset();     // Restore defaults on the Key bindings page resets every mouse button
    add(INPUT_FUNC_MAP, DIK_TAB); add(INPUT_FUNC_MAP, KEY_MOUSE_B5);
    add(INPUT_FUNC_ACTIVATE0, KEY_MOUSE_B4); add(INPUT_FUNC_FIRE1, KEY_MOUSE_B2);
    sithControl_RebindMouseButtons();
    assert(keys(INPUT_FUNC_MAP) == 1 && key(INPUT_FUNC_MAP, 0) == DIK_TAB);
    assert(keys(INPUT_FUNC_ACTIVATE0) == 0);
    assert(keys(INPUT_FUNC_FIRE1) == 1 && key(INPUT_FUNC_FIRE1, 0) == KEY_MOUSE_B1);
    assert(keys(INPUT_FUNC_FIRE2) == 2 && key(INPUT_FUNC_FIRE2, 0) == KEY_MOUSE_B2 && key(INPUT_FUNC_FIRE2, 1) == KEY_MOUSE_B3);
    return 0;
}
'''

with tempfile.TemporaryDirectory() as tmp:
    cfile, binary = Path(tmp) / "mouse_bindings.c", Path(tmp) / "mouse_bindings"
    cfile.write_text(harness + "\n".join(function("Devices/sithControl.c", name) for name in (
        "sithControl_UnbindFunctionIndex", "sithControl_KeyBound", "sithControl_MigrateForceKeys",
        "sithControl_BindDefaultMouseButtons", "sithControl_RebindMouseButtons")) + checks)
    subprocess.run(["cc", "-std=c99", str(cfile), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
print("mouse bindings, default keys and Force key migration verified")
