"""Compile the actual clothing-variety rules and check their choices, exclusions and colours.
Run in WSL: python3 tools/test_outfits.py ~/src/OpenJKDF2
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

src = Path(sys.argv[1]) / "src"
source = (src / "Main/jkRpgOutfits.c").read_text()
rules = source[source.index("// ---- Outfit rules"):source.index("// ---- End of outfit rules")]

# Every dressed thing goes through one render hook; faces swap only while it draws.
render = (src / "Engine/sithRender.c").read_text()
body = render[render.index("int sithRender_RenderThing(SithThing *pThing)"):]
body = body[:body.index("\n}") + 2]
assert re.search(r"jkRpg_BeginOutfit\(pThing\);[^\n]*\n\s*ret = rdThing_Draw\(&pThing->renderData, &pThing->orient\);\n"
                 r"\s*jkRpg_EndOutfit\(\);", body), "outfit must wrap only the thing's own model"
model = (src / "Primitives/rdModel3.c").read_text()
face = model[model.index("procEntry->material = pFace->material;"):]
assert face.index("rdModel3_pMaterialSwaps[i].from == pFace->material") < face.index("rdCache_AddProcFace(")
world = (src / "World/sithWorld.c").read_text()
free = world[world.index("void sithWorld_FreeEntry(SithWorld *pWorld)"):]
assert "jkRpg_FreeOutfits();" in free[:free.index("\n}")], "copies must be freed with the world"
material = (src / "Engine/rdMaterial.c").read_text()
assert "rdMaterial* rdMaterial_CopyRecolored(" in material and "skip_jkgm = 1" in material
assert "rdroid_bSoftwareRenderer" in source  # the software rasterizer keeps the 8-bit originals

harness = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
'''
checks = r'''
static const char* outfit(const char* model) {
    int o = jkRpg_OutfitForModel(model); return o < 0 ? NULL : jkRpg_aOutfits[o].name;
}
static int dressed(const char* material) {
    for (int o = 0; o < RPG_NUM_OUTFITS; o++) if (jkRpg_InList(jkRpg_aOutfits[o].clothes, material)) return 1;
    return 0;
}
static void rgb(uint16_t v, int* r, int* g, int* b) { *r = (v >> 11) << 3; *g = ((v >> 5) & 63) << 2; *b = (v & 31) << 3; }
static int lum(int r, int g, int b) { return (299 * r + 587 * g + 114 * b) / 1000; }
int main(void) {
    // The four most common clothed enemy types, plus ordinary civilians and workers.
    const char* rodian[] = {"ry.3do", "RYSTR.3DO"}, *hunter[] = {"rh.3do", "rhstr.3do"};
    const char* tusken[] = {"tk.3do", "tkstr.3do"}, *tuskenHunter[] = {"th.3do", "thstr.3do"};
    for (int i = 0; i < 2; i++) {
        assert(!strcmp(outfit(rodian[i]), "Gran") && !strcmp(outfit(hunter[i]), "Gran bounty hunter"));
        assert(!strcmp(outfit(tusken[i]), "Tusken") && !strcmp(outfit(tuskenHunter[i]), "Tusken bounty hunter"));
    }
    const char* people[] = {"mn.3do", "m2.3do", "wm.3do", "w2.3do"};
    for (int i = 0; i < 4; i++) assert(!strcmp(outfit(people[i]), "Civilian"));
    assert(!strcmp(outfit("ugalt.3do"), "Worker") && !strcmp(outfit("u2alt.3do"), "Worker"));
    // Stormtroopers and every related Imperial type, the player, droids and unique characters keep their art.
    const char* excluded[] = {"st.3do", "s2.3do", "s3.3do", "s4.3do", "io.3do", "ic.3do", "icrpt.3do", "at.3do",
        "pb.3do", "ky.3do", "kyle.3do", "gr.3do", "bs.3do", "bsrld.3do", "wg.3do", "8t.3do", "gm.3do", "c3.3do",
        "ry", "ry.3do2", "xry.3do", ""};
    for (unsigned i = 0; i < sizeof(excluded) / sizeof(*excluded); i++) assert(!outfit(excluded[i]));
    // Only clothing changes: faces, skin, hair, necks, hands and weapons are never recoloured.
    const char* kept[] = {"ryeye.mat", "ryface.mat", "ryheadbk.mat", "ryneck.mat", "ryuparm.mat", "ryforarm.mat",
        "ryhandbk.mat", "ryhandtp.mat", "rypalm.mat", "det0side.mat", "strvsite.mat", "tkfacef.mat", "tkfaceb.mat",
        "tkfacesd.mat", "tkfacet.mat", "tkneck.mat", "tkhand.mat", "thfacef.mat", "tharm.mat", "th4arm.mat",
        "bowpside.mat", "mn-hd.mat", "mn-hdf.mat", "mn-hds.mat", "m2-head.mat", "m2-headf.mat", "m2-arm.mat",
        "wm1-hand.mat", "wm1-hdf.mat", "wm1-hds.mat", "wm1-hdb.mat", "wm1-nkf.mat", "wm1-nkb.mat", "w2-hdf.mat",
        "w2-hds.mat", "w2-hdb.mat", "w2-nkf.mat", "ug-hdf.mat", "ug-hnd.mat"};
    for (unsigned i = 0; i < sizeof(kept) / sizeof(*kept); i++) assert(!dressed(kept[i]));
    assert(dressed("rychstt.mat") && dressed("RHRTORS.mat") && dressed("THtors.mat") && dressed("mn-robe.mat"));
    // Bartenders and story roles share civilian models but not their scripts.
    for (int o = 0; o < RPG_NUM_OUTFITS; o++) {
        const jkRpgOutfit* t = &jkRpg_aOutfits[o];
        assert(t->numTints >= 1 && t->numTints <= RPG_OUTFIT_MAX_LOOKS - 1);
        if (t->scripts) assert(!jkRpg_InList(t->scripts, "actor_bt.cog") && !jkRpg_InList(t->scripts, "actor_wg.cog"));
    }
    const jkRpgOutfit* civ = &jkRpg_aOutfits[jkRpg_OutfitForModel("mn.3do")];
    assert(jkRpg_InList(civ->scripts, "ACTOR_PM.COG") && jkRpg_InList(civ->scripts, "actor_fn.cog"));
    assert(!jkRpg_InList(jkRpg_aOutfits[jkRpg_OutfitForModel("ugalt.3do")].scripts, "actor_pm.cog"));
    // A look depends only on the saved GUID: repeatable, evenly spread, original art kept for some.
    for (int n = 3; n <= 4; n++) {
        int count[5] = {0};
        for (uint32_t g = 0; g < 100000; g++) {
            int look = jkRpg_OutfitLook(g, n);
            assert(look >= 0 && look <= n && look == jkRpg_OutfitLook(g, n));
            count[look]++;
        }
        for (int l = 0; l <= n; l++) assert(count[l] > 90000 / (n + 1) && count[l] < 110000 / (n + 1));
        int runs = 0;  // neighbouring level things and crowd GUIDs (0x10000 + n) do not repeat in step
        for (uint32_t g = 1; g < 400; g++) runs += jkRpg_OutfitLook(g, n) == jkRpg_OutfitLook(g - 1, n);
        for (uint32_t g = 0x10001; g < 0x10190; g++) runs += jkRpg_OutfitLook(g, n) == jkRpg_OutfitLook(g - 1, n);
        assert(runs < 800 * 2 / (n + 1));
    }
    // Colours keep each texel's brightness (within RGB565 rounding), so folds and patterns stay.
    for (int o = 0; o < RPG_NUM_OUTFITS; o++)
        for (int l = 0; l < jkRpg_aOutfits[o].numTints; l++) {
            const jkRpgTint* t = &jkRpg_aOutfits[o].tints[l];
            assert(t->strength > 0 && t->strength <= 60 && t->brightness >= 85 && t->brightness <= 105);
            for (int v = 0; v < 256; v += 5) {
                int samples[3][3] = {{v, v, v}, {v, v * 3 / 4, v / 2}, {v / 3, v / 2, v}};
                for (int s = 0; s < 3; s++) {
                    int r, g, b, *c = samples[s];
                    rgb(jkRpg_TintTexel(c[0], c[1], c[2], t), &r, &g, &b);
                    int want = lum(c[0], c[1], c[2]) * t->brightness / 100;
                    // Near-white texels may clip in one channel and lose a little brightness.
                    if (lum(r, g, b) > want + 8 || (want < 160 && lum(r, g, b) < want - 8))
                        printf("%s %d (%d %d %d) -> %d want %d\n", jkRpg_aOutfits[o].name, l, c[0], c[1], c[2], lum(r, g, b), want);
                    assert(lum(r, g, b) <= want + 8 && (want >= 160 || lum(r, g, b) >= want - 8));
                }
            }
        }
    // Bounty hunters stay as dark as the originals; ordinary Gran keep a warm tunic.
    const char* hunters[] = {"rh.3do", "th.3do"};
    for (int h = 0; h < 2; h++) {
        const jkRpgOutfit* t = &jkRpg_aOutfits[jkRpg_OutfitForModel(hunters[h])];
        for (int l = 0; l < t->numTints; l++) assert(t->tints[l].brightness <= 100);
    }
    const jkRpgOutfit* ry = &jkRpg_aOutfits[jkRpg_OutfitForModel("ry.3do")];
    for (int l = 0; l < ry->numTints; l++) assert(ry->tints[l].r > ry->tints[l].b + 20);
    // Zero strength at full brightness reproduces the original colour, apart from RGB565 precision.
    jkRpgTint none = {200, 10, 10, 0, 100};
    for (int v = 0; v < 256; v++) {
        int r, g, b; rgb(jkRpg_TintTexel(v, 255 - v, v / 2, &none), &r, &g, &b);
        assert(r == (v & ~7) && g == ((255 - v) & ~3) && b == ((v / 2) & ~7));
    }
    puts("Outfits: Gran, Gran and Tusken bounty hunters, Tuskens, civilians and workers vary by GUID; "
         "Imperials, story roles, skin and gear keep their art; brightness and type colours preserved");
}
'''
with tempfile.TemporaryDirectory() as tmp:
    c = Path(tmp) / "outfits.c"
    c.write_text(harness + rules + checks)
    exe = Path(tmp) / "outfits"
    subprocess.run(["cc", "-std=gnu11", "-Wall", "-Werror", "-Wno-unused-function", str(c), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
