"""Reproduce saving empty animation tracks and round-trip the real serializer."""
from pathlib import Path
import subprocess
import sys
import tempfile

src = Path(sys.argv[1]) / "src"
text = (src / "Dss/sithDSS.c").read_text()
def function(signature):
    start = text.index(signature)
    return text[start:text.index("\n}\n", start)+3]
code = r"""
#include <assert.h>
#include <stdint.h>
#include <string.h>
#define _memset memset
typedef struct {int id;} Key;
typedef struct {uint32_t status;Key* keyframe;int field_4,lowPri,highPri;float speed,playSpeed,field_120,field_124,fadeSpeed;} Track;
typedef Track rdPuppetTrack;
typedef struct {Track aTracks[4];} rdPuppet;
typedef struct {int otherTrack,field_0,field_4;} Controller;
typedef struct {int idx;struct {rdPuppet* puppet;} renderData;Controller* puppet;void* pPuppetClass;} SithThing;
typedef int SithMessage;
static double packet[64];static int written,readpos,sends,sithComm_netMsgTmp;
static rdPuppet animation;
static Controller control;
static SithThing thing={42,{&animation},&control,&control};
static Key key={7};
static SithThing* sithPlayer_g_pLocalPlayerThing=&thing;
static int Main_bMotsCompat,sithNet_isMulti;
#define NETMSG_START written=0
#define NETMSG_PUSHU32(v) (packet[written++]=(v))
#define NETMSG_PUSHS32(v) NETMSG_PUSHU32(v)
#define NETMSG_PUSHS16(v) NETMSG_PUSHU32(v)
#define NETMSG_PUSHF32(v) NETMSG_PUSHU32(v)
#define NETMSG_END(v) ((void)0)
#define NETMSG_IN_START(v) readpos=0
#define NETMSG_POPS32() ((int)packet[readpos++])
#define NETMSG_POPU32() ((uint32_t)packet[readpos++])
#define NETMSG_POPS16() NETMSG_POPS32()
#define NETMSG_POPF32() ((float)packet[readpos++])
static void sithComm_SendMsgToPlayer(int* m,int id,int stream,int flags) {sends++;}
static SithThing* sithThing_GetThingByIndex(int idx) {assert(idx==42);return &thing;}
static void rdPuppet_NewEntry(rdPuppet* p,void* parent) {memset(p,0,sizeof(*p));}
static Key* sithKeyFrame_GetByIdx(int id) {return id==7?&key:0;}
static void rdPuppet_FadeOutTrack(rdPuppet* p,int i,float speed) {assert(p->aTracks[i].keyframe);p->aTracks[i].fadeSpeed=1/speed;}
static void rdPuppet_FadeInTrack(rdPuppet* p,int i,float speed) {assert(p->aTracks[i].keyframe);p->aTracks[i].fadeSpeed=1/speed;}
static void sithPuppet_SetArmedMode(SithThing* t,int mode) {t->puppet->field_0=mode;}
static void sithPuppet_SetMoveMode(SithThing* t,int mode) {t->puppet->field_4=mode;}
"""
weapons=(src/"Main/jkRpgWeapons.c").read_text()
a=weapons.index("int jkRpg_IsSaberPoseTrack(")
code+=weapons[a:weapons.index("\n}\n",a)+3]
code += function("void sithDSS_PuppetStatus(") + function("int sithDSS_ProcessPuppetStatus(")
code += r"""
typedef struct {int id;} rdModel3;
typedef struct {struct {rdModel3* model3;rdPuppet* puppet;} povModel;} jkPlayerInfo;
static rdModel3 model={32770};
static jkPlayerInfo playerThings[2];static int playerThingIdx,jkPlayer_numThings=2;
static rdModel3* sithModel_GetModelByIndex(int id) {return id==32770?&model:0;}
static void jkPlayer_SetPovModel(jkPlayerInfo* p,rdModel3* m) {p->povModel.model3=m;}
"""
text=(src/"Dss/jkDSS.c").read_text()
code+=function("void jkDSS_Sendx32(")+function("int jkDSS_Processx32(")
code += r"""
int main(void) {
    // Noise/fade flags may exist without a keyframe. Saving must encode these as empty.
    animation.aTracks[0].status=0x1000;
    animation.aTracks[1].status=8;
    animation.aTracks[2]=(Track){.status=3,.keyframe=&key,.speed=24,.playSpeed=1,.lowPri=2,.highPri=4};
    control=(Controller){2,1,3};
    sithDSS_PuppetStatus(&thing,0,4);assert(sends==1 && packet[1]==0 && packet[2]==0);
    assert(sithDSS_ProcessPuppetStatus(0));assert(readpos==written);
    assert(!animation.aTracks[0].status && !animation.aTracks[1].status);
    assert(animation.aTracks[2].keyframe==&key && animation.aTracks[2].status==3);
    assert(animation.aTracks[2].speed==24 && control.otherTrack==2 && control.field_4==3);
    // Old saves can reference an unavailable keyframe. Consume its fields, then clear it.
    sithDSS_PuppetStatus(&thing,0,4);packet[4]=-1;packet[3]=8;
    assert(sithDSS_ProcessPuppetStatus(0));assert(readpos==written);
    assert(!animation.aTracks[2].status && !animation.aTracks[2].keyframe);
    sithDSS_PuppetStatus(&thing,0,4);assert(written==8);
    // The reported save carries a frozen wind-up at priority 3/5, status 0x53.
    animation.aTracks[0]=(Track){.status=0x53,.keyframe=&key,.lowPri=3,.highPri=5,.speed=1.17647f,.playSpeed=1};
    playerThings[0].povModel.model3=&model;playerThings[0].povModel.puppet=&animation;
    sithDSS_PuppetStatus(&thing,0,4);assert(packet[1]==0);
    jkDSS_Sendx32(&playerThings[0]);assert(packet[2]==0);
    assert(jkDSS_Processx32(0) && !animation.aTracks[0].status);
    // Older saves still contain the pose. Drop it on load even when the keyframe exists.
    animation.aTracks[0]=(Track){.status=0x53,.keyframe=&key,.lowPri=0,.highPri=2};
    jkDSS_Sendx32(&playerThings[0]);packet[5]=3;packet[6]=5;
    assert(jkDSS_Processx32(0) && !animation.aTracks[0].status && readpos==written);
    animation.aTracks[0]=(Track){.status=0x53,.keyframe=&key,.lowPri=0,.highPri=2};
    sithDSS_PuppetStatus(&thing,0,4);packet[4]=3;packet[5]=5;
    assert(sithDSS_ProcessPuppetStatus(0) && !animation.aTracks[0].status && readpos==written);
    // Missing first-person keys must neither crash saving nor persist on restore.
    animation.aTracks[0]=(Track){.status=8};jkDSS_Sendx32(&playerThings[0]);assert(packet[2]==0);
    animation.aTracks[0]=(Track){.status=8,.keyframe=&key};jkDSS_Sendx32(&playerThings[0]);packet[3]=-1;
    assert(jkDSS_Processx32(0) && !animation.aTracks[0].status && readpos==written);
    // Ordinary weapon blends resume rather than inheriting an old zero fade rate.
    animation.aTracks[0]=(Track){.status=8,.keyframe=&key,.lowPri=0,.highPri=2};
    jkDSS_Sendx32(&playerThings[0]);assert(jkDSS_Processx32(0));assert(animation.aTracks[0].fadeSpeed>6);
    assert(animation.aTracks[0].keyframe==&key);
    // No multiplayer/MotS pose filtering.
    Track pose={.lowPri=3,.highPri=5};Main_bMotsCompat=1;assert(!jkRpg_IsSaberPoseTrack(&pose));
    Main_bMotsCompat=0;sithNet_isMulti=1;assert(!jkRpg_IsSaberPoseTrack(&pose));
    return 0;
}
"""
with tempfile.TemporaryDirectory(prefix="jk-puppet-save-") as tmp:
    p=Path(tmp)
    (p/"check.c").write_text(code)
    subprocess.run(["cc","-std=c99","-fsanitize=undefined,address",str(p/"check.c"),"-o",str(p/"check")],check=True)
    subprocess.run([str(p/"check")],check=True)
print("Animation save/load handles empty tracks and unavailable keyframes without losing valid animations")
