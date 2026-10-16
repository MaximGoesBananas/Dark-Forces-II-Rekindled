"""Check actual civilian duplicate-voice suppression without muting other sounds."""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

src = Path(sys.argv[1]) / "src"
source = (src / "Main/jkRpg.c").read_text()
def function(name):
    match = re.search(r"(?:static )?int " + name + r"\([^;]*?\)\n\{", source)
    return source[match.start():source.index("\n}", match.end()) + 2]

mixer = (src / "Devices/sithSoundMixer.c").read_text()
body = mixer[mixer.index("sithPlayingSound* sithSoundMixer_PlaySoundThing("):]
assert body.index("jkRpg_CivilianVoiceDuplicate(pThing, hSnd, playflags)") < body.index("sithSoundMixer_PlayingSoundFromSound(")
assert mixer.count("jkRpg_CivilianVoiceDuplicate(") == 1
code = r'''
#include <assert.h>
#include <stddef.h>
#include <stdio.h>
#include <strings.h>
#define __strcmpi strcasecmp
#define SITH_THING_ACTOR 2
#define SITHSOUNDFLAG_VOICE 0x10000
typedef struct { const char* aName; } Script;
typedef struct { Script* pScript; } Cog;
typedef struct { int type; Cog* pCog; } SithThing;
typedef struct { int id; } sithSound;
static int sithNet_isMulti;
static sithSound *playing;
static int sithSoundMixer_GetThingSoundIdx(SithThing* thing, sithSound* sound) {
    assert(thing == NULL); return playing == sound ? 0 : -1;
}
''' + function("jkRpg_CivilianKind") + "\n" + function("jkRpg_CivilianVoiceDuplicate") + r'''
int main(void) {
    Script script={"actor_mn.cog"}; Cog cog={&script}; SithThing actor={2,&cog};
    sithSound line={1}, other={2}; int voice=SITHSOUNDFLAG_VOICE;
    assert(!jkRpg_CivilianVoiceDuplicate(&actor,&line,voice));
    playing=&line;
    const char* civilians[]={"actor_mn.cog","ACTOR_FN.COG","actor_pm.cog","actor_pf.cog",
        "actor_mu.cog","actor_gd.cog","actor_ug.cog","actor_bt.cog"};
    for (unsigned i=0;i<sizeof(civilians)/sizeof(*civilians);i++) {
        script.aName=civilians[i];
        assert(jkRpg_CivilianVoiceDuplicate(&actor,&line,voice));
    }
    assert(!jkRpg_CivilianVoiceDuplicate(&actor,&other,voice));
    assert(!jkRpg_CivilianVoiceDuplicate(&actor,&line,0)); // footsteps, impacts
    playing=NULL; assert(!jkRpg_CivilianVoiceDuplicate(&actor,&line,voice)); // finished/stopped
    playing=&line; script.aName="actor_st.cog";
    assert(!jkRpg_CivilianVoiceDuplicate(&actor,&line,voice)); // combat calls
    script.aName="story.cog"; assert(!jkRpg_CivilianVoiceDuplicate(&actor,&line,voice));
    script.aName="actor_mn.cog"; sithNet_isMulti=1;
    assert(!jkRpg_CivilianVoiceDuplicate(&actor,&line,voice)); sithNet_isMulti=0;
    actor.type=10; assert(!jkRpg_CivilianVoiceDuplicate(&actor,&line,voice));
    actor.type=2; actor.pCog=NULL; assert(!jkRpg_CivilianVoiceDuplicate(&actor,&line,voice));
    assert(!jkRpg_CivilianVoiceDuplicate(NULL,&line,voice));
    puts("Crowd voices: duplicate spoken lines suppressed; other lines, combat, story and footsteps preserved");
}
'''
with tempfile.TemporaryDirectory() as tmp:
    c = Path(tmp) / "voices.c"; c.write_text(code)
    exe = Path(tmp) / "voices"
    subprocess.run(["cc", "-std=gnu11", "-Wall", "-Werror", str(c), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
