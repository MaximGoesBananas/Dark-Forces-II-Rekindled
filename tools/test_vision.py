"""Compile actual G defaults/migration and field-light toggle against item-script stand-ins."""
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
        if not depth:
            return source[match.start():i + 1] + "\n"
    raise ValueError(name)


inputs = {}
for name, value in re.findall(r"\b(INPUT_FUNC_\w+) = (\d+)", (src / "types_enums.h").read_text()):
    inputs.setdefault(name, value)
keyboard = function("Devices/sithControl.c", "sithControl_RegisterKeyboardBindings")
real_keys = {"DIK_G": 34, "DIK_SLASH": 53, "DIK_K": 37, "DIK_R": 19,
             "DIK_C": 46, "DIK_RBRACKET": 27, "DIK_LBRACKET": 26}
dik = sorted(set(re.findall(r"\bDIK_\w+", keyboard)) | set(real_keys))
harness = r'''
#include <assert.h>
#include <stdint.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <strings.h>
#define __strcmpi strcasecmp
#define SITH_ASSERTREL assert
#define KEY_IS_MOUSE(k) ((k) >= 280 && (k) < 288)
enum { JK_EXTENDED_KEY_START = 256, INPUT_MAPPING_FLAG_DXKEY = 2, DEBUGFLAG_IN_EDITOR = 1 };
enum { ''' + ", ".join(f"{k} = {v}" for k, v in inputs.items()) + r''' };
enum { ''' + ", ".join(f"{k} = {real_keys.get(k, 1000+i)}" for i, k in enumerate(dik)) + r''' };
typedef struct { int flags; unsigned dxKeyNum; float binaryAxisVal; } stdControlKeyInfoEntry;
typedef struct { unsigned numEntries; stdControlKeyInfoEntry aEntries[8]; } stdControlKeyInfo;
static stdControlKeyInfo sithControl_aInputFuncToKeyinfo[INPUT_FUNC_MAX];
static int sithControl_inputFuncToControlType[INPUT_FUNC_MAX];
static int sithWeapon_controlOptions, Main_bMotsCompat, g_debugmodeFlags, held[1200], presses[1200];
static void sithControl_DefaultHelper(int f, int key, int flags) {
    stdControlKeyInfo* k = &sithControl_aInputFuncToKeyinfo[f];
    k->aEntries[k->numEntries++] = (stdControlKeyInfoEntry){flags, key, 0};
}
static int stdControl_ReadKey(int key, int* count) { if (count) *count += presses[key]; return held[key]; }
enum { RPG_BIN_VISIONKEY = 184, SITHBIN_BATTERY = 13, SITHBIN_FIELDLIGHT = 42, SITHBIN_IRGOGGLES = 41, SITH_TF_DEAD = 1, SITH_TF_DESTROYED = 2, SITH_THING_ITEM = 3,
       SITH_MESSAGE_ACTIVATE = 1, SENDERTYPE_SYSTEM = 1, SENDERTYPE_THING = 3 };
typedef struct { unsigned id; } SithSector;
typedef struct { char aName[64]; } Template;
typedef struct { int idx, flags; SithSector* sector; int guid, type; Template* pTemplate; } SithThing;
typedef struct { char map_jkl_fname[64]; int numThingsLoaded; SithThing* aThings; } SithWorld;
static SithWorld world = {"01narshadda.jkl"};
static SithWorld* sithWorld_g_pCurrentWorld = &world;
typedef int sithCog;
static struct { sithCog* cog; } sithInventory_g_aTypes[200];
static int active = 1, battery = 100, owned[200], available[200], enabled[200], calls[8], numCalls;
static int jkRpg_IsActive(SithThing* p) { return active && !Main_bMotsCompat; }
static float sithInventory_GetInventory(SithThing* p, int bin) { return owned[bin]; }
static void sithInventory_SetInventory(SithThing* p, int bin, float value) { owned[bin] = value; }
static void sithInventory_SetInventoryAvailable(SithThing* p, int bin, int value) { available[bin] = value; }
static void sithThing_DestroyThing(SithThing* p) { assert(!(p->flags & SITH_TF_DESTROYED)); p->flags |= SITH_TF_DESTROYED; }
static int jkRpg_Get(SithThing* p, int bin) { return owned[bin]; }
typedef float flex_t;
typedef uint16_t char16_t;
static flex_t sithTime_g_secGameTime;
static char reminder[192];
static int reminderCount;
static void jkRpg_Print(const char* fmt, ...) {
    va_list args; va_start(args, fmt); vsnprintf(reminder, sizeof(reminder), fmt, args); va_end(args);
    reminderCount++;
}
static const char* jkGuiKeyboard_DIKNumToStr(unsigned key, int axis) {
    return key == DIK_G ? "G" : key == DIK_K ? "K" : "?";
}
static char16_t* jkStrings_GetUniStringWithFallback(const char* id) {
    static char16_t result[16];
    for (int i = 0; (result[i] = id[i]); i++) {}
    return result;
}
static void stdString_WcharToChar(char* out, const char16_t* in, int n) {
    for (int i = 0; i < n; i++) if (!(out[i] = in[i])) break;
}
static int sithInventory_IsInventoryAvailable(SithThing* p, int bin) { return available[bin]; }
static int sithInventory_IsInventoryActivated(SithThing* p, int bin) { return enabled[bin]; }
// The stock scripts toggle only owned items; depleted batteries prevent activation, not deactivation.
static void sithCog_SendMessage(sithCog* cog, int message, int st, int bin, int tt, int idx, int arg) {
    assert(message == SITH_MESSAGE_ACTIVATE && st == SENDERTYPE_SYSTEM && tt == SENDERTYPE_THING && idx == 7);
    calls[numCalls++] = bin;
    if (owned[bin] && (enabled[bin] || battery > 0)) enabled[bin] = !enabled[bin];
}
'''
checks = r'''
static void bind(int f, int key) { sithControl_DefaultHelper(f, key, 2); }
static int bound(int f, int key) {
    for (unsigned i = 0; i < sithControl_aInputFuncToKeyinfo[f].numEntries; i++)
        if (sithControl_aInputFuncToKeyinfo[f].aEntries[i].dxKeyNum == key) return 1;
    return 0;
}
static void reset(void) { memset(sithControl_aInputFuncToKeyinfo, 0, sizeof(sithControl_aInputFuncToKeyinfo)); }
static SithThing player = {7, 0};
static void press(void) { presses[DIK_G] = held[DIK_G] = 1; numCalls = 0; jkRpg_VisionTick(&player); presses[DIK_G] = 0; }
int main(void) {
    for (int i = 0; i < INPUT_FUNC_MAX; i++) sithControl_inputFuncToControlType[i] = 5;
    sithControl_RegisterKeyboardBindings();
    assert(bound(INPUT_FUNC_USEVISION, DIK_G) && !bound(INPUT_FUNC_NEXTWEAPON, DIK_G));
    assert(bound(INPUT_FUNC_NEXTWEAPON, DIK_SLASH) && bound(INPUT_FUNC_USEBACTA, DIK_R));
    assert(bound(INPUT_FUNC_DUCK, DIK_C)); // Preserve the crouch binding.
    assert(bound(INPUT_FUNC_NEXTINV, DIK_RBRACKET) && bound(INPUT_FUNC_PREVINV, DIK_LBRACKET));
    reset(); bind(INPUT_FUNC_NEXTWEAPON, DIK_G); bind(INPUT_FUNC_NEXTWEAPON, DIK_SLASH); bind(INPUT_FUNC_NEXTWEAPON, 260);
    sithControl_MigrateVisionKey(0);
    assert(bound(INPUT_FUNC_USEVISION, DIK_G) && !bound(INPUT_FUNC_NEXTWEAPON, DIK_G));
    assert(bound(INPUT_FUNC_NEXTWEAPON, DIK_SLASH) && bound(INPUT_FUNC_NEXTWEAPON, 260));
    sithControl_MigrateVisionKey(0); assert(sithControl_aInputFuncToKeyinfo[INPUT_FUNC_USEVISION].numEntries == 1);
    reset(); sithControl_MigrateVisionKey(0); assert(bound(INPUT_FUNC_USEVISION, DIK_G));
    reset(); sithControl_MigrateVisionKey(1); assert(!sithControl_aInputFuncToKeyinfo[INPUT_FUNC_USEVISION].numEntries);
    reset(); bind(INPUT_FUNC_USEVISION, DIK_K); sithControl_MigrateVisionKey(0);
    assert(bound(INPUT_FUNC_USEVISION, DIK_K) && !bound(INPUT_FUNC_USEVISION, DIK_G));
    reset(); bind(INPUT_FUNC_NEXTWEAPON, DIK_G); bind(INPUT_FUNC_NEXTWEAPON, 260);
    sithControl_MigrateVisionKey(0); assert(!sithControl_aInputFuncToKeyinfo[INPUT_FUNC_USEVISION].numEntries);
    reset(); bind(INPUT_FUNC_JUMP, DIK_G); sithControl_MigrateVisionKey(0);
    assert(bound(INPUT_FUNC_JUMP, DIK_G) && !bound(INPUT_FUNC_USEVISION, DIK_G));

    reset(); bind(INPUT_FUNC_USEVISION, DIK_G);
    sithInventory_g_aTypes[41].cog = &owned[41]; sithInventory_g_aTypes[42].cog = &owned[42];
    press(); assert(!numCalls && !owned[RPG_BIN_VISIONKEY]); // Neither owned.
    owned[41] = available[41] = 1; press(); assert(!enabled[41] && !enabled[42]); // Goggles never a fallback.
    owned[42] = available[42] = 1; press(); assert(enabled[42] && !enabled[41] && owned[RPG_BIN_VISIONKEY]);
    numCalls = 0; jkRpg_VisionTick(&player); assert(!numCalls && enabled[42]); // Held key.
    press(); assert(!enabled[42] && !enabled[41]);
    available[42] = 0; press(); assert(!numCalls); // No fallback when unavailable.
    available[42] = 1; battery = 0; owned[RPG_BIN_VISIONKEY] = 0; press(); assert(!enabled[42] && !owned[RPG_BIN_VISIONKEY]); // Script owns battery decision.
    enabled[42] = 1; press(); assert(!enabled[42]); // Can turn off with empty battery.
    battery = 100; sithInventory_g_aTypes[42].cog = 0; press(); assert(!numCalls);
    sithInventory_g_aTypes[42].cog = &owned[42];
    player.flags = SITH_TF_DEAD; press(); assert(!numCalls); player.flags = 0;
    active = 0; press(); assert(!numCalls); active = 1;
    Main_bMotsCompat = 1; press(); assert(!numCalls); Main_bMotsCompat = 0;
    reset(); bind(INPUT_FUNC_USEVISION, DIK_K); press(); assert(!numCalls);
    presses[DIK_K] = 1; jkRpg_VisionTick(&player); assert(enabled[42]);
    // Reminder starts at eight seconds and never consumes that first hint on an ineligible frame.
    reset(); bind(INPUT_FUNC_USEVISION, DIK_G);
    memset(owned, 0, sizeof(owned)); memset(enabled, 0, sizeof(enabled));
    memset(available, 0, sizeof(available));
    owned[42] = available[42] = 1; owned[SITHBIN_BATTERY] = 50;
    sithTime_g_secGameTime = 7.99f; jkRpg_VisionReminder(&player, 0); assert(!reminderCount);
    sithTime_g_secGameTime = 8;
    player.flags = SITH_TF_DEAD; jkRpg_VisionReminder(&player, 0); assert(!reminderCount); player.flags = 0;
    active = 0; jkRpg_VisionReminder(&player, 0); assert(!reminderCount); active = 1;
    Main_bMotsCompat = 1; jkRpg_VisionReminder(&player, 0); assert(!reminderCount); Main_bMotsCompat = 0;
    owned[RPG_BIN_VISIONKEY] = 1; jkRpg_VisionReminder(&player, 0); assert(!reminderCount); owned[RPG_BIN_VISIONKEY] = 0;
    enabled[42] = 1; jkRpg_VisionReminder(&player, 0); assert(!reminderCount); enabled[42] = 0;
    owned[SITHBIN_BATTERY] = 0; jkRpg_VisionReminder(&player, 0); assert(!reminderCount); owned[SITHBIN_BATTERY] = 50;
    owned[42] = 0; jkRpg_VisionReminder(&player, 0); assert(!reminderCount); owned[42] = 1;
    available[42] = 0; jkRpg_VisionReminder(&player, 0); assert(!reminderCount); available[42] = 1;
    jkRpg_VisionReminder(&player, 0);
    assert(reminderCount == 1 && !strcmp(reminder, "Press G to use your field light."));
    sithTime_g_secGameTime = 127.99f; jkRpg_VisionReminder(&player, 1); assert(reminderCount == 1);
    sithTime_g_secGameTime = 128; jkRpg_VisionReminder(&player, 0); assert(reminderCount == 1);
    // Pickup hook runs before ChangeInv credits the battery, so it can remind from empty charge.
    owned[SITHBIN_BATTERY] = 0; reset(); bind(INPUT_FUNC_USEVISION, DIK_K);
    jkRpg_VisionReminder(&player, 1);
    assert(reminderCount == 2 && !strcmp(reminder, "Press K to use your field light."));
    sithTime_g_secGameTime = 248; reset(); jkRpg_VisionReminder(&player, 1);
    assert(reminderCount == 3 && strstr(reminder, "Bind Toggle field light in Setup"));
    // Goggles alone do not generate a reminder.
    owned[41] = available[41] = 1; sithTime_g_secGameTime = 368;
    owned[42] = 0; jkRpg_VisionReminder(&player, 1); assert(reminderCount == 3);
    owned[42] = available[42] = 1; bind(INPUT_FUNC_USEVISION, DIK_G);
    jkRpg_VisionReminder(&player, 1);
    assert(reminderCount == 4 && !strcmp(reminder, "Press G to use your field light."));
    // A load can rewind time: no idle repeat, but the next battery pickup can remind again.
    sithTime_g_secGameTime = 10; owned[SITHBIN_BATTERY] = 50;
    jkRpg_VisionReminder(&player, 0); assert(reminderCount == 4);
    jkRpg_VisionReminder(&player, 1); assert(reminderCount == 5);
    // Successful input marks the persistent bin and suppresses all subsequent reminders.
    presses[DIK_K] = 0; press(); assert(owned[RPG_BIN_VISIONKEY] && enabled[42]);
    press(); assert(!enabled[42]); sithTime_g_secGameTime = 1000;
    jkRpg_VisionReminder(&player, 0); jkRpg_VisionReminder(&player, 1); assert(reminderCount == 5);
    // A saved first-use flag must not suppress the one-time house-entry reminder.
    memset(owned, 0, sizeof(owned)); memset(enabled, 0, sizeof(enabled));
    memset(available, 0, sizeof(available)); reset(); bind(INPUT_FUNC_USEVISION, DIK_G);
    owned[42] = available[42] = 1; owned[SITHBIN_BATTERY] = 50;
    owned[RPG_BIN_VISIONKEY] = 1;
    SithSector outside = {257}, entrance = {140}; player.sector = &outside;
    strcpy(world.map_jkl_fname, "03katarn.jkl");
    jkRpg_VisionReminder(&player, 0); assert(reminderCount == 5);
    owned[RPG_BIN_VISIONKEY] = 0; // Even a new player waits for the entrance in mission 3.
    jkRpg_VisionReminder(&player, 0); assert(reminderCount == 5);
    owned[RPG_BIN_VISIONKEY] = 1; player.sector = &entrance;
    player.flags = SITH_TF_DEAD; jkRpg_VisionReminder(&player, 0);
    assert(reminderCount == 5 && owned[RPG_BIN_VISIONKEY] == 1); player.flags = 0;
    owned[SITHBIN_BATTERY] = 0; jkRpg_VisionReminder(&player, 0);
    assert(reminderCount == 5 && owned[RPG_BIN_VISIONKEY] == 1); owned[SITHBIN_BATTERY] = 50;
    jkRpg_VisionReminder(&player, 0);
    assert(reminderCount == 6 && owned[RPG_BIN_VISIONKEY] == 3 && strstr(reminder, "Press G"));
    player.sector = &outside; jkRpg_VisionReminder(&player, 0);
    player.sector = &entrance; jkRpg_VisionReminder(&player, 0); assert(reminderCount == 6);
    // Restoring the saved flags still suppresses the entrance hint, including after key use.
    owned[RPG_BIN_VISIONKEY] = 2; press(); assert(owned[RPG_BIN_VISIONKEY] == 3);
    press(); jkRpg_VisionReminder(&player, 0); assert(reminderCount == 6);
    // Already-lit entry is handled without an unnecessary reminder when the light goes off.
    owned[RPG_BIN_VISIONKEY] = 1; enabled[42] = 1; jkRpg_VisionReminder(&player, 0);
    assert(owned[RPG_BIN_VISIONKEY] == 3 && reminderCount == 6);
    enabled[42] = 0; jkRpg_VisionReminder(&player, 0); assert(reminderCount == 6);
    owned[RPG_BIN_VISIONKEY] = 1; strcpy(world.map_jkl_fname, "04escapehouse.jkl");
    jkRpg_VisionReminder(&player, 0); assert(reminderCount == 6);
    strcpy(world.map_jkl_fname, "03katarn.jkl"); reset();
    jkRpg_VisionReminder(&player, 0);
    assert(reminderCount == 7 && owned[RPG_BIN_VISIONKEY] == 3 && strstr(reminder, "Bind Toggle field light"));
    // Removal only destroys the eight original goggles, never another reward or a reused slot.
    static SithThing things[400]; Template goggles = {"goggles"}, batteryItem = {"battery"};
    static const struct { const char* map; int ids[4]; } cases[] = {
        {"01narshadda.jkl", {141, -1}}, {"02narshadda.jkl", {384, -1}},
        {"04escapehouse.jkl", {301, -1}}, {"06abarons.jkl", {272, -1}},
        {"06bbarons.jkl", {206, 214, 291, 328}}
    };
    world.aThings = things; world.numThingsLoaded = 400;
    for (unsigned m = 0; m < sizeof(cases)/sizeof(cases[0]); ++m) {
        strcpy(world.map_jkl_fname, cases[m].map); memset(things, 0, sizeof(things));
        for (int n = 0; n < 4 && cases[m].ids[n] >= 0; ++n) {
            int id = cases[m].ids[n];
            things[id] = (SithThing){.guid=id, .type=SITH_THING_ITEM, .pTemplate=&goggles};
            things[id+1] = (SithThing){.guid=id+1, .type=SITH_THING_ITEM, .pTemplate=&batteryItem};
        }
        jkRpg_RemoveGoggles(&player); jkRpg_RemoveGoggles(&player); // Idempotent after save/reload.
        for (int n = 0; n < 4 && cases[m].ids[n] >= 0; ++n) {
            int id = cases[m].ids[n]; assert(things[id].flags & SITH_TF_DESTROYED); assert(!things[id+1].flags);
        }
    }
    strcpy(world.map_jkl_fname, "01narshadda.jkl");
    things[141] = (SithThing){.guid=999, .type=SITH_THING_ITEM, .pTemplate=&goggles};
    jkRpg_RemoveGoggles(&player); assert(!things[141].flags);
    things[141].guid = 141; things[141].pTemplate = &batteryItem;
    jkRpg_RemoveGoggles(&player); assert(!things[141].flags);
    things[141].pTemplate = &goggles; world.numThingsLoaded = 141;
    jkRpg_RemoveGoggles(&player); assert(!things[141].flags); world.numThingsLoaded = 400;
    Main_bMotsCompat = 1; jkRpg_RemoveGoggles(&player); assert(!things[141].flags); Main_bMotsCompat = 0;
    active = 0; jkRpg_RemoveGoggles(&player); assert(!things[141].flags); active = 1;
    owned[41] = available[41] = enabled[41] = 1; owned[13] = 79; enabled[42] = 1;
    numCalls = 0; jkRpg_RemoveGoggles(&player);
    assert(numCalls == 1 && calls[0] == 41 && !owned[41] && !available[41] && !enabled[41]);
    assert(owned[13] == 79 && enabled[42]); // Battery and active field light preserved.
    jkRpg_RemoveGoggles(&player); assert(numCalls == 1);
    puts("Field light controls, reminders and original goggles removal passed");
}
'''
read_conf = function("Devices/sithControl.c", "sithControl_ReadConf")
write_conf = function("Devices/sithControl.c", "sithControl_WriteConf")
assert 'hasVisionSetting = 0' in read_conf and '"rpgvisionkey"' in read_conf
assert 'hasVisionSetting = 1;' in read_conf and 'sithControl_MigrateVisionKey(hasVisionSetting)' in read_conf
assert 'stdConffile_WriteLine("rpgvisionkey=1\\n")' in write_conf
assert 'jkRpg_RemoveGoggles(p);' in function("Main/jkRpg.c", "jkRpg_PlayerTick")
assert 'jkRpg_VisionTick(p);' in function("Main/jkRpg.c", "jkRpg_PlayerTick")
strings = (src.parent / "resource/ui/openjkdf2.uni").read_text()
assert '"USEVISION"       0 "Toggle field light"' in strings
assert int(re.search(r'MSGS\s+(\d+)', strings)[1]) == len(re.findall(r'^\s*"[^"\n]+"\s+\d+\s+"', strings, re.M))
overrides = (src.parent / "resource/ui/openjkdf2_i8n.uni").read_text()
for warning in ("COG_00253", "COG_00256"):
    assert re.search(r'"' + warning + r'"\s+0\s+"Battery empty\. Pick up a battery to recharge\."', overrides)
assert int(re.search(r'MSGS\s+(\d+)', overrides)[1]) == len(re.findall(r'^\s*"[^"\n]+"\s+\d+\s+"', overrides, re.M))
scratch = Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-vision-check"
scratch.mkdir(parents=True, exist_ok=True)
cfile, binary = scratch / "vision.c", scratch / "vision"
try:
    cfile.write_text(harness
        + function("Devices/sithControl.c", "sithControl_GetKey")
        + function("Devices/sithControl.c", "sithControl_BindControl") + keyboard
        + function("Devices/sithControl.c", "sithControl_MigrateVisionKey")
        + function("Main/jkRpg.c", "jkRpg_ToggleVisionItem")
        + function("Main/jkRpg.c", "jkRpg_RemoveGoggles")
        + function("Main/jkRpg.c", "jkRpg_VisionTick")
        + function("Main/jkRpg.c", "jkRpg_BindingName")
        + function("Main/jkRpg.c", "jkRpg_VisionReminder") + checks)
    subprocess.run(["cc", "-std=c99", "-w", str(cfile), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
finally:
    cfile.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)
