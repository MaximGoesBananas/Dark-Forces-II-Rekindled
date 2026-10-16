"""Compile the real lightsaber control rules: release swings, guard, timed deflects, recovery and guard breaks."""
import os
import tempfile
from pathlib import Path
import re
import subprocess
import sys

root = Path(sys.argv[1]) / "src"
weapons = (root / "Main/jkRpgWeapons.c").read_text()
header = (root / "Main/jkRpg.h").read_text()
weapon = (root / "World/sithWeapon.c").read_text()
saber = (root / "Gameplay/jkSaber.c").read_text()


def function(source, signature):
    start = source.index(signature)
    return source[start:source.index("\n}\n", start) + 3]


# Integration: the controls run before the mount-wait return and own the saber's stock buttons;
# both guard sites ask the manual guard; the player's blocked blows strain it; heavy swings cut through.
controls = function(weapon, "int sithWeapon_ProcessWeaponControls(")
assert controls.index("jkRpg_SaberControls(pThing)") < controls.index("sithTime_g_secGameTime < sithWeapon_secMountWait")
assert "sithControl_GetKey(v20, &readInput) && !bSaberControls" in controls
assert "jkRpg_CanBlock(pThing, pThing->weaponParams.flags & SITH_WF_INSTANT_IMPACT)" in weapon
collide = function(saber, "void  jkSaber_UpdateCollision2(")
assert "!jkRpg_CanBlock(resultThing, resultThing->actorParams.flags & SITH_AF_BLEEDS)" in collide
assert "jkRpg_SaberBreaksGuard(pPlayerThing, pCollideInfo->damage)" in collide
assert "rdVector_Dot3(&v52, &local_3c) >= jkRpg_GuardCone(resultThing)" in collide
actor = (root / "World/sithActor.c").read_text()
assert "rdVector_Dot3(&v18, &a1a) < jkRpg_GuardCone(thing2)" in function(actor, "int sithActor_thing_anim_blocked(")
blocked = collide.index("sithCog_ThingSendMessage(resultThing, 0, SITH_MESSAGE_BLOCKED)")
assert blocked < collide.index("jkRpg_OnGuardBlow(resultThing, pCollideInfo->damage)") < collide.index("break;", blocked + 200)

rules = weapons[weapons.index("// ---- Lightsaber controls: pure rules"):weapons.index("// ---- End of lightsaber control rules. ----")]
state = "\n".join(re.findall(r"^static (?:jkRpgSaber jkRpg_saber|flex_t jkRpg_saberUpdated) .*$", weapons, re.M))
glue = "".join(function(weapons, name) for name in (
    "static int jkRpg_SaberFresh(", "int jkRpg_CanBlock(", "flex_t jkRpg_GuardCone(", "int jkRpg_SaberBreaksGuard("))
heavy = re.search(r"^#define RPG_SABER_HEAVY\s+.*$", header, re.M)[0]

harness = r'''
#include <assert.h>
#include <stdio.h>
typedef double flex_t;
typedef struct SithThing { struct { double fov; } actorParams; } SithThing;
enum { SITHBIN_FISTS=1, SITHBIN_LIGHTSABER=10 };
static SithThing player, enemy;
static int Main_bMotsCompat, active=1, held=SITHBIN_LIGHTSABER;
static flex_t sithTime_g_secGameTime;
static int jkRpg_IsActive(SithThing* p) { return active && p==&player; }
static int jkRpg_CurWeapon(SithThing* p) { return held; }
'''
checks = r'''
static jkRpgSaber s;
static flex_t now;
static int step(int attack, int block, int ready) { return jkRpg_SaberStep(&s, attack, block, ready, now, RPG_SABER_RECOVERY); }
static void fresh(void) { jkRpg_SaberReset(&s); now = 10; step(0, 0, 1); }

int main(void) {
    // A click swings once, on release; no swing while the button is down.
    fresh();
    assert(step(1, 0, 1) == RPG_SWING_NONE && !s.charging);
    now += 0.1; assert(step(1, 0, 1) == RPG_SWING_NONE && !s.charging);
    now += 0.02; assert(step(0, 0, 1) == RPG_SWING_NORMAL && s.swung == now);
    now += 0.02; assert(step(0, 0, 1) == RPG_SWING_NONE);

    // Holding draws the saber back and never swings by itself; once charged, release swings heavy.
    fresh();
    for (int i = 0; i <= 300; i++, now += 0.01) {
        assert(step(1, 0, 1) == RPG_SWING_NONE);
        flex_t held = i * 0.01; // the boundaries themselves depend on rounding
        if (held < RPG_SABER_POSE - 0.005 || held > RPG_SABER_POSE + 0.005) assert(s.charging == (held > RPG_SABER_POSE));
        if (held < RPG_SABER_CHARGE - 0.005 || held > RPG_SABER_CHARGE + 0.005) assert(s.charged == (held > RPG_SABER_CHARGE));
    }
    assert(step(0, 0, 1) == RPG_SWING_HEAVY && !s.charging && !s.charged && s.swung == now);
    now += 0.02; assert(step(0, 0, 1) == RPG_SWING_NONE);
    // Released just before the charge completes, it is a normal swing.
    fresh(); step(1, 0, 1); now += RPG_SABER_CHARGE - 0.02; step(1, 0, 1);
    assert(!s.charged && step(0, 0, 1) == RPG_SWING_NORMAL);

    // A press during recovery counts its charge from when the saber is ready again.
    fresh(); step(1, 0, 0); now += 0.8; assert(step(1, 0, 0) == RPG_SWING_NONE && !s.charging);
    now += 0.01; step(1, 0, 1); now += RPG_SABER_CHARGE - 0.1; step(1, 0, 1); assert(!s.charged);
    now += 0.11; step(1, 0, 1); assert(s.charged && step(0, 0, 1) == RPG_SWING_HEAVY);
    // A click released during recovery swings when recovery ends within the buffer, otherwise never.
    fresh(); step(1, 0, 0); now += 0.05; assert(step(0, 0, 0) == RPG_SWING_NONE);
    now += RPG_SABER_BUFFER - 0.1; assert(step(0, 0, 1) == RPG_SWING_NORMAL);
    fresh(); step(1, 0, 0); now += 0.05; step(0, 0, 0);
    now += RPG_SABER_BUFFER + 0.05; assert(step(0, 0, 1) == RPG_SWING_NONE);
    now += 0.05; assert(step(0, 0, 1) == RPG_SWING_NONE);

    // An interrupted button (menu, load, weapon switch) must be released before it charges or swings.
    jkRpg_SaberReset(&s); now = 50;
    for (int i = 0; i < 300; i++, now += 0.01) assert(step(1, 0, 1) == RPG_SWING_NONE && !s.charging);
    assert(step(0, 0, 1) == RPG_SWING_NONE);

    // Timed deflect: only a guard raised just before the bolt arrives; the upgrade doubles the window.
    fresh(); step(0, 1, 1); flex_t raised = now; assert(s.raised == raised);
    now = raised + RPG_PARRY_WINDOW; step(0, 1, 1);
    assert(jkRpg_TimedBlock(&s, now, 0) && jkRpg_TimedBlock(&s, now, 1) && s.raised == raised);
    now = raised + RPG_PARRY_WINDOW + 0.01; step(0, 1, 1);
    assert(!jkRpg_TimedBlock(&s, now, 0) && jkRpg_TimedBlock(&s, now, 1));
    now = raised + RPG_PARRY_UPGRADED + 0.01; step(0, 1, 1); assert(!jkRpg_TimedBlock(&s, now, 1));
    step(0, 0, 1); assert(!jkRpg_TimedBlock(&s, now, 1));         // no guard, no deflect
    step(0, 1, 1); assert(jkRpg_TimedBlock(&s, now, 0));          // raising it again restarts the timing
    assert(!jkRpg_TimedBlock(&s, now - 1, 1));                     // a loaded earlier time

    // The guard: only while the block button is held, never while attacking, charging or recovering.
    fresh(); assert(!s.guard); step(0, 1, 1); assert(s.guard);
    step(1, 1, 1); assert(!s.guard);
    now += 0.05; assert(step(0, 1, 1) == RPG_SWING_NORMAL && !s.guard);
    flex_t swung = now;
    now = swung + RPG_SABER_RECOVERY - 0.01; step(0, 1, 1); assert(!s.guard);
    now = swung + RPG_SABER_RECOVERY; step(0, 1, 1); assert(s.guard);
    step(0, 0, 1); assert(!s.guard);
    // Quicker recovery (half the delay) raises it sooner.
    fresh(); step(1, 1, 1); now += 0.05; assert(jkRpg_SaberStep(&s, 0, 1, 1, now, RPG_SABER_RECOVERY * 0.5) == RPG_SWING_NORMAL);
    now += RPG_SABER_RECOVERY * 0.5; jkRpg_SaberStep(&s, 0, 1, 1, now, RPG_SABER_RECOVERY * 0.5); assert(s.guard);
    // A buffered click keeps the guard down until it swings.
    fresh(); step(1, 1, 0); now += 0.05; step(0, 1, 0); assert(!s.guard);

    // Guard strain: quick heavy blows break the guard within a few blows; calm light blows
    // take about half a minute, so a held guard is never permanent.
    const struct { flex_t damage, every; int breaksOn; } bosses[] = {{30, 0.925, 5}, {45, 0.9, 3}, {40, 0.95, 3}, {40, 1.7, 4}, {20, 1.5, 17}};
    for (int b = 0; b < 5; b++) {
        fresh(); step(0, 1, 1); assert(s.guard);
        int blow = 1;
        while (!jkRpg_GuardStrain(&s, bosses[b].damage, now)) { now += bosses[b].every; blow++; assert(blow < 30); }
        if (blow != bosses[b].breaksOn) fprintf(stderr, "boss %d broke on blow %d\n", b, blow);
        assert(blow == bosses[b].breaksOn && !s.guard && s.strain == 0 && s.broken == now + RPG_GUARD_BROKEN);
        flex_t broke = now;
        now = broke + RPG_GUARD_BROKEN - 0.01; step(0, 1, 1); assert(!s.guard);
        now = broke + RPG_GUARD_BROKEN; step(0, 1, 1); assert(s.guard);
    }
    // Strain recovers over time, never below zero, and a reload (earlier time) recovers nothing.
    fresh(); jkRpg_GuardStrain(&s, 50, now); now += 100; jkRpg_GuardStrain(&s, 10, now); assert(s.strain == 10);
    now -= 50; jkRpg_GuardStrain(&s, 10, now); assert(s.strain == 20);

    // The manual guard replaces the stock flag only for the local JK player holding the saber.
    sithTime_g_secGameTime = 20; jkRpg_saberUpdated = 20; jkRpg_saber.guard = 1;
    assert(jkRpg_CanBlock(&player, 0));
    jkRpg_saber.guard = 0; assert(!jkRpg_CanBlock(&player, 1)); jkRpg_saber.guard = 1;
    held = SITHBIN_FISTS; assert(!jkRpg_CanBlock(&player, 1)); held = SITHBIN_LIGHTSABER;
    sithTime_g_secGameTime = 20.3; assert(!jkRpg_CanBlock(&player, 1)); // controls no longer updating
    sithTime_g_secGameTime = 19; assert(!jkRpg_CanBlock(&player, 1));   // a loaded earlier time
    sithTime_g_secGameTime = 20;
    assert(jkRpg_CanBlock(&enemy, 1) && !jkRpg_CanBlock(&enemy, 0));
    Main_bMotsCompat = 1; assert(!jkRpg_CanBlock(&player, 0) && jkRpg_CanBlock(&player, 1)); Main_bMotsCompat = 0;
    active = 0; assert(!jkRpg_CanBlock(&player, 0)); active = 1;

    // A raised guard covers the front (wider than the stock automatic guard); enemies keep theirs.
    player.actorParams.fov = 0.71; enemy.actorParams.fov = 0.5;
    assert(RPG_GUARD_CONE < 0.71 && RPG_GUARD_CONE > 0 && jkRpg_GuardCone(&player) == RPG_GUARD_CONE);
    assert(jkRpg_GuardCone(&enemy) == 0.5);
    Main_bMotsCompat = 1; assert(jkRpg_GuardCone(&player) == 0.71); Main_bMotsCompat = 0;

    // Only the player's heavy swing cuts through an enemy guard.
    assert(jkRpg_SaberBreaksGuard(&player, RPG_SABER_HEAVY));
    assert(!jkRpg_SaberBreaksGuard(&player, 60) && !jkRpg_SaberBreaksGuard(&enemy, RPG_SABER_HEAVY));
    Main_bMotsCompat = 1; assert(!jkRpg_SaberBreaksGuard(&player, RPG_SABER_HEAVY)); Main_bMotsCompat = 0;
    puts("Saber controls: release swings, wind-up, recovery buffer, manual guard, timed deflect, guard breaks and integration passed");
}
'''
# Poses: the held guard and wind-up outrank the stock block reaction (2/4) and survive kyle.cog
# stopping their track by a stale slot number, without stopping or freezing another animation.
pose_code = "\n".join(re.findall(r"^#define (?:RPG_HEAVY_APEX|RPG_GUARD_FRAME) .*$", weapons, re.M)) + "\n" + "\n".join(
    re.findall(r"^static (?:const char\* const jkRpg_a(?:Heavy|Guard)Key|int jkRpg_aSaberTrack)\[.*$", weapons, re.M)) + "\n" + "".join(
    function(weapons, name) for name in (
        "static rdPuppet* jkRpg_SaberPuppet(", "static rdKeyframe* jkRpg_PoseKey(", "static int jkRpg_PoseHeld(",
        "static void jkRpg_SaberPoseView(", "static void jkRpg_SaberPose(", "static void jkRpg_KeepPose(",
        "static void jkRpg_HoldWindup("))
pose_harness = r"""
#include <assert.h>
#include <stdio.h>
#include <string.h>
#define RDPUPPET_MAX_TRACKS 4
typedef double flex_t;
typedef struct { const char* name; } rdKeyframe;
typedef struct { int status, lowPri, highPri; flex_t speed, playSpeed, field_124; rdKeyframe* keyframe; } rdPuppetTrack;
typedef struct { rdPuppetTrack aTracks[4]; } rdPuppet;
typedef struct { struct { rdPuppet* puppet; } povModel; } jkPlayerInfo;
typedef struct { struct { rdPuppet* puppet; } renderData; jkPlayerInfo* playerInfo; } SithThing;
static rdKeyframe keys[5] = {{"SabVch.key"}, {"KYcharge.key"}, {"SabVblk2.key"}, {"KYblock2.key"}, {"SabVblk0.key"}};
static rdKeyframe* sithKeyFrame_LoadEntry(const char* name) {
    for (int i = 0; i < 5; i++) if (!strcmp(keys[i].name, name)) return &keys[i];
    return NULL;
}
static int plays, stops;
static int sithPuppet_PlayKey(rdPuppet* p, rdKeyframe* k, int lo, int hi, int flags, void* cb) {
    for (int i = 0; i < 4; i++) if (!p->aTracks[i].status) {
        p->aTracks[i] = (rdPuppetTrack){2, lo, hi, 1, 1, 0, k}; plays++; return i; }
    return -1;
}
static void sithPuppet_StopKey(rdPuppet* p, int t, flex_t fade) { p->aTracks[t] = (rdPuppetTrack){0}; stops++; }
static void rdPuppet_FadeInTrack(rdPuppet* p, int t, flex_t s) {}
static void rdPuppet_AdvanceTrack(rdPuppet* p, int t, flex_t f) { p->aTracks[t].field_124 += f; }
"""
pose_checks = r"""
int main(void) {
    rdPuppet pov = {0}, body = {0}; jkPlayerInfo info = {{&pov}}; SithThing p = {{&body}, &info};
    rdPuppet* views[2] = {&pov, &body};
    // The guard plays in both views above the block reaction's priority, on its held frame.
    jkRpg_SaberPose(&p, 1, 1);
    for (int v = 0; v < 2; v++) {
        rdPuppetTrack* t = &views[v]->aTracks[jkRpg_aSaberTrack[2 + v]];
        assert(t->keyframe == &keys[2 + v] && t->lowPri > 2 && t->highPri > 4 && t->field_124 == RPG_GUARD_FRAME && t->speed == 0);
    }
    // A held pose is left alone.
    plays = 0; jkRpg_KeepPose(&p, 1, 0); assert(!plays);
    // kyle.cog stops our first-person slot and its next block reaction takes it: the guard returns
    // on another track and the block reaction keeps playing; stopping the guard leaves it alone.
    int old = jkRpg_aSaberTrack[2];
    pov.aTracks[old] = (rdPuppetTrack){2, 2, 4, 1, 1, 0, &keys[4]};
    jkRpg_KeepPose(&p, 1, 0);
    assert(plays == 1 && jkRpg_aSaberTrack[2] != old && pov.aTracks[jkRpg_aSaberTrack[2]].keyframe == &keys[2]);
    assert(pov.aTracks[jkRpg_aSaberTrack[2]].field_124 == RPG_GUARD_FRAME && pov.aTracks[old].keyframe == &keys[4]);
    stops = 0; jkRpg_SaberPose(&p, 1, 0);
    assert(stops == 2 && pov.aTracks[old].keyframe == &keys[4] && pov.aTracks[old].status == 2);
    assert(jkRpg_aSaberTrack[2] < 0 && jkRpg_aSaberTrack[3] < 0);
    // A lost slot that nothing reused is not stopped again.
    pov.aTracks[old] = (rdPuppetTrack){0};
    jkRpg_SaberPose(&p, 0, 1); old = jkRpg_aSaberTrack[0];
    pov.aTracks[old] = (rdPuppetTrack){0}; stops = 0; jkRpg_SaberPose(&p, 0, 0); assert(stops == 1);
    // The wind-up resumes where the charge has reached, never past its raised frame, and holding
    // it never freezes an animation that took its old slot.
    memset(&pov, 0, sizeof pov); memset(&body, 0, sizeof body);
    jkRpg_SaberPose(&p, 0, 1); old = jkRpg_aSaberTrack[0];
    pov.aTracks[old] = (rdPuppetTrack){2, 2, 4, 1, 1, RPG_HEAVY_APEX + 1, &keys[4]};
    int was = jkRpg_aSaberTrack[0]; jkRpg_aSaberTrack[0] = old; jkRpg_HoldWindup(&p);
    assert(!(pov.aTracks[old].status & 0x10)); jkRpg_aSaberTrack[0] = was;
    jkRpg_KeepPose(&p, 0, 0.4 * RPG_HEAVY_APEX);
    rdPuppetTrack* w = &pov.aTracks[jkRpg_aSaberTrack[0]];
    assert(w->keyframe == &keys[0] && w->highPri > 4 && w->field_124 == 0.4 * RPG_HEAVY_APEX);
    w->status = 0; jkRpg_KeepPose(&p, 0, 5 * RPG_HEAVY_APEX);
    w = &pov.aTracks[jkRpg_aSaberTrack[0]]; assert(w->field_124 == RPG_HEAVY_APEX);
    jkRpg_HoldWindup(&p); assert(w->status & 0x10);
    // No first-person model: nothing plays, nothing crashes.
    info.povModel.puppet = NULL; jkRpg_SaberPose(&p, 1, 1); jkRpg_KeepPose(&p, 1, 0); jkRpg_SaberPose(&p, 1, 0);
    puts("Saber poses: above the block reaction, restored after a stale stop, never stopping or freezing other animations passed");
}
"""
pose_file, pose_binary = Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-saber-guard" / "pose.c", Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-saber-guard" / "pose"
scratch = Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-saber-guard"
scratch.mkdir(parents=True, exist_ok=True)
cfile, binary = scratch / "guard.c", scratch / "guard"
try:
    cfile.write_text(harness + heavy + "\n" + rules + state + "\n" + glue + checks)
    subprocess.run(["cc", "-std=gnu99", "-Wall", "-Wno-unused-function", str(cfile), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
    pose_file.write_text(pose_harness + rules + pose_code + pose_checks)
    subprocess.run(["cc", "-std=gnu99", "-Wall", "-Wno-unused-function", str(pose_file), "-o", str(pose_binary)], check=True)
    subprocess.run([str(pose_binary)], check=True)
finally:
    for path in (cfile, binary, pose_file, pose_binary):
        path.unlink(missing_ok=True)
