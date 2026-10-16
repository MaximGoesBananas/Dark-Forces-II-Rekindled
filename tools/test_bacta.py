"""Compile and exercise the bacta tank key, HUD count, item-list exclusion and pickup reminder.

Run in WSL: python3 tools/test_bacta.py ~/src/OpenJKDF2
Uses the engine's actual functions: fresh-profile key defaults, the older-profile R migration,
the bacta key lookup and use, the HUD count/empty state, Next/Previous Item searches and the
reminder conditions. Only the temporary C harness/binary are written under Helm scratch.
"""
import os
import tempfile
import re
import subprocess
import sys
from pathlib import Path

src = Path(sys.argv[1]) / "src"


def function(file, name):
    source = (src / file).read_text()
    match = re.search(r"^(?:static )?[\w\* ]*?\b" + name + r"\(", source, re.M)
    if not match:
        raise ValueError(name)
    body = source.index("{", match.end())
    depth = 0
    for i in range(body, len(source)):
        depth += {"{": 1, "}": -1}.get(source[i], 0)
        if depth == 0:
            return source[match.start():i + 1] + "\n"
    raise ValueError(name)


enums = (src / "types_enums.h").read_text()
inputs = {}
for name, value in re.findall(r"\b(INPUT_FUNC_\w+) = (\d+)", enums):
    inputs.setdefault(name, value)  # the first INPUT_FUNC_MAX is the QOL_IMPROVEMENTS one
keyboard = function("Devices/sithControl.c", "sithControl_RegisterKeyboardBindings")
real_keys = {"DIK_R": 0x13, "DIK_RBRACKET": 0x1B, "DIK_K": 0x25, "DIK_F9": 0x43, "DIK_SPACE": 0x39}
dik = sorted(set(re.findall(r"\bDIK_\w+", keyboard)) | set(real_keys))
defines = "\n".join(re.findall(r"^#define RPG_(?:LOW_SHARE|BACTA_NOTICE_GAP)\s.*$",
                               (src / "Main/jkRpg.c").read_text(), re.M))

harness = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef float flex_t;
typedef uint16_t char16_t;
#define SITH_ASSERTREL assert
#define stdString_snprintf snprintf
#define KEY_IS_MOUSE(k) ((k) >= 256 && (k) < 264)
enum { JK_EXTENDED_KEY_START = 256, INPUT_MAPPING_FLAG_DXKEY = 2, DEBUGFLAG_IN_EDITOR = 1 };
enum { ''' + ", ".join(f"{k} = {v}" for k, v in inputs.items()) + r''' };
enum { ''' + ", ".join(f"{k} = {real_keys.get(k, 1000 + i)}" for i, k in enumerate(dik)) + r''' };
typedef struct { int flags; unsigned dxKeyNum; float binaryAxisVal; } stdControlKeyInfoEntry;
typedef struct { unsigned numEntries; stdControlKeyInfoEntry aEntries[8]; } stdControlKeyInfo;
static stdControlKeyInfo sithControl_aInputFuncToKeyinfo[INPUT_FUNC_MAX];
static int sithControl_inputFuncToControlType[INPUT_FUNC_MAX];
static int sithWeapon_controlOptions, Main_bMotsCompat, g_debugmodeFlags, held[1200], presses[1200];
static void sithControl_DefaultHelper(int func, int key, int flags) {
    stdControlKeyInfo* k = &sithControl_aInputFuncToKeyinfo[func];
    k->aEntries[k->numEntries++] = (stdControlKeyInfoEntry){flags, key, 0};
}
static int stdControl_ReadKey(int key, int* count) { if (count) *count += presses[key]; return held[key]; }
static const char* jkGuiKeyboard_DIKNumToStr(unsigned key, int axis) { return key == DIK_R ? "R" : key == DIK_K ? "K" : "?"; }
static char16_t* jkStrings_GetUniStringWithFallback(const char* id) {
    static char16_t text[16];
    for (int i = 0; (text[i] = id[i]); i++) {}
    return text;
}
static void stdString_WcharToChar(char* out, const char16_t* in, int n) { for (int i = 0; i < n; i++) if (!(out[i] = in[i])) break; }

// Inventory: bins, player state and the bacta tank's item script.
enum { SITHBIN_NUMBINS = 200, SITHBIN_BACTATANK = 40, SITHBIN_IRGOGGLES = 41, SITHBIN_FIELDLIGHT = 42,
       SITHINVENTORY_TYPE_REGISTERED = 1, ITEMINFO_ITEM = 2, ITEMINFO_WEAPON = 4, SITHINVENTORY_ITEM_AVAILABLE = 4,
       SITH_MESSAGE_ACTIVATE = 1, SENDERTYPE_SYSTEM = 1, SENDERTYPE_THING = 3 };
typedef struct { int flags; void* cog; } SithInventoryType;
typedef struct { struct { int state; } aItems[SITHBIN_NUMBINS]; } SithPlayer;
typedef struct { int idx; struct { SithPlayer* pPlayer; flex_t health, maxHealth; } actorParams; } SithThing;
typedef void sithCog;
static SithInventoryType sithInventory_g_aTypes[SITHBIN_NUMBINS];
static const int sithInventory_aMotsForcePowerBins[18];
static flex_t inventory[SITHBIN_NUMBINS];
static int active = 1, cogCalls;
static flex_t sithInventory_GetInventory(SithThing* p, int bin) { return inventory[bin]; }
static int jkRpg_IsActive(SithThing* p) { return active; }
static void sithCog_SendMessage(sithCog* cog, int msg, int st, int bin, int tt, int idx, int arg) {
    SithThing* p = cog; // item_bacta.cog: below 100 health, heal 30 and use one tank
    cogCalls++;
    if (inventory[bin] > 0 && p->actorParams.health < 100) { p->actorParams.health += 30; inventory[bin] -= 1; }
}
'''

checks = r'''
static int bound(int func, unsigned key) {
    for (unsigned i = 0; i < sithControl_aInputFuncToKeyinfo[func].numEntries; i++)
        if (sithControl_aInputFuncToKeyinfo[func].aEntries[i].dxKeyNum == key) return 1;
    return 0;
}
static void reset(void) { memset(sithControl_aInputFuncToKeyinfo, 0, sizeof(sithControl_aInputFuncToKeyinfo)); }
static void bind(int func, unsigned key) { sithControl_DefaultHelper(func, key, INPUT_MAPPING_FLAG_DXKEY); }

int main(void) {
    for (int i = 0; i < INPUT_FUNC_MAX; i++) sithControl_inputFuncToControlType[i] = 4 | 1;

    // Fresh profiles: R uses a bacta tank; Next Item keeps ] only; the menu stays on K.
    sithControl_RegisterKeyboardBindings();
    assert(bound(INPUT_FUNC_USEBACTA, DIK_R) && sithControl_aInputFuncToKeyinfo[INPUT_FUNC_USEBACTA].numEntries == 1);
    assert(!bound(INPUT_FUNC_NEXTINV, DIK_R) && bound(INPUT_FUNC_NEXTINV, DIK_RBRACKET));
    assert(bound(INPUT_FUNC_UPGRADEMENU, DIK_K) && bound(INPUT_FUNC_QUICKLOAD, DIK_F9));
    for (int f = 0; f < INPUT_FUNC_MAX; f++) assert(f == INPUT_FUNC_USEBACTA || !bound(f, DIK_R));

    // Older profiles: R moves from the stock R/] Next Item pair; ] stays.
    reset(); bind(INPUT_FUNC_NEXTINV, DIK_R); bind(INPUT_FUNC_NEXTINV, DIK_RBRACKET);
    sithControl_MigrateBactaKey(0);
    assert(bound(INPUT_FUNC_USEBACTA, DIK_R) && !bound(INPUT_FUNC_NEXTINV, DIK_R) && bound(INPUT_FUNC_NEXTINV, DIK_RBRACKET));
    // Unused R is given; R as the only Next Item key, or on anything else, is kept.
    reset(); sithControl_MigrateBactaKey(0); assert(bound(INPUT_FUNC_USEBACTA, DIK_R));
    reset(); bind(INPUT_FUNC_NEXTINV, DIK_R); sithControl_MigrateBactaKey(0);
    assert(!sithControl_aInputFuncToKeyinfo[INPUT_FUNC_USEBACTA].numEntries && bound(INPUT_FUNC_NEXTINV, DIK_R));
    reset(); bind(INPUT_FUNC_JUMP, DIK_R); sithControl_MigrateBactaKey(0);
    assert(!sithControl_aInputFuncToKeyinfo[INPUT_FUNC_USEBACTA].numEntries && bound(INPUT_FUNC_JUMP, DIK_R));
    // Already offered (saved by this version) or bound elsewhere: left alone, including unbound.
    reset(); sithControl_MigrateBactaKey(1); assert(!sithControl_aInputFuncToKeyinfo[INPUT_FUNC_USEBACTA].numEntries);
    reset(); bind(INPUT_FUNC_USEBACTA, DIK_K); bind(INPUT_FUNC_NEXTINV, DIK_R); bind(INPUT_FUNC_NEXTINV, DIK_RBRACKET);
    sithControl_MigrateBactaKey(0);
    assert(bound(INPUT_FUNC_USEBACTA, DIK_K) && !bound(INPUT_FUNC_USEBACTA, DIK_R) && bound(INPUT_FUNC_NEXTINV, DIK_R));

    // Key name for the reminder follows the binding; unbound gives NULL (Setup instruction).
    reset(); assert(!jkRpg_BactaKeyName() && !jkRpg_BactaPressed());
    bind(INPUT_FUNC_USEBACTA, DIK_R); assert(!strcmp(jkRpg_BactaKeyName(), "R"));
    presses[DIK_R] = held[DIK_R] = 1; assert(jkRpg_BactaPressed());
    presses[DIK_R] = 0; assert(!jkRpg_BactaPressed()); // holding R uses one tank, not one per frame
    reset(); bind(INPUT_FUNC_USEBACTA, DIK_K); presses[DIK_R] = presses[DIK_K] = 1;
    assert(jkRpg_BactaPressed() && !strcmp(jkRpg_BactaKeyName(), "K"));
    presses[DIK_K] = 0; assert(!jkRpg_BactaPressed()); // R no longer uses it after rebinding

    // Using a tank goes through the tank's script: hurt uses one, full health or none uses nothing.
    SithPlayer player = {0};
    SithThing kyle = {0, {&player, 40, 100}};
    sithInventory_g_aTypes[SITHBIN_BACTATANK].cog = &kyle;
    inventory[SITHBIN_BACTATANK] = 2;
    assert(jkRpg_UseBacta(&kyle) && inventory[SITHBIN_BACTATANK] == 1 && kyle.actorParams.health == 70);
    kyle.actorParams.health = 100; cogCalls = 0;
    assert(!jkRpg_UseBacta(&kyle) && inventory[SITHBIN_BACTATANK] == 1 && cogCalls == 1);
    inventory[SITHBIN_BACTATANK] = 0; kyle.actorParams.health = 10; cogCalls = 0;
    assert(!jkRpg_UseBacta(&kyle) && cogCalls == 0);
    sithInventory_g_aTypes[SITHBIN_BACTATANK].cog = 0; inventory[SITHBIN_BACTATANK] = 3;
    assert(!jkRpg_UseBacta(&kyle) && inventory[SITHBIN_BACTATANK] == 3);

    // HUD: the carried count up to the maximum of five; zero is the dimmed empty icon.
    assert(jkRpg_BactaShown(0) == 0 && jkRpg_BactaShown(-1) == 0 && jkRpg_BactaShown(0.5f) == 0);
    assert(jkRpg_BactaShown(1) == 1 && jkRpg_BactaShown(3) == 3 && jkRpg_BactaShown(5) == 5);

    // Item cycling skips bacta and removed goggles, leaving the field light; weapons are unchanged.
    int items[] = {SITHBIN_BACTATANK, SITHBIN_IRGOGGLES, SITHBIN_FIELDLIGHT};
    for (int i = 0; i < 3; i++) {
        sithInventory_g_aTypes[items[i]].flags = SITHINVENTORY_TYPE_REGISTERED | ITEMINFO_ITEM | 0x100;
        player.aItems[items[i]].state = SITHINVENTORY_ITEM_AVAILABLE;
    }
    sithInventory_g_aTypes[3].flags = SITHINVENTORY_TYPE_REGISTERED | ITEMINFO_WEAPON;
    player.aItems[3].state = SITHINVENTORY_ITEM_AVAILABLE;
    assert(sithInventory_FindNextTypeID(&kyle, 0, ITEMINFO_ITEM) == SITHBIN_FIELDLIGHT);
    assert(sithInventory_FindNextTypeID(&kyle, SITHBIN_FIELDLIGHT, ITEMINFO_ITEM) == -1);
    assert(sithInventory_FindPreviousTypeID(&kyle, SITHBIN_IRGOGGLES, ITEMINFO_ITEM) == SITHBIN_FIELDLIGHT);
    assert(sithInventory_FindPreviousTypeID(&kyle, SITHBIN_FIELDLIGHT, ITEMINFO_ITEM) == -1);
    assert(sithInventory_FindNextTypeID(&kyle, SITHBIN_BACTATANK, ITEMINFO_ITEM) == SITHBIN_FIELDLIGHT); // old saves
    assert(sithInventory_FindNextTypeID(&kyle, 0, ITEMINFO_WEAPON) == 3);
    player.aItems[SITHBIN_IRGOGGLES].state = player.aItems[SITHBIN_FIELDLIGHT].state = 0;
    assert(sithInventory_FindNextTypeID(&kyle, 0, ITEMINFO_ITEM) == -1); // only tanks: nothing to cycle
    assert(sithInventory_FindPreviousTypeID(&kyle, 0, ITEMINFO_ITEM) == -1);
    active = 0; // other game modes keep the original list
    assert(sithInventory_FindNextTypeID(&kyle, 0, ITEMINFO_ITEM) == SITHBIN_BACTATANK);

    // Reminder: the first tank always; later only at a quarter of health or less, before the key
    // has been used, and at least the gap after the previous reminder.
    const float gap = RPG_BACTA_NOTICE_GAP;
    assert(jkRpg_BactaNotice(1, 0, 100, 100, 0) && jkRpg_BactaNotice(1, 0, 10, 150, 0));
    assert(!jkRpg_BactaNotice(0, 0, 26, 100, gap) && jkRpg_BactaNotice(0, 0, 25, 100, gap));
    assert(jkRpg_BactaNotice(0, 0, 37.5f, 150, gap) && !jkRpg_BactaNotice(0, 0, 37.6f, 150, gap));
    assert(!jkRpg_BactaNotice(0, 1, 10, 100, gap)); // already knows the key
    assert(!jkRpg_BactaNotice(0, 0, 10, 100, gap - 0.1f)); // no repeat for several pickups in a row
    assert(gap >= 20);
    puts("bacta key defaults and migration, key use, HUD count, item cycling and reminders passed");
}
'''

jkrpg = ["jkRpg_BindingName", "jkRpg_BactaKeyName", "jkRpg_BactaPressed", "jkRpg_UseBacta",
         "jkRpg_HiddenItem", "jkRpg_BactaNotice"]
scratch = Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-bacta-check"
scratch.mkdir(parents=True, exist_ok=True)
cfile, binary = scratch / "bacta.c", scratch / "bacta"
try:
    cfile.write_text(harness + defines + "\n"
                     + function("Devices/sithControl.c", "sithControl_GetKey")
                     + function("Devices/sithControl.c", "sithControl_BindControl")
                     + keyboard + function("Devices/sithControl.c", "sithControl_MigrateBactaKey")
                     + "".join(function("Main/jkRpg.c", n) for n in jkrpg)
                     + function("Main/jkRpgMenu.c", "jkRpg_BactaShown")
                     + function("Gameplay/sithInventory.c", "sithInventory_FindNextTypeID")
                     + function("Gameplay/sithInventory.c", "sithInventory_FindPreviousTypeID") + checks)
    subprocess.run(["cc", "-std=c99", "-w", str(cfile), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
finally:
    cfile.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)
