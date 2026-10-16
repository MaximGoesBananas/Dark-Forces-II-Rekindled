"""Compile the actual weapon upgrade rules and check their numbers and edge cases.
Run in WSL: python3 tools/test_weapon_upgrades.py ~/src/OpenJKDF2
"""
import os
import tempfile
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1]) / "src"
source = (root / "Main/jkRpgWeapons.c").read_text()
start = source.index("// ---- Upgrade rules")
rules = source[start:source.index("// ---- End of upgrade rules")]

# The engine must route each rule through its hook.
hooks = {
    "World/sithWeapon.c": ["jkRpg_MineTouched(pWeapon, pThing)", "jkRpg_ChargeTime(pThing, mode,",
                           "jkRpg_FireWait(pThing, waitTime)", "jkRpg_OnWeaponExplosion(pWeapon, spawned)"],
    "World/sithActor.c": ["jkRpg_OnDeflect(a1, thing2)", "jkRpg_DamageBeforeShields("],
    "Gameplay/sithInventory.c": ["jkRpg_AmmoCost(pThing, typeId, amount)"],
    "Cog/sithCogFunction.c": ["jkRpg_ScriptTimer(pCog, params.timerIdx,"],
}
for name, calls in hooks.items():
    text = (root / name).read_text()
    for call in calls:
        assert call in text, f"{name} lacks {call}"
# Catch-up shots also get their upgrades (tagging and speed).
fire = (root / "World/sithWeapon.c").read_text()
fire = fire[fire.index("SithThing* sithWeapon_FireProjectile("):]
fire = fire[:fire.index("\n}") + 2]
assert fire.count("jkRpg_OnFire(") == 2
assert "jkRpg_AdjustAim(pShooter, pProjectile, pAimError)" in fire
assert fire.index("sithWeapon_GetAimOrient(") < fire.index("rdMatrix_PreRotate34(&fireOrient, pAimError)")
# The deflection hook must see the original shooter, before the blocker becomes the bolt's parent.
actor = (root / "World/sithActor.c").read_text()
assert actor.index("jkRpg_OnDeflect(a1, thing2)") < actor.index("a1->pParent = thing2;")

harness = r'''
#include <assert.h>
#include <math.h>
#include <stdio.h>
typedef double flex_t;
#define near(a, b) (fabs((a) - (b)) < 1e-9)
'''
checks = r'''
static flex_t wait(int weapon, int rank, flex_t script) {jkRpgMods m; jkRpg_Mods(weapon, rank, &m); return script * m.fireWait;}
static flex_t hit(int weapon, int rank, flex_t base) {jkRpgMods m; jkRpg_Mods(weapon, rank, &m); return base * m.damage;}
int main(void) {
    jkRpgMods m;
    // Firing rates: +25% rate divides the delay by 1.25, +50% by 1.5.
    assert(near(wait(2, 0, 0.5), 0.5) && near(wait(2, 2, 0.5), 0.5) && near(wait(2, 3, 0.5), 0.4));
    assert(near(wait(3, 0, 0.2), 0.2 / 0.75) && near(wait(3, 3, 0.2), 0.2 / 0.75 / 1.25));
    assert(near(wait(6, 3, 0.1), 0.15) && near(wait(7, 1, 1.0), 1.6) && near(wait(7, 2, 1.0), 1.28));
    assert(near(wait(8, 0, 0.8), 0.8) && near(wait(8, 1, 0.8), 0.8) && near(wait(8, 2, 0.8), 0.8 / 1.5) && near(wait(9, 3, 1.2), 1.5));
    assert(near(wait(10, 3, 0.8), 0.8) && near(wait(5, 3, 0.6), 0.6)); // no faster strikes, bowcaster recovery kept
    // Sustained repeater fire doubles the base rate after one second, never beyond.
    flex_t base = wait(6, 3, 0.1);
    jkRpg_Mods(6, 3, &m);assert(near(m.sustained,1.0));
    assert(near(jkRpg_SustainedWait(base, 0, m.sustained), 0.15));
    assert(near(jkRpg_SustainedWait(base, -1, m.sustained), 0.15));
    assert(near(jkRpg_SustainedWait(base, 0.5, m.sustained), 0.10));
    assert(near(jkRpg_SustainedWait(base, 1.0, m.sustained), 0.075));
    assert(near(jkRpg_SustainedWait(base, 60, m.sustained), 0.075));
    jkRpg_Mods(6, 2, &m); assert(m.sustained == 0);
    // Base balance kept: Bryar 0.6, rifle 0.75, repeater 0.85; Bryar +25% on top.
    assert(near(hit(2, 0, 30), 18) && near(hit(2, 1, 30), 22.5) && near(hit(6, 3, 20), 17));
    for (int rank = 0; rank < 3; ++rank) assert(near(hit(3, rank, 30), 22.5));
    assert(near(hit(3, 3, 30), 20.25));
    assert(near((hit(3, 3, 30) / wait(3, 3, 0.2)) / (hit(3, 2, 30) / wait(3, 2, 0.2)), 1.125));
    // Bowcaster: 25% weaker for every bolt, then 1.25 times that.
    assert(near(hit(5, 0, 60), 45) && near(hit(5, 1, 60), 56.25) && near(hit(5, 0, 40), 30) && near(hit(5, 1, 40), 37.5));
    assert(near(hit(5, 3, 60), 56.25));
    // Bryar falloff: half the loss at every flight time, including the long-range minimum.
    flex_t minDamage = 10, rate = 15;
    jkRpg_Mods(2, 2, &m); jkRpg_FocusBolt(30, &minDamage, &rate, m.falloff);
    assert(near(minDamage, 20) && near(rate, 7.5));
    for (flex_t t = 0; t < 5; t += 0.05) {
        flex_t before = fmax(30 - 15 * t, 10), after = fmax(30 - rate * t, minDamage);
        assert(near(30 - after, (30 - before) / 2));
    }
    jkRpg_Mods(2, 1, &m); assert(m.falloff == 1);
    // Concussion: 8/4 cells, 6/3 when upgraded; each mode may fire with exactly its own cost.
    jkRpg_Mods(9, 1, &m); assert(jkRpg_ConcussionCost(0, m.ammo) == 8 && jkRpg_ConcussionCost(1, m.ammo) == 4);
    jkRpg_Mods(9, 2, &m); assert(jkRpg_ConcussionCost(0, m.ammo) == 6 && jkRpg_ConcussionCost(1, m.ammo) == 3);
    // The script refuses below 8 shown cells: shown = cells * 8 / cost.
    for (int mode = 0; mode < 2; mode++)
        for (int cells = 0; cells <= 10; cells++) {
            flex_t cost = jkRpg_ConcussionCost(mode, m.ammo);
            assert(!(cells * 8.0 / cost < 8.0) == (cells >= cost));
        }
    // Thermal and concussion: half self damage, +25% radius (0.45 -> 0.5625, 0.8 -> 1.0).
    jkRpg_Mods(4, 1, &m); assert(m.selfBlast == 0.5 && m.blast == 1 && !m.twin);
    jkRpg_Mods(4, 3, &m); assert(near(0.45 * m.blast, 0.5625) && m.twin);
    jkRpg_Mods(9, 3, &m); assert(near(0.8 * m.blast, 1.0) && m.selfBlast == 0.5 && m.damage == 1);
    // Sequencer: protection first, then faster placement, then mine recovery.
    jkRpg_Mods(8, 0, &m); assert(m.mineBlast == 1 && !m.recover);
    jkRpg_Mods(8, 1, &m); assert(m.mineBlast == 0.35 && !m.recover && m.fireWait == 1);
    jkRpg_Mods(8, 2, &m); assert(m.mineBlast == 0.35 && !m.recover);
    jkRpg_Mods(8, 3, &m); assert(m.recover);
    // Lightsaber: a quarter less blaster damage, deflection, block returns after 0.25 instead of 0.5 seconds.
    jkRpg_Mods(10, 0, &m); assert(m.guard == 1 && !m.deflect && m.block == 1 && m.damage == 1);
    jkRpg_Mods(10, 3, &m); assert(m.guard == 0.75 && m.deflect && near(0.5 * m.block, 0.25));
    // Free repeater rounds count projectiles: one in four, for single rounds and 3-round bursts.
    int count = 0, free = 0;
    for (int i = 0; i < 12; i++) free += jkRpg_FreeShots(&count, 1, 4);
    assert(free == 3 && count == 0);
    free = 0;
    for (int i = 0; i < 4; i++) free += jkRpg_FreeShots(&count, 3, 4);
    assert(free == 3 && count == 0);
    assert(jkRpg_FreeShots(&count, 1, 0) == 0 && count == 0);
    jkRpg_Mods(6, 0, &m); assert(m.freeEvery == 0);
    jkRpg_Mods(6, 1, &m); assert(m.freeEvery == 4 && m.speed == 1);
    jkRpg_Mods(6, 2, &m); assert(m.speed == 1.25);
    // Bowcaster charge: stages at 0.6/1.2 seconds, 0.3/0.6 when twice as fast; a third at 0.9 for full spread.
    jkRpg_Mods(5, 1, &m); assert(jkRpg_BowStages(0.59 * m.charge, m.bolts) == 0 && jkRpg_BowStages(0.61 * m.charge, m.bolts) == 1);
    assert(jkRpg_BowStages(1.21 * m.charge, m.bolts) == 2 && jkRpg_BowStages(5 * m.charge, m.bolts) == 2);
    jkRpg_Mods(5, 2, &m); assert(jkRpg_BowStages(0.29 * m.charge, m.bolts) == 0 && jkRpg_BowStages(0.31 * m.charge, m.bolts) == 1);
    assert(jkRpg_BowStages(0.61 * m.charge, m.bolts) == 2 && jkRpg_BowStages(5 * m.charge, m.bolts) == 2 && m.bolts == 5);
    jkRpg_Mods(5, 3, &m); assert(m.bolts == 7 && jkRpg_BowStages(0.89 * m.charge, m.bolts) == 2);
    assert(jkRpg_BowStages(0.91 * m.charge, m.bolts) == 3 && jkRpg_BowStages(5 * m.charge, m.bolts) == 3);
    assert(1 + 2 * 3 == m.bolts); // centre plus three horizontal pairs
    assert(RPG_BOW_OUTER_YAW == 18 && RPG_BOW_AIM_ERROR == 2);
    // Rail: +25% speed, +25% rate, then a cluster only from the detonating projectile.
    jkRpg_Mods(7, 1, &m); assert(m.speed == 1.25 && !jkRpg_ClusterSize(&m, 1));
    jkRpg_Mods(7, 3, &m); assert(m.speed == 1.25 && jkRpg_ClusterSize(&m, 1) == 4 && jkRpg_ClusterSize(&m, 0) == 0);
    assert(RPG_CLUSTER_DAMAGE < 1 && RPG_CLUSTER_RANGE < 1);
    // Rifle: +25% speed, half spread.
    jkRpg_Mods(3, 2, &m); assert(m.speed == 1.25 && m.spread == 0.5 && near(2.5 * m.spread, 1.25));
    // Fists and unknown bins have no upgrades.
    for (int w = 0; w < 12; w += (w == 1 ? 10 : 1)) {
        jkRpg_Mods(w, 3, &m);
        assert(m.damage == 1 && m.fireWait == 1 && m.speed == 1 && !m.cluster && !m.twin && m.bolts == 5);
    }
    puts("Weapon upgrades: rates, damage, falloff, ammo costs, charge stages, free rounds and clusters passed");
}
'''
scratch = Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-weapon-upgrades"
scratch.mkdir(parents=True, exist_ok=True)
cfile, binary = scratch / "rules.c", scratch / "rules"
try:
    cfile.write_text(harness + rules + checks)
    subprocess.run(["cc", "-std=c99", "-Wall", "-Wno-unused-function", str(cfile), "-lm", "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
finally:
    cfile.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)

# The real volley hook must accept exactly the seven cells the full spread costs.
a = source.index('static void jkRpg_BowcasterVolley(')
b = source.index('\n}', a) + 2
volley = r'''
#include <string.h>
typedef struct { double x,y,z; } rdVector3;
typedef struct { rdVector3 lvec; } rdMatrix34;
typedef struct { int id; struct { rdVector3 vel; } physicsParams; rdMatrix34 orient; } SithThing;
#define SITHBIN_POWER 12
#define RPG_BOWCASTER 5
static int jkRpg_bowSides, extras;
static double jkRpg_bowCharge, cells;
static rdVector3 jkRpg_bowDir, jkRpg_bowPos;
static int jkRpg_IsTemplate(SithThing* t,const char* name) { return t->id==(!strcmp(name,"+crossbowbolt")?1:2); }
static double sithInventory_GetInventory(SithThing* p,int bin) { assert(bin==12); return cells; }
static void sithInventory_ChangeInventory(SithThing* p,int bin,double delta) { assert(bin==12); cells+=delta; }
static void rdMatrix_BuildFromLook34(rdMatrix34* m,const rdVector3* d) { m->lvec=*d; }
static void rdMatrix_PreRotate34(rdMatrix34* m,const rdVector3* d) {}
static double rdVector_Len3(rdVector3* d) { return sqrt(d->x*d->x+d->y*d->y+d->z*d->z); }
static void rdVector_Scale3(rdVector3* d,const rdVector3* v,double scale) { *d=(rdVector3){v->x*scale,v->y*scale,v->z*scale}; }
static SithThing* jkRpg_FireExtra(SithThing* p,SithThing* t,const rdVector3* d,rdVector3* pos,rdVector3 pyr,double scale,int flags,int extra,int weapon,const jkRpgMods* m) {
    assert(pyr.x==0 && fabs(pyr.y)==RPG_BOW_OUTER_YAW && weapon==5);
    extras++; return p;
}
'''
volley_checks = r'''
int main(void) {
    SithThing player={0}, side={.id=2}, centre={.id=1}, fired={.physicsParams={{0,5,0}}};
    rdVector3 dir={0,1,0}, pos={0}; jkRpgMods m; jkRpg_Mods(5,3,&m);
    for(int available=0;available<=8;available++) {
        cells=available; extras=0; jkRpg_bowCharge=2; jkRpg_bowSides=3;
        jkRpg_BowcasterVolley(&player,&side,&fired,&dir,&pos,&m);
        assert(fired.physicsParams.vel.y==5); // the original outer row is never redirected
        assert(extras==(available>=3?2:0)); // two reserved for original outer pair, one for extras
        assert(cells==available-(available>=3?1:0));
    }
    cells=3; extras=0; jkRpg_bowSides=3; jkRpg_bowCharge=1.3;
    jkRpg_BowcasterVolley(&player,&side,&fired,&dir,&pos,&m); assert(!extras && cells==3);
    jkRpg_bowSides=3;
    jkRpg_BowcasterVolley(&player,&centre,&fired,&dir,&pos,&m); assert(!jkRpg_bowSides && !extras);
    puts("Bowcaster volley: exact seven-cell charge, low ammo, partial charge and volley reset passed");
}
'''
try:
    cfile.write_text(harness + rules + volley + source[a:b] + volley_checks)
    subprocess.run(['cc', '-std=c99', str(cfile), '-lm', '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
finally:
    cfile.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)


# Compile the actual projectile preparation: both bow modes and extra bolts share it.
a = source.index('static void jkRpg_PrepareProjectile(')
b = source.index('\n}', a) + 2
spread = r"""
typedef struct {double x,y,z;} rdVector3;
typedef struct {rdVector3 lvec;} rdMatrix34;
typedef struct {int moveType,type;struct {rdVector3 vel;} physicsParams;
    struct {int flags;double damage,minDamage,rate;} weaponParams;rdMatrix34 orient;} SithThing;
enum {RPG_BOWCASTER=5,SITH_MT_PHYSICS=1,SITH_THING_WEAPON=2,SITH_WF_DAMAGE_DECAY=4};
static int randomIndex,rotations,tags;static rdVector3 lastError;
static double _frand(void){return randomIndex++%2?1:0;}
static void jkRpg_Tag(SithThing* p,int weapon){tags++;}
static void rdVector_Rotate3Acc(rdVector3* v,const rdVector3* error){rotations++;lastError=*error;}
static double rdVector_Normalize3Acc(rdVector3* v){double n=sqrt(v->x*v->x+v->y*v->y+v->z*v->z);if(n){v->x/=n;v->y/=n;v->z/=n;}return n;}
static void rdMatrix_BuildFromLook34(rdMatrix34* m,const rdVector3* v){assert(fabs(v->x*v->x+v->y*v->y+v->z*v->z-1)<1e-6);m->lvec=*v;}
static void rdVector_Scale3Acc(rdVector3* v,double scale){v->x*=scale;v->y*=scale;v->z*=scale;}
"""
spread_checks = r"""
int main(void){
    jkRpgMods m;jkRpg_Mods(5,0,&m);
    SithThing p={.moveType=1,.type=2,.physicsParams={{0,5,0}}};
    jkRpg_PrepareProjectile(&p,5,&m);
    assert(tags==1 && rotations==1 && lastError.x==-2 && lastError.y==2 && !lastError.z);
    assert(p.physicsParams.vel.y==5 && p.orient.lvec.y==1);
    jkRpg_PrepareProjectile(&p,3,&m);assert(rotations==1);
    p.moveType=0;jkRpg_PrepareProjectile(&p,5,&m);assert(rotations==1);
    jkRpg_PrepareProjectile(NULL,5,&m);assert(tags==3);
    puts("Bowcaster aim variation, normalized orientation and exclusions passed");
}
"""
try:
    cfile.write_text(harness + rules + spread + source[a:b] + spread_checks)
    subprocess.run(['cc', '-std=c99', str(cfile), '-lm', '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
finally:
    cfile.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)

# Concussion scripts supply zero aim error: multiplying it cannot create spread.
a = source.index('void jkRpg_AdjustAim(')
b = source.index('\n}', a) + 2
aim = r'''
#include <string.h>
#define RPG_CONCUSSION 9
typedef struct { double x,y,z; } rdVector3;
typedef struct { int weapon, rank; } SithThing;
static SithThing player={9,0}, enemy={9,0}, primary, alternate, force;
static double randomValues[2];
static int draws;
static double _frand(void){assert(draws<2);return randomValues[draws++];}
static int jkRpg_IsActive(SithThing* p){return p==&player;}
static int jkRpg_CurWeapon(SithThing* p){return p->weapon;}
static void jkRpg_GetMods(SithThing* p,int weapon,jkRpgMods* m){jkRpg_Mods(weapon,p->rank,m);}
static void rdVector_Scale3Acc(rdVector3* v,double s){v->x*=s;v->y*=s;v->z*=s;}
static int jkRpg_IsTemplate(SithThing* p,const char* name){
    return p && ((!strcmp(name,"+concbullet") && p==&primary) || (!strcmp(name,"+concblast2") && p==&alternate));
}
'''
aim_checks = r'''
int main(void){
    for(int rank=0;rank<=3;rank++)
    for(int x=0;x<=2;x++)for(int y=0;y<=2;y++){
        player.rank=rank;draws=0;randomValues[0]=x*0.5;randomValues[1]=y*0.5;
        rdVector3 error={0,0,0};
        jkRpg_AdjustAim(&player,&primary,&error);
        assert(draws==2 && near(error.x,(x-1)*2.5) && near(error.y,(y-1)*2.5) && error.z==0);
    }
    draws=0;rdVector3 error={1,2,3};
    jkRpg_AdjustAim(&enemy,&primary,&error);
    jkRpg_AdjustAim(NULL,&primary,&error);
    jkRpg_AdjustAim(&player,&primary,NULL);
    jkRpg_AdjustAim(&player,&force,&error);
    jkRpg_AdjustAim(&player,&alternate,&error);
    jkRpg_AdjustAim(&player,NULL,&error);
    assert(!draws && error.x==1 && error.y==2 && error.z==3);
    player.weapon=3;player.rank=2;
    jkRpg_AdjustAim(&player,&primary,&error);
    assert(!draws && error.x==0.5 && error.y==1 && error.z==1.5);
    puts("Concussion spread: primary only, all ranks, symmetric bounds and exclusions passed");
}
'''
try:
    cfile.write_text(harness + rules + aim + source[a:b] + aim_checks)
    subprocess.run(['cc', '-std=c99', str(cfile), '-lm', '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
finally:
    cfile.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)
