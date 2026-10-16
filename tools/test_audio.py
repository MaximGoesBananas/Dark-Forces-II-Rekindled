"""Exercise actual desktop sound gain and streaming with OpenAL's silent backend.

Run in WSL: python3 tools/test_audio.py ~/src/OpenJKDF2
"""
import tempfile
import os
import re
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
source = (root / "src/Win95/stdSound.c").read_text()


def function(name, text=source):
    start = re.search(r"^(?:int|void|flex_t) " + name + r"\([^;]*?\)\n\{", text, re.M)
    return text[start.start():text.index("\n}", start.end()) + 2]


harness = r'''
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <strings.h>
#include <AL/al.h>
#include <AL/alc.h>
typedef float flex_t;
typedef struct {
    ALuint buffer, source;
    int bHasPos, bHasVel;
    ALfloat pos[3], vel[3];
    flex_t vol;
} stdSound_buffer_t;
typedef struct { char sound_fname[32]; } sithSound;
static int active=1;
static void* sithPlayer_g_pLocalPlayerThing;
static int jkRpg_IsActive(void* p) { return active; }
#define _strlen strlen
#define __strnicmp strncasecmp
#define __strcmpi strcasecmp
static float stdMath_Clamp(float x,float lo,float hi) { return x<lo?lo:x>hi?hi:x; }
static int Main_bHeadless;
static flex_t stdSound_fMenuVolume;
static void stdSound_BufferReset(stdSound_buffer_t* b) { assert(0); }
void stdSound_BufferSetVolumeAbsolute(stdSound_buffer_t*, flex_t);
'''
checks = r'''
static void checkGain(stdSound_buffer_t* b, float expected) {
    float actual;
    alGetSourcef(b->source, AL_GAIN, &actual);
    assert(fabsf(actual - expected) < .00001f);
    assert(fabsf(b->vol - expected) < .00001f);
    assert(alGetError() == AL_NO_ERROR);
}
int main(void) {
    ALCdevice* d = alcOpenDevice(NULL); assert(d);
    ALCcontext* c = alcCreateContext(d, NULL); assert(c);
    assert(alcMakeContextCurrent(c));
    short silence[2048] = {0};
    sithSound rahn={"i00ra33z.wav"}, other={"i00ky33z.wav"}, upper={"I00RA58Z.WAV"}, malformed={"i00ra33z.wavx"};
    assert(fabsf(jkRpg_NarrationVolume(&rahn,1)-4.0f/3)<.00001f);
    assert(fabsf(jkRpg_NarrationVolume(&upper,1)-4.0f/3)<.00001f);
    assert(jkRpg_NarrationVolume(&rahn,0)==0 && jkRpg_NarrationVolume(&rahn,10)==1.5f);
    assert(jkRpg_NarrationVolume(&other,1)==1 && jkRpg_NarrationVolume(&malformed,1)==1);
    assert(jkRpg_NarrationVolume(NULL,1)==1);
    active=0;assert(jkRpg_NarrationVolume(&rahn,1)==1);active=1;

    for (int effects = 0; effects <= 5; effects++) {
        stdSound_fMenuVolume = effects / 10.0f;
        for (int music = 0; music <= 5; music++) {
            float gain = music / 10.0f;
            stdSound_buffer_t b = {0};
            alGenBuffers(1, &b.buffer);
            alBufferData(b.buffer, AL_FORMAT_MONO16, silence, sizeof(silence), 22050);
            stdSound_BufferSetVolumeAbsolute(&b, gain);
            stdSound_BufferQueueAfterAnother(&b, &b);
            checkGain(&b, gain); // Movie stream ignores effects, including effects mute.
            stdSound_BufferSetVolumeAbsolute(&b, gain / 2);
            checkGain(&b, gain / 2); // Existing source receives updates too.
            alDeleteSources(1, &b.source);
            alDeleteBuffers(1, &b.buffer);
        }
        stdSound_buffer_t effect = {0};
        alGenBuffers(1, &effect.buffer);
        alBufferData(effect.buffer, AL_FORMAT_MONO16, silence, sizeof(silence), 22050);
        stdSound_BufferSetVolume(&effect, .75f);
        stdSound_BufferPlay(&effect, 0);
        checkGain(&effect, .75f * stdSound_fMenuVolume); // Exactly one effects scaling.
        // Narration now reaches the selected effects gain once; mute and the 0.5 default ceiling remain.
        stdSound_BufferSetVolume(&effect, jkRpg_NarrationVolume(&rahn,1) * .75f);
        checkGain(&effect, stdSound_fMenuVolume);
        assert(effect.vol <= .5f);
        alDeleteSources(1, &effect.source);
        alDeleteBuffers(1, &effect.buffer);
    }
    stdSound_BufferSetVolumeAbsolute(NULL, .5f);
    alcMakeContextCurrent(NULL); alcDestroyContext(c); alcCloseDevice(d);
    puts("Movie streaming/music gain, mute and single effects scaling passed (OpenAL)");
}
'''
cutscene = (root / "src/Main/jkCutscene.c").read_text()
assert cutscene.count("stdSound_BufferSetVolumeAbsolute(jkCutscene_audio[i], jkGuiSound_musicVolume)") == 2
rpg = (root / "src/Main/jkRpg.c").read_text()
cog = (root / "src/Cog/sithCogFunctionSound.c").read_text()
local = function("sithCogFunctionSound_PlaySoundLocal", cog)
assert local.count("jkRpg_NarrationVolume(pSound, volume)") == 1
assert local.index("jkRpg_NarrationVolume") < local.index("sithSoundMixer_PlaySound(")
# The saved channel volume is already adjusted, so restore and fading must not boost it again.
assert "jkRpg_NarrationVolume" not in (root / "src/Devices/sithSoundMixer.c").read_text()
scratch = Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-cutscene-audio"
scratch.mkdir(parents=True, exist_ok=True)
cfile, binary = scratch / "check.c", scratch / "check"
try:
    cfile.write_text(harness + function("jkRpg_NarrationVolume", rpg) + "\n".join(function(name) for name in (
        "stdSound_BufferSetVolumeAbsolute", "stdSound_BufferSetVolume",
        "stdSound_BufferPlay", "stdSound_BufferQueueAfterAnother")) + checks)
    subprocess.run(["cc", str(cfile), "-lopenal", "-lm", "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True, env={**os.environ, "ALSOFT_DRIVERS": "null"})
finally:
    cfile.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)
