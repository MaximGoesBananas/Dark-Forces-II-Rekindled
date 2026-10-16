"""Compile actual crosshair drawing, FOV limits and the upgrade menu's layout and keyboard handling;
inspect menu layouts in-game too.
Usage in WSL: python3 tools/test_ui.py ~/src/OpenJKDF2
"""
import os
import tempfile
import re
import subprocess
import sys
from pathlib import Path
root = Path(sys.argv[1]) / "src"

def function(file, name):
    source = (root / file).read_text()
    start = re.search(r"(?:static )?void " + name + r"\([^;]*?\)\n\{", source)
    return source[start.start():source.index("\n}", start.end()) + 2]

harness = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
typedef double flex_t;
typedef struct { int x,y,width,height; } rdRect;
static int color, calls, gray, partial, jkPlayer_fov, jkPlayer_fovIsVertical, Window_ySize;
static double jkPlayer_crosshairLineWidth=1;
static int jkRpg_GetCrosshairColor(void) { return color; }
static void jkRpg_CrosshairRgb(uint8_t*, uint8_t*, uint8_t*);
static uint32_t pixels[512][512];
static void std3D_DrawUIClearedRectRGBA(uint8_t r,uint8_t g,uint8_t b,uint8_t a,rdRect* rect) {
    assert(rect->width>0 && rect->height>0);
    uint8_t cr,cg,cb; jkRpg_CrosshairRgb(&cr,&cg,&cb);
    assert(r==cr && g==cg && b==cb); // No black outline or darkened ring-edge pixels.
    calls++; if (r==170 && g==170 && b==170 && a==255) gray++;
    if (a>0 && a<200) partial++;
    for(int y=rect->y;y<rect->y+rect->height;y++) for(int x=rect->x;x<rect->x+rect->width;x++) {
        assert(x>=0 && x<512 && y>=0 && y<512);
        pixels[y][x]=((uint32_t)r<<24)|(g<<16)|(b<<8)|a;
    }
}
'''
checks = r'''
int main(void) {
    Window_ySize=480; assert(jkPlayer_DefaultHudScale()==1.0);
    Window_ySize=1080; assert(jkPlayer_DefaultHudScale()==2.0);
    Window_ySize=1440; assert(jkPlayer_DefaultHudScale()==2.75);
    Window_ySize=2160; assert(jkPlayer_DefaultHudScale()==4.0);
    Window_ySize=4320; assert(jkPlayer_DefaultHudScale()==4.0);
    for(int fov=-100;fov<=300;fov++) {
        jkPlayer_fov=fov;jkPlayer_fovIsVertical=1;jkPlayer_ClampFov();
        assert(jkPlayer_fov==(fov<70?70:(fov>100?100:fov)) && jkPlayer_fovIsVertical);
    }
    jkPlayer_fov=110;jkPlayer_fovIsVertical=0;jkPlayer_ClampFov();
    assert(jkPlayer_fov==90 && jkPlayer_fovIsVertical); // Restore the original wide view.
    for(color=0;color<5;color++) for(int style=1;style<=4;style++) {
        calls=gray=partial=0;memset(pixels,0,sizeof(pixels));
        jkRpg_DrawCrosshair(style,128,128,1);
        assert(calls>0 && (color!=0 || gray>0));
        if(style==4) {
            assert(partial>0); // Fractional edge coverage, not disconnected square dots.
            for(int y=117;y<=139;y++) for(int x=117;x<=139;x++)
                assert(pixels[y][x]==pixels[256-y][256-x]);
        }
    }
    color=0;
    for(int size=1;size<=36;size++) {
        calls=0;jkRpg_DrawCrosshair(4,128,128,size*0.5);
        assert(calls<3500); // 8K/200% crosshair still leaves UI capacity.
    }
    calls=0;jkRpg_DrawCrosshair(4,128,128,NAN);assert(calls==0);
    jkRpg_DrawCrosshair(4,128,128,1000000);assert(calls<3500);
    color=2;calls=0;gray=0;jkRpg_DrawCrosshair(1,128,128,1);
    assert(calls==4 && gray==0); // Classic keeps its shape and supports other colors.
    puts("FOV limits, neutral gray, antialiased symmetric ring and draw budget passed");
}
'''
scratch=Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-ui"
scratch.mkdir(parents=True,exist_ok=True)
cfile,binary=scratch/"check.c",scratch/"check"
try:
    source=(root/"Main/jkRpg.c").read_text()
    colors=re.search(r"static const uint8_t jkRpg_aCrosshairRgb[^;]+;",source).group()
    limits="\n".join(re.findall(r"^#define FOV_(?:MIN|MAX).*$",(root/"World/jkPlayer.h").read_text(),re.M))
    player_source=(root/"World/jkPlayer.c").read_text()
    begin=player_source.index("static flex_t jkPlayer_DefaultHudScale(")
    hud_default=player_source[begin:player_source.index("\n}",begin)+2]
    code=harness+limits+"\n"+colors+"\n"+hud_default
    for file,name in [("World/jkPlayer.c","jkPlayer_ClampFov"),("Main/jkRpg.c","jkRpg_CrosshairRgb"),
                      ("Main/jkRpg.c","jkRpg_CrosshairRect"),("Main/jkRpg.c","jkRpg_DrawCrosshair")]:
        code+=function(file,name)+"\n"
    cfile.write_text(code+checks)
    subprocess.run(["cc","-std=gnu99",str(cfile),"-lm","-o",str(binary)],check=True)
    subprocess.run([str(binary)],check=True)
finally:
    cfile.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)

# Upgrade menu: the harness in test_upgrade_previews.py compiles the real menu source.
menu_checks = r'''
#include <math.h>
static void everything(int on) { for (int up = 0; up < UP_COUNT; up++) found[up] = on; }
static void startingKit(void) { // general skills only, as at the start of the game
    everything(0);
    for (int up = UP_HEALTH; up <= UP_MEDIC; up++) found[up] = 1;
}
static int tabs(void) { int n = 0; for (int page = 0; page < PAGE_COUNT; page++) n += shown(jkRpg_aPageNames[page]); return n; }

int main(void) {
    // Every page and branch fits on 4:3, 16:9 and extreme screens with narrow and wide fonts.
    const int sizes[][2] = {{640, 480}, {800, 600}, {1024, 768}, {1280, 1024}, {1920, 1080}, {2560, 1080},
                            {3440, 1440}, {3840, 2160}, {5760, 1080}, {7680, 1080}, {640, 1080}, {1080, 1920}};
    for (size_t i = 0; i < sizeof(sizes) / sizeof(sizes[0]); i++)
    for (int f = 0; f < 3; f++)
    for (glyphW = 4; glyphW <= 6; glyphW += 2) {
        fontH = (int[]){7, 11, 16}[f]; // the HUD message font is 11 pixels tall
        setup(sizes[i][0], sizes[i][1]);
        everything(1);
        for (int up = 0; up < UP_COUNT; up++) {
            jkRpg_menuSel = -1; selectBranch(up);
            for (int r = 0; r <= RPG_MAX_RANK; r += 1) {
                for (int b = 0; b < UP_COUNT; b++) { rank[b] = r; raised[b] = r == 1; undo[b] = r == 2; }
                draw(); // every rectangle, picture and letter is checked against the screen and panel
                assert(panelW <= 0.96 * Video_format.width + 1 && panelH <= 0.96 * Video_format.height + 1);
                assert(abs(2 * panelX + panelW - Video_format.width) <= 1 && abs(2 * panelY + panelH - Video_format.height) <= 1);
                if (fontH <= 11) assert(jkRpg_u >= (flex_t)fmin(Video_format.height / 480.0, Video_format.width * 0.96 / MENU_W) - 0.001);
                assert(tabs() == PAGE_COUNT);
            }
        }
        // 16:9 uses the height: the panel is as tall as on 4:3 and centred, not stretched sideways.
        if (sizes[i][0] == 1920) assert(panelH > 0.8 * 1080 && panelW < 0.75 * 1920);
    }
    fontH = 11; glyphW = 4; setup(1920, 1080);
    for (int b = 0; b < UP_COUNT; b++) { rank[b] = 0; raised[b] = undo[b] = 0; }

    // Pages without a discovered branch are hidden: no tab and no keyboard stop.
    startingKit();
    jkRpg_menuPage = PAGE_JEDI; jkRpg_menuSel = UP_SABER; draw(); // e.g. a load without the saber
    assert(jkRpg_menuPage == PAGE_CHARACTER && found[jkRpg_menuSel]);
    assert(tabs() == 2 && shown("Character") && shown("Supplies") && !shown("Blasters") && !shown("Jedi"));
    const int pageKeys[][2] = {{DIK_RIGHT, 1}, {DIK_D, 1}, {DIK_E, 1}, {DIK_TAB, 1}, {DIK_LEFT, -1}, {DIK_A, -1}, {DIK_Q, -1}};
    for (int i = 0; i < 7; i++) {
        int before = jkRpg_menuPage;
        press(pageKeys[i][0]);
        assert(jkRpg_menuPage == (before == PAGE_CHARACTER ? PAGE_SUPPLIES : PAGE_CHARACTER));
        assert(found[jkRpg_menuSel] && jkRpg_aUpgrades[jkRpg_menuSel].page == jkRpg_menuPage);
    }
    // Undiscovered equipment stays hidden within a page.
    jkRpg_menuPage = PAGE_SUPPLIES; jkRpg_menuSel = UP_SCAVENGER; draw();
    assert(!shown("Bacta tank") && !shown("Field light and goggles") && shown("Scavenger") && shown("Field Medic"));
    found[UP_BACTA] = 1; draw(); assert(shown("Bacta tank"));

    // One branch on a page: Up/Down stay on it; a page appears once its first branch is found.
    found[UP_BRYAR] = 1;
    jkRpg_menuPage = PAGE_SUPPLIES; press(DIK_E);
    assert(jkRpg_menuPage == PAGE_BLASTERS && jkRpg_menuSel == UP_BRYAR);
    for (int i = 0; i < 3; i++) { press(i % 2 ? DIK_UP : DIK_S); assert(jkRpg_menuSel == UP_BRYAR); }
    draw(); assert(drawn[UP_BRYAR * TILES_PER_BRANCH + 1] && !drawn[UP_RIFLE * TILES_PER_BRANCH + 1] && tabs() == 3);
    press(DIK_RETURN); assert(toggled == UP_BRYAR);

    // Two branches that are not neighbours in the table: selection alternates between them only.
    found[UP_THERMAL] = found[UP_CONCUSSION] = 1;
    press(DIK_E); assert(jkRpg_menuPage == PAGE_HEAVY && jkRpg_menuSel == UP_THERMAL);
    press(DIK_DOWN); assert(jkRpg_menuSel == UP_CONCUSSION);
    press(DIK_S); assert(jkRpg_menuSel == UP_THERMAL);
    press(DIK_W); assert(jkRpg_menuSel == UP_CONCUSSION);
    draw(); assert(shown("Thermal detonators") && shown("Concussion rifle") && !shown("Rail detonator"));
    // The selected equipment disappearing (another save) moves the selection to what remains.
    found[UP_CONCUSSION] = 0; draw(); assert(jkRpg_menuSel == UP_THERMAL);
    found[UP_THERMAL] = 0; draw(); assert(jkRpg_menuPage != PAGE_HEAVY && found[jkRpg_menuSel]);
    // The Force page follows the story: Jedi appears for the lightsaber or Force alone.
    found[UP_FORCE] = 1; draw(); assert(shown("Jedi") && tabs() == 4);
    jkRpg_menuPage = PAGE_JEDI; jkRpg_menuSel = -1; draw(); assert(jkRpg_menuSel == UP_FORCE && !shown("Lightsaber"));
    puts("Upgrade menu: fits 4:3, 16:9 and extreme screens; hidden pages skipped; 1-2 branch selection passed");

    // Level plate on the left HUD gauge, 54 of the gauge's 59 pixels wide
    // and centred on it at every HUD size, on screen and clear of the right gauge; while points wait
    // it shows the pulsing arrow and the menu key instead of the level, or SETUP when unbound.
    const char* keyNames[] = {"K", "Right Ctrl", NULL};
    for (size_t i = 0; i < sizeof(sizes) / sizeof(sizes[0]); i++)
    for (int step = 0; step <= 12; step++)
    for (int k = 0; k < 3; k++)
    for (points = 0; points <= 49; points += 49) {
        fontH = 11; glyphW = 4; setup(sizes[i][0], sizes[i][1]);
        flex_t hud = jkPlayer_hudScale = 1.0 + 0.25 * step; // the Setup slider's range
        menuKey = keyNames[k];
        resetDrawn();
        int gaugeY = Video_format.height - (int)(60 * hud);
        jkRpg_DrawLevelBadge(&player, &font, 0, gaugeY); // inside() checks the screen edges
        int plateW = jkRpg_pPlate->mipSurfaces[0]->format.width;
        assert(abs(plateW - (int)(54 * hud)) <= 1 && abs(minX - (int)(1.5 * hud)) <= 1);
        assert(abs(2 * minX + plateW - (int)(57 * hud)) <= 2); // centred on the ring (57 pixels wide)
        assert(abs(minY - (gaugeY - (int)(8.5 * hud))) <= 1 && maxY <= gaugeY + (int)(4.0 * hud) + 2); // the original chain continues below
        assert(maxX <= Video_format.width - (int)(61 * hud)); // clear of the right gauge
        if (points) assert(bitmaps == 2 && strstr(jkRpg_plateText, menuKey ? menuKey : "SETUP") && !strstr(jkRpg_plateText, "LEVEL"));
        else assert(bitmaps == 1 && !strncmp(jkRpg_plateText, "LEVEL ", 6));
    }
    // The level is painted in gold into the plate's window and repainted when it changes.
    jkPlayer_hudScale = 2; points = 0;
    int goldAt[2];
    for (int l = 0; l < 2; l++) {
        levelValue = l ? 40 : 1;
        resetDrawn(); jkRpg_DrawLevelBadge(&player, &font, 0, 600);
        tVBuffer* v = jkRpg_pPlate->mipSurfaces[0];
        goldAt[l] = 0;
        for (int y = 0; y < v->format.height; y++) for (int x = 0; x < v->format.width; x++) {
            uint16_t c = ((uint16_t*)((uint8_t*)v->surface_lock_alloc + y * v->format.rowSize))[x];
            int r = (c >> 10) & 31, g = (c >> 5) & 31, b = c & 31;
            goldAt[l] += (c & 0x8000) && r > 24 && g > 12 && g < r && b < g / 2;
        }
        assert(goldAt[l] > 40);
    }
    assert(goldAt[1] > goldAt[0]); // "LEVEL 40" has more letters than "LEVEL 1"
    assert(fontLoads == 1);
    // Without the font file the plate still shows its text as HUD text.
    jkRpg_FreeMenuArt(); assert(!jkRpg_pPlate && !jkRpg_pArrow);
    failFontLoad = 1; points = 4; menuKey = NULL;
    resetDrawn(); jkRpg_DrawLevelBadge(&player, &font, 0, 600);
    assert(jkRpg_pPlate && strstr(text, "SETUP"));
    points = 0; resetDrawn(); jkRpg_DrawLevelBadge(&player, &font, 0, 600);
    assert(strstr(text, "LEVEL 40"));
    failFontLoad = 0; jkRpg_FreeMenuArt();
    // With the shipped art installed (rpg/art): the generated frame, title bar and plate, at every
    // size and HUD scale, stay on screen and in the panel; the plate keeps the specified size and
    // position; a broken file falls back to the drawn version.
    writeArt();
    menuKey = "K"; levelValue = 40;
    for (size_t i = 0; i < sizeof(sizes) / sizeof(sizes[0]); i++) {
        fontH = 11; glyphW = 4; setup(sizes[i][0], sizes[i][1]);
        everything(1);
        for (int up = 0; up < UP_COUNT; up += 4) { jkRpg_menuSel = -1; selectBranch(up); draw(); }
        assert(jkRpg_pFrame && jkRpg_pBar && jkRpg_pFrame->mipSurfaces[0]->format.width == panelW);
        for (int step = 0; step <= 12; step += 2)
        for (points = 0; points <= 3; points += 3) {
            flex_t hud = jkPlayer_hudScale = 1.0 + 0.25 * step;
            resetDrawn();
            int gaugeY = Video_format.height - (int)(60 * hud);
            jkRpg_DrawLevelBadge(&player, &font, 0, gaugeY);
            int plateW = jkRpg_pArtPlate->mipSurfaces[0]->format.width;
            assert(abs(plateW - (int)(54 * hud)) <= 1 && abs(minX - (int)(1.5 * hud)) <= 1);
            assert(abs(minY - (gaugeY - (int)(8.5 * hud))) <= 1 && maxX <= Video_format.width - (int)(61 * hud));
            assert(bitmaps == (points ? 2 : 1)); // the plate, and the arrow while points wait
            assert(!strcmp(jkRpg_artPlateText, points ? "PRESS K" : "LEVEL 40"));
        }
    }
    assert(menuFontLoads == 1);
    jkPlayer_hudScale = 2; points = 0;
    FILE* bad = fopen("rpg/art/plate.bmp", "wb"); fputs("BM", bad); fclose(bad);
    jkRpg_FreeMenuArt(); resetDrawn(); jkRpg_DrawLevelBadge(&player, &font, 0, 600);
    assert(!jkRpg_pArtPlate && jkRpg_pPlate); // the drawn plate instead
    removeArt();
    setup(1920, 1080); draw(); assert(!jkRpg_pFrame && !jkRpg_pBar); // the drawn frame and bar
    puts("Level plate: plate size and position at every HUD size, on screen, clear of the right gauge, waiting points show the key (or Setup) passed");
    return 0;
}
'''
from test_upgrade_previews import compile_menu
compile_menu(sys.argv[1], menu_checks, "menu_ui")
