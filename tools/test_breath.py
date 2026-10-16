"""Run the actual air timer and drowning protection through submersion, surfacing and exclusions."""
import os
import tempfile
from pathlib import Path
import re
import subprocess
import sys
r=Path(sys.argv[1])/'src'
main=(r/'Main/jkRpg.c').read_text();actor=(r/'World/sithActor.c').read_text()
def function(text,name):
    start=re.search(r'^.*\b'+name+r'\([^;\n]*\)\s*\{',text,re.M).start()
    return text[start:text.index('\n}',start)+2]+'\n'
assert 'jkRpg_JumpSpeed' not in main and 'RPG_JUMP_SCALE' not in main
assert 'p->actorParams.jumpSpeed = t->actorParams.jumpSpeed;' in main
harness=r'''
#include <assert.h>
#include <stdio.h>
typedef double flex_t;
static flex_t jkRpg_autosaveActivity, sithTime_g_secGameTime;
enum {UP_ENDURANCE=17,SITH_AF_BREATHEUNDERWATER=1,SITH_TF_DEAD=2,SITH_TF_DESTROYED=4,
SITH_PF_ONWATERSURFACE=8,SITH_SECTOR_UNDERWATER=16,SITH_SC_BREATH=1,SITH_SC_GASP=2,SITH_DAMAGE_DROWN=32};
typedef struct {int flags;} Sector;
typedef struct {struct {int flags;unsigned endurance;} actorParams;struct {int flags;} physicsParams;int flags;Sector* sector;} SithThing;
static SithThing player;static int active=1,rank,hits,breath,gasp;static double lost;
static int jkRpg_IsActive(SithThing* p){return active && p==&player;}
static int jkRpg_Rank(SithThing* p,int branch){return rank;}
static double jkRpg_WeaponProtection(SithThing* p,SithThing* a,double d,int t){return d;}
static double jkRpg_SkillProtection(SithThing* p,SithThing* a,double d,int t){return d;}
static void sithSoundClass_PlayModeRandom(SithThing* p,int sound){if(sound==1)breath++;else gasp++;}
'''
code=harness+function(main,'jkRpg_BreathTime')+function(main,'jkRpg_DamageBeforeShields')
code+=r'''
static void sithThing_DamageThing(SithThing* p,SithThing* a,double d,int t){assert(t==32);hits++;lost+=jkRpg_DamageBeforeShields(p,a,d,t);}
'''+function(actor,'sithActor_Update')+r'''
int main(void){
 Sector water={16},air={0};
 for(rank=0;rank<=3;rank++) {
  player=(SithThing){.sector=&water};hits=0;lost=0;
  int limit=rank>=2?20000:16000;
  assert(jkRpg_BreathTime(&player)==limit);
  for(int elapsed=0;elapsed<limit;elapsed+=10)sithActor_Update(&player,10);
  assert(hits==0);sithActor_Update(&player,10);assert(hits==1);
  assert(lost==(rank>=2?5:10));
  for(int i=0;i<200;i++)sithActor_Update(&player,10);
  assert(hits==2 && lost==(rank>=2?10:20));
  player.physicsParams.flags=8;sithActor_Update(&player,10);assert(player.actorParams.endurance==0);
  player.physicsParams.flags=0;player.actorParams.endurance=limit-1000;player.sector=&air;
  sithActor_Update(&player,10);assert(player.actorParams.endurance==0);
  assert(jkRpg_DamageBeforeShields(&player,&player,40,2)==40);
  assert(jkRpg_DamageBeforeShields(&player,&player,40,1)==40);
 }
 rank=2;active=0;assert(jkRpg_BreathTime(&player)==20000);
 assert(jkRpg_DamageBeforeShields(&player,&player,10,32)==10);
 active=1;SithThing enemy={.sector=&water};assert(jkRpg_BreathTime(&enemy)==20000);
 assert(jkRpg_DamageBeforeShields(&enemy,&enemy,10,32)==10);
 player=(SithThing){.sector=&water,.flags=2};hits=0;sithActor_Update(&player,30000);assert(!hits);
 player.flags=0;player.actorParams.flags=1;sithActor_Update(&player,30000);assert(!hits);
 sithActor_Update(NULL,10);
 puts("Air 16/20 seconds, drowning 10/5 per tick, surfacing reset, normal jump and exclusions passed");
}
'''
scratch=Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-breath-check";scratch.mkdir(parents=True,exist_ok=True)
c,exe=scratch/'check.c',scratch/'check'
try:
 c.write_text(code);subprocess.run(['cc',str(c),'-o',str(exe)],check=True);subprocess.run([str(exe)],check=True)
finally:c.unlink(missing_ok=True);exe.unlink(missing_ok=True)
