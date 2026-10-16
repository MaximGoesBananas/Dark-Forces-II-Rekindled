"""Compile and exercise the actual skill and item upgrade arithmetic from jkRpg.c.

Run in WSL: python3 tools/test_skill_upgrades.py ~/src/OpenJKDF2
Covers pickup amounts (health packs, shield recharges, ammo with emergency supplies and weapon
salvage, bacta), Lasting recovery and Emergency treatment, Force capacity/recovery and Force
Healing, the Force powers on Force Speed's scale, the Safer landings threshold and movement speed.
Only the temporary C harness/binary are written under Helm scratch.
"""
import os
import tempfile
import re
import subprocess
import sys
from pathlib import Path

source = (Path(sys.argv[1]) / "src/Main/jkRpg.c").read_text()


def function(name):
    match = re.search(r"static (?:flex_t|int) " + name + r"\(", source)
    body = source.index("{", match.end())
    depth = 0
    for i in range(body, len(source)):
        depth += {"{": 1, "}": -1}.get(source[i], 0)
        if depth == 0:
            return source[match.start():i + 1] + "\n"
    raise ValueError(name)


names = ["IsLow", "MaxHealthBonus", "AmmoShare", "HealthPackShare", "ShieldPackShare", "BactaShare",
         "ShieldCost", "LastingStep", "BactaDue", "ForceHealAmount", "ForceRankClamp", "ForceSeconds",
         "ForceStep", "ForceDamageScale", "ForceScriptRank", "ForceCapacityScale",
         "ForceRegenScale", "LandingDamage"]
defines = "\n".join(re.findall(r"^#define RPG_(?:LOW_SHARE|REGEN_PER_SEC|BACTA_\w+|BASE_SPEED|LETHAL_LANDING|FORCE_SPEED)\s.*$",
                               source, re.M))
harness = r'''
#include <assert.h>
#include <math.h>
#include <stdio.h>
typedef float flex_t;
#define near(a, b) (fabs((double)(a) - (double)(b)) < 1e-4)
enum { SITHBIN_F_JUMP = 21, SITHBIN_F_ABSORB = 28, SITHBIN_F_PROTECTION = 29, SITHBIN_F_GRIP = 31, SITHBIN_F_DEADLYSIGHT = 34 };
'''
checks = r'''
int main(void) {
    // Health: 100, 125, 150, then regeneration without more maximum.
    assert(jkRpg_MaxHealthBonus(0) == 0 && jkRpg_MaxHealthBonus(1) == 25);
    assert(jkRpg_MaxHealthBonus(2) == 50 && jkRpg_MaxHealthBonus(3) == 50);
    assert(RPG_REGEN_PER_SEC == 0.5f);

    // "Low" means strictly below a quarter of the current maximum.
    assert(jkRpg_IsLow(37.4f, 150) && !jkRpg_IsLow(37.5f, 150) && !jkRpg_IsLow(25, 100));

    // Health packs (original 20): 15, 18, 20; Emergency care adds 5 from the first upgrade.
    const float pack = 20, packs[4] = {15, 15, 18, 20}, emergency[4] = {15, 20, 23, 25};
    for (int rank = 0; rank <= 3; rank++) {
        assert(near(pack * jkRpg_HealthPackShare(rank, 0), packs[rank]));
        assert(near(pack * jkRpg_HealthPackShare(rank, 1), emergency[rank]));
    }

    // Shield recharges (original 20): 12, then 18 from Better recharging. Bacta (30): 18, then 30.
    assert(near(20 * jkRpg_ShieldPackShare(0), 12) && near(20 * jkRpg_ShieldPackShare(1), 12));
    assert(near(20 * jkRpg_ShieldPackShare(2), 18) && near(20 * jkRpg_ShieldPackShare(3), 18));
    assert(near(30 * jkRpg_BactaShare(0), 18) && near(30 * jkRpg_BactaShare(1), 30) && near(30 * jkRpg_BactaShare(3), 30));

    // Ammo (original 20): 15 unupgraded, 20 with Better scavenging. Bonuses add 5 each.
    const float ammo = 20;
    assert(near(ammo * jkRpg_AmmoShare(0, 0, 0), 15) && near(ammo * jkRpg_AmmoShare(0, 1, 1), 15));
    assert(near(ammo * jkRpg_AmmoShare(1, 1, 0), 20) && near(ammo * jkRpg_AmmoShare(1, 0, 1), 15));
    assert(near(ammo * jkRpg_AmmoShare(2, 0, 1), 20) && near(ammo * jkRpg_AmmoShare(2, 0, 0), 15));
    assert(near(ammo * jkRpg_AmmoShare(2, 1, 1), 25));
    assert(near(ammo * jkRpg_AmmoShare(3, 0, 0), 20) && near(ammo * jkRpg_AmmoShare(3, 1, 0), 25));
    assert(near(ammo * jkRpg_AmmoShare(3, 0, 1), 25) && near(ammo * jkRpg_AmmoShare(3, 1, 1), 30));

    // Blast resistance: explosions cost 25% fewer shields; other hits unchanged.
    assert(jkRpg_ShieldCost(0, 1) == 1 && jkRpg_ShieldCost(1, 0) == 1 && near(jkRpg_ShieldCost(1, 1), 0.75f));

    // Lasting recovery: 20 more health over six seconds, at any frame rate.
    const float rates[3] = {30, 60, 270};
    for (int r = 0; r < 3; r++) {
        float pending = RPG_BACTA_LASTING, healed = 0, t = 0, dt = 1.0f / rates[r], half = 0;
        while (pending > 0) {
            float step = jkRpg_LastingStep(pending, dt);
            pending -= step; healed += step; t += dt;
            if (t <= 3.0f) half = healed;
        }
        assert(near(healed, 20) && fabs(t - 6.0f) < 2 * dt && fabs(half - 10.0f) < 0.2f);
    }

    // Emergency treatment: alive, strictly below a quarter of the maximum, off cooldown, tank carried.
    assert(jkRpg_BactaDue(37, 150, 0, 1) && !jkRpg_BactaDue(37.5f, 150, 0, 1));
    assert(!jkRpg_BactaDue(37, 150, 0.1f, 1) && !jkRpg_BactaDue(37, 150, 0, 0) && !jkRpg_BactaDue(0.5f, 150, 0, 1));
    assert(RPG_BACTA_COOLDOWN == 10.0f && RPG_BACTA_SECONDS == 6.0f);

    // Force Healing: 40/45/50/60 for the script's 20/40/60/80.
    assert(jkRpg_ForceHealAmount(20) == 40 && jkRpg_ForceHealAmount(40) == 45);
    assert(jkRpg_ForceHealAmount(60) == 50 && jkRpg_ForceHealAmount(80) == 60);

    // Force powers on Force Speed's scale: Speed 1.5x; timed powers 7.5/10/12.5/15 s; Jump and
    // Destruction's radius 1.2-1.5; Grip and Destruction 40/45/50/60 (scale times 40).
    assert(RPG_FORCE_SPEED == 1.5);
    const float seconds[4] = {7.5f, 10, 12.5f, 15}, step[4] = {1.2f, 1.3f, 1.4f, 1.5f}, hits[4] = {40, 45, 50, 60};
    for (int rank = 1; rank <= 4; rank++) {
        assert(near(jkRpg_ForceSeconds(rank), seconds[rank - 1]) && near(jkRpg_ForceStep(rank), step[rank - 1]));
        assert(near(40 * jkRpg_ForceDamageScale(rank), hits[rank - 1]));
        // Scripts see: Absorb, Grip and Deadly Sight rank 2 (half absorbed, 4 squeezes, 3 s of burns),
        // Protection rank 1 (75 damage); Jump and others their real rank.
        assert(jkRpg_ForceScriptRank(SITHBIN_F_ABSORB, rank) == 2 && jkRpg_ForceScriptRank(SITHBIN_F_GRIP, rank) == 2);
        assert(jkRpg_ForceScriptRank(SITHBIN_F_DEADLYSIGHT, rank) == 2 && jkRpg_ForceScriptRank(SITHBIN_F_PROTECTION, rank) == 1);
        assert(jkRpg_ForceScriptRank(SITHBIN_F_JUMP, rank) == rank);
    }
    // An unlearned power stays unlearned; out-of-range ranks are clamped.
    assert(jkRpg_ForceScriptRank(SITHBIN_F_GRIP, 0) == 0 && jkRpg_ForceScriptRank(SITHBIN_F_PROTECTION, 0) == 0);
    assert(near(jkRpg_ForceSeconds(9), 15) && near(jkRpg_ForceStep(0), 1.2f));

    // Force: +25% capacity; recovery x1.25 then x1.5 in total, not during Persuasion.
    for (int rank = 0; rank <= 3; rank++) assert(jkRpg_ForceRegenScale(rank, 1) == 1);
    assert(jkRpg_ForceCapacityScale(0) == 1 && jkRpg_ForceCapacityScale(1) == 1.25f && jkRpg_ForceCapacityScale(3) == 1.25f);
    assert(jkRpg_ForceRegenScale(1, 0) == 1 && jkRpg_ForceRegenScale(2, 0) == 1.25f && jkRpg_ForceRegenScale(3, 0) == 1.5f);
    // Empty-to-full at story Jedi rank 8 (capacity 400, rank / 2 = 4 per second): 100, 125, 100, 83.3 s.
    const float refill[4] = {100, 125, 100, 83.3333f};
    for (int rank = 0; rank <= 3; rank++)
        assert(fabs(400 * jkRpg_ForceCapacityScale(rank) / (4 * jkRpg_ForceRegenScale(rank, 0)) - refill[rank]) < 0.01f);
    // Persuasion at rank 8 with the final upgrade: 4 energy per second, 160 over 40 seconds.
    assert(near(4 * jkRpg_ForceRegenScale(3, 1) * 40, 160));

    // Safer landings (first Endurance upgrade): half of ordinary landing damage; 100 or more stays.
    assert(near(jkRpg_LandingDamage(1, 60), 30) && near(jkRpg_LandingDamage(3, 99.9f), 49.95f));
    assert(jkRpg_LandingDamage(1, 100) == 100 && jkRpg_LandingDamage(3, 400) == 400);
    assert(jkRpg_LandingDamage(0, 60) == 60);
    float lethal = 2.5f + sqrtf(RPG_LETHAL_LANDING / 45.0f); // impact speed of a 100-damage landing
    assert(jkRpg_LandingDamage(3, (lethal - 2.5f) * (lethal - 2.5f) * 45) >= 99.99f);

    // Without Quick feet: about 13% slower (within the 20% limit); Quick feet restores the original.
    assert(near(RPG_BASE_SPEED * 1.15, 1.0) && 1 - RPG_BASE_SPEED > 0.12 && 1 - RPG_BASE_SPEED < 0.14);
    puts("skill upgrade arithmetic passed");
}
'''
scratch = Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-skills-check"
scratch.mkdir(parents=True, exist_ok=True)
cfile = scratch / "skill_check.c"
binary = scratch / "skill_check"
try:
    cfile.write_text(harness + defines + "\n" + "".join(function("jkRpg_" + n) for n in names) + checks)
    subprocess.run(["cc", "-std=c99", "-Wall", str(cfile), "-o", str(binary), "-lm"], check=True)
    subprocess.run([str(binary)], check=True)
finally:
    cfile.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)
