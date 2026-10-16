"""Compile the real Listen damage branch and projectile owner resolution."""
import subprocess
import sys
import tempfile
from pathlib import Path

src = Path(sys.argv[1]) / "src"
rpg = (src / "Main/jkRpg.c").read_text()
ai = (src / "AI/sithAICmd.c").read_text()
events = (src / "AI/sithAI.c").read_text()
thing = (src / "World/sithThing.c").read_text()
def extract(text, signature):
    start = text.index(signature)
    return text[start:text.index("\n}\n", start) + 3]

listen = extract(ai, "int sithAICmd_Listen(")
# The rest of Listen handles sound/touch events, not the MOVING damage event.
listen = listen[:listen.index("    if ( event != SITHAI_MODE_ATTACKING )")] + "return 0;\n}\n"
damage = (src / "World/sithActor.c").read_text()
assert "sithAI_EmitEvent(pActor->actor, SITHAI_MODE_MOVING, (intptr_t)pThing)" in damage
code = r'''
#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <strings.h>
#define __strcmpi strcasecmp
#define MOTS_ONLY_COND(x) (1)
typedef double flex_t, flex_d_t;
enum { SITHAI_MODE_SEARCHING=4, SITHAI_MODE_MOVING=1, SITHAI_MODE_TOUGHSKIN=32,
    SITHAI_MODE_ACTIVE=512, SITHAI_MODE_HASDEST=16, SITHAI_MODE_ATTACKING=2,
    SITH_THING_ACTOR=2, SITH_THING_PLAYER=10, SITH_SC_SURPRISE=1, SITH_SC_CURIOUS=2 };
enum { SITHAI_MODE_SLEEPING=0x1000, SITHAI_MODE_DISABLED=0x2000,
    SITHAI_MODE_UNK100=0x100, SITH_TF_DEAD=1, SITH_TF_DESTROYED=2,
    DEBUGFLAG_NO_AIEVENTS=1, SITH_MESSAGE_AIEVENT=1, SITHAI_EVENTMODECHANGED=1 };
static int g_debugmodeFlags;
typedef struct { double x,y,z; } rdVector3;
typedef struct { const char* aName; } Script;
typedef struct { Script* pScript; } Cog;
typedef struct { int id; } Sector;
typedef struct SithThing { int type; Cog* pCog; struct SithThing* pParent;
    int parentSignature, signature; rdVector3 position; Sector* sector;
    int flags; struct { double health; } actorParams; } SithThing;
typedef struct { flex_t fltArg[16]; int param3; int (*func)(); } SithAIInstinct;
typedef struct { flex_t param0; int field_0; } SithAIInstinctState;
typedef struct { flex_t alignment; SithAIInstinct entries[1]; } Class;
typedef struct { Class* pClass; SithThing* thing; SithThing* pDistractor;
    SithThing* pMoveThing; int flags; unsigned numInstincts;
    SithAIInstinctState aInstinctStates[1]; } SithAIControlBlock;
typedef struct { int unused; } sithSectorAlloc;
static sithSectorAlloc sithAIAwareness_g_aSectors[1];
static SithThing player;
static SithThing* sithPlayer_g_pLocalPlayerThing=&player;
static int Main_bMotsCompat, active=1;
static rdVector3 looked;
static int jkRpg_IsActive(SithThing* p) { return active && p==&player; }
static double _frand(void) { return .9; } // Original random response always declines.
static void sithSoundClass_PlayModeRandom(SithThing* t,int m) {}
static void sithAI_SetLookFrame(SithAIControlBlock* a,rdVector3* p) { looked=*p; }
static void sithAI_SetMoveThing(SithAIControlBlock* a,rdVector3* p,double s) {}
static void rdVector_Sub3(rdVector3* d,rdVector3* a,rdVector3* b) { *d=*a; }
static void rdVector_Normalize3Acc(rdVector3* a) {}
static void rdVector_Scale3Acc(rdVector3* a,double v) {}
static void rdVector_Add3Acc(rdVector3* a,rdVector3* b) {}
static void sithCog_ThingSendMessageEx(SithThing* t,int a,int b,double c,double d,double e,double f) {}
''' + extract(thing, "SithThing* sithThing_GetThingParent(") + extract(rpg, "static int jkRpg_IsOrdinaryGunman(") + extract(rpg, "SithThing* jkRpg_RetaliationTarget(") + listen + extract(events, "void sithAI_EmitEvent(") + r'''
int main(void) {
    Script script={"actor_tk.cog"}; Cog cog={&script}; Sector sector={0};
    SithThing victim={.type=2,.pCog=&cog,.sector=&sector};
    player.type=10; player.signature=42; player.position.x=-4; // Player is behind.
    SithThing bolt={.type=3,.pParent=&player,.parentSignature=42,.signature=43};
    SithThing explosion={.type=4,.pParent=&bolt,.parentSignature=43};
    Class c={-1}; SithAIControlBlock a={.pClass=&c,.thing=&victim,.flags=4};
    SithAIInstinct instinct={0}; SithAIInstinctState state={0};
    SithThing* hits[]={&player,&bolt,&explosion};
    for (int i=0;i<3;i++) {
        a.flags=4; a.pDistractor=NULL; state.param0=0; looked.x=100;
        sithAICmd_Listen(&a,&instinct,&state,SITHAI_MODE_MOVING,hits[i]);
        assert(looked.x==-4); // Never faces the impact point at x=0.
        assert(a.pDistractor==&player && a.pMoveThing==&player);
        assert(!(a.flags&4) && (a.flags&512) && (a.flags&2));
        assert(state.param0==.1);
    }
    a.flags=4;
    bolt.parentSignature=41; assert(!jkRpg_RetaliationTarget(&a,&bolt));
    bolt.parentSignature=42;
    const char* excluded[]={"actor_fn.cog","actor_ug.cog","actor_dj.cog","unknown.cog"};
    for (unsigned i=0;i<sizeof(excluded)/sizeof(*excluded);i++) {
        script.aName=excluded[i]; assert(!jkRpg_RetaliationTarget(&a,&bolt));
    }
    script.aName="actor_tk.cog";
    c.alignment=0; assert(!jkRpg_RetaliationTarget(&a,&bolt)); c.alignment=-1;
    a.flags=4|32; assert(!jkRpg_RetaliationTarget(&a,&bolt)); a.flags=4;
    active=0; assert(!jkRpg_RetaliationTarget(&a,&bolt)); active=1;
    Main_bMotsCompat=1; assert(!jkRpg_RetaliationTarget(&a,&bolt)); Main_bMotsCompat=0;
    assert(!jkRpg_RetaliationTarget(&a,NULL));
    assert(!jkRpg_RetaliationTarget(&a,&victim));
    assert(!jkRpg_RetaliationTarget(NULL,&bolt));
    a.flags=512; assert(!jkRpg_RetaliationTarget(&a,&bolt));
    // Exercise the real event dispatch too: a sleeping guard must receive the hit.
    victim.actorParams.health=60;
    c.entries[0].func=(int (*)())sithAICmd_Listen;
    c.entries[0].param3=SITHAI_MODE_MOVING;
    a.numInstincts=1; a.flags=4|SITHAI_MODE_SLEEPING; a.pDistractor=NULL;
    sithAI_EmitEvent(&a,SITHAI_MODE_MOVING,(intptr_t)&bolt);
    assert(!(a.flags&SITHAI_MODE_SLEEPING) && (a.flags&SITHAI_MODE_ACTIVE));
    assert(a.pDistractor==&player && looked.x==-4);
    a.flags=4|SITHAI_MODE_SLEEPING|SITHAI_MODE_DISABLED; a.pDistractor=NULL;
    sithAI_EmitEvent(&a,SITHAI_MODE_MOVING,(intptr_t)&bolt);
    assert(a.flags&SITHAI_MODE_SLEEPING); assert(!a.pDistractor);
    a.flags=4|SITHAI_MODE_SLEEPING; script.aName="actor_fn.cog";
    sithAI_EmitEvent(&a,SITHAI_MODE_MOVING,(intptr_t)&bolt);
    assert(a.flags&SITHAI_MODE_SLEEPING); assert(!a.pDistractor);
    puts("Rear hits: melee/bolt/explosion owner targeted, guaranteed engagement; exclusions and stale owners preserved");
}
'''
with tempfile.TemporaryDirectory() as tmp:
    c = Path(tmp) / "retaliation.c"; c.write_text(code)
    exe = Path(tmp) / "retaliation"
    subprocess.run(["cc", "-std=gnu11", "-Werror=implicit-function-declaration", str(c), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
