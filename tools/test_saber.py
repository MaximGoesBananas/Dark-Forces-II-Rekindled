"""Compile actual saber color persistence and material conversion. Inspect the blade in-game too."""
import os
import tempfile
from pathlib import Path
import subprocess
import sys

root = Path(sys.argv[1]) / "src"
rpg = (root / "Main/jkRpg.c").read_text()
material = (root / "Engine/rdMaterial.c").read_text()
colors = rpg[rpg.index("static const char* jkRpg_aSaberColors"):rpg.index("void jkRpg_SaberMaterials")]
conversion = material[material.index("static int rdMaterial_BlueSaberPixel"):material.index("#endif", material.index("static int rdMaterial_BlueSaberPixel"))]
harness = r'''
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <strings.h>
#define __strcmpi strcasecmp
static int saved=-999, writes, failAllocation, freed;
static int wuRegistry_GetInt(const char* key, int fallback) { return saved==-999 ? fallback : saved; }
static void wuRegistry_SaveInt(const char* key, int value) { saved=value; writes++; }
typedef struct { int width,height,rowSize; struct { int bpp,is16bit; } format; } tRasterInfo;
typedef struct { tRasterInfo format; void* surface_lock_alloc; } tVBuffer;
static const char* stdFileFromPath(const char* p) { const char* n=p; for (;*p;p++) if (*p=='/' || *p=='\\') n=p+1; return n; }
static void stdDisplay_VBufferLock(tVBuffer* p) {}
static void stdDisplay_VBufferUnlock(tVBuffer* p) {}
static tVBuffer* stdDisplay_VBufferNew(tRasterInfo* f,int a,int b,const void* p) {
    if (failAllocation) return NULL;
    tVBuffer* v=calloc(1,sizeof(*v)); v->format=*f;
    v->format.rowSize=(f->width*f->format.bpp/8+3)&~3;
    v->surface_lock_alloc=calloc(f->height,v->format.rowSize); return v;
}
static void stdDisplay_VBufferFree(tVBuffer* v) { freed++; free(v->surface_lock_alloc);free(v); }
'''
checks = r'''
int main(void) {
    const char* names[]={"Green","Blue","Purple","Yellow","Red"};
    int ids[]={2,0,3,4,1};
    assert(jkRpg_GetSaberColor()==0); // Fresh settings: green.
    for (int i=0;i<5;i++) {
        saved=ids[i];jkRpg_saberColor=-1;
        assert(jkRpg_GetSaberColor()==i && !strcmp(jkRpg_SaberColorName(i),names[i]));
        jkRpg_SetSaberColor(i);assert(saved==ids[i]);
        jkRpg_saberColor=-1;assert(jkRpg_GetSaberColor()==i);
    }
    for (int i=-2;i<=6;i++) if (i<0 || i>4) {
        int before=writes; jkRpg_SetSaberColor(i);assert(writes==before);
        saved=i;jkRpg_saberColor=-1;assert(jkRpg_GetSaberColor()==0);
    }
    for (int alpha=0;alpha<2;alpha++) {
        assert(rdMaterial_BlueSaberPixel(0,alpha)==0);
        assert(rdMaterial_BlueSaberPixel(16,alpha)==65535);
        int edge=rdMaterial_BlueSaberPixel(137,alpha);
        assert((edge&31)==31 && ((edge>>(alpha?10:11))&31)<=1);
        if(alpha) assert(edge&0x8000);
        tRasterInfo f={.width=3,.height=2,.format={.bpp=8}};
        tVBuffer* v=stdDisplay_VBufferNew(&f,0,0,NULL);
        unsigned char* pixels=v->surface_lock_alloc;
        unsigned char indices[]={0,16,137,99,17,138,140,99};
        memcpy(pixels,indices,8); // Non-pixel padding must never be read.
        assert(rdMaterial_BlueSaber(v,"sabergreen1.mat",alpha)==v);
        failAllocation=1;assert(rdMaterial_BlueSaber(v,"saberblue1.mat",alpha)==v);failAllocation=0;
        pixels[0]=99;assert(rdMaterial_BlueSaber(v,"saberblue1.mat",alpha)==v);pixels[0]=0;
        int before=freed;
        tVBuffer* converted=rdMaterial_BlueSaber(v,"mat/SABERBLUE1.MAT",alpha);
        assert(converted!=v && freed==before+1 && converted->format.format.bpp==16);
        for(int y=0;y<2;y++) for(int x=0;x<3;x++)
            assert(((uint16_t*)((char*)converted->surface_lock_alloc+y*converted->format.rowSize))[x]==rdMaterial_BlueSaberPixel(indices[y*4+x],alpha));
        assert(rdMaterial_BlueSaber(converted,"saberblue1.mat",alpha)==converted);
        stdDisplay_VBufferFree(converted);
    }
    puts("Saber order, saved colors, blue gradient, transparency and conversion fallbacks passed");
}
'''
scratch = Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-saber-check"
scratch.mkdir(exist_ok=True, parents=True)
cfile, binary = scratch / "check.c", scratch / "check"
try:
    cfile.write_text(harness + colors + conversion + checks)
    subprocess.run(["cc", "-std=gnu99", str(cfile), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
finally:
    cfile.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)
