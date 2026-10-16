"""Check actual space-sky selection and depth projection; see DEVELOPING.md for visual checks.
Run in WSL: python3 tools/test_sky.py ~/src/OpenJKDF2
"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

source = (Path(sys.argv[1]) / "src/Engine/sithRenderSky.c").read_text()


def function(name):
    start = re.search(r"^(?:int|void) " + name + r"\([^;]*?\)\n\{", source, re.M)
    return source[start.start():source.index("\n}", start.end()) + 2]


harness = r'''
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <strings.h>
#define SDL2_RENDER
#define __strcmpi strcasecmp
#define RD_GEOMETRY_FULL 4
#define RD_LIGHTMODE_FULLYLIT 0
#define RD_TEXTUREMODE_AFFINE 1
typedef double flex_t;
typedef double flex_d_t;
typedef struct { double x,y; } rdVector2;
typedef struct { double x,y,z; } rdVector3;
typedef struct { char mat_fpath[32]; } rdMaterial;
typedef struct { struct { rdMaterial* material; rdVector2 texVertOffset; } face; } sithSurfaceInfo;
typedef struct { int geometryMode,lightingMode,textureMode; rdVector3* aVertices; rdVector2* aTexVerticies; } rdProcEntry;
static int sithRender_geoMode=4, sithRender_lightMode, sithRender_texMode=1, intersections;
static struct { double farPlane; } frustum={1000};
static struct { double half_screen_width,half_screen_height; } canvas={320,240};
static struct { typeof(frustum)* pClipFrustum; double focalLength; typeof(canvas)* pCanvas; } camera={&frustum,240,&canvas}, *rdCamera_g_pCurCamera=&camera;
static struct { rdVector3 lookPos; struct { int orient; } rdCamera; } view, *sithCamera_g_pCurCamera=&view;
static struct { rdVector2 ceilingSkyOffset,horizonSkyOffset; } world, *sithWorld_g_pCurrentWorld=&world;
static int rdCamera_g_camMatrix;
static double sithSector_flt_8553C0=1,sithSector_flt_8553C8=1,sithSector_flt_8553F4,sithSector_flt_8553B8,sithSector_flt_8553C4;
static rdVector3 sithSector_surfaceNormal, sithSector_zMaxVec;
static void rdMatrix_TransformPoint34(rdVector3* out,const rdVector3* in,const int* mat) { *out=*in; }
static void rdVector_Sub3Acc(rdVector3* a,const rdVector3* b) { a->x-=b->x;a->y-=b->y;a->z-=b->z; }
static void rdVector_Add3Acc(rdVector3* a,const rdVector3* b) { a->x+=b->x;a->y+=b->y;a->z+=b->z; }
static void rdVector_Scale3Acc(rdVector3* a,double s) { a->x*=s;a->y*=s;a->z*=s; }
static void rdVector_Normalize3(rdVector3* a,const rdVector3* b) { *a=*b;rdVector_Scale3Acc(a,1/sqrt(b->x*b->x+b->y*b->y+b->z*b->z)); }
static void rdVector_Scale2(rdVector2* a,const rdVector2* b,double s) { a->x=b->x*s;a->y=b->y*s; }
static void rdVector_Add2Acc(rdVector2* a,const rdVector2* b) { a->x+=b->x;a->y+=b->y; }
static int sithIntersect_CheckSphereHit(const rdVector3* a,const rdVector3* b,double c,double d,
 const rdVector3* e,const rdVector3* f,double* g,int h) { intersections++;return 0; }
'''
checks = r'''
int main(void) {
    rdMaterial materials[]={{"00starry.mat"},{"00STARS2.MAT"},{"03sky09k.mat"},{"00starry.mat.extra"}};
    assert(!sithRenderSky_IsSpaceMaterial(NULL));
    for(int m=0;m<4;m++) assert(sithRenderSky_IsSpaceMaterial(&materials[m])==(m<2));
    rdVector3 vertices[3]={{0,0,3},{640,0,3},{320,480,3}};
    rdVector3 viewVertices[3]={{1,2,3},{-1,2,3},{1,2,-3}};
    rdVector2 uv[3]; rdProcEntry face={.aVertices=vertices,.aTexVerticies=uv};
    sithSurfaceInfo info={0};
    for(int m=0;m<2;m++) for(int position=-1000;position<=1000;position+=100) {
        view.lookPos=(rdVector3){position,position/2.0,position/3.0};
        info.face.material=&materials[m];
        sithRenderSky_CeilingFaceToPlane(&face,&info,viewVertices,3);
        for(int i=0;i<3;i++) assert(vertices[i].z==frustum.farPlane && uv[i].x==0 && uv[i].y==0);
        assert(vertices[0].x==0 && vertices[1].x==640 && vertices[2].y==480);
    }
    assert(intersections==0); // No ceiling intersection or camera-position parallax for space.
    info.face.material=&materials[2];
    sithRenderSky_CeilingFaceToPlane(&face,&info,viewVertices,3);
    assert(intersections==3); // Other skies retain their original projection.
    world.horizonSkyOffset=(rdVector2){2,-16};info.face.texVertOffset=(rdVector2){3,4};
    for(int angle=-89;angle<=89;angle++) {
        sithSector_flt_8553B8=angle*2;sithSector_flt_8553C4=angle*3;
        sithRenderSky_HorizonFaceToPlane(&face,&info,3);
        for(int i=0;i<3;i++) assert(vertices[i].z==1000 && uv[i].x==5 && uv[i].y==-12);
    } // SDL horizon UVs carry authored offsets only; no camera-following linear pitch.
    puts("Space materials, distant depth, translation independence and ordinary-sky fallback passed");
}
'''
scratch = Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-sky"
scratch.mkdir(parents=True, exist_ok=True)
cfile, binary = scratch / "sky.c", scratch / "sky"
try:
    cfile.write_text(harness + function("sithRenderSky_IsSpaceMaterial") + "\n" +
                     function("sithRenderSky_CeilingFaceToPlane") + "\n" + function("sithRenderSky_HorizonFaceToPlane") + checks)
    subprocess.run(["cc", "-std=gnu99", str(cfile), "-lm", "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
finally:
    cfile.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)

# The material keeps its authored dimensions when JKGM uploads a larger PNG.
# Compile the real uniform setup, so a 4x replacement cannot enlarge the sky.
engine = Path(sys.argv[1])
renderer = (engine / "src/Platform/GL/std3D.c").read_text()
shader = (engine / "resource/shaders/default_f.glsl").read_text()
start = renderer.index("void std3D_DoTex(")
setup = renderer[start:renderer.index("    if (!tex) {", start)] + "}\n"
assert "uniform vec2 horizonScale;" in shader
assert "horizonScale / vec2(textureSize(tex, 0))" not in shader
assert "* horizonScale;" in shader and "vec2 scale = horizonScale;" in shader
material_source = (engine / "src/Engine/rdMaterial.c").read_text()
start = material_source.index("        texture->alphaMats[mipmap_num].texture_loaded = 0;")
material_init = material_source[start:material_source.index("#if defined(RDMATERIAL_LRU_LOAD_UNLOAD)", start)]
initialization = r'''
static void load_original_dimensions(rdDDrawSurface* out){
    struct {rdDDrawSurface alphaMats[4],opaqueMats[4];} storage={0},*texture=&storage;
    struct {unsigned width,height;} format={256,128};
    for(int mipmap_num=0;mipmap_num<4;mipmap_num++){
''' + material_init + r'''
        assert(texture->alphaMats[mipmap_num].width==format.width);
        assert(texture->alphaMats[mipmap_num].height==format.height);
        assert(texture->opaqueMats[mipmap_num].width==format.width);
        assert(texture->opaqueMats[mipmap_num].height==format.height);
        format.width/=2;format.height/=2;
    }
    *out=texture->alphaMats[0];
}
'''
uniforms = r'''
#include <assert.h>
#include <math.h>
#include <stdio.h>
#define RD_FF_RPG_SPACE_SKY 1
#define RD_FF_RPG_HORIZON_SKY 2
#define RD_FF_RPG_CLOUD_TILE 4
#define SDL2_RENDER
#define TARGET_CAN_JKGM
typedef struct {unsigned width,height;int texture_loaded,frameNum,skip_jkgm;} rdDDrawSurface;
typedef struct {int flags;} rdTri;
static int uniform_spaceSky=0,uniform_horizonSky=1,uniform_horizonScale=2,uniform_cloudTile=3;
static struct {double horizontalPixelsPerRev;} world={1024},*sithWorld_g_pCurrentWorld=&world;
static int flags[4],updates;
static double scale[2];
static void glUniform1i(int uniform,int value){flags[uniform]=value;}
static void glUniform2f(int uniform,float x,float y){assert(uniform==2);scale[0]=x;scale[1]=y;updates++;}
''' + initialization + setup + r'''
int main(void){
    rdTri horizon={2},space={1},wall={0};
    rdDDrawSurface original={0};load_original_dimensions(&original);
    std3D_DoTex(&original,&horizon,1);
    double x=scale[0],y=scale[1];
    assert(flags[1] && fabs(x-1024.0/(2*M_PI*256))<1e-6 && fabs(y-2*x)<1e-6);
    // Uploaded resolution is independent of this original material descriptor.
    int count=updates;
    std3D_DoTex(&original,&space,1);assert(flags[0] && !flags[1] && updates==count);
    std3D_DoTex(&original,&wall,1);assert(!flags[0] && !flags[1] && updates==count);
    std3D_DoTex(NULL,&horizon,1);assert(!flags[1] && updates==count);
    original=(rdDDrawSurface){0,0};std3D_DoTex(&original,&horizon,1);
    assert(isfinite(scale[0]) && isfinite(scale[1]));
    rdTri cloud={4};std3D_DoTex(&original,&cloud,1);assert(flags[3]);
    std3D_DoTex(&original,&wall,1);assert(!flags[3]);
    puts("Sky replacement angular scale, rectangular originals and ordinary/space fallback passed");
}
'''
try:
    cfile.write_text(uniforms)
    subprocess.run(["cc", "-std=gnu99", str(cfile), "-lm", "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
finally:
    cfile.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)

# Compile the actual GLSL edge-blend body with minimal vector/sampler stand-ins.
# A discontinuous source ramp must become continuous across both repeat boundaries.
start = shader.index('vec4 cloudTexture(')
cloud_function = shader[start:shader.index('\n}\n', start)+3]
cloud_check = r'''
#include <cassert>
#include <cmath>
#include <cstdio>
struct vec2 {double x,y; vec2(double v):x(v),y(v){} vec2(double a,double b):x(a),y(b){} };
struct vec4 {double v;};
vec2 operator+(vec2 a,vec2 b){return {a.x+b.x,a.y+b.y};}
vec2 operator*(vec2 a,double b){return {a.x*b,a.y*b};}
vec2 fract(vec2 a){return {a.x-floor(a.x),a.y-floor(a.y)};}
double smooth(double a,double b,double x){x=fmin(1,fmax(0,(x-a)/(b-a)));return x*x*(3-2*x);}
vec2 smoothstep(vec2 a,vec2 b,vec2 x){return {smooth(a.x,b.x,x.x),smooth(a.y,b.y,x.y)};}
vec4 mix(vec4 a,vec4 b,double w){return {a.v*(1-w)+b.v*w};}
static int tex;
vec4 texture(int,vec2 p){return {p.x+2*p.y};}
''' + cloud_function + r'''
int main(){
    const double e=1e-7;
    for(int edge=-3;edge<=3;edge++) for(int i=0;i<=100;i++){
        double v=i/100.;
        assert(fabs(cloudTexture({edge-e,v}).v-cloudTexture({edge+e,v}).v)<1e-5);
        assert(fabs(cloudTexture({v,edge-e}).v-cloudTexture({v,edge+e}).v)<1e-5);
        assert(fabs(cloudTexture({edge-e,edge-e}).v-cloudTexture({edge+e,edge+e}).v)<1e-5);
    }
    assert(fabs(cloudTexture({.5,.5}).v-1.5*.9375)<1e-10);
    puts("Actual cloud sampler preserves interior detail and joins both axes, corners and negative UVs");
}
'''
cloud_cpp = scratch / 'cloud.cpp'
try:
    cloud_cpp.write_text(cloud_check)
    subprocess.run(['c++', '-std=c++17', str(cloud_cpp), '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
finally:
    cloud_cpp.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)

# Exercise the actual JKGM directory/metadata and upload-fallback code with GL and
# image decoding stubbed; source MAT pixels remain the fallback when PNGs are absent.
import tempfile
jkgm = (engine / "src/Platform/GL/jkgm.cpp").read_text()
def cpp_function(signature):
    start = jkgm.index(signature)
    return jkgm[start:jkgm.index("\n}\n", start)+3]
start = jkgm.index("typedef struct jkgm_cache_entry_t")
entry = jkgm[start:jkgm.index("} jkgm_cache_entry_t;",start)+len("} jkgm_cache_entry_t;")]
start = jkgm.index("const fs::path jkgm_materials_path")
paths = jkgm[start:jkgm.index("void jkgm_populate_cache()",start)]
cache_code = r'''
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <filesystem>
#include <unordered_map>
#include <nlohmann/json.hpp>
namespace fs=std::filesystem;
using GLuint=unsigned;using GLubyte=unsigned char;using GLint=int;
''' + entry + paths + r'''
static std::unordered_map<std::string,jkgm_cache_entry_t> jkgm_cache,jkgm_cache_hash;
static bool jkgm_cache_once=false,jkgm_fastpath_disable=false;
struct rdTexture {int has_jkgm_override;};
struct rdMaterial {char mat_full_fpath[128];rdTexture textures[1];};
struct tVBuffer {struct {unsigned width,height;} format;};
struct rdDDrawSurface {
    unsigned width,height,texture_id,emissive_texture_id,displacement_texture_id;
    int texture_loaded,is_16bit,skip_jkgm;
    float emissive_factor[3],albedo_factor[4],displacement_factor;
    void *emissive_data,*albedo_data,*displacement_data;
    jkgm_cache_entry_t* cache_entry;
};
static int Main_bHeadless,jkGuiBuildMulti_bRendering,jkPlayer_bEnableTexturePrecache;
static int jkPlayer_bEnableJkgm=1,jkPlayer_enableTextureFilter=1;
static rdDDrawSurface* std3D_aLoadedSurfaces[1024];
static GLuint std3D_aLoadedTextures[1024],worldpal_texture;
static size_t std3D_loadedTexturesAmt;
static int uploads,deletes,uploadWidth,uploadHeight,alignment=4;
#define stdPlatform_Printf printf
static void jkgm_free_cache_entry(jkgm_cache_entry_t*){}
static int loadPngImage(const char* path,int* w,int* h,int* alpha,GLubyte** data,int){
    if(!fs::is_regular_file(path)) return 0;
    static GLubyte pixels[4];*w=1254;*h=627;*alpha=0;*data=pixels;return 1;
}
static std::string jkgm_get_tex_hash(tVBuffer*,rdDDrawSurface*,rdMaterial*,int){return "";}
static int std3D_AddToTextureCache(tVBuffer*,rdDDrawSurface*,int,int){return 0;}
int jkgm_std3D_AddToTextureCache(tVBuffer*,rdDDrawSurface*,int,int,rdMaterial*,int);
#define glActiveTexture(...) ((void)0)
#define glBindTexture(...) ((void)0)
#define glTexParameteri(...) ((void)0)
static void glPixelStorei(int,int);
static void glGetIntegerv(int,int*);
static void glGenTextures(int,GLuint* out){*out=7;}
static void glDeleteTextures(int,GLuint*){deletes++;}
static void glTexImage2D(int,int,int,int w,int h,int,int,int,const void*){assert(alignment==1);uploads++;uploadWidth=w;uploadHeight=h;}
'''
# Names are numeric only in these stubs; real cache decisions and metadata parsing compile unchanged.
constants=sorted(set(re.findall(r"\bGL_[A-Z0-9_]+\b",cpp_function("int jkgm_std3D_AddToTextureCache("))))
cache_code += "enum {"+",".join(constants)+"};\n"
cache_code += "static void glPixelStorei(int key,int value){if(key==GL_UNPACK_ALIGNMENT)alignment=value;}\n"
cache_code += "static void glGetIntegerv(int key,int* value){assert(key==GL_UNPACK_ALIGNMENT);*value=alignment;}\n"
cache_code += cpp_function("void jkgm_populate_cache()") + cpp_function("void jkgm_populate_shortcuts(") + cpp_function("int jkgm_std3D_AddToTextureCache(")
cache_code += r'''
static void metadata(const char* root,const char* filename){
    fs::create_directories(root);
    nlohmann::json entry={{"albedo_map",filename},{"replaces",{{{"name","mat/03sky09k.mat"},{"cel",0}}}},{"replaces_signatures",nlohmann::json::array()}};
    std::ofstream(std::string(root)+"/metadata.json") << nlohmann::json{{"materials",{entry}}};
}
int main(){
    jkgm_populate_cache();assert(jkgm_fastpath_disable && jkgm_cache.empty());
    jkgm_fastpath_disable=false;
    metadata("jkgm/materials/external","old.png");
    metadata("rpg/jkgm/materials/rekindled-sky","new.png");
    jkgm_populate_cache();assert(jkgm_cache_once && jkgm_cache.size()==1);
    auto& entry=jkgm_cache.at("mat/03sky09k.mat0");
    assert(entry.albedo_tex=="rpg/jkgm/materials/rekindled-sky/new.png");
    tVBuffer buffer={{256,128}};rdDDrawSurface texture={};texture.width=256;texture.height=128;
    rdMaterial material={"mat/03sky09k.mat",{}};
    jkgm_populate_shortcuts(&buffer,&texture,&material,0,0,0);
    assert(texture.cache_entry==&entry && !texture.skip_jkgm);
    assert(!jkgm_std3D_AddToTextureCache(&buffer,&texture,0,0,&material,0));
    assert(!texture.texture_loaded && !material.textures[0].has_jkgm_override && !uploads && deletes==1);
    // Providing a valid decoded image changes upload resolution, never the authored dimensions.
    std::ofstream(entry.albedo_tex)<<"decoded by test stub";
    assert(jkgm_std3D_AddToTextureCache(&buffer,&texture,0,0,&material,0));
    assert(uploads==1 && uploadWidth==1254 && uploadHeight==627 && texture.is_16bit && alignment==4);
    assert(texture.width==256 && texture.height==128 && buffer.format.width==256 && buffer.format.height==128);
    assert(material.textures[0].has_jkgm_override && texture.texture_loaded);
    rdMaterial wall={"mat/wall.mat",{}};rdDDrawSurface untouched={};
    jkgm_populate_shortcuts(&buffer,&untouched,&wall,0,0,0);assert(untouched.skip_jkgm);
    assert(!jkgm_std3D_AddToTextureCache(&buffer,&untouched,0,0,&wall,0));
    texture.texture_loaded=0;jkPlayer_bEnableJkgm=0;
    assert(!jkgm_std3D_AddToTextureCache(&buffer,&texture,0,0,&material,0));
    assert(!material.textures[0].has_jkgm_override);
    puts("Sky PNG lookup, mod precedence, missing-image fallback, original dimensions and unaffected materials passed");
}
'''
cpp = scratch / "sky-cache.cpp"
try:
    cpp.write_text(cache_code)
    subprocess.run(["c++", "-std=c++17", "-I"+str(engine/"3rdparty/json/single_include"), str(cpp), "-o", str(binary)], check=True)
    with tempfile.TemporaryDirectory(prefix="cache-",dir=scratch) as fixture:
        subprocess.run([str(binary)],cwd=fixture,check=True)
finally:
    cpp.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)

# The release embeds only the mod's runtime PNGs and metadata, never extracted references.
import ast
release = Path(__file__).with_name("build_release.py")
module = ast.parse(release.read_text())
main = next(node for node in module.body if isinstance(node,ast.FunctionDef) and node.name=="main")
start = next(i for i,node in enumerate(main.body) if isinstance(node,ast.Assign)
             and any(isinstance(t,ast.Name) and t.id=="sky" for t in node.targets))
asset_block = ast.Module(body=main.body[start:start+2],type_ignores=[])
with tempfile.TemporaryDirectory(prefix="package-",dir=scratch) as fixture:
    project = Path(fixture)
    folder = project/"jkgm/materials/rekindled-sky"
    folder.mkdir(parents=True)
    (folder/"03sky09k.png").write_bytes(b"replacement")
    (folder/"metadata.json").write_text('{"materials":[]}')
    (folder/"source.mat").write_bytes(b"original, never packaged")
    (folder/"notes.txt").write_text("not runtime")
    scope={"PROJECT":project,"files":{}}
    exec(compile(asset_block,str(release),"exec"),scope)
    assert scope["files"]=={"jkgm/materials/rekindled-sky/03sky09k.png":b"replacement",
                            "jkgm/materials/rekindled-sky/metadata.json":b'{"materials":[]}'}
    (folder/"metadata.json").unlink()
    scope["files"]={}
    exec(compile(asset_block,str(release),"exec"),scope)
    assert not scope["files"]
print("Sky release asset allowlist and absent-pack fallback passed")
