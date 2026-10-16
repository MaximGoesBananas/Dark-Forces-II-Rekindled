"""Check glass back-face UVs, collision flags and save repair using the real code."""
from pathlib import Path
import subprocess
import sys
import tempfile

src = Path(sys.argv[1]) / "src"
source = (src / "Main/jkRpg.c").read_text()
start = source.index("int jkRpg_IsGlassBackSurface(")
end = source.index("\n}", source.index("static void jkRpg_TextureGlassBacks(", start)) + 2
code = source[start:end]
assert "|| jkRpg_IsGlassBackSurface(pWorld, v67)" in (src / "World/sithSurface.c").read_text()
assert "    jkRpg_TextureGlassBacks();" in source
assert "pWorld->numTexVertices = textureVertices;" in (src / "World/sithWorld.c").read_text()
assert "static void jkRpg_ResetSession(void)\n{\n    jkRpg_glassPrepared = 0;" in source
harness = r'''
#include <assert.h>
#include <string.h>
#include <strings.h>
#define __strcmpi strcasecmp
#define RD_GEOMETRY_FULL 4
#define RD_FF_TEX_TRANSLUCENT 2
#define SITHSURF_ADJOIN_ALLOW_MOVEMENT 2
static int Main_bMotsCompat, sithNet_isMulti, jkRpg_glassPrepared;
typedef struct { char mat_fpath[32]; } rdMaterial;
typedef struct { unsigned type, numVertices, wallCel; int geometryMode, textureMode;
 int *vertexPosIdx, *vertexUVIdx; rdMaterial *material; int texVertOffset; } rdFace;
typedef struct SithSurface SithSurface;
typedef struct SithSurfaceAdjoin { unsigned flags; struct SithSurfaceAdjoin *mirror; SithSurface *surface; } SithSurfaceAdjoin;
struct SithSurface { struct { rdFace face; } surfaceInfo; SithSurfaceAdjoin *pAdjoin; };
typedef struct { const char *map_jkl_fname; int numSurfaces; SithSurface *surfaces; int numTexVertices; } SithWorld;
static SithSurface surfaces[5500];
static SithWorld world = {"10cargo.jkl", 5500, surfaces, 20000}, *sithWorld_g_pCurrentWorld = &world;
static SithWorld* sithWorld_g_pLastLoadedWorld=&world;
static rdMaterial escapeGlass={"00wglas2.mat"}, fallback={"dflt.mat"};
static int loadFailure;
static rdMaterial* sithMaterial_Load(const char* name,int a,int b) {
 assert(!strcmp(name,"00wglas2.mat"));return loadFailure==1?0:loadFailure==2?&fallback:&escapeGlass;
}
'''
checks = r'''
int main(void) {
 rdMaterial glass={"00wglas2.mat"}, wall={"wall.mat"};
 int frontPos[]={10,11,12,13}, backPos[]={13,12,11,10}, frontUV[]={20,21,22,23}, backUV[4]={-1,-1,-1,-1};
 SithSurface *front=&surfaces[1880], *back=&surfaces[1891];
 SithSurfaceAdjoin a={5,0,back}, b={5,&a,front}; a.mirror=&b;
 back->pAdjoin=&a; front->pAdjoin=&b;
 front->surfaceInfo.face=(rdFace){.numVertices=4,.geometryMode=4,.textureMode=1,.material=&glass,
 .vertexPosIdx=frontPos,.vertexUVIdx=frontUV,.wallCel=0,.texVertOffset=7};
 rdFace original=front->surfaceInfo.face;
 back->surfaceInfo.face=(rdFace){.numVertices=4,.vertexPosIdx=backPos,.vertexUVIdx=backUV};
 jkRpg_TextureGlassBacks();
 assert(back->surfaceInfo.face.material==&glass && back->surfaceInfo.face.type==2);
 assert(back->surfaceInfo.face.geometryMode==4 && back->surfaceInfo.face.texVertOffset==7);
 for(int i=0;i<4;i++) assert(backUV[i]==23-i);
 assert(a.flags==5 && b.flags==5 && !memcmp(&original,&front->surfaceInfo.face,sizeof(rdFace)));
 // A freshly parsed world with a new save's surface status still needs its UVs rebuilt.
 memset(backUV,0,sizeof(backUV)); jkRpg_glassPrepared=0; jkRpg_TextureGlassBacks(); assert(backUV[0]==23);
 // An old save can restore the original invisible face in the same world.
 back->surfaceInfo.face.material=0; back->surfaceInfo.face.geometryMode=0;
 jkRpg_glassPrepared=0; jkRpg_TextureGlassBacks(); assert(back->surfaceInfo.face.material==&glass);
 // Open/broken panes, other materials, unmatched vertices and unavailable arrays remain untouched.
 back->surfaceInfo.face.material=0; a.flags=7; jkRpg_glassPrepared=0; jkRpg_TextureGlassBacks(); assert(!back->surfaceInfo.face.material);
 a.flags=5; front->surfaceInfo.face.material=&wall; jkRpg_glassPrepared=0; jkRpg_TextureGlassBacks(); assert(!back->surfaceInfo.face.material);
 front->surfaceInfo.face.material=&glass; backPos[3]=99; jkRpg_glassPrepared=0; jkRpg_TextureGlassBacks(); assert(!back->surfaceInfo.face.material);
 backPos[3]=10; back->surfaceInfo.face.vertexUVIdx=0; jkRpg_glassPrepared=0; jkRpg_TextureGlassBacks(); assert(!back->surfaceInfo.face.material);
 assert(!jkRpg_IsGlassBackSurface(&world,1880));
 world.map_jkl_fname="12escape.jkl"; assert(!jkRpg_IsGlassBackSurface(&world,3921));
 // The reported control-room pane has neither front nor back artwork initially.
 world.map_jkl_fname="12escape.jkl";
 int panePos[]={10,11,12,13}, paneBackPos[]={13,12,11,10};
 int paneUV[]={-1,-1,-1,-1}, paneBackUV[]={-1,-1,-1,-1};
 SithSurface *pane=&surfaces[2448], *paneBack=&surfaces[2460];
 SithSurfaceAdjoin pa={29,0,pane}, pb={29,&pa,paneBack}; pa.mirror=&pb;
 pane->pAdjoin=&pa; paneBack->pAdjoin=&pb;
 pane->surfaceInfo.face=(rdFace){.numVertices=4,.vertexPosIdx=panePos,.vertexUVIdx=paneUV};
 paneBack->surfaceInfo.face=(rdFace){.numVertices=4,.vertexPosIdx=paneBackPos,.vertexUVIdx=paneBackUV};
 surfaces[3735].surfaceInfo.face=original;
 jkRpg_glassPrepared=0; jkRpg_TextureGlassBacks();
 assert(pane->surfaceInfo.face.material==&glass && paneBack->surfaceInfo.face.material==&glass);
 assert(pane->surfaceInfo.face.type==2 && paneBack->surfaceInfo.face.type==2);
 assert(paneUV[0]==22 && paneBackUV[0]==21 && pa.flags==29 && pb.flags==29);
 memset(paneUV,0,sizeof(paneUV)); memset(paneBackUV,0,sizeof(paneBackUV));
 jkRpg_glassPrepared=0; jkRpg_TextureGlassBacks(); assert(paneUV[0]==22 && paneBackUV[0]==21);
 pane->surfaceInfo.face.material=0; paneBack->surfaceInfo.face.material=0; pa.flags=pb.flags=31;
 jkRpg_glassPrepared=0; jkRpg_TextureGlassBacks();
 assert(!pane->surfaceInfo.face.material && !paneBack->surfaceInfo.face.material);
 // The escape window's inside is glass; its authored outer wall and one-way visibility stay intact.
 rdMaterial hull={"00_base3.mat"};
 SithSurface *inside=&surfaces[5264], *outside=&surfaces[5367];
 SithSurfaceAdjoin ea={5,0,inside}, eb={4,&ea,outside};ea.mirror=&eb;
 inside->pAdjoin=&ea;outside->pAdjoin=&eb;
 outside->surfaceInfo.face=original;outside->surfaceInfo.face.material=&hull;
 rdFace outerOriginal=outside->surfaceInfo.face;
 const char* maps[]={"16aescapeship.jkl","16BESCAPESHIP.JKL"};
 for(int m=0;m<2;m++) {
  world.map_jkl_fname=maps[m];assert(jkRpg_IsGlassBackSurface(&world,5264));
  assert(!jkRpg_IsGlassBackSurface(&world,5367) && !jkRpg_IsGlassBackSurface(&world,4419));
  for(int restored=0;restored<2;restored++) {
   inside->surfaceInfo.face=(rdFace){.numVertices=4,.vertexPosIdx=backPos,.vertexUVIdx=backUV,
       .material=restored?&escapeGlass:0};
   memset(backUV,0,sizeof(backUV));jkRpg_glassPrepared=0;jkRpg_TextureGlassBacks();
   assert(inside->surfaceInfo.face.material==&escapeGlass && inside->surfaceInfo.face.geometryMode==4);
   assert(inside->surfaceInfo.face.type==2 && backUV[0]==23 && backUV[3]==20);
   assert(ea.flags==5 && eb.flags==4 && !memcmp(&outerOriginal,&outside->surfaceInfo.face,sizeof(rdFace)));
  }
  inside->surfaceInfo.face.material=0;ea.flags=7;
  jkRpg_glassPrepared=0;jkRpg_TextureGlassBacks();assert(!inside->surfaceInfo.face.material);ea.flags=5;
  for(loadFailure=1;loadFailure<=2;loadFailure++) {
   jkRpg_glassPrepared=0;jkRpg_TextureGlassBacks();assert(!inside->surfaceInfo.face.material);
  }
  loadFailure=0;
  sithWorld_g_pLastLoadedWorld=0;jkRpg_glassPrepared=0;jkRpg_TextureGlassBacks();
  assert(!inside->surfaceInfo.face.material);sithWorld_g_pLastLoadedWorld=&world;
 }
 // Both blank panes in the descent control-room window gain visible front and back faces.
 memset(surfaces,0,sizeof(surfaces));world.map_jkl_fname="19a.jkl";
 surfaces[3337].surfaceInfo.face=original;
 for(int pane=0;pane<2;pane++) {
  SithSurface* outside=&surfaces[65+pane];
  SithSurface* inside=&surfaces[pane?305:299];
  SithSurfaceAdjoin out={5,0,outside},in={5,&out,inside};out.mirror=&in;
  outside->pAdjoin=&out;inside->pAdjoin=&in;
  int uv[4]={-1,-1,-1,-1},reverseUV[4]={-1,-1,-1,-1};
  outside->surfaceInfo.face=(rdFace){.numVertices=4,.vertexPosIdx=frontPos,.vertexUVIdx=uv};
  inside->surfaceInfo.face=(rdFace){.numVertices=4,.vertexPosIdx=backPos,.vertexUVIdx=reverseUV};
  jkRpg_glassPrepared=0;jkRpg_TextureGlassBacks();
  assert(outside->surfaceInfo.face.material==&glass && inside->surfaceInfo.face.material==&glass);
  for(int v=0;v<4;v++)assert(uv[v]==20+v && reverseUV[v]==23-v);
  assert(out.flags==5 && in.flags==5);
  outside->surfaceInfo.face.material=0;outside->surfaceInfo.face.geometryMode=0;
  jkRpg_glassPrepared=0;jkRpg_TextureGlassBacks();assert(outside->surfaceInfo.face.material==&glass);
  outside->surfaceInfo.face.material=0;inside->surfaceInfo.face.material=0;out.flags=in.flags=7;
  jkRpg_glassPrepared=0;jkRpg_TextureGlassBacks();assert(!outside->surfaceInfo.face.material && !inside->surfaceInfo.face.material);
  outside->pAdjoin=inside->pAdjoin=0;
 }
 // The lower window includes a five-vertex pane with a collinear midpoint.
 for(int map=0;map<2;map++) for(int p=0;p<2;p++) {
  world.map_jkl_fname=map?"19b.jkl":"19a.jkl";
  int indices[2][2]={{map?424:5146,map?436:5158},{map?554:5262,map?442:5164}}, count=p?4:5;
  int pos[5]={1,2,3,4,5},rev[5],uv[5],revUV[5];
  const int expected[2][2][5]={{{116,267,680,3361,676},{676,680,267,116,0}},{{33,160,1972,1753,1916},{1916,1972,160,33,0}}};
  SithSurface *front=&surfaces[indices[p][0]],*back=&surfaces[indices[p][1]];
  SithSurfaceAdjoin a={5,0,front},b={5,&a,back};a.mirror=&b;
  front->pAdjoin=&a;back->pAdjoin=&b;
  assert(jkRpg_IsGlassBackSurface(&world,indices[p][0]) && jkRpg_IsGlassBackSurface(&world,indices[p][1]));
  for(int v=0;v<count;v++)rev[v]=pos[count-1-v];
  front->surfaceInfo.face=(rdFace){.numVertices=count,.vertexPosIdx=pos,.vertexUVIdx=uv};
  back->surfaceInfo.face=(rdFace){.numVertices=count,.vertexPosIdx=rev,.vertexUVIdx=revUV};
  for(int restored=0;restored<3;restored++) {
   if(restored==1)front->surfaceInfo.face.material=back->surfaceInfo.face.material=0;
   memset(uv,0,sizeof(uv));memset(revUV,0,sizeof(revUV));
   jkRpg_glassPrepared=0;jkRpg_TextureGlassBacks();
   assert(front->surfaceInfo.face.material==&escapeGlass && back->surfaceInfo.face.material==&escapeGlass);
   for(int v=0;v<count;v++)assert(uv[v]==expected[map][p][v] && revUV[v]==expected[map][p][count-1-v]);
   assert(a.flags==5 && b.flags==5);
  }
  front->surfaceInfo.face.material=back->surfaceInfo.face.material=0;a.flags=b.flags=7;
  jkRpg_glassPrepared=0;jkRpg_TextureGlassBacks();assert(!front->surfaceInfo.face.material && !back->surfaceInfo.face.material);
  a.flags=b.flags=5;world.numTexVertices=map?1972:3361;
  jkRpg_glassPrepared=0;jkRpg_TextureGlassBacks();assert(!front->surfaceInfo.face.material && !back->surfaceInfo.face.material);
  world.numTexVertices=20000;front->pAdjoin=back->pAdjoin=0;
 }
 world.map_jkl_fname="19a.jkl"; assert(jkRpg_IsGlassBackSurface(&world,2669));
 sithNet_isMulti=1; assert(!jkRpg_IsGlassBackSurface(&world,2669)); sithNet_isMulti=0;
 Main_bMotsCompat=1; assert(!jkRpg_IsGlassBackSurface(&world,2669));
 sithWorld_g_pCurrentWorld=0; jkRpg_glassPrepared=0; jkRpg_TextureGlassBacks();
 return 0;
}
'''
with tempfile.TemporaryDirectory(prefix="jk-glass-") as tmp:
    path=Path(tmp)
    (path/"check.c").write_text(harness+code+checks)
    subprocess.run(["cc", "-std=c99", "-Wall", "-Werror", str(path/"check.c"), "-o", str(path/"check")],check=True)
    subprocess.run([str(path/"check")],check=True)
print("Glass backs: matched UVs, old/new saves, original fronts, collision and exclusions passed")
