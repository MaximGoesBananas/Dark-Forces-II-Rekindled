"""Keep the distance of the accepted collision when later faces/meshes miss.
Run in WSL: python3 tools/test_collision_distance.py ~/src/OpenJKDF2
"""
import os
import tempfile
import subprocess
import sys
from pathlib import Path

source = (Path(sys.argv[1]) / "src/Engine/sithIntersect.c").read_text()
start = source.index("int sithIntersect_CheckSphereMeshIntersection(")
mesh = source[start:source.index("\n}", start) + 2]
start = source.index("    for (thinga = 0;")
end = source.index("\n    return v28;", start)
# Compile the actual mesh traversal and accepted-result block from the thing query.
traversal = source[start:end]
harness = r'''
#include <assert.h>
#include <stdio.h>
typedef double flex_t,flex_d_t;
typedef struct {double x,y,z;} rdVector3;
typedef struct {rdVector3 normal;double distance;int result;} rdFace;
typedef struct {int numFaces;rdFace* faces;rdVector3* aVertices;} rdMesh;
typedef struct {int numMeshes;rdMesh* aMeshes;} rdGeoset;
enum {SITHCOLLISION_THING=1,SITHCOLLISION_THINGADJOINCROSS=4};
#define SITH_ASSERTREL assert
static void rdVector_Copy3(rdVector3* a,const rdVector3* b){*a=*b;}
static double rdVector_Dot3(const rdVector3* a,const rdVector3* b){return a->x*b->x+a->y*b->y+a->z*b->z;}
static void rdMatrix_TransformVector34Acc(rdVector3* v,void* m){}
static void rdVector_Neg3Acc(rdVector3* v){v->x=-v->x;v->y=-v->y;v->z=-v->z;}
static int sithIntersect_CheckSphereFaceIntersectionEx(rdVector3* start,rdVector3* dir,
 double limit,double radius,rdFace* face,rdVector3* vertices,double* distance,rdVector3* normal,int flags){
    /* The real plane query writes distance even when the polygon rejects the hit. */
    *distance=face->distance;*normal=face->normal;
    return face->result && face->distance<=limit ? face->result : 0;
}
'''
wrapper = r'''
static int query(rdGeoset* v27, double* pHitDistance, rdFace** ppHitFace){
    int thinga,v30=0,v28=0,v31,v39=0;double moveDist=100,radius=0;
    rdVector3 posVec={0},dirVec={0,1,0},normal,*v26=&normal;
    rdMesh* selected=NULL;rdMesh** ppHitMesh=&selected;void* a2a=NULL;
'''
checks = r'''
    return v28;
}
int main(void){
    rdFace faces[]={{{0,-1,0},.4,4},{{0,0,1},.235274,0}};
    rdMesh meshes[]={{2,faces,NULL}};rdGeoset geo={1,meshes};
    double distance=-1;rdFace* face=NULL;
    assert(query(&geo,&distance,&face)==5 && distance==.4 && face==&faces[0]);
    /* A rejected mesh after an accepted one must not replace its distance either. */
    meshes[0].numFaces=1;
    rdMesh multiple[]={{1,faces,NULL},{1,faces+1,NULL}};geo=(rdGeoset){2,multiple};
    assert(query(&geo,&distance,&face)==5 && distance==.4 && face==&faces[0]);
    /* A nearer valid mesh still wins; rejected earlier faces cannot invent a hit. */
    faces[1].result=4;
    assert(query(&geo,&distance,&face)==5 && distance==.235274 && face==&faces[1]);
    faces[0].result=faces[1].result=0;
    assert(query(&geo,&distance,&face)==0);
    puts("Collision distance: rejected faces/meshes preserve accepted hits; nearer hits and misses passed");
}
'''
scratch = Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-collision-distance"
scratch.mkdir(parents=True, exist_ok=True)
cfile, binary = scratch / "distance.c", scratch / "distance"
try:
    cfile.write_text(harness + mesh + wrapper + traversal + checks)
    subprocess.run(["cc", "-std=c99", str(cfile), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
finally:
    cfile.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)
