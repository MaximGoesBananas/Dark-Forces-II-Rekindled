"""Exercise the 1-10 sensitivity curve and unchanged/inversion-only Setup application."""
import os
import tempfile
import re
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1]) / "src"
source = (root / "Gui/jkGUISetup.c").read_text()


def function(name):
    match = re.search(r"^static [\w* ]+\b" + name + r"\([^;]*?\)\n\{", source, re.M)
    return source[match.start():source.index("\n}", match.end()) + 2] + "\n"


defines = re.search(r"^#define RPGSETUP_MOUSE_STEPS\s+.*$", source, re.M)[0]
assert 'Dpi' not in source and 'u"DPI"' not in source
assert 'jkGuiSetup_ApplyMouse();' in function('jkGuiSetup_Apply')
assert 'u"%.1f", 1.0 + v * 0.1' in source
harness = r'''
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
typedef float flex_t;
typedef uint16_t char16_t;
static int jkGuiSetup_loadedMouseStep;
enum {RPGS_MOUSE, RPGC_INVERT};
typedef struct {int selectedTextEntry,boxChecked;} jkGuiElement;
static jkGuiElement slider,check;
static jkGuiElement* jkGuiSetup_Slider(int which){return &slider;}
static jkGuiElement* jkGuiSetup_Check(int which){return &check;}
static float turn=.04f,pitch=.073217f;
static int inverted,axisWrites,invertWrites;
static int sithControl_GetMouseInverted(void){return inverted;}
static void sithControl_SetMouseInverted(int value){inverted=value;invertWrites++;}
static void sithControl_SetMouseLook(float value,int inv){turn=pitch=value;inverted=inv;axisWrites++;}
'''
checks = r'''
int main(void) {
    float prior = 0;
    for (int i = 0; i <= RPGSETUP_MOUSE_STEPS; i++) {
        float value = jkGuiSetup_MouseFromStep(i);
        assert(value > prior && jkGuiSetup_MouseToStep(value) == i);
        if (prior) assert(fabs(value / prior - pow(2, 0.1)) < 0.000001);
        prior = value;
    }
    int low = jkGuiSetup_MouseToStep(0.04f);
    assert(fabs(jkGuiSetup_MouseFromStep(low) - 0.04f) < 0.000001);
    assert(low == 40); // 0.04 actual is displayed as 5.0.
    assert(jkGuiSetup_MouseFromStep(low + 1) - 0.04f < 0.003f);
    assert(jkGuiSetup_MouseToStep(0.16f) == low + 20);
    assert(RPGSETUP_MOUSE_STEPS == 90); // 1.0 through 10.0 in 0.1 steps.
    assert(jkGuiSetup_MouseFromStep(-1) == jkGuiSetup_MouseFromStep(0));
    assert(jkGuiSetup_MouseToStep(NAN) == 0);
    assert(jkGuiSetup_MouseToStep(INFINITY) == RPGSETUP_MOUSE_STEPS);
    const float existing[] = {0.04f, 0.043217f, 0.4f, 0.0001f, 5.0f};
    for (int i = 0; i < 5; i++) {
        jkGuiSetup_loadedMouseStep = jkGuiSetup_MouseToStep(existing[i]);
        slider.selectedTextEntry=jkGuiSetup_loadedMouseStep;
        turn=existing[i];pitch=.073217f;check.boxChecked=inverted=1;
        axisWrites=invertWrites=0;
        jkGuiSetup_ApplyMouse();
        assert(turn==existing[i] && pitch==.073217f && !axisWrites && !invertWrites);
        check.boxChecked=0;jkGuiSetup_ApplyMouse();
        assert(turn==existing[i] && pitch==.073217f && !axisWrites && invertWrites==1 && !inverted);
        slider.selectedTextEntry=jkGuiSetup_loadedMouseStep ? jkGuiSetup_loadedMouseStep-1 : 1;
        jkGuiSetup_ApplyMouse();
        assert(axisWrites==1 && turn==pitch && turn==jkGuiSetup_MouseFromStep(slider.selectedTextEntry));
    }
    puts("1-10 sensitivity, proportional steps, exact independent axes and inversion-only Apply passed");
}
'''
scratch = Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-mouse-controls"
scratch.mkdir(parents=True, exist_ok=True)
cfile, binary = scratch / "setup.c", scratch / "setup"
try:
    cfile.write_text(harness + defines + "\n" + "".join(function(name) for name in
        ("jkGuiSetup_MouseFromStep", "jkGuiSetup_MouseToStep", "jkGuiSetup_ApplyMouse")) + checks)
    subprocess.run(["cc", "-std=c11", str(cfile), "-lm", "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
finally:
    cfile.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)
