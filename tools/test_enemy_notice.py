"""Compile the real initial sight-range rule; run with the engine checkout path."""
import subprocess
import sys
import tempfile
from pathlib import Path

src = Path(sys.argv[1]) / "src"
source = (src / "Main/jkRpg.c").read_text()
start = source.index("flex_t jkRpg_NoticeDistance(")
code = source[start:source.index("\n}\n", start) + 3]
for helper in ("static int jkRpg_IsOrdinaryGunman(", "static int jkRpg_IsOrdinaryBrawler("):
    start = source.index(helper)
    code = source[start:source.index("\n}\n", start) + 3] + code
sight = (src / "AI/sithAI.c").read_text()
assert sight.count("jkRpg_NoticeDistance(actor)") == 1
assert "actor->pClass->fov, jkRpg_NoticeDistance(actor), actora" in sight
# Scripted fire targets use TOUGHSKIN even when ACTIVE is not set.
script = (src / "Cog/sithCogFunctionAI.c").read_text()
script = script[script.index("void sithCogFunctionAI_AISetFireTarget("):]
assert "v5 | SITHAI_MODE_TOUGHSKIN" in script[:1800]
harness = r'''
#include <assert.h>
#include <stddef.h>
#include <stdio.h>
#include <strings.h>
#define __strcmpi strcasecmp
typedef double flex_t;
typedef int (*sithAICommandFunc_t)(void);
enum { SITHAI_MODE_SEARCHING=1, SITHAI_MODE_ACTIVE=2,
       SITHAI_MODE_ATTACKING=4, SITHAI_MODE_TOUGHSKIN=8 };
typedef struct { const char* aName; } Script;
typedef struct { Script* pScript; } Cog;
typedef struct { Cog* pCog; } SithThing;
typedef struct { sithAICommandFunc_t func; } Instinct;
typedef struct { flex_t sightDistance, alignment; int numEntries; Instinct entries[16]; } Class;
typedef struct { flex_t param0; } State;
typedef struct { Class* pClass; SithThing* thing; SithThing* pDistractor;
                 int flags; State aInstinctStates[16]; } SithAIControlBlock;
static SithThing player;
static SithThing* sithPlayer_g_pLocalPlayerThing = &player;
static int Main_bMotsCompat, active = 1;
static int jkRpg_IsActive(SithThing* p) { return active && p == &player; }
static int sithAICmd_Listen(void) { return 0; }
''' + code + r'''
int main(void) {
    Script script = {"actor_st.cog"}; Cog cog = {&script}; SithThing thing = {&cog};
    Class c = {.sightDistance=5, .alignment=-1, .numEntries=1};
    c.entries[0].func = sithAICmd_Listen;
    SithAIControlBlock a = {.pClass=&c, .thing=&thing, .pDistractor=&player,
                           .flags=SITHAI_MODE_SEARCHING};
    const char* regular[] = {"ACTOR_ST.COG", "actor_s2.cog", "actor_s3.cog",
        "actor_tk.cog", "actor_tb.cog", "actor_rb.cog", "actor_ry.cog", "actor_bs.cog",
        "actor_rf.cog", "ACTOR_GG.COG"}; // gunmen, then the brawlers (Rodian fists, Gamorreans)
    for (size_t i=0; i<sizeof(regular)/sizeof(*regular); i++) {
        script.aName=regular[i]; assert(jkRpg_NoticeDistance(&a)==2.5);
    }
    const char* excluded[] = {"actor_at.cog", "actor_probe.cog", "actor_mailoc.cog",
        "actor_dj.cog", "actor_go.cog", "actor_civ.cog", "actor_kd.cog", "actor_re.cog", "unknown.cog"};
    for (size_t i=0; i<sizeof(excluded)/sizeof(*excluded); i++) {
        script.aName=excluded[i]; assert(jkRpg_NoticeDistance(&a)==5);
    }
    script.aName="actor_st.cog";
    int flags[] = {0, SITHAI_MODE_ACTIVE, SITHAI_MODE_ATTACKING, SITHAI_MODE_TOUGHSKIN};
    for (int i=0;i<4;i++) {
        a.flags=flags[i]; assert(jkRpg_NoticeDistance(&a)==5);
        if (flags[i]) { a.flags|=SITHAI_MODE_SEARCHING; assert(jkRpg_NoticeDistance(&a)==5); }
    }
    a.flags=SITHAI_MODE_SEARCHING;
    // Listen retains both damage/touch alerts (.1) and heard gunfire strength.
    a.aInstinctStates[0].param0=.1; assert(jkRpg_NoticeDistance(&a)==5);
    a.aInstinctStates[0].param0=2; assert(jkRpg_NoticeDistance(&a)==5);
    a.aInstinctStates[0].param0=0; assert(jkRpg_NoticeDistance(&a)==2.5);
    a.pDistractor=&thing; assert(jkRpg_NoticeDistance(&a)==5); a.pDistractor=&player;
    c.alignment=0; assert(jkRpg_NoticeDistance(&a)==5); c.alignment=-1;
    active=0; assert(jkRpg_NoticeDistance(&a)==5); active=1;
    Main_bMotsCompat=1; assert(jkRpg_NoticeDistance(&a)==5); Main_bMotsCompat=0;
    thing.pCog=NULL; assert(jkRpg_NoticeDistance(&a)==5); thing.pCog=&cog;
    cog.pScript=NULL; assert(jkRpg_NoticeDistance(&a)==5); cog.pScript=&script;
    a.thing=NULL; assert(jkRpg_NoticeDistance(&a)==5); a.thing=&thing;
    c.sightDistance=7; assert(jkRpg_NoticeDistance(&a)==3.5);
    assert(c.sightDistance==7); // Shared hearing/chasing class values never change.
    puts("Initial notice: ordinary gunmen and brawlers half range; alerted/scripted/excluded actors unchanged");
}
'''
with tempfile.TemporaryDirectory() as tmp:
    c = Path(tmp) / "notice.c"
    c.write_text(harness)
    exe = Path(tmp) / "notice"
    subprocess.run(["cc", "-std=gnu11", "-Wall", "-Werror", str(c), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
