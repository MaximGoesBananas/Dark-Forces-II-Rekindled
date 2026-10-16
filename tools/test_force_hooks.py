"""Compile the actual Force power script hooks from jkRpg.c with small stand-ins.

Run in WSL: python3 tools/test_force_hooks.py ~/src/OpenJKDF2
Level scripts also push debris and other non-player things with SetThingVel; the hooks must never
read an inventory from them (the game's inventory read stops the game for a non-player).
Only the temporary C harness/binary are written under Helm scratch.
"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

source = (Path(sys.argv[1]) / "src/Main/jkRpg.c").read_text()


def function(name):
    match = re.search(r"^(?:static )?[\w* ]*?\b" + name + r"\([^;]*?\)\s*\{", source, re.M)
    depth = 0
    for i in range(match.end() - 1, len(source)):
        depth += {"{": 1, "}": -1}.get(source[i], 0)
        if not depth:
            return source[match.start():i + 1] + "\n"
    raise ValueError(name)


names = ["jkRpg_ForceRankClamp", "jkRpg_ForceSeconds", "jkRpg_IsPowerScript",
         "jkRpg_ForceExtraSpeed", "jkRpg_ForceJumpVel", "jkRpg_ForceTimer"]
defines = "\n".join(re.findall(r"^#define RPG_FORCE_SPEED\s.*$", source, re.M))
harness = r'''
#include <assert.h>
#include <math.h>
#include <stdio.h>
typedef float flex_t;
#define near(a, b) (fabs((double)(a) - (double)(b)) < 1e-4)
enum { SITH_THING_ACTOR = 2, SITH_THING_PLAYER = 10 };
enum { SITHBIN_F_JUMP = 21, SITHBIN_F_SPEED = 22, SITHBIN_F_SEEING = 23, SITHBIN_F_PERSUASION = 26,
       SITHBIN_F_BLINDING = 27, SITHBIN_F_ABSORB = 28, SITHBIN_NUMBINS = 200 };
typedef struct { float x, y, z; } rdVector3;
typedef struct { int unused; } sithCog;
typedef struct SithThing { int type; float rank[SITHBIN_NUMBINS];
    struct { float maxThrust, jumpSpeed; } actorParams; struct { rdVector3 vel; } physicsParams; } SithThing;
typedef struct { sithCog* cog; } SithInventoryType;
static SithInventoryType sithInventory_g_aTypes[SITHBIN_NUMBINS];
static SithThing* sithPlayer_g_pLocalPlayerThing;
static int reads;
static int jkRpg_IsActive(SithThing* p) { return p && p == sithPlayer_g_pLocalPlayerThing; }
// The game's own read asserts on a non-player, which stops the Windows game.
static flex_t sithInventory_GetInventory(SithThing* p, int bin) { assert(p->type == SITH_THING_PLAYER); reads++; return p->rank[bin]; }
'''
checks = r'''
// Independent airborne physics integration: normal campaign gravity and player drag.
static float jumpHeight(float velocity, float dt) {
    float height = 0, peak = 0;
    while (velocity > 0) {
        velocity *= 1.0f - 0.5f * dt;
        velocity -= 4.0f * dt;
        height += velocity * dt;
        if (height > peak) peak = height;
    }
    return peak;
}
int main(void) {
    static sithCog jump, speed, seeing, other;
    sithInventory_g_aTypes[SITHBIN_F_JUMP].cog = &jump;
    sithInventory_g_aTypes[SITHBIN_F_SPEED].cog = &speed;
    sithInventory_g_aTypes[SITHBIN_F_SEEING].cog = &seeing;
    static SithThing player = {SITH_THING_PLAYER}, debris = {SITH_THING_ACTOR};
    sithPlayer_g_pLocalPlayerThing = &player;
    player.actorParams.maxThrust = 2.0f; player.actorParams.jumpSpeed = 1.5f;
    player.rank[SITHBIN_F_JUMP] = 1; player.rank[SITHBIN_F_SEEING] = 3;

    // Debris pushed by any script, including the jump script, is left alone and never read.
    rdVector3 v = {1, 2, 3};
    jkRpg_ForceJumpVel(&other, &debris, &v);
    jkRpg_ForceJumpVel(&jump, &debris, &v);
    jkRpg_ForceJumpVel(&jump, 0, &v);
    assert(reads == 0 && v.x == 1 && v.y == 2 && v.z == 3);
    assert(jkRpg_ForceExtraSpeed(&speed, &debris, 1.0f) == 1.0f && reads == 0);

    // Tap and full hold use the full boost. Check resulting HEIGHT, not velocity multiples.
    const float heights[] = {0, 3.0f, 3.6f, 4.4f, 4.9f};
    for (int rank = 1; rank <= 4; rank++) {
        player.rank[SITHBIN_F_JUMP] = rank;
        player.physicsParams.vel.z = 0;
        v = (rdVector3){0.4f, -0.2f, 2.5f + 0.35f * rank};
        jkRpg_ForceJumpVel(&jump, &player, &v);
        float full = v.z;
        assert(near(v.x, 0.4f) && near(v.y, -0.2f));
        for (int hz = 50; hz <= 250; hz += 50) {
            float ratio = jumpHeight(full, 1.0f / hz) / jumpHeight(1.5f, 1.0f / hz);
            assert(fabsf(ratio / heights[rank] - 1.0f) < 0.025f);
        }
        // Half charge scales only the extra boost; existing vertical motion is preserved.
        player.physicsParams.vel.z = 0.25f;
        v.z = 0.25f + 2.5f + 0.175f * rank;
        jkRpg_ForceJumpVel(&jump, &player, &v);
        assert(near(v.z, 0.25f + (1.5f + full) * 0.5f));
        v.z = 0.25f + 2.5f + 0.7f * rank;
        jkRpg_ForceJumpVel(&jump, &player, &v);
        assert(near(v.z, 0.25f + full));
    }
    player.rank[SITHBIN_F_JUMP] = 0;
    v.z = 2.5f;
    jkRpg_ForceJumpVel(&jump, &player, &v);
    assert(near(v.z, 2.5f));
    // Other scripts moving the player are unchanged.
    v.z = 2.85f; jkRpg_ForceJumpVel(&other, &player, &v); assert(near(v.z, 2.85f));
    // Speed: 1.5 times running speed while active; stopping (0) is untouched.
    assert(near(jkRpg_ForceExtraSpeed(&speed, &player, 1.0f), 1.0f) && jkRpg_ForceExtraSpeed(&speed, &player, 0) == 0);
    // Seeing's duration timer by rank (3: 12.5 s); its other timers keep their delay.
    assert(near(jkRpg_ForceTimer(&seeing, 1, 20), 12.5f) && near(jkRpg_ForceTimer(&seeing, 2, 0.5f), 0.5f));
    puts("Force hooks passed");
}
'''
scratch = Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-force-hooks"
scratch.mkdir(parents=True, exist_ok=True)
cfile = scratch / "force_hooks.c"
binary = scratch / "force_hooks"
try:
    cfile.write_text(harness + defines + "\n" + "".join(function(n) for n in names) + checks)
    subprocess.run(["cc", "-std=c99", "-Wall", str(cfile), "-o", str(binary), "-lm"], check=True)
    subprocess.run([str(binary)], check=True)
finally:
    cfile.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)
