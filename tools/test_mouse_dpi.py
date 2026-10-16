"""Check passive legacy DPI persistence and actual raw sensitivity/inversion controls."""
import os
import tempfile
import re
import subprocess
import sys
from pathlib import Path

src = Path(sys.argv[1]) / 'src'
source = (src / 'Devices/sithControl.c').read_text()


def function(name):
    match = re.search(r'^(?:static )?[\w* ]*?\b' + name + r'\([^;]*?\)\n\{', source, re.M)
    if not match:
        raise ValueError(name)
    start = match.end() - 1
    depth = 0
    for i in range(start, len(source)):
        depth += {'{': 1, '}': -1}.get(source[i], 0)
        if not depth:
            return source[match.start():i + 1] + '\n'
    raise ValueError(name)


inputs = {}
for k, v in re.findall(r'\b(INPUT_FUNC_\w+) = (\d+)', (src / 'types_enums.h').read_text()):
    inputs.setdefault(k, v)
harness = r'''
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
#include <math.h>
#include <float.h>
#define _memset memset
#define _strcmp strcmp
#define _sscanf sscanf
#define _atoi atoi
#define _atof atof
#define SITH_ASSERTREL assert
#define QOL_IMPROVEMENTS 1
#define JK_NUM_KEYS 300
#define JK_NUM_AXES 16
typedef float flex_t;
typedef double flex_d_t;
enum { ''' + ', '.join(f'{k}={v}' for k, v in inputs.items()) + r''' };
enum { AXIS_MOUSE_X=12, AXIS_MOUSE_Y=13, AXIS_JOY1_X=0, AXIS_JOY1_Y=1,
       INPUT_MAPPING_FLAG_AXIS_REVERSED=4, INPUT_MAPPING_FLAG_RAW_AXIS=8,
       INPUT_MAPPING_FLAG_DXKEY=2, DIK_K=37, DIK_F9=67 };
typedef struct { int flags; unsigned dxKeyNum; float binaryAxisVal; } stdControlKeyInfoEntry;
typedef struct { unsigned numEntries; stdControlKeyInfoEntry aEntries[8]; } stdControlKeyInfo;
static stdControlKeyInfo sithControl_aInputFuncToKeyinfo[INPUT_FUNC_MAX];
static int sithControl_inputFuncToControlType[INPUT_FUNC_MAX];
static int sithWeapon_controlOptions;
''' + re.search(r'^static int sithControl_mouseDpi = .*$', source, re.M)[0] + r'''
static double counts[16];
static double stdControl_ReadAxisRaw(int axis) { return counts[axis]; }
static void stdControl_Reset(void) {}
static void sithControl_RegisterKeyboardBindings(void) {}
static void sithControl_MapDefaultsJoystick(void) {}
static int controllerMigrations;
static void sithControl_RekindledControllerBindings(void) {controllerMigrations++;}
static stdControlKeyInfoEntry* sithControl_BindAxis(int f, int axis, int flags) {
    stdControlKeyInfo* keys = &sithControl_aInputFuncToKeyinfo[f];
    if (keys->numEntries == 8) return NULL;
    stdControlKeyInfoEntry* e = &keys->aEntries[keys->numEntries++];
    *e = (stdControlKeyInfoEntry){flags | 1, axis, 0}; return e;
}
static void sithControl_BindControl(int f, int key, int flags) {}
static void sithControl_RegisterMouseBindings(void) {
    sithControl_BindAxis(INPUT_FUNC_TURN, AXIS_MOUSE_X, 12)->binaryAxisVal = 0.04f;
    sithControl_BindAxis(INPUT_FUNC_PITCH, AXIS_MOUSE_Y, 12)->binaryAxisVal = 0.04f;
}
static void sithControl_MigrateBactaKey(int setting) {}
static void sithControl_MigrateVisionKey(int setting) {}
static struct { int numArgs; struct { char* key; char* value; } aArgs[8]; } stdConffile_g_entry;
static const char* conf;
static char line[256], written[8192];
static int failDpiWrite;
static int stdConffile_ReadArgs(void) {
    if (!*conf) return 0;
    int i = 0; while (*conf && *conf != '\n') line[i++] = *conf++;
    if (*conf) conf++;
    line[i] = 0; stdConffile_g_entry.numArgs = 0;
    char* eq = strchr(line, '=');
    if (eq) {
        *eq++ = 0; stdConffile_g_entry.numArgs = 1;
        stdConffile_g_entry.aArgs[0].key = line; stdConffile_g_entry.aArgs[0].value = eq;
    } else {
        for (char* token = strtok(line, " "); token; token = strtok(NULL, " ")) {
            int n = stdConffile_g_entry.numArgs++;
            stdConffile_g_entry.aArgs[n].key = stdConffile_g_entry.aArgs[n].value = token;
        }
    }
    return 1;
}
static int stdConffile_Printf(const char* fmt, ...) {
    if (failDpiWrite && strstr(fmt, "rpgmousedpi")) return 0;
    va_list args; va_start(args, fmt);
    vsnprintf(written + strlen(written), sizeof(written) - strlen(written), fmt, args);
    va_end(args); return 1;
}
static void stdConffile_WriteLine(const char* line) { strcat(written, line); }
'''
checks = r'''
static void near(float actual, float expected) { assert(fabsf(actual-expected) < 0.0001f); }
static void load(const char* text) { conf = text; assert(sithControl_ReadConf()); }
int main(void) {
    for (int f = 0; f < INPUT_FUNC_MAX; f++) sithControl_inputFuncToControlType[f] = 5;
    sithControl_DefaultInit(); assert(sithControl_mouseDpi == 800);
    near(sithControl_GetMouseSensitivity(), 0.04f);
    // Legacy DPI metadata never rescales saved axis values, including independent axes.
    load("flags=6\nrpgmousedpi=1600\nbind 1 12 0xd 0.04\nbind 8 13 0xd 0.073217\nend.\n");
    assert(sithControl_mouseDpi == 1600); near(sithControl_GetMouseSensitivity(), 0.04f);
    stdControlKeyInfoEntry* pitchEntry=sithControl_FindMouseEntry(INPUT_FUNC_PITCH,AXIS_MOUSE_Y);
    assert(pitchEntry->binaryAxisVal == 0.073217f);
    counts[12]=1600; counts[13]=800;
    float yaw=sithControl_GetAxis(INPUT_FUNC_TURN), pitch=sithControl_GetAxis(INPUT_FUNC_PITCH);
    sithControl_SetMouseInverted(1);
    near(sithControl_GetAxis(INPUT_FUNC_TURN),yaw); near(sithControl_GetAxis(INPUT_FUNC_PITCH),-pitch);
    assert(pitchEntry->binaryAxisVal==0.073217f && sithControl_GetMouseInverted());
    sithControl_SetMouseInverted(0);
    assert(pitchEntry->binaryAxisVal==0.073217f && !sithControl_GetMouseInverted());
    assert(sithControl_WriteConf()); assert(strstr(written,"rpgmousedpi=1600\n"));
    assert(strstr(written,"rpgcontroller=1\n"));
    int beforeReload=controllerMigrations;
    char saved[8192];strcpy(saved,written);load(saved);
    assert(controllerMigrations==beforeReload);
    near(sithControl_GetMouseSensitivity(),0.04f);
    near(sithControl_FindMouseEntry(INPUT_FUNC_PITCH,AXIS_MOUSE_Y)->binaryAxisVal,0.073217f);
    // Explicit sensitivity changes use actual multipliers regardless of old DPI metadata.
    sithControl_SetMouseLook(0.08f,1);
    near(sithControl_GetMouseSensitivity(),0.08f);assert(sithControl_mouseDpi==1600);
    near(sithControl_GetAxis(INPUT_FUNC_TURN),2*yaw);near(sithControl_GetAxis(INPUT_FUNC_PITCH),-2*pitch);
    const float invalid[]={0,-0.1f,NAN,INFINITY,-INFINITY};
    for(unsigned i=0;i<sizeof(invalid)/sizeof(*invalid);i++) {
        stdControlKeyInfo unchanged[INPUT_FUNC_MAX];memcpy(unchanged,sithControl_aInputFuncToKeyinfo,sizeof(unchanged));
        sithControl_SetMouseLook(invalid[i],0);
        assert(!memcmp(unchanged,sithControl_aInputFuncToKeyinfo,sizeof(unchanged)));
    }
    load("flags=6\nbind 1 12 0xd 0.173\nbind 8 13 0xd 0.173\nend.\n");
    assert(sithControl_mouseDpi==800);near(sithControl_GetMouseSensitivity(),0.173f);
    const char* invalidDpi[]={"99","64001","-1","0","garbage","1600junk","4294968096","999999999999999999999"};
    for(unsigned i=0;i<sizeof(invalidDpi)/sizeof(*invalidDpi);i++) {
        char bad[128];snprintf(bad,sizeof(bad),"flags=6\nrpgmousedpi=%s\nend.\n",invalidDpi[i]);
        load(bad);assert(sithControl_mouseDpi==800);
    }
    conf="bad\n";assert(!sithControl_ReadConf() && sithControl_mouseDpi==800);
    failDpiWrite=1;written[0]=0;assert(!sithControl_WriteConf());
    puts("Passive DPI compatibility, actual sensitivity, independent axes, inversion and profile read/write passed");
}
'''
functions = ['sithControl_ReadConf', 'sithControl_WriteConf', 'sithControl_MouseSensitivity',
             'sithControl_GetAxis', 'sithControl_FindMouseEntry', 'sithControl_GetMouseSensitivity',
             'sithControl_GetMouseInverted', 'sithControl_SetMouseInverted', 'sithControl_SetMouseLook',
             'sithControl_DefaultInit']
scratch = Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-mouse-dpi-check"
scratch.mkdir(parents=True, exist_ok=True)
cfile, binary = scratch / 'mouse.c', scratch / 'mouse'
try:
    bounds = '\n'.join(re.findall(r'^#define SITH_MOUSE_DPI_(?:MIN|MAX) .*$', (src / 'Devices/sithControl.h').read_text(), re.M))
    cfile.write_text(bounds + '\n' + harness + ''.join(function(name) for name in functions) + checks)
    subprocess.run(['cc', '-std=c99', '-w', str(cfile), '-lm', '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
finally:
    cfile.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)
