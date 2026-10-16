"""Check the actual upgrade table, equipment discovery and the old-save refund.
Run in WSL: python3 tools/test_upgrade_data.py ~/src/OpenJKDF2
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

main = Path(sys.argv[1]) / "src/Main"
source = (main / "jkRpg.c").read_text()
header = (main / "jkRpgInternal.h").read_text().replace('#include "types.h"', "")


def function(name):
    start = re.search(r"^(?:static )?[\w *]+\b" + name + r"\([^;\n]*\)\s*(?:\{|$)", source, re.M).start()
    line = source[start:source.index("\n", start)]
    end = start + len(line) if line.endswith("}") else source.index("\n}\n", start) + 2
    return source[start:end] + "\n"


def block(start, end):
    a = source.index(start)
    return source[a:source.index(end, a) + len(end)] + "\n"


defines = "\n".join(re.findall(r"^#define RPG_(?:BIN_\w+|SLOTS|DATA_VERSION|MAX_LEVEL)\s+\d+.*$", source, re.M))
harness = r'''
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <strings.h>
#define __strcmpi strcasecmp
static int Main_bMotsCompat;
static struct { const char* map_jkl_fname; } world, *sithWorld_g_pCurrentWorld = &world;
typedef double flex_t;
typedef int stdFont;
typedef struct SithThing { struct { flex_t health, maxHealth; } actorParams; } SithThing;
enum { SITHBIN_ENERGY = 11, SITHBIN_POWER = 12, SITHBIN_FORCEMANA = 14, SITHBIN_RAILCHARGES = 15,
       SITHBIN_JEDI_RANK = 20, SITHBIN_BACTATANK = 40, SITHBIN_IRGOGGLES = 41, SITHBIN_FIELDLIGHT = 42,
       SITHBIN_SHIELDS = 60 };
''' + header + r'''
static flex_t inv[200];
static struct { flex_t max; } sithInventory_g_aTypes[200];
static int printed;
static flex_t sithInventory_GetInventory(SithThing* p, int bin) { return inv[bin]; }
static flex_t sithInventory_SetInventory(SithThing* p, int bin, flex_t v)
{
    if (sithInventory_g_aTypes[bin].max > 0 && v > sithInventory_g_aTypes[bin].max) v = sithInventory_g_aTypes[bin].max;
    return inv[bin] = v;
}
static flex_t sithInventory_ChangeInventory(SithThing* p, int bin, flex_t v) { return sithInventory_SetInventory(p, bin, inv[bin] + v); }
static void jkRpg_ApplyStats(SithThing* p)
{
    p->actorParams.maxHealth = 100;
    sithInventory_g_aTypes[SITHBIN_SHIELDS].max = 100;
}
static void jkRpg_Print(const char* fmt, ...) { printed++; }
static const char* jkRpg_MenuHint(void) { return "PRESS K"; }
enum { RPG_SOUND_UPGRADE, RPG_SOUND_UNDO };
static void jkRpg_PlaySound(int sound) {}
'''
code = (defines + harness
        + block("const char* const jkRpg_aPageNames", ";")
        + block("const jkRpgUpgrade jkRpg_aUpgrades[UP_COUNT] = {", "\n};")
        + function("jkRpg_Get") + function("jkRpg_Rank")
        + function("jkRpg_OwnsTier") + function("jkRpg_NextTier")
        + block("static struct { int up, rank, lightGap, raised; } jkRpg_aUndo", "jkRpg_aUndo[UP_COUNT];")
        + "static int jkRpg_numUndo;\n"
        + function("jkRpg_FoundBin") + function("jkRpg_Discover") + function("jkRpg_IsFound")
        + function("jkRpg_Migrate") + function("jkRpg_RaisedThisMission") + function("jkRpg_CanSpend")
        + function("jkRpg_SetRank") + function("jkRpg_Spend") + function("jkRpg_FindUndo")
        + function("jkRpg_Undo") + function("jkRpg_CanUndo") + function("jkRpg_UndoTier") + function("jkRpg_Toggle") + r'''
static void reset(SithThing* p)
{
    memset(inv, 0, sizeof(inv));
    memset(sithInventory_g_aTypes, 0, sizeof(sithInventory_g_aTypes));
    for (int bin = 0; bin < 200; bin++) sithInventory_g_aTypes[bin].max = 1e9;
    sithInventory_g_aTypes[SITHBIN_SHIELDS].max = 200; // the old Shields upgrades raised the limit
    sithInventory_g_aTypes[RPG_BIN_POINTS].max = RPG_MAX_LEVEL;
    p->actorParams.maxHealth = p->actorParams.health = 100;
    printed = 0;
    jkRpg_numUndo = 0;
    sithWorld_g_pCurrentWorld = &world; world.map_jkl_fname = "01narshadda.jkl"; Main_bMotsCompat = 0;
}

int main(void)
{
    SithThing p;
    // Table: three upgrades each, grouped in page order, descriptions without numbers.
    int lastPage = 0, pageSeen[PAGE_COUNT] = {0};
    for (int up = 0; up < UP_COUNT; up++) {
        const jkRpgUpgrade* u = &jkRpg_aUpgrades[up];
        // Grouped in page order; Endurance is appended to keep earlier save and picture slots.
        assert(u->name && *u->name && (u->page >= lastPage || up == UP_ENDURANCE) && u->page < PAGE_COUNT);
        if (up != UP_ENDURANCE) lastPage = u->page;
        pageSeen[u->page] = 1;
        for (int i = 0; i < RPG_MAX_RANK; i++) {
            assert(u->nodes[i].name && *u->nodes[i].name && u->nodes[i].desc && *u->nodes[i].desc);
            for (const char* c = u->nodes[i].desc; *c; c++) assert(!(*c >= '0' && *c <= '9') && *c != '%');
            for (int other = 0; other <= up; other++)
                for (int j = 0; j < RPG_MAX_RANK; j++)
                    if (other != up || j != i) assert(strcmp(u->nodes[i].name, jkRpg_aUpgrades[other].nodes[j].name));
        }
    }
    for (int page = 0; page < PAGE_COUNT; page++) assert(pageSeen[page] && jkRpg_aPageNames[page]);
    assert(UP_COUNT * RPG_MAX_RANK == 54 && UP_COUNT <= RPG_SLOTS && UP_COUNT < 20);
    assert(UP_ENDURANCE == UP_COUNT - 1 && jkRpg_aUpgrades[UP_ENDURANCE].page == PAGE_CHARACTER);
    assert(!strcmp(jkRpg_aUpgrades[UP_ATHLETICS].nodes[1].name, "Quick draw"));
    assert(!strcmp(jkRpg_aUpgrades[UP_ENDURANCE].nodes[0].name, "Safer landings"));
    assert(RPG_BIN_FOUND >= RPG_BIN_MISSION0 + RPG_SLOTS);

    // Discovery: skills always, equipment once held, kept after it runs out, Force with the story.
    reset(&p);
    assert(jkRpg_IsFound(&p, UP_HEALTH) && jkRpg_IsFound(&p, UP_SCAVENGER) && jkRpg_IsFound(&p, UP_MEDIC));
    assert(!jkRpg_IsFound(&p, UP_BRYAR) && !jkRpg_IsFound(&p, UP_BACTA) && !jkRpg_IsFound(&p, UP_FORCE));
    inv[2] = 1; inv[SITHBIN_FIELDLIGHT] = 1; inv[SITHBIN_BACTATANK] = 1; inv[4] = 3;
    jkRpg_Discover(&p);
    assert(jkRpg_IsFound(&p, UP_BRYAR) && jkRpg_IsFound(&p, UP_LIGHT) && jkRpg_IsFound(&p, UP_BACTA) && jkRpg_IsFound(&p, UP_THERMAL));
    inv[SITHBIN_BACTATANK] = 0; inv[4] = 0;
    jkRpg_Discover(&p);
    assert(jkRpg_IsFound(&p, UP_BACTA) && jkRpg_IsFound(&p, UP_THERMAL) && !jkRpg_IsFound(&p, UP_RAIL));
    reset(&p);
    inv[SITHBIN_IRGOGGLES] = 1; // goggles no longer discover the field-light branch
    jkRpg_Discover(&p);
    assert(!jkRpg_IsFound(&p, UP_LIGHT));
    inv[SITHBIN_JEDI_RANK] = 1;
    assert(jkRpg_IsFound(&p, UP_FORCE));

    // Mission 4 reveals mine protection without giving the weapon, ammo or points.
    reset(&p);
    const char* early[] = {"01narshadda.jkl", "02narshadda.jkl", "03katarn.jkl", "custom.jkl"};
    for (int i=0; i<4; i++) { world.map_jkl_fname=early[i]; jkRpg_Discover(&p); assert(!jkRpg_IsFound(&p,UP_SEQUENCER)); }
    sithWorld_g_pCurrentWorld=NULL; jkRpg_Discover(&p); assert(!jkRpg_IsFound(&p,UP_SEQUENCER));
    sithWorld_g_pCurrentWorld=&world; world.map_jkl_fname="04EscapeHouse.jkl";
    Main_bMotsCompat=1; jkRpg_Discover(&p); assert(!jkRpg_IsFound(&p,UP_SEQUENCER)); Main_bMotsCompat=0;
    jkRpg_Discover(&p);
    assert(inv[RPG_BIN_FOUND]==(1<<UP_SEQUENCER) && !inv[8] && !inv[RPG_BIN_POINTS]);
    assert(!jkRpg_CanSpend(&p,UP_SEQUENCER)); inv[RPG_BIN_POINTS]=1;
    assert(jkRpg_CanSpend(&p,UP_SEQUENCER) && !jkRpg_CanSpend(&p,UP_RAIL));
    assert(!strcmp(jkRpg_aUpgrades[UP_SEQUENCER].nodes[0].name,"Blast padding"));
    inv[RPG_BIN_MISSION0+UP_SEQUENCER]=1; assert(!jkRpg_CanSpend(&p,UP_SEQUENCER));
    world.map_jkl_fname="06abarons.jkl"; jkRpg_Discover(&p); assert(jkRpg_IsFound(&p,UP_SEQUENCER));
    reset(&p); inv[8]=1; jkRpg_Discover(&p); assert(jkRpg_IsFound(&p,UP_SEQUENCER)); // earlier pickup still works

    // Modern saves keep every tier and lock except the replaced light tier 2.
    for (int ver=4; ver<RPG_DATA_VERSION; ver++) {
        reset(&p); inv[RPG_BIN_DATAVER]=ver; inv[RPG_BIN_POINTS]=2;
        inv[RPG_BIN_FOUND]=1<<UP_SABER;
        for (int up=0;up<UP_COUNT;up++) {
            inv[RPG_BIN_RANK0+up]=(up%3)+1;
            inv[RPG_BIN_MISSION0+up]=up%2;
        }
        jkRpg_Migrate(&p); jkRpg_Migrate(&p);
        assert(inv[RPG_BIN_DATAVER]==RPG_DATA_VERSION && inv[RPG_BIN_POINTS]==2 && !printed);
        for (int up=0;up<UP_COUNT;up++) {
            assert(inv[RPG_BIN_RANK0+up]==(up%3)+1);
            assert(inv[RPG_BIN_MISSION0+up]==up%2);
        }
        assert(inv[RPG_BIN_FOUND]==(1<<UP_SABER));
    }

    for (int ver=4; ver<=9; ++ver) for (int light=0; light<=3; ++light) for (int lock=0; lock<=1; ++lock) {
        reset(&p); inv[RPG_BIN_DATAVER]=ver; inv[RPG_BIN_POINTS]=2;
        inv[RPG_BIN_LIGHTGAP]=12; // obsolete value in this reused bin must not leak into new rules
        inv[RPG_BIN_FOUND]=(1<<UP_COUNT)-1;
        for (int up=0; up<UP_COUNT; ++up) {
            inv[RPG_BIN_RANK0+up]=(up%3)+1;
            inv[RPG_BIN_MISSION0+up]=up%2;
        }
        inv[RPG_BIN_RANK0+UP_LIGHT]=light; inv[RPG_BIN_MISSION0+UP_LIGHT]=lock;
        jkRpg_Migrate(&p);
        assert(inv[RPG_BIN_POINTS]==2+(light>=2) && printed==(light>=2));
        assert(inv[RPG_BIN_LIGHTGAP]==(light>=2) && inv[RPG_BIN_DATAVER]==10);
        for (int up=0; up<UP_COUNT; ++up) {
            assert(jkRpg_Rank(&p,up)==(up==UP_LIGHT ? light : up%3+1));
            assert(inv[RPG_BIN_MISSION0+up]==(up==UP_LIGHT ? lock : up%2));
        }
        assert(jkRpg_OwnsTier(&p,UP_LIGHT,1)==(light>=1));
        assert(!jkRpg_OwnsTier(&p,UP_LIGHT,2));
        assert(jkRpg_OwnsTier(&p,UP_LIGHT,3)==(light==3));
        assert(jkRpg_NextTier(&p,UP_LIGHT)==(light>=2 ? 2 : light+1));
        // Inventory is the save payload: restore into a fresh runtime, then migrate twice.
        flex_t saved[200]; memcpy(saved,inv,sizeof(saved)); reset(&p); memcpy(inv,saved,sizeof(inv));
        jkRpg_Migrate(&p); jkRpg_Migrate(&p); assert(!printed && !memcmp(saved,inv,sizeof(saved)));
        if (light<2) continue;
        assert(jkRpg_CanSpend(&p,UP_LIGHT) && !jkRpg_RaisedThisMission(&p,UP_LIGHT));
        jkRpg_Toggle(&p,UP_LIGHT);
        assert(inv[RPG_BIN_POINTS]==2 && jkRpg_Rank(&p,UP_LIGHT)==light);
        assert(jkRpg_OwnsTier(&p,UP_LIGHT,2) && jkRpg_OwnsTier(&p,UP_LIGHT,3)==(light==3));
        assert(jkRpg_UndoTier(UP_LIGHT)==2 && inv[RPG_BIN_MISSION0+UP_LIGHT]==1);
        assert(!jkRpg_CanSpend(&p,UP_LIGHT));
        jkRpg_Toggle(&p,UP_HEALTH); assert(jkRpg_Rank(&p,UP_HEALTH)==2 && jkRpg_CanUndo(UP_HEALTH));
        // Taking back the replacement restores both the hole and the pre-existing mission lock.
        jkRpg_Toggle(&p,UP_LIGHT); assert(!jkRpg_CanUndo(UP_LIGHT) && jkRpg_CanUndo(UP_HEALTH));
        assert(!jkRpg_OwnsTier(&p,UP_LIGHT,2) && inv[RPG_BIN_MISSION0+UP_LIGHT]==lock);
        assert(jkRpg_Rank(&p,UP_HEALTH)==2 && inv[RPG_BIN_MISSION0+UP_HEALTH]==1);
        jkRpg_Toggle(&p,UP_HEALTH); assert(!memcmp(saved,inv,sizeof(saved)));
        jkRpg_Toggle(&p,UP_LIGHT); jkRpg_numUndo=0; // close menu and save/load the committed purchase
        memcpy(saved,inv,sizeof(saved)); reset(&p); memcpy(inv,saved,sizeof(inv)); jkRpg_Migrate(&p);
        assert(!memcmp(saved,inv,sizeof(saved)) && jkRpg_OwnsTier(&p,UP_LIGHT,2));
        assert(!jkRpg_CanSpend(&p,UP_LIGHT));
        inv[RPG_BIN_MISSION0+UP_LIGHT]=0; // next mission: rank-2 owner can now buy retained tier 3 normally
        if (light==2) {
            jkRpg_Toggle(&p,UP_LIGHT); assert(jkRpg_Rank(&p,UP_LIGHT)==3 && jkRpg_UndoTier(UP_LIGHT)==3);
            jkRpg_Toggle(&p,UP_LIGHT); assert(jkRpg_Rank(&p,UP_LIGHT)==2 && jkRpg_OwnsTier(&p,UP_LIGHT,2));
        } else assert(!jkRpg_CanSpend(&p,UP_LIGHT));
    }

    // Old five-rank save (data version 3): every point back, raised limits restored, weapons
    // with old upgrades counted as found.
    reset(&p);
    inv[RPG_BIN_DATAVER] = 3; inv[RPG_BIN_POINTS] = 2;
    inv[RPG_BIN_RANK0 + 0] = 5;   // old Health
    inv[RPG_BIN_RANK0 + 1] = 4;   // old Shields
    inv[RPG_BIN_RANK0 + 12] = 2;  // old thermal detonators (weapon 4)
    inv[RPG_BIN_RANK0 + 18] = 1;  // old lightsaber (weapon 10)
    inv[RPG_BIN_MISSION0 + 12] = 1;
    p.actorParams.maxHealth = 200; p.actorParams.health = 180; inv[SITHBIN_SHIELDS] = 170;
    jkRpg_Migrate(&p);
    assert(inv[RPG_BIN_POINTS] == 14 && inv[RPG_BIN_DATAVER] == RPG_DATA_VERSION && printed == 1);
    for (int slot = 0; slot < RPG_SLOTS; slot++) assert(!inv[RPG_BIN_RANK0 + slot] && !inv[RPG_BIN_MISSION0 + slot]);
    assert(p.actorParams.health == 100 && inv[SITHBIN_SHIELDS] == 100);
    assert(jkRpg_IsFound(&p, UP_THERMAL) && jkRpg_IsFound(&p, UP_SABER) && !jkRpg_IsFound(&p, UP_RIFLE));
    inv[RPG_BIN_POINTS]=14;
    // Current saves are left alone; a save without spent points is updated silently.
    inv[RPG_BIN_RANK0 + UP_HEALTH] = 2;
    jkRpg_Migrate(&p);
    assert(inv[RPG_BIN_RANK0 + UP_HEALTH] == 2 && inv[RPG_BIN_POINTS] == 14 && printed == 1);
    reset(&p);
    jkRpg_Migrate(&p);
    assert(inv[RPG_BIN_DATAVER] == RPG_DATA_VERSION && !inv[RPG_BIN_POINTS] && !printed);
    puts("Upgrade table, discovery and old-save refund passed");
    return 0;
}
''')
with tempfile.TemporaryDirectory() as tmp:
    c = Path(tmp) / "t.c"
    c.write_text(code)
    exe = Path(tmp) / "t"
    subprocess.run(["cc", "-std=gnu11", "-Wall", "-Wno-unused-function", "-o", exe, c, "-lm"], check=True)
    subprocess.run([exe], check=True)
