"""Compile the actual Force selection, panel cache, placement and hidden-HUD rules."""
import os
import tempfile
import re
import subprocess
import sys
from pathlib import Path
src = Path(sys.argv[1]) / "src/Main"
def function(file, name):
    text = (src / file).read_text()
    match = re.search(r"^(?:static )?[\w* ]*?\b" + name + r"\([^;]*?\)\s*\{", text, re.M)
    body = match.end() - 1
    depth = 0
    for i in range(body, len(text)):
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        if not depth:
            return text[match.start():i + 1] + "\n"
harness = r'''
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <strings.h>
#include <stdint.h>
#define __strcmpi strcasecmp
#define NULL ((void*)0)
typedef float flex_t;
typedef struct {int r_bits,g_bits,b_bits,r_shift,g_shift,b_shift;} rdTexFormat;
typedef struct { struct { int width, height; } format; } tVBuffer;
typedef struct { tVBuffer** mipSurfaces; } stdBitmap;
typedef struct { int x,y,width,height; } rdRect;
typedef struct { float* px; int w,h; float scale; } jkRpgCanvas;
typedef struct { struct { void* pPlayer; } actorParams; } SithThing;
typedef int stdFont;
enum { SITHBIN_FORCEMANA=14, SITHBIN_NUMBINS=200, SITHBIN_JEDI_RANK=70, SITHINVENTORY_TYPE_AUTOAIM=8, ARTFILE_FORCE, ARTFILE_BACTA };
#define PLATE_TEXELS 4.0f
#define BACTA_INSET 3
#define BACTA_SCALE 0.75
#define BACTA_DIM 80
typedef struct { const char* aName; } sithCogScript; typedef struct { sithCogScript* pScript; } sithCog;
static struct { int flags; stdBitmap* hudBitmap; sithCog* cog; } sithInventory_g_aTypes[200];
static stdBitmap grayIcon; static stdBitmap* grayFor;
static stdBitmap* jkRpg_ForceGray(stdBitmap* source) { grayFor = source; return &grayIcon; }
static float amounts[200]; static int available[200], selected, active=1;
static float sithInventory_GetInventory(SithThing* p,int bin) { return amounts[bin]; }
static int sithInventory_GetCurPower(SithThing* p) { return selected; }
static int sithInventory_IsInventoryAvailable(SithThing* p,int bin) { return available[bin]; }
static int running[200];
static int sithInventory_IsInventoryActivated(SithThing* p,int bin) { return running[bin]; }
static struct { int width,height; } Video_format={1920,1080};
static float jkPlayer_hudScale=3;
static stdBitmap* jkRpg_aHudPanels[2]; static flex_t jkRpg_aHudPanelScales[2];
static jkRpgCanvas art={0,136,128,1}; static int missing,failCanvas,freed,created;
static const jkRpgCanvas* jkRpg_ShippedArt(int index) { return missing?NULL:&art; }
static void stdBitmap_Free(stdBitmap* b) { freed++; free(b->mipSurfaces[0]);free(b->mipSurfaces);free(b); }
static int jkRpg_NewCanvas(jkRpgCanvas* c,float w,float h,float s) { if(failCanvas)return 0; *c=(jkRpgCanvas){NULL,(int)(w*s+0.5f),(int)(h*s+0.5f),s};return 1; }
static void jkRpg_Stretch(const jkRpgCanvas*a,float x,float y,float w,float h,jkRpgCanvas*b,int p,int q,int r,int s) {}
static float pixelBlock; static void jkRpg_Pixelate(jkRpgCanvas*c,float block) { pixelBlock=block; }
static stdBitmap* jkRpg_CanvasBitmap(jkRpgCanvas*c) { created++; stdBitmap*b=calloc(1,sizeof(*b));b->mipSurfaces=calloc(1,sizeof(tVBuffer*));b->mipSurfaces[0]=calloc(1,sizeof(tVBuffer));b->mipSurfaces[0]->format.width=c->w;b->mipSurfaces[0]->format.height=c->h;return b; }
static int draws,boxes; static float panelX,panelY,iconX,iconY; static stdBitmap* drawnIcon;
static int iconShade, frameShade;
static void std3D_DrawUIBitmapRGBA(stdBitmap*b,int mip,float x,float y,rdRect*src,float sx,float sy,int a,int r,int g,int blue,int alpha) { draws++; if(src){drawnIcon=b;iconX=x;iconY=y;iconShade=r;assert(src->width>0&&src->height>0);}else{panelX=x;panelY=y;frameShade=r;} }
static void jkRpg_Rect(int x,int y,int w,int h,int r,int g,int b,int a) {}
static void jkRpg_Box(int x,int y,int w,int h,int t,int r,int g,int b) { boxes++; }
static SithThing kyle={{(void*)1}}; static SithThing* sithPlayer_g_pLocalPlayerThing=&kyle;
static int Main_bNoHUD,jkRpg_bMenuOpen,badges,bacta,menus,finder,weapons;
static int jkRpg_IsActive(SithThing*p){return active;}
static void jkRpg_DrawLevelBadge(SithThing*p,stdFont*f,int x,int y){badges++;}
static void jkRpg_DrawBactaHud(SithThing*p,stdFont*f,int x,int w){bacta++;}
static void jkRpg_DrawMenu(SithThing*p,stdFont*f){menus++;}
static void jkRpg_DrawSupplyFinder(SithThing*p){finder++;}
static void jkRpg_DrawWeapons(SithThing*p,stdFont*f){weapons++;}
'''
checks=r'''
int main(void){
 // Real inventory RGB565 pixels have a color key, not a one-bit alpha channel.
 rdTexFormat formats[]={{5,6,5,11,5,0},{5,5,5,10,5,0}};
 for(int f=0;f<2;f++) for(int p=0;p<65536;p++) {
  rdTexFormat* fmt=&formats[f];
  int r=((p>>fmt->r_shift)&31), b=p&31;
  int g=((p>>5)&((1<<fmt->g_bits)-1))*31/((1<<fmt->g_bits)-1);
  int v=r>g?r:g;if(b>v)v=b;
  assert(jkRpg_ForceGrayPixel(p,fmt,0)==(p?0x8000|(v<<10)|(v<<5)|v:0));
 }
 assert(jkRpg_ForceGrayPixel(31,&formats[0],0)==0xffff); // blue must remain visible
 assert(jkRpg_ForceGrayPixel(31,&formats[0],31)==0); // colored transparency key
 assert(jkRpg_ForceGrayPixel(0,&formats[0],31)==0x8000); // opaque black
 tVBuffer pixels={{24,24}},tiny={{5,24}};tVBuffer* surfaces[]={&pixels};tVBuffer* small[]={&tiny};
 stdBitmap jump={surfaces},speed={surfaces},bad={small};
 selected=21;available[21]=1;amounts[21]=1;sithInventory_g_aTypes[21].flags=8;sithInventory_g_aTypes[21].hudBitmap=&jump;
 assert(!jkRpg_SelectedForceIcon(&kyle));amounts[70]=1;assert(jkRpg_SelectedForceIcon(&kyle)==&jump);
 selected=-1;assert(!jkRpg_SelectedForceIcon(&kyle));selected=200;assert(!jkRpg_SelectedForceIcon(&kyle));selected=21;
 available[21]=0;assert(!jkRpg_SelectedForceIcon(&kyle));available[21]=1;
 amounts[21]=0;assert(!jkRpg_SelectedForceIcon(&kyle));amounts[21]=1;
 sithInventory_g_aTypes[21].flags=2;assert(!jkRpg_SelectedForceIcon(&kyle));sithInventory_g_aTypes[21].flags=8;
 sithInventory_g_aTypes[21].hudBitmap=&bad;assert(!jkRpg_SelectedForceIcon(&kyle));sithInventory_g_aTypes[21].hudBitmap=&jump;
 // No mana check: a selected learned power stays visible at zero energy.
 jkRpg_DrawForceHud(&kyle,1740);assert(draws==2&&drawnIcon==&jump&&panelX==1656&&panelY==1005);
 // A power the player cannot afford is grayscale at full brightness, and switching
 // powers shows the newly selected power's state.
 sithCogScript jumpScript={"force_jump.cog"}, healScript={"FORCE_HEAL.COG"}, odd={"force_custom.cog"};
 sithCog jumpCog={&jumpScript}, healCog={&healScript}, oddCog={&odd};
 sithInventory_g_aTypes[21].cog=&jumpCog; sithInventory_g_aTypes[25].cog=&healCog;
 stdBitmap heal={surfaces}; available[25]=amounts[25]=1; sithInventory_g_aTypes[25].flags=8; sithInventory_g_aTypes[25].hudBitmap=&heal;
 amounts[SITHBIN_FORCEMANA]=19; jkRpg_DrawForceHud(&kyle,1740);
 assert(drawnIcon==&grayIcon && grayFor==&jump && iconShade==255 && frameShade==255);
 amounts[SITHBIN_FORCEMANA]=20; jkRpg_DrawForceHud(&kyle,1740); assert(drawnIcon==&jump && iconShade==255 && frameShade==255);
 selected=25; jkRpg_DrawForceHud(&kyle,1740); assert(drawnIcon==&grayIcon && grayFor==&heal && iconShade==255);
 amounts[SITHBIN_FORCEMANA]=200; jkRpg_DrawForceHud(&kyle,1740); assert(drawnIcon==&heal && iconShade==255);
 amounts[SITHBIN_FORCEMANA]=0; sithInventory_g_aTypes[25].cog=&oddCog; jkRpg_DrawForceHud(&kyle,1740); assert(drawnIcon==&heal); // unknown cost
 sithInventory_g_aTypes[25].cog=0; jkRpg_DrawForceHud(&kyle,1740); assert(drawnIcon==&heal);
 // A power already running (Speed, for example) cannot be started again: greyed as well.
 selected=21; amounts[SITHBIN_FORCEMANA]=100; running[21]=1; jkRpg_DrawForceHud(&kyle,1740);
 assert(drawnIcon==&grayIcon && iconShade==255); running[21]=0;
 assert(iconX>panelX&&iconX<1740&&iconY>panelY);int count=created;
 assert(pixelBlock==3); // the panel's grain is one gauge pixel (the HUD scale), not its 3/4 drawing scale
 jkRpg_DrawForceHud(&kyle,1740);assert(created==count);
 selected=22;available[22]=amounts[22]=1;sithInventory_g_aTypes[22].flags=8;sithInventory_g_aTypes[22].hudBitmap=&speed;
 jkRpg_DrawForceHud(&kyle,1740);assert(drawnIcon==&speed&&created==count);
 jkPlayer_hudScale=1;Video_format.height=480;jkRpg_DrawForceHud(&kyle,580);assert(freed==1&&created==count+1&&panelX==552&&panelY==455);
 failCanvas=1;jkPlayer_hudScale=2;jkRpg_DrawForceHud(&kyle,1160);assert(freed==2&&!jkRpg_aHudPanels[1]&&boxes==1);failCanvas=0;
 jkRpg_DrawForceHud(&kyle,1160);assert(jkRpg_aHudPanels[1]);
 stdFont font=1;draws=0;Main_bNoHUD=1;jkRpg_DrawHud(&font,0,0,180,1740);assert(!draws&&!badges&&!bacta&&!menus&&!finder&&!weapons);
 jkRpg_bMenuOpen=1;jkRpg_DrawHud(&font,0,0,180,1740);assert(menus==1&&!draws&&!badges);
 Main_bNoHUD=0;jkRpg_DrawHud(&font,0,0,180,1740);assert(menus==2&&badges==1&&bacta==1&&draws==2&&!finder&&!weapons);
 jkRpg_bMenuOpen=0;jkRpg_DrawHud(&font,0,0,180,1740);assert(finder==1&&weapons==1);
 stdBitmap_Free(jkRpg_aHudPanels[1]);puts("Force selection, ownership, live switching, resize/failure cache, mirrored placement and hidden/menu HUD passed");
}
'''
text=(src/'jkRpgMenu.c').read_text()
cleanup=function('jkRpgMenu.c','jkRpg_FreeShippedArt')
assert 'stdBitmap_Free(jkRpg_aHudPanels[i])' in cleanup and 'jkRpg_aHudPanels[i] = NULL' in cleanup
assert 'jkHud_rightBlitX); // RPG' in (src/'jkHud.c').read_text()
scratch=Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-force-hud-check";scratch.mkdir(parents=True,exist_ok=True)
c=scratch/'check.c';binary=scratch/'check'
try:
 c.write_text(harness+function('jkRpgMenu.c','jkRpg_ForceGrayPixel')+''.join(function('jkRpgMenu.c',name) for name in ['jkRpg_ShippedHudPanel','jkRpg_SelectedForceIcon','jkRpg_ForceCost','jkRpg_DrawForceHud'])+function('jkRpg.c','jkRpg_DrawHud')+checks)
 subprocess.run(['cc','-std=c99','-w',str(c),'-lm','-o',str(binary)],check=True)
 subprocess.run([str(binary)],check=True)
finally:
 c.unlink(missing_ok=True);binary.unlink(missing_ok=True)
