"""Compile the actual Grip boots and Stand firm rules and drive them through simulated ground physics.
Run in WSL: python3 tools/test_movement.py ~/src/OpenJKDF2
"""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

root = Path(sys.argv[1]) / "src"
main = (root / "Main/jkRpg.c").read_text()
for file, call in {
    "Engine/sithPhysics.c": "jkRpg_StopDragScale(pThing, 1)",
    "World/sithExplosion.c": "* jkRpg_PushScale(v4)",
    "World/sithWeapon.c": "* jkRpg_PushScale(receiveThing)",
}.items():
    text = (root / file).read_text()
    assert call in text and '#include "Main/jkRpg.h"' in text, file
assert "* jkRpg_PushScale(damageReceiver)" in (root / "World/sithWeapon.c").read_text()


def function(name):
    start = re.search(r"^flex_t " + name + r"\(", main, re.M).start()
    return main[start:main.index("\n}\n", start) + 3]


defines = "\n".join(re.findall(r"^#define RPG_(?:GRIP_\w+|PUSH_SCALE)\s.*$", main, re.M))
code = r'''
#include <assert.h>
#include <math.h>
#include <stdio.h>
typedef double flex_t;
typedef struct { flex_t x, y, z; } rdVector3;
typedef struct SithThing {
    struct { flex_t maxThrust, extraSpeed; } actorParams;
    struct { rdVector3 vel; flex_t surfDrag, staticDrag; } physicsParams;
} SithThing;
enum { UP_ATHLETICS = 2, UP_ENDURANCE = 17 };
static SithThing player, enemy;
static int athletics, endurance;
static flex_t frameStep = 1.0 / 120;
static int jkRpg_IsActive(SithThing* p) { return p == &player; }
static int jkRpg_Rank(SithThing* p, int up) { return up == UP_ATHLETICS ? athletics : up == UP_ENDURANCE ? endurance : 0; }
''' + defines + "\n" + function("jkRpg_StopDragScale") + function("jkRpg_PushScale") + r'''
// The ground step from sithPhysics_UpdateAttachedThingPhysics and sithPhysics_ApplyDrag on a normal floor.
static void step(SithThing* p, flex_t thrust, flex_t dt)
{
    rdVector3* v = &p->physicsParams.vel;
    int coasting = thrust == 0;
    flex_t speed = hypot(v->x, v->y);
    if (speed > 0) {
        flex_t drag = p->physicsParams.surfDrag * jkRpg_StopDragScale(p, coasting) * dt, mag = coasting ? p->physicsParams.staticDrag : 0;
        if (mag != 0 && speed < mag) v->x = v->y = 0;
        else { if (drag > 1) drag = 1; v->x -= v->x * drag; v->y -= v->y * drag; }
    } else if (!coasting) jkRpg_StopDragScale(p, 0);
    v->x += thrust * dt;
}
// Hold the controls for `held` seconds at `share` of full thrust, release, return seconds until still.
static flex_t stopTime(SithThing* p, flex_t held, flex_t share)
{
    p->physicsParams.vel = (rdVector3){0, 0, 0};
    const flex_t dt = frameStep;
    for (flex_t t = 0; t < held; t += dt) step(p, p->actorParams.maxThrust * share, dt);
    flex_t t = 0;
    while (hypot(p->physicsParams.vel.x, p->physicsParams.vel.y) > 0 && t < 5) { step(p, 0, dt); t += dt; }
    return t;
}
int main(void)
{
    // The player template: maxthrust 2 (13% less without Quick feet), surfdrag 3, staticdrag 0.3.
    player = enemy = (SithThing){{2.0 / 1.15, 0}, {{0, 0, 0}, 3.0, 0.3}};
    for (athletics = 0; athletics <= 3; athletics++) {
        player.actorParams.maxThrust = athletics >= 1 ? 2.0 : 2.0 / 1.15;
        flex_t run = stopTime(&player, 2.0, 1.0), tap = stopTime(&player, 0.15, 1.0);
        flex_t jog = stopTime(&player, 0.4, 1.0), walk = stopTime(&player, 2.0, 0.5);
        if (athletics >= 3) assert(run > 0.10 && run < 0.16);
        else assert(run > 0.15 && run < 0.3);
        int keep = athletics; athletics = 0;                 // taps, short runs and walking keep their feel
        flex_t tap0 = stopTime(&player, 0.15, 1.0), jog0 = stopTime(&player, 0.4, 1.0), walk0 = stopTime(&player, 2.0, 0.5);
        athletics = keep;
        assert(jog0 > 0.05 && fabs(tap - tap0) < 1e-9 && fabs(jog - jog0) < 1e-9 && fabs(walk - walk0) < 1e-9);
    }
    // Compare the same top running speed, with only the boots changing. Check both
    // normal running and Force Speed across representative physics step sizes.
    const flex_t rates[] = {30, 60, 120};
    for (int i = 0; i < 3; ++i) {
        frameStep = 1.0 / rates[i];
        for (int force = 0; force < 2; ++force) {
            player.actorParams.extraSpeed = force ? 1.0 : 0;
            flex_t thrust = 1.0 + player.actorParams.extraSpeed / player.actorParams.maxThrust;
            athletics = 2; flex_t normal = stopTime(&player, 2, thrust);
            athletics = 3; flex_t boots = stopTime(&player, 2, thrust);
            assert(fabs(boots - normal * 0.5) <= frameStep);
            printf("Grip boots %.0f Hz%s: %.4f -> %.4f s (%.1f%%)\n", rates[i], force ? " Force Speed" : "", normal, boots, boots / normal * 100);
        }
    }
    frameStep = 1.0 / 120;
    player.actorParams.extraSpeed = 0;
    // After a boots stop, a push while standing slides normally.
    athletics = 3;
    stopTime(&player, 2.0, 1.0);
    player.physicsParams.vel = (rdVector3){0.5, 0, 0};
    flex_t t = 0;
    while (player.physicsParams.vel.x > 0) { step(&player, 0, 1.0 / 120); t += 1.0 / 120; }
    assert(t > 0.12); // 0.17 s unbraked, 0.04 s braked
    // Force Speed raises the top speed; the boots still recognise running at that speed.
    player.actorParams.extraSpeed = 1.0;
    assert(stopTime(&player, 2.0, 1.0 + 1.0 / player.actorParams.maxThrust) < 0.22);
    player.actorParams.extraSpeed = 0;
    // Enemies and other things never change.
    enemy.physicsParams.vel = (rdVector3){0.6, 0, 0};
    assert(jkRpg_StopDragScale(&enemy, 0) == 1.0 && jkRpg_StopDragScale(&enemy, 1) == 1.0);
    // Stand firm: the third Endurance upgrade halves pushes on the player only.
    for (endurance = 0; endurance <= 3; endurance++)
        assert(jkRpg_PushScale(&player) == (endurance >= 3 ? 0.5 : 1.0) && jkRpg_PushScale(&enemy) == 1.0);
    puts("Grip boots: running stop, taps, walking, later pushes and Force Speed; Stand firm passed");
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix="jk-movement-check-") as tmp:
    path = Path(tmp)
    (path / "check.c").write_text(code)
    subprocess.run(["cc", "-std=c99", "-Wall", "-Wno-unused-function", str(path / "check.c"), "-o", str(path / "check"), "-lm"], check=True)
    subprocess.run([str(path / "check")], check=True)
