"""Compile the real ammo limits, saved-amount clamp and inventory set/add paths."""
import os
import tempfile
from pathlib import Path
import subprocess
import re
import sys

root = Path(sys.argv[1])/'src'
source = (root/'Main/jkRpg.c').read_text()
inv = (root/'Gameplay/sithInventory.c').read_text()
def function(text, name):
    start = re.search(r'^.*\b'+name+r'\([^;\n]*\)\s*\{', text, re.M).start()
    body = text.index('{', start)
    depth = 0
    for end in range(body, len(text)):
        depth += {'{': 1, '}': -1}.get(text[end], 0)
        if depth == 0:
            return text[start:end+1]+'\n'
    raise ValueError(name)
def capacity_loop(name):
    text = function(source,name)
    start = text.index('    for (size_t i = 0; i < sizeof(jkRpg_aCapacityBins)')
    return text[start:text.index('\n    }',start)+6]
array = source[source.index('static const int jkRpg_aCapacityBins'):]
array = array[:array.index(';')+1]
harness = r'''
#include <assert.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <strings.h>
typedef double flex_t;
enum { SITHBIN_ENERGY=11,SITHBIN_POWER=12,SITHBIN_RAILCHARGES=15,SITHBIN_NUMBINS=200,
SITH_THING_PLAYER=10,SITHINVENTORY_TYPE_REGISTERED=1,SITHINVENTORY_ITEM_CHANGED=2,
SITH_MESSAGE_CHANGED=0,SENDERTYPE_0=0,SENDERTYPE_THING=0 };
#define SITH_ASSERTREL assert
typedef struct { double amount;int state; } SithInventoryItem;
typedef struct { SithInventoryItem aItems[200]; } SithPlayer;
typedef struct { int type,idx;struct { SithPlayer* pPlayer; double health,maxHealth; } actorParams; } SithThing;
static struct { double min,max;int flags;void* cog; } sithInventory_g_aTypes[200];
static double jkRpg_aBaseMax[200];
static int notices;
static void sithCog_SendMessage(void* c,int a,int b,int d,int e,int f,int g){notices++;}
static double jkRpg_AmmoCost(SithThing* p,int bin,double amount){return amount;}
'''
code = harness+array+'\n'+function(source,'jkRpg_AmmoCapacity')
for name in ('sithInventory_SetInventory','sithInventory_GetInventory','sithInventory_ChangeInventory'):
    code += function(inv,name)
code += r'''
enum { SITHBIN_FORCEMANA=14,SITHBIN_BATTERY=13,SITHBIN_BACTATANK=40,SITHBIN_SHIELDS=60,
SITHBIN_F_PERSUASION=27,UP_FORCE,UP_LIGHT,UP_BACTA,UP_MEDIC,UP_SHIELDS,UP_SCAVENGER,
RPG_BIN_BACTAHEAL,RPG_BACTA_LASTING=20 };
typedef struct { const char* aName; } Script;
typedef struct { Script* pScript; } sithCog;
static int active=1,rank=0,salvage=0;
static double jkRpg_aLeftover[200];
#define __strnicmp strncasecmp
#define __strcmpi strcasecmp
static struct { const char* map_jkl_fname; } world={"18ascend.jkl"}, *sithWorld_g_pCurrentWorld=&world;
#define RPG_LOW_SHARE 0.25
static int jkRpg_IsActive(SithThing* p){return active;}
static int jkRpg_IsScript(sithCog* c,const char* n){return !strcmp(c->pScript->aName,n);}
static int jkRpg_Rank(SithThing* p,int upgrade){return rank;}
static int jkRpg_IsEnemyWeapon(sithCog* c){return salvage;}
static int sithInventory_IsInventoryActivated(SithThing* p,int bin){return 0;}
static void jkRpg_VisionReminder(SithThing* p,int b){}
static void jkRpg_BactaReminder(SithThing* p){}
'''
for name in ('IsLow','AmmoShare','ForceRegenScale','ForceHealAmount','BactaShare','HealthPackShare','ShieldPackShare','PickupAmount'):
    code += function(source,'jkRpg_'+name)
code += 'static void register_caps(void){\n'+capacity_loop('jkRpg_RegisterBins')+'\n}\n'
code += 'static void apply_caps(SithThing* p){\n'+capacity_loop('jkRpg_ApplyStats')+'\n}\n'
code += r'''
int main(void){
    SithPlayer inventory={0};SithThing p={.type=10,.actorParams.pPlayer=&inventory};
    int bins[]={11,12,15,4,8},old[]={500,500,30,30,30},caps[]={200,100,10,10,10};
    for(int i=0;i<5;i++) {
        int bin=bins[i];sithInventory_g_aTypes[bin].max=old[i];
        sithInventory_g_aTypes[bin].flags=1;sithInventory_g_aTypes[bin].cog=&p;
        inventory.aItems[bin].amount=old[i];
        assert(jkRpg_AmmoCapacity(bin,5)==5); // never raise a smaller custom limit
    }
    assert(jkRpg_AmmoCapacity(40,5)==5 && jkRpg_AmmoCapacity(60,100)==100);
    register_caps();apply_caps(&p);
    for(int i=0;i<5;i++) {
        int bin=bins[i];assert(sithInventory_g_aTypes[bin].max==caps[i]);
        assert(sithInventory_GetInventory(&p,bin)==caps[i]); // loaded over-cap save
        assert(sithInventory_ChangeInventory(&p,bin,100)==caps[i]);
        assert(sithInventory_ChangeInventory(&p,bin,-1)==caps[i]-1);
        assert(sithInventory_ChangeInventory(&p,bin,20)==caps[i]);
        assert(sithInventory_SetInventory(&p,bin,0)==0);
        apply_caps(&p);assert(sithInventory_GetInventory(&p,bin)==0); // never refill
        assert(sithInventory_SetInventory(&p,bin,-10)==0);
        assert(sithInventory_SetInventory(&p,bin,1000)==caps[i]);
    }
    int before=notices;apply_caps(&p);assert(notices==before); // no per-frame change messages
    // Real pickup path: all rocket sources and Scavenger combinations yield half as much.
    Script script={"pow_railcharges.cog"};sithCog cog={&script};
    const char* scripts[]={"pow_railcharges.cog","pow_railgun.cog","pow_drailgun.cog"};
    const double base[]={3,6,3};
    for(int source=0;source<3;source++) for(rank=0;rank<=3;rank++) for(int low=0;low<2;low++) {
        script.aName=scripts[source];salvage=source==2;jkRpg_aLeftover[15]=0;
        sithInventory_SetInventory(&p,15,low?0:5);
        double total=0,share=(rank>=3?1:0.75)+(rank>=1&&low?0.25:0)+(rank>=2&&salvage?0.25:0);
        for(int i=0;i<8;i++) total+=jkRpg_PickupAmount(&cog,&p,15,base[source]);
        assert(total==8*base[source]*share*0.5 && jkRpg_aLeftover[15]==0);
    }
    rank=0;salvage=0;script.aName=scripts[0];jkRpg_aLeftover[15]=0;
    for(int i=0;i<8;i++) assert(jkRpg_PickupAmount(&cog,&p,15,3)==(i==7?2:1));
    jkRpg_aLeftover[11]=0;assert(jkRpg_PickupAmount(&cog,&p,11,20)==15);
    jkRpg_aLeftover[12]=0;assert(jkRpg_PickupAmount(&cog,&p,12,20)==15);
    assert(jkRpg_PickupAmount(&cog,&p,15,-1)==-1); // firing costs stay unchanged
    assert(jkRpg_PickupAmount(&cog,&p,7,1)==1); // acquiring the launcher itself
    script.aName="weap_railgun.cog";assert(jkRpg_PickupAmount(&cog,&p,15,3)==3);
    script.aName=scripts[0];active=0;assert(jkRpg_PickupAmount(&cog,&p,15,3)==3);active=1;
    sithInventory_SetInventory(&p,15,9);
    sithInventory_ChangeInventory(&p,15,jkRpg_PickupAmount(&cog,&p,15,6));
    assert(sithInventory_GetInventory(&p,15)==10);
    // Mission 18 halves the real shared-ammo pickup path, including all Scavenger combinations.
    world.map_jkl_fname="19a.jkl";
    const char* powerScripts[]={"pow_drepeater.cog","pow_power.cog","pow_concrifle.cog"};
    const double powerBase[]={12,25,32};
    for(int source=0;source<3;source++)for(rank=0;rank<=3;rank++)for(int low=0;low<2;low++) {
        script.aName=powerScripts[source];salvage=source==0;jkRpg_aLeftover[12]=0;
        sithInventory_SetInventory(&p,12,low?0:50);
        double total=0,share=(rank>=3?1:.75)+(rank>=1&&low?.25:0)+(rank>=2&&salvage?.25:0);
        for(int i=0;i<16;i++)total+=jkRpg_PickupAmount(&cog,&p,12,powerBase[source]);
        assert(total==16*powerBase[source]*share*.5 && jkRpg_aLeftover[12]==0);
    }
    rank=0;salvage=1;script.aName=powerScripts[0];jkRpg_aLeftover[12]=0;
    assert(jkRpg_PickupAmount(&cog,&p,12,12)==4);
    assert(jkRpg_PickupAmount(&cog,&p,12,12)==5);
    assert(jkRpg_PickupAmount(&cog,&p,6,1)==1); // still grants the repeater
    assert(jkRpg_PickupAmount(&cog,&p,12,-8)==-8); // firing remains unchanged
    script.aName="weap_concrifle.cog";assert(jkRpg_PickupAmount(&cog,&p,12,12)==12);
    script.aName=powerScripts[0];active=0;assert(jkRpg_PickupAmount(&cog,&p,12,12)==12);active=1;
    world.map_jkl_fname="19b.jkl";assert(jkRpg_PickupAmount(&cog,&p,12,12)==9);
    sithWorld_g_pCurrentWorld=0;assert(jkRpg_PickupAmount(&cog,&p,12,12)==9);
    puts("Ammo ceilings, saved overflow, pickup/cheat limits, spending, empty supply and smaller custom limits passed");
}
'''
scratch=Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-ammo-check";scratch.mkdir(parents=True,exist_ok=True)
c,exe=scratch/'check.c',scratch/'check'
try:
    c.write_text(code)
    subprocess.run(['cc',str(c),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
finally:
    c.unlink(missing_ok=True);exe.unlink(missing_ok=True)
