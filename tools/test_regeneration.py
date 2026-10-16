"""Check actual regeneration, shield-hit and after-damage paths, including saved delay."""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

src = Path(sys.argv[1]) / 'src'
s = (src / 'Main/jkRpg.c').read_text()
def function(name):
    start = re.search(r'^(?:static )?\w+ '+name+r'\(', s, re.M).start()
    return s[start:s.index('\n}\n', start)+3]
defines = '\n'.join(re.findall(r'^#define RPG_(?:REGEN_\w+|BIN_REGENWAIT|BIN_BACTA\w+|BACTA_\w+|LOW_SHARE)\s.*$', s, re.M))
assert 'RPG_BIN_REGENWAIT, NULL, "rpg_regenwait", 0, RPG_REGEN_DELAY, 0' in s
assert 'RPG_BIN_REGENWAIT' in function('jkRpg_OnRestoreStart')
actor = (src/'World/sithActor.c').read_text()
assert actor.index('health -= damage') < actor.index('jkRpg_AfterDamage(pActor, damage)')
inventory = (src/'Gameplay/sithInventory.c').read_text()
assert 'jkRpg_ShieldHit(desc->cog, pThing,' in inventory
code = r'''
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
typedef double flex_t;
typedef int sithCog;
typedef struct { int type; } SithThingSource;
typedef struct { int idx, flags; struct { double health,maxHealth; } actorParams; double inv[200]; } SithThing;
enum { UP_HEALTH, UP_BACTA, UP_SHIELDS, SITH_TF_DEAD=1, SITHBIN_SHIELDS=60,
SITHBIN_BACTATANK=40, SITH_DAMAGE_ENERGY=2, SITH_DAMAGE_FIRE=4, SENDERTYPE_THING=1,
SITH_MESSAGE_DAMAGED=1,SITH_THING_EXPLOSION=6 };
static int active=1, rank[3]={3,0,0}, treatments, shieldDrain=1;
static SithThing player={0,0,{50,150},{0}}, other={0};
static int jkRpg_IsActive(SithThing* p){return active && p==&player;}
static int jkRpg_Rank(SithThing* p,int up){return rank[up];}
static double sithInventory_GetInventory(SithThing* p,int bin){return p->inv[bin];}
static void sithInventory_SetInventory(SithThing* p,int bin,double value){p->inv[bin]=value;}
static SithThing* sithThing_GetThingByIndex(int idx){return NULL;}
static double jkRpg_ShieldCost(int rank,int blast){return 1;}
static double sithCog_SendMessageEx(sithCog* c,int msg,int target,int idx,int source,int srcidx,
int link,double units,double type,double x,double y){
    if(!shieldDrain)return units;
    double used=fmin(units,player.inv[SITHBIN_SHIELDS]);player.inv[SITHBIN_SHIELDS]-=used;return units-used;
}
static int jkRpg_UseBacta(SithThing* p){ treatments++; return 1; }
''' + defines + '\n'
# ShieldHit only needs the damager's type for blast resistance.
code=code.replace('int idx, flags; struct', 'int idx, flags, type; struct').replace('player={0,0,{50,150},{0}}','player={.actorParams={50,150}}')
code += ''.join(function(n) for n in ('jkRpg_IsLow','jkRpg_LastingStep','jkRpg_BactaDue',
    'jkRpg_ShieldHit','jkRpg_AfterDamage','jkRpg_Heal','jkRpg_SkillsTick'))
code += r'''
#define near(a,b) (fabs((a)-(b))<1e-7)
int main(void){
    assert(RPG_REGEN_PER_SEC==0.5 && RPG_REGEN_DELAY==3);
    jkRpg_SkillsTick(&player,2); assert(near(player.actorParams.health,51));
    jkRpg_AfterDamage(&player,1); assert(player.inv[RPG_BIN_REGENWAIT]==3);
    jkRpg_SkillsTick(&player,2.5); assert(near(player.actorParams.health,51));
    // Shield-only damage restarts the entire wait even when no health was lost.
    player.inv[SITHBIN_SHIELDS]=100;
    assert(jkRpg_ShieldHit(NULL,&player,0,0,10,2)==0);
    assert(player.inv[SITHBIN_SHIELDS]==90 && player.inv[RPG_BIN_REGENWAIT]==3);
    jkRpg_SkillsTick(&player,3); assert(near(player.actorParams.health,51));
    jkRpg_SkillsTick(&player,2); assert(near(player.actorParams.health,52));
    // Only the portion of a long frame after the deadline heals.
    jkRpg_AfterDamage(&player,1);jkRpg_SkillsTick(&player,4);assert(near(player.actorParams.health,52.5));
    for(int hz=30;hz<=144;hz+=57){
        player.actorParams.health=50; jkRpg_AfterDamage(&player,1);
        for(int i=0;i<hz*5;i++)jkRpg_SkillsTick(&player,1.0/hz);
        assert(near(player.actorParams.health,51));
    }
    // Pause, negative time, fully prevented damage and other actors cannot restart/advance it.
    player.inv[RPG_BIN_REGENWAIT]=1;
    jkRpg_SkillsTick(&player,0);jkRpg_SkillsTick(&player,-1);assert(player.inv[RPG_BIN_REGENWAIT]==1);
    jkRpg_AfterDamage(&player,0);jkRpg_AfterDamage(&other,10);assert(player.inv[RPG_BIN_REGENWAIT]==1);
    shieldDrain=0;jkRpg_ShieldHit(NULL,&player,0,0,10,2);assert(player.inv[RPG_BIN_REGENWAIT]==1);shieldDrain=1;
    active=0;jkRpg_AfterDamage(&player,10);assert(player.inv[RPG_BIN_REGENWAIT]==1);active=1;
    // A save preserves the remaining seconds in inventory, not a wall-clock timestamp.
    SithThing saved=player;player.inv[RPG_BIN_REGENWAIT]=0;player=saved;
    double before=player.actorParams.health;jkRpg_SkillsTick(&player,1);assert(near(player.actorParams.health,before));
    // Bacta still heals during the delay; emergency treatment still works after health damage.
    player.inv[RPG_BIN_REGENWAIT]=3;player.inv[RPG_BIN_BACTAHEAL]=20;
    jkRpg_SkillsTick(&player,1);assert(near(player.actorParams.health,before+20.0/6));
    rank[UP_BACTA]=3;player.actorParams.health=20;player.inv[SITHBIN_BACTATANK]=1;
    jkRpg_AfterDamage(&player,1);assert(treatments==1 && player.inv[RPG_BIN_REGENWAIT]==3);
    player.inv[RPG_BIN_BACTAHEAL]=0;player.actorParams.health=149.9;player.inv[RPG_BIN_REGENWAIT]=0;
    jkRpg_SkillsTick(&player,1);assert(player.actorParams.health==150);
    player.actorParams.health=0;jkRpg_SkillsTick(&player,10);assert(player.actorParams.health==0);
    player.actorParams.health=50;rank[UP_HEALTH]=2;jkRpg_SkillsTick(&player,10);assert(player.actorParams.health==50);
    puts("Regeneration waits three seconds after health/shield damage; frame rates, save state, pause and bacta passed");
}
'''
scratch=Path('/mnt/d/Dev/helm/temp/rekindled-regeneration')
with tempfile.TemporaryDirectory(dir=scratch if scratch.is_dir() else None) as tmp:
    c=Path(tmp)/'check.c';c.write_text(code)
    subprocess.run(['cc','-std=c99','-Wall',str(c),'-lm','-o',str(Path(tmp)/'check')],check=True)
    subprocess.run([str(Path(tmp)/'check')],check=True)
