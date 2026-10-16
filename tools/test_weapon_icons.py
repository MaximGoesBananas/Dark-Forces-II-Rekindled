"""Check the actual runtime weapon-mesh projection, cache and allocation failures.
Run in WSL: python3 tools/test_weapon_icons.py ~/src/OpenJKDF2
The running game supplies the real meshes for the separate visual check.
"""
import os
import tempfile
import subprocess
import sys
from pathlib import Path

source = (Path(sys.argv[1]) / "src/Main/jkRpg.c").read_text()
start = source.index("#define RPG_ICON_W")
code = source[start:source.index("void jkRpg_DrawWeaponIcon", start)]
harness = r'''
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#define SDL2_RENDER 1
#define STDBITMAP_PARTIAL_LOAD 1
typedef float flex_t;
typedef struct {flex_t x,y,z;} rdVector3;
typedef struct {flex_t x,y;} rdVector2;
typedef struct {uint8_t r,g,b;} rdColor24;
typedef struct rdMaterial rdMaterial;
typedef struct {unsigned numVertices; int* vertexPosIdx; rdVector3 normal; rdMaterial* material; int* vertexUVIdx; rdVector2 texVertOffset;} rdFace;
typedef struct {int numVertices,numFaces;rdVector3* aVertices;rdFace* faces; rdVector2* aTexVerticies; int numUVs;} rdMesh;
typedef struct {int numGeos;struct {int numMeshes;rdMesh* aMeshes;} aGeos[1];} rdModel3;
typedef struct {int bpp,is16bit,r_bits,g_bits,b_bits,r_shift,g_shift,b_shift,r_bitdiff,g_bitdiff,b_bitdiff;} rdTexFormat;
typedef struct {int width,height,rowSize;rdTexFormat format;} tRasterInfo;
typedef struct {tRasterInfo format;void* surface_lock_alloc;} tVBuffer;
typedef struct {tVBuffer* mipSurfaces[1];uint32_t* aTextureIds;int* abLoadedToGPU;void** paDataDepthConverted;int bLoaded;} stdBitmap;
typedef struct {tVBuffer* texture_struct[4];} rdTexture;
typedef struct {rdTexture* texture_ptr;} rdTexinfo;
struct rdMaterial {unsigned num_texinfo;rdTexinfo* texinfos[1];rdColor24* palette_alloc;};
static int rdMaterial_EnsureData(rdMaterial* m){return 1;}
typedef struct {rdColor24 colors[256];} Colormap;
static struct {Colormap* colormaps;} world,*sithWorld_g_pCurrentWorld=&world;
static int allocation,failAt,live,missing,lockFail,loads;
static void* allocate(size_t n) {if (++allocation==failAt)return NULL;void* p=calloc(1,n);assert(p);live++;return p;}
static void release(void* p) {if(p){free(p);live--;}}
#define STD_ALLOC allocate
#define STD_FREE release
static rdModel3 model;
static rdModel3* sithModel_Load(const char* n,int fallback) {loads++;return missing?NULL:&model;}
static stdBitmap* stdBitmap_New(int a,int b,int c,int d,rdTexFormat* f){return allocate(sizeof(stdBitmap));}
static tVBuffer* stdDisplay_VBufferNew(tRasterInfo* f,int a,int b,void* c){
    tVBuffer* v=allocate(sizeof(*v));if(!v)return NULL;
    v->format=*f;v->format.rowSize=f->width*2;v->surface_lock_alloc=allocate(f->height*v->format.rowSize);
    if(!v->surface_lock_alloc){release(v);return NULL;}return v;
}
static void stdBitmap_Free(stdBitmap* b){
    if(b->mipSurfaces[0]){release(b->mipSurfaces[0]->surface_lock_alloc);release(b->mipSurfaces[0]);}
    release(b->aTextureIds);release(b->abLoadedToGPU);release(b->paDataDepthConverted);release(b);
}
static int stdDisplay_VBufferLock(tVBuffer* b){return !lockFail;}
static void stdDisplay_VBufferUnlock(tVBuffer* b){}
'''
checks = r'''
int main(void){
    rdVector3 vertices[]={{0,-1,-.5},{0,1,-.5},{0,0,.5}};
    int indices[]={0,1,2};rdFace face={3,indices,{0,0,1}};rdMesh mesh={3,1,vertices,&face};
    model=(rdModel3){1,{{1,&mesh}}};
    assert(!jkRpg_WeaponIcon(0) && !jkRpg_WeaponIcon(12));
    // A model that cannot become an icon is not reloaded every frame, only after the HUD is rebuilt.
    missing=1;assert(!jkRpg_WeaponIcon(2));int tries=loads;assert(!jkRpg_WeaponIcon(2) && loads==tries);missing=0;
    assert(!jkRpg_WeaponIcon(2));jkRpg_FreeWeaponIcons();
    stdBitmap* b=jkRpg_WeaponIcon(2);assert(b && b->bLoaded);
    int before=loads;assert(jkRpg_WeaponIcon(2)==b && loads==before);
    uint16_t* pixels=b->mipSurfaces[0]->surface_lock_alloc;
    int filled=0;for(int i=0;i<RPG_ICON_W*RPG_ICON_H;i++)if(pixels[i]&0x8000)filled++;
    assert(filled>100 && filled<RPG_ICON_W*RPG_ICON_H/2);
    assert(pixels[(RPG_ICON_H/2)*RPG_ICON_W+RPG_ICON_W/2]&0x8000);
    for(int x=0;x<RPG_ICON_W;x++)assert(pixels[x]==0 && pixels[(RPG_ICON_H-1)*RPG_ICON_W+x]==0);
    jkRpg_FreeWeaponIcons();assert(live==0);
    // Every allocation failure is clean and permits a successful retry once the HUD is rebuilt.
    for(int f=1;f<=8;f++){
        allocation=0;failAt=f;assert(!jkRpg_WeaponIcon(3));assert(live==0);jkRpg_FreeWeaponIcons();
    }
    failAt=0;lockFail=1;assert(!jkRpg_WeaponIcon(3) && live==0);lockFail=0;jkRpg_FreeWeaponIcons();
    b=jkRpg_WeaponIcon(3);assert(b);jkRpg_FreeWeaponIcons();assert(live==0);
    indices[2]=999;b=jkRpg_WeaponIcon(4);assert(b);
    pixels=b->mipSurfaces[0]->surface_lock_alloc;
    for(int i=0;i<RPG_ICON_W*RPG_ICON_H;i++)assert(!pixels[i]);
    jkRpg_FreeWeaponIcons();assert(live==0);
    // The original fist uses its own UVs and palette; missing textures retain the shaded model.
    indices[2]=2;rdVector2 uv[3]={{0,0},{0,0},{0,0}};mesh.aTexVerticies=uv;mesh.numUVs=3;
    face.vertexUVIdx=indices;Colormap cm={0};cm.colors[7]=(rdColor24){160,80,40};world.colormaps=&cm;
    uint8_t texel=7;tVBuffer skin={.format={.width=1,.height=1,.rowSize=1,.format={.bpp=8}},.surface_lock_alloc=&texel};
    rdTexture texture={{&skin}};rdTexinfo info={&texture};rdMaterial material={1,{&info},NULL};face.material=&material;
    b=jkRpg_WeaponIcon(1);assert(b);pixels=b->mipSurfaces[0]->surface_lock_alloc;
    uint16_t centre=pixels[(RPG_ICON_H/2)*RPG_ICON_W+RPG_ICON_W/2];
    assert(centre==(0x8000|(18<<10)|(9<<5)|4));jkRpg_FreeWeaponIcons();assert(live==0);
    puts("Weapon model icons: projection, transparency, cache, invalid faces and allocation recovery passed");
}
'''
scratch = Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-weapons"
scratch.mkdir(parents=True, exist_ok=True)
cfile, binary = scratch / "icons.c", scratch / "icons"
try:
    cfile.write_text(harness + code + checks)
    subprocess.run(["cc", "-std=c99", str(cfile), "-lm", "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
finally:
    cfile.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)
