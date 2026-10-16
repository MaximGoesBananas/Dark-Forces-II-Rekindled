"""Compile the real upgrade menu (src/Main/jkRpgMenu.c) with the real upgrade table and check its
pictures and text: every upgrade has its own picture inside a tile, each visible branch draws three
upgrades, the selected branch describes all three, Enter's effect is explained in every state, and
player-facing upgrade text has no numbers. tools/test_ui.py reuses this harness for layout checks.
Run in WSL: python3 tools/test_upgrade_previews.py ~/src/OpenJKDF2
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HARNESS = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#define __strcmpi strcasecmp
#include <sys/stat.h>
typedef double flex_t;
typedef struct { int x, y, width, height; } rdRect;
typedef struct { uint32_t is16bit, bpp, r_bits, g_bits, b_bits, r_shift, g_shift, b_shift, r_bitdiff, g_bitdiff, b_bitdiff; } rdTexFormat;
typedef struct { int32_t width, height; uint32_t size, rowSize, rowWidth; rdTexFormat format; } tRasterInfo;
typedef struct { tRasterInfo format; void* surface_lock_alloc; uint32_t transparent_color; } tVBuffer;
typedef struct { tVBuffer** mipSurfaces; rdTexFormat format; int palFmt; uint32_t colorkey; void* palette; } stdBitmap;
typedef struct { int32_t glyphTexX, glyphWidth; } stdFontEntry;
typedef struct stdFontCharset { struct stdFontCharset* previous; uint16_t charFirst, charLast; stdFontEntry* pEntries; } stdFontCharset;
typedef struct { int32_t marginY, marginX; int16_t field_28, monospaceW; stdBitmap* pBitmap; stdFontCharset charsetHead; } stdFont;
typedef struct SithThing { int unused; struct { void* pPlayer; } actorParams; } SithThing;
typedef struct { char aName[32]; } sithCogScript; typedef struct { sithCogScript* pScript; } sithCog;
typedef struct { stdBitmap* hudBitmap; int flags; sithCog* cog; } ItemType;
enum { DIK_TAB = 0x0F, DIK_Q, DIK_W, DIK_E, DIK_RETURN = 0x1C, DIK_A = 0x1E, DIK_S, DIK_D, DIK_SPACE = 0x39,
       DIK_UP = 0xC8, DIK_LEFT = 0xCB, DIK_RIGHT = 0xCD, DIK_DOWN = 0xD0 };
enum { SITHBIN_FORCEMANA = 14, SITHBIN_NUMBINS = 200, SITHBIN_JEDI_RANK = 70, SITHINVENTORY_TYPE_AUTOAIM = 8, SITHBIN_BACTATANK = 40, SITHBIN_IRGOGGLES = 41, SITHBIN_FIELDLIGHT = 42 };
#define stdString_snprintf snprintf
struct { int width, height; } Video_format;
flex_t jkPlayer_hudScale = 2;
ItemType sithInventory_g_aTypes[200];
void stdControl_ReadKey(int key, int* count);
enum { AXIS_JOY1_X, AXIS_JOY1_Y };
enum { KEY_JOY1_B1=300, KEY_JOY1_B2, KEY_JOY1_B10, KEY_JOY1_B11, KEY_JOY1_HUP, KEY_JOY1_HDOWN, KEY_JOY1_HLEFT, KEY_JOY1_HRIGHT };
static int stdControl_bHasPhysicalJoystick;
static flex_t joyAxes[2];
static flex_t stdControl_ReadAxis(int axis) { return joyAxes[axis]; }
stdFont* stdFont_Load(char* path, int a, int b);
void stdFont_Free(stdFont* f);
stdBitmap* stdBitmap_Load(char* path, int a, int b);
int stdFont_GetHeight(stdFont* f);
uint32_t stdPlatform_GetTimeMsec(void);
flex_t sithInventory_GetInventory(SithThing* p, int bin);
int sithInventory_GetCurPower(SithThing* p);
int sithInventory_IsInventoryAvailable(SithThing* p, int bin);
stdBitmap* stdBitmap_New(int a, int b, int c, int d, rdTexFormat* format);
void stdBitmap_Free(stdBitmap* b);
tVBuffer* stdDisplay_VBufferNew(tRasterInfo* format, int a, int b, void* c);
int stdDisplay_VBufferLock(tVBuffer* v);
void stdDisplay_VBufferUnlock(tVBuffer* v);
void std3D_DrawUIBitmapRGBA(stdBitmap* b, int mip, flex_t x, flex_t y, rdRect* src, flex_t sx, flex_t sy, int alpha, uint8_t r, uint8_t g, uint8_t bl, uint8_t a);
void std3D_DrawUIBitmap(stdBitmap* b, int mip, flex_t x, flex_t y, rdRect* src, flex_t s, int alpha);
'''

STATE = r'''
// The player as the menu sees it.
static int rank[UP_COUNT], found[UP_COUNT], raised[UP_COUNT], undo[UP_COUNT], points = 2, goggles;
static int lightGap;
static int keys[8], numKeys, fontH = 11, glyphW = 4, drawn[UP_COUNT * TILES_PER_BRANCH + 1], weaponIcons, itemIcons;
static int grayDrawn[UP_COUNT * TILES_PER_BRANCH + 1]; static char grayText[4096]; static int grayLen;
static int inMenu, panelX, panelY, panelW, panelH, rects, bitmaps, minX, minY, maxX, maxY;
static char text[8192]; static int textLen, lastX = -1000, lastY = -1000;
static stdBitmap fontBitmap, itemIcon; static tVBuffer itemBuffer, fontBuffer; static tVBuffer* itemMips[1] = {&itemBuffer};
static tVBuffer* fontMips[1] = {&fontBuffer};
static stdFontEntry glyphs[95]; static stdFont font;
SithThing player;

stdBitmap* jkRpg_BactaModelIcon(void) { return NULL; } // the item icon path
int jkRpg_IsFound(SithThing* p, int up) { return found[up]; }
int jkRpg_Rank(SithThing* p, int up) { return rank[up]; }
int jkRpg_OwnsTier(SithThing* p, int up, int tier) { return tier<=rank[up] && !(up==UP_LIGHT && tier==2 && lightGap); }
int jkRpg_NextTier(SithThing* p, int up) { return up==UP_LIGHT && lightGap ? 2 : rank[up]+1; }
int jkRpg_UndoTier(int up) { return undo[up] ? rank[up] : 0; }
int jkRpg_RaisedThisMission(SithThing* p, int up) { return raised[up] && !(up==UP_LIGHT && lightGap); }
int jkRpg_CanUndo(int up) { return undo[up]; }
int jkRpg_CanSpend(SithThing* p, int up) { return points > 0 && found[up] && jkRpg_NextTier(p,up)<=RPG_MAX_RANK && !jkRpg_RaisedThisMission(p,up); }
static int toggled = -1;
void jkRpg_Toggle(SithThing* p, int up) { assert(found[up]); toggled = up; }
static int levelValue = 7;
int jkRpg_Level(SithThing* p) { return levelValue; }
int jkRpg_Xp(SithThing* p) { return 1200; }
int jkRpg_Points(SithThing* p) { return points; }
int jkRpg_CanBuyAny(SithThing* p) { for (int up = 0; up < UP_COUNT; up++) if (jkRpg_CanSpend(p, up)) return 1; return 0; }
int jkRpg_XpForLevel(int level) { return 1375; }
int jkRpg_MaxLevel(void) { return 50; }
static const char* menuKey = "K";
const char* jkRpg_MenuKeyName(void) { return menuKey; }
int sithInventory_GetCurPower(SithThing* p) { return -1; }
int sithInventory_IsInventoryActivated(SithThing* p, int bin) { return 0; }
int sithInventory_IsInventoryAvailable(SithThing* p, int bin) { return 0; }
flex_t sithInventory_GetInventory(SithThing* p, int bin) { return bin == SITHBIN_IRGOGGLES ? goggles : 0; }
uint32_t stdPlatform_GetTimeMsec(void) { static uint32_t t; return t += 97; }
int stdFont_GetHeight(stdFont* f) { return fontH; }
void stdControl_ReadKey(int key, int* count) {
    *count = 0;
    for (int i = 0; i < numKeys; i++) if (keys[i] == key) *count = 1;
}
static void press(int key) { numKeys = 1; keys[0] = key; jkRpg_MenuInput(&player); numKeys = 0; }

stdBitmap* stdBitmap_New(int a, int b, int c, int d, rdTexFormat* format) {
    stdBitmap* bm = calloc(1, sizeof(stdBitmap)); bm->mipSurfaces = calloc(1, sizeof(tVBuffer*)); return bm;
}
void stdBitmap_Free(stdBitmap* b) {
    if (b->mipSurfaces[0]) { free(b->mipSurfaces[0]->surface_lock_alloc); free(b->mipSurfaces[0]); }
    free(b->mipSurfaces); free(b->palette); free(b);
}
tVBuffer* stdDisplay_VBufferNew(tRasterInfo* format, int a, int b, void* c) {
    tVBuffer* v = calloc(1, sizeof(tVBuffer)); v->format = *format; v->format.rowSize = format->width * 2 + 6;
    v->surface_lock_alloc = malloc(v->format.rowSize * format->height); memset(v->surface_lock_alloc, 0xAB, v->format.rowSize * format->height);
    return v;
}
int stdDisplay_VBufferLock(tVBuffer* v) { return 1; }
void stdDisplay_VBufferUnlock(tVBuffer* v) {}

static void inside(flex_t x, flex_t y, flex_t w, flex_t h) {
    assert(w > 0 && h > 0);
    assert(x >= 0 && y >= 0 && x + w <= Video_format.width + 0.01 && y + h <= Video_format.height + 0.01);
    if (x < minX) minX = (int)x;
    if (y < minY) minY = (int)y;
    if (x + w > maxX) maxX = (int)(x + w + 0.5);
    if (y + h > maxY) maxY = (int)(y + h + 0.5);
    if (panelW) assert(x >= panelX && y >= panelY && x + w <= panelX + panelW + 0.01 && y + h <= panelY + panelH + 0.01);
}
void jkRpg_Rect(int x, int y, int w, int h, uint8_t r, uint8_t g, uint8_t b, uint8_t a) {
    inside(x, y, w, h); rects++;
    if (!panelW && inMenu) { panelX = x; panelY = y; panelW = w; panelH = h; } // the menu's first rectangle
}
void jkRpg_DrawWeaponIcon(int weapon, int x, int y, int w, int h) { inside(x, y, w, h); weaponIcons++; }
void std3D_DrawUIBitmap(stdBitmap* b, int mip, flex_t x, flex_t y, rdRect* src, flex_t s, int alpha) {
    assert(b == &itemIcon && !src);
    inside(x, y, 24 * s, 24 * s); itemIcons++;
}
void std3D_DrawUIBitmapRGBA(stdBitmap* b, int mip, flex_t x, flex_t y, rdRect* src, flex_t sx, flex_t sy, int alpha, uint8_t r, uint8_t g, uint8_t bl, uint8_t a) {
    if (!src) { // a whole texture: the level plate, the frame or the title bar
        inside(x, y, b->mipSurfaces[0]->format.width * sx, b->mipSurfaces[0]->format.height * sy); bitmaps++;
        return;
    }
    inside(x, y, src->width * sx, src->height * sy); bitmaps++;
    if (b->mipSurfaces[0]->format.width == 960) { assert(src->width == 192 && src->height == 96); return; }
    if (b == jkRpg_pArrow) return; // the waiting-points arrow
    if (b && b == jkRpg_pGrayFont) { // colourless text: also kept apart, letters only
        grayText[grayLen++] = (char)(src->x / 16); grayText[grayLen] = 0; assert(grayLen < (int)sizeof(grayText) - 2);
    }
    if (b == &fontBitmap || (b && b == jkRpg_pGrayFont)) { // collect drawn text; a jump back or a wide gap starts a new string
        char ch = (char)(src->x / 16);
        if (textLen && ((int)y != lastY || x < lastX || x > lastX + 4 * glyphW * sx)) text[textLen++] = '|';
        else if (textLen && x > lastX + (glyphW + 1) * sx + 1) text[textLen++] = ' ';
        text[textLen++] = ch; text[textLen] = 0; lastX = (int)x; lastY = (int)y;
        assert(textLen < (int)sizeof(text) - 4);
        return;
    }
    assert(b == jkRpg_pMenuArt && src->width == TILE && src->height == TILE);
    int col = (src->x - 1) / TILE_CELL, row = (src->y - 1) / TILE_CELL;
    assert(src->x == col * TILE_CELL + 1 && src->y == row * TILE_CELL + 1 && row < 2 * ATLAS_ROWS);
    if (row >= ATLAS_ROWS) { row -= ATLAS_ROWS; grayDrawn[row * ATLAS_COLS + col]++; } // the colourless half
    drawn[row * ATLAS_COLS + col]++;
}

static void setup(int width, int height) {
    Video_format.width = width; Video_format.height = height;
    for (int i = 0; i < 95; i++) { glyphs[i].glyphTexX = (32 + i) * 16; glyphs[i].glyphWidth = glyphW; }
    font.marginY = 1; font.marginX = glyphW - 1; font.field_28 = '?'; font.pBitmap = &fontBitmap;
    font.charsetHead.charFirst = 32; font.charsetHead.charLast = 126; font.charsetHead.pEntries = glyphs;
    fontBitmap.mipSurfaces = fontMips; itemIcon.mipSurfaces = itemMips;
    // A 16-bit 5-6-5 glyph sheet: yellow letters on the magenta key colour.
    fontBuffer.transparent_color = 0xF81F;
    fontBuffer.format.width = 128 * 16; fontBuffer.format.height = fontH; fontBuffer.format.rowSize = 128 * 16 * 2;
    fontBuffer.format.format = (rdTexFormat){.bpp = 16, .is16bit = 1, .r_bits = 5, .g_bits = 6, .b_bits = 5, .r_shift = 11, .g_shift = 5, .b_shift = 0};
    if (!fontBuffer.surface_lock_alloc) {
        uint16_t* px = fontBuffer.surface_lock_alloc = malloc(fontBuffer.format.rowSize * fontH);
        for (int i = 0; i < 128 * 16 * fontH; i++) px[i] = i % 16 < glyphW ? 0xFFE0 : 0xF81F;
    }
    itemBuffer.format.width = itemBuffer.format.height = 24;
    sithInventory_g_aTypes[SITHBIN_BACTATANK].hudBitmap = &itemIcon;
    sithInventory_g_aTypes[SITHBIN_FIELDLIGHT].hudBitmap = &itemIcon;
    sithInventory_g_aTypes[SITHBIN_IRGOGGLES].hudBitmap = &itemIcon;
}

// The HUD message font as stdFont_Load returns it: 16-bit 5-6-5, yellow letters shaded red on
// the transparent key colour, 11 rows. failFontLoad simulates a missing file.
static int fontLoads, failFontLoad, menuFontLoads;
static stdFont* menuFontStandIn(void) { // small1.sft: 8-bit, 15 rows, index 2 letters on index 0
    stdFont* f = calloc(1, sizeof(stdFont)); stdBitmap* bm = calloc(1, sizeof(stdBitmap));
    stdFontEntry* e = calloc(95, sizeof(stdFontEntry));
    for (int i = 0; i < 95; i++) { e[i].glyphTexX = i * 8; e[i].glyphWidth = 7; }
    f->marginY = 0; f->marginX = 8; f->field_28 = '?'; f->pBitmap = bm;
    f->charsetHead.charFirst = 32; f->charsetHead.charLast = 126; f->charsetHead.pEntries = e;
    bm->format = (rdTexFormat){.bpp = 8};
    tRasterInfo info = {.width = 95 * 8, .height = 15};
    bm->mipSurfaces = calloc(1, sizeof(tVBuffer*)); bm->mipSurfaces[0] = stdDisplay_VBufferNew(&info, 0, 0, NULL);
    tVBuffer* v = bm->mipSurfaces[0]; v->format.rowSize = 95 * 8;
    uint8_t* px = v->surface_lock_alloc;
    for (int y = 0; y < 15; y++) for (int x = 0; x < 95 * 8; x++) px[y * 95 * 8 + x] = y >= 2 && y < 12 && x % 8 < 5 ? 2 : 0;
    menuFontLoads++;
    return f;
}
stdBitmap* stdBitmap_Load(char* path, int a, int b) { // bkMain.bm, only its palette is used
    assert(!strcmp(path, "ui\\bm\\bkMain.bm"));
    if (failFontLoad) return NULL;
    stdBitmap* bm = calloc(1, sizeof(stdBitmap)); bm->mipSurfaces = calloc(1, sizeof(tVBuffer*));
    uint8_t* pal = calloc(768, 1); pal[6] = 255; pal[7] = 235; // index 2: the menu's yellow
    bm->palette = pal;
    return bm;
}
stdFont* stdFont_Load(char* path, int a, int b) {
    if (!strcmp(path, "ui\\sft\\small1.sft")) return failFontLoad ? NULL : menuFontStandIn();
    assert(!strcmp(path, "ui\\sft\\msgFont16.sft"));
    if (failFontLoad) return NULL;
    fontLoads++;
    stdFont* f = calloc(1, sizeof(stdFont)); stdBitmap* bm = calloc(1, sizeof(stdBitmap));
    stdFontEntry* e = calloc(95, sizeof(stdFontEntry));
    for (int i = 0; i < 95; i++) { e[i].glyphTexX = i * 6; e[i].glyphWidth = 6; }
    f->marginY = 1; f->marginX = 5; f->field_28 = '?'; f->pBitmap = bm;
    f->charsetHead.charFirst = 32; f->charsetHead.charLast = 126; f->charsetHead.pEntries = e;
    bm->format = (rdTexFormat){.is16bit = 1, .bpp = 16, .r_bits = 5, .g_bits = 6, .b_bits = 5, .r_shift = 11, .g_shift = 5};
    bm->palFmt = 1; bm->colorkey = 0xF81F;
    tRasterInfo info = {.width = 95 * 6, .height = 11};
    bm->mipSurfaces = calloc(1, sizeof(tVBuffer*)); bm->mipSurfaces[0] = stdDisplay_VBufferNew(&info, 0, 0, NULL);
    uint16_t* px = bm->mipSurfaces[0]->surface_lock_alloc;
    for (int y = 0; y < 11; y++) for (int x = 0; x < 95 * 6; x++)
        px[y * (bm->mipSurfaces[0]->format.rowSize / 2) + x] = y > 9 || x % 6 > 3 ? 0xF81F : (y == 9 ? 0xF800 : 0xFFE0);
    return f;
}
void stdFont_Free(stdFont* f) { free(f->charsetHead.pEntries); stdBitmap_Free(f->pBitmap); free(f); }

static void resetDrawn(void) {
    memset(drawn, 0, sizeof(drawn)); memset(grayDrawn, 0, sizeof(grayDrawn)); grayLen = 0; grayText[0] = 0; weaponIcons = itemIcons = rects = bitmaps = 0;
    panelX = panelY = panelW = panelH = 0; textLen = 0; text[0] = 0; lastX = lastY = -1000;
    minX = minY = 1 << 30; maxX = maxY = -1;
}

static void draw(void) {
    resetDrawn();
    inMenu = 1;
    jkRpg_DrawMenu(&player, &font);
    inMenu = 0;
}
static int shown(const char* s) {
    char key[200]; snprintf(key, sizeof(key), "|%s|", s);
    char all[8300]; snprintf(all, sizeof(all), "|%s|", text);
    return strstr(all, key) != NULL;
}
static int pageOf(int up) { return jkRpg_aUpgrades[up].page; }

// Writes rpg/art/<name> as a 24-bit BMP (the checks run in a scratch folder); fill(x, y, rgb).
static void writeBmp(const char* name, int w, int h, void (*fill)(int, int, uint8_t*)) {
    char path[128]; snprintf(path, sizeof(path), "rpg/art/%s", name);
    FILE* f = fopen(path, "wb"); assert(f);
    int stride = (w * 3 + 3) & ~3, size = 54 + stride * h;
    uint8_t hd[54] = {'B', 'M', size, size >> 8, size >> 16, size >> 24, 0, 0, 0, 0, 54, 0, 0, 0, 40, 0, 0, 0,
        w, w >> 8, 0, 0, h, h >> 8, 0, 0, 1, 0, 24, 0};
    fwrite(hd, 1, 54, f);
    uint8_t* row = calloc(stride, 1);
    for (int y = h - 1; y >= 0; y--) { // bottom-up
        for (int x = 0; x < w; x++) { uint8_t c[3]; fill(x, y, c); row[x * 3] = c[2]; row[x * 3 + 1] = c[1]; row[x * 3 + 2] = c[0]; }
        fwrite(row, 1, stride, f);
    }
    free(row); fclose(f);
}
static void removeArt(void) {
    const char* names[] = {"upgrades.bmp", "plate.bmp", "frame.bmp", "titlebar.bmp", "weapons.bmp", "force.bmp"};
    for (int i = 0; i < 6; i++) { char p[64]; snprintf(p, sizeof(p), "rpg/art/%s", names[i]); remove(p); }
    jkRpg_FreeMenuArt();
}
// Upgrade pictures: every slot a flat colour from its index; the Health heading slot left empty.
static void fillUpgrades(int x, int y, uint8_t* c) {
    int tile = (y / 24) * 8 + x / 24;
    if (tile == 0 || tile >= UP_COUNT * 4) { c[0] = 255; c[1] = 0; c[2] = 255; return; }
    c[0] = 40 + tile; c[1] = 200; c[2] = 10;
}
static void fillWeapons(int x, int y, uint8_t* c) {
    int tile = (y / 96) * 5 + x / 192;
    c[0] = tile ? 40 + tile : 255; c[1] = tile ? 140 : 0; c[2] = tile ? 20 : 255;
}
static void fillPlate(int x, int y, uint8_t* c) { // 216x50: steel with a black window, magenta around
    int body = y < 49 && x > 2 && x < 213;
    c[0] = body ? 120 : 255; c[1] = body ? 120 : 0; c[2] = body ? 130 : 255;
    if (body && x > 29 && x < 186 && y > 10 && y < 41) c[0] = c[1] = c[2] = 0;
}
static void fillFrame(int x, int y, uint8_t* c) { c[0] = 150; c[1] = 70; c[2] = 30; if (x > 20 && x < 235 && y > 20 && y < 235) c[0] = c[1] = c[2] = 0; }
static void fillBar(int x, int y, uint8_t* c) { c[0] = x < 52 || x > 590 ? 150 : 100; c[1] = 50; c[2] = 20; }
static void writeArt(void) {
    mkdir("rpg", 0777); mkdir("rpg/art", 0777);
    writeBmp("upgrades.bmp", 192, 216, fillUpgrades);
    writeBmp("plate.bmp", 216, 50, fillPlate);
    writeBmp("frame.bmp", 256, 256, fillFrame);
    writeBmp("titlebar.bmp", 643, 48, fillBar);
    jkRpg_FreeMenuArt(); // read again
}
static void selectBranch(int up) { // through the keyboard, like a player
    for (int i = 0; i < PAGE_COUNT && jkRpg_menuPage != pageOf(up); i++) press(DIK_E);
    for (int i = 0; i < UP_COUNT && jkRpg_menuSel != up; i++) press(DIK_S);
    assert(jkRpg_menuPage == pageOf(up) && jkRpg_menuSel == up);
}
'''

PREVIEW_CHECKS = r'''
static int tilePixels(int tile, uint16_t* out) { // copy a tile out of the atlas; returns how many are not black
    tVBuffer* v = jkRpg_pMenuArt->mipSurfaces[0];
    int stride = v->format.rowSize / 2, lit = 0;
    uint16_t* px = (uint16_t*)v->surface_lock_alloc + ((tile / ATLAS_COLS) * TILE_CELL + 1) * stride + (tile % ATLAS_COLS) * TILE_CELL + 1;
    for (int r = 0; r < TILE; r++) for (int c = 0; c < TILE; c++) {
        uint16_t p = px[r * stride + c];
        assert(p != 0xABAB); // painted
        if (out) out[r * TILE + c] = p;
        if (r > 0 && c > 0 && r < TILE - 1 && c < TILE - 1 && p != 0x8000) lit++;
    }
    return lit;
}

int main(void) {
    setup(1920, 1080);
    // Player-facing upgrade text explains effects without numbers.
    for (int up = 0; up < UP_COUNT; up++) for (int k = 0; k < RPG_MAX_RANK; k++) {
        const jkRpgNode* n = &jkRpg_aUpgrades[up].nodes[k];
        assert(n->name && n->desc && *n->name && *n->desc);
        assert(!strpbrk(n->name, "0123456789%") && !strpbrk(n->desc, "0123456789%"));
    }
    // Every picture is hand-drawn with the shared palette and fits a tile with its frame.
    for (int art = 0; art < ART_COUNT; art++) {
        int h = 0; while (jkRpg_aArt[art][h]) h++;
        int w = (int)strlen(jkRpg_aArt[art][0]);
        assert(h > 0 && h <= TILE - 4 && w <= TILE - 4);
        if (art >= BADGE_UP) assert(w == 7 && h == 7);
        for (int r = 0; r < h; r++) {
            assert((int)strlen(jkRpg_aArt[art][r]) == w);
            for (int c = 0; c < w; c++) assert(strchr(".abcdefghstuwxy", jkRpg_aArt[art][r][c]));
        }
    }
    for (int up = 0; up < UP_COUNT; up++) found[up] = 1;
    draw(); // builds the pictures
    assert(jkRpg_pMenuArt);
    static uint16_t tiles[TILE_COUNT][TILE * TILE];
    for (int up = 0; up < UP_COUNT; up++) {
        // Weapons use their model; every other branch has its own heading picture (bacta and the
        // field light only when the game's item icon is unavailable).
        assert(jkRpg_aUpgrades[up].weapon ? jkRpg_aBranchArt[up].heading == ART_NONE : jkRpg_aBranchArt[up].heading != ART_NONE);
        for (int k = 1; k <= RPG_MAX_RANK; k++) {
            int tile = up * TILES_PER_BRANCH + k;
            assert(tilePixels(tile, tiles[tile]) >= 25); // a real picture, not an empty frame
            for (int j = 1; j < k; j++) // each upgrade of a branch looks different
                assert(memcmp(tiles[tile], tiles[up * TILES_PER_BRANCH + j], sizeof(tiles[0])));
        }
    }
    tVBuffer* atlas = jkRpg_pMenuArt->mipSurfaces[0];
    int lockPixels = 0;
    for (int r = 0; r < TILE; r++) for (int c = 0; c < TILE; c++)
        lockPixels += (((uint16_t*)atlas->surface_lock_alloc)[((TILE_LOCK / ATLAS_COLS) * TILE_CELL + 1 + r) * (atlas->format.rowSize / 2)
                       + (TILE_LOCK % ATLAS_COLS) * TILE_CELL + 1 + c] & 0x8000) != 0;
    assert(lockPixels > 20 && lockPixels < 100); // a small lock badge, the rest see-through

    // Each visible branch: heading, three linked upgrades with names; the selected one described.
    for (int up = 0; up < UP_COUNT; up++) {
        jkRpg_menuSel = -1; selectBranch(up);
        for (int r = 0; r <= RPG_MAX_RANK; r++) {
            for (int b = 0; b < UP_COUNT; b++) rank[b] = r;
            draw();
            for (int b = 0; b < UP_COUNT; b++) {
                int visible = pageOf(b) == pageOf(up);
                for (int k = 1; k <= RPG_MAX_RANK; k++)
                    assert(drawn[b * TILES_PER_BRANCH + k] == visible);
                if (visible) {
                    assert(shown(jkRpg_aUpgrades[b].name));
                    for (int k = 0; k < RPG_MAX_RANK; k++) assert(shown(jkRpg_aUpgrades[b].nodes[k].name));
                }
            }
            for (int k = 0; k < RPG_MAX_RANK; k++) {
                assert(shown(jkRpg_aUpgrades[up].nodes[k].desc));
                assert(shown(k < r ? "Owned" : (k == r ? "Next" : "Later")));
            }
        }
    }
    for (int up = 0; up < UP_COUNT; up++) { // skill headings use their own picture
        jkRpg_menuSel = -1; selectBranch(up); draw();
        int own = !jkRpg_aUpgrades[up].weapon && up != UP_BACTA && up != UP_LIGHT;
        assert(drawn[up * TILES_PER_BRANCH] == own);
    }
    selectBranch(UP_RIFLE); draw(); assert(weaponIcons == 4);       // four blaster headings
    selectBranch(UP_LIGHT); goggles = 0; draw(); assert(itemIcons == 2); // bacta + field light
    goggles = 1; draw(); assert(itemIcons == 2);                      // field light keeps its own heading

    // Owned, next and later upgrades; one bought this mission makes the next wait for the next mission.
    selectBranch(UP_BACTA);
    rank[UP_BACTA] = 1; raised[UP_BACTA] = 1; undo[UP_BACTA] = 1; points = 0;
    draw(); assert(shown("Owned") && shown("Next mission") && shown("Later") && !shown("Enter: take back"));
    undo[UP_BACTA] = 0; draw(); assert(shown("Next mission"));
    assert(drawn[TILE_LOCK] == 1); // the locked next upgrade shows a lock
    raised[UP_BACTA] = 0; draw(); assert(!shown("Next mission") && shown("Next") && !shown("No points"));
    assert(drawn[TILE_LOCK] == 0);
    // Out of reach (no point, waiting or later): colourless picture and text; owned and buyable keep colour.
    int t0 = UP_BACTA * TILES_PER_BRANCH;
    rank[UP_BACTA] = 1; points = 0; draw();
    assert(!grayDrawn[t0 + 1] && grayDrawn[t0 + 2] && grayDrawn[t0 + 3] && strstr(grayText, "Later"));
    points = 2; draw(); assert(!grayDrawn[t0 + 1] && !grayDrawn[t0 + 2] && grayDrawn[t0 + 3] && !strstr(grayText, "Next"));
    raised[UP_BACTA] = 1; draw(); assert(grayDrawn[t0 + 2] && grayDrawn[TILE_LOCK] && strstr(grayText, "Nextmission"));
    raised[UP_BACTA] = 0; rank[UP_BACTA] = 3; draw(); assert(!grayDrawn[t0 + 1] && !grayDrawn[t0 + 3] && !grayLen);
    { // the colourless font keeps the key colour see-through and the letters opaque grey
        uint16_t* g = jkRpg_pGrayFont->mipSurfaces[0]->surface_lock_alloc; int stride = jkRpg_pGrayFont->mipSurfaces[0]->format.rowSize / 2;
        assert((g[0] & 0x8000) && !(g[glyphW] & 0x8000) && !(g[stride * 3 + 10] & 0x8000));
        int r = (g[0] >> 10) & 31, gg = (g[0] >> 5) & 31, bb = g[0] & 31; assert(r == gg && gg == bb && r > 0);
    }
    rank[UP_BACTA] = 3; draw(); assert(!shown("Next") && !shown("Later"));
    press(DIK_RETURN); assert(toggled == UP_BACTA);
    toggled = -1; press(DIK_SPACE); assert(toggled == UP_BACTA);

    menuKey = NULL; draw();
    assert(strstr(text, "Bind Upgrade Menu in Setup to close") && !strstr(text, "Unbound: close"));
    menuKey = "K"; draw(); assert(strstr(text, "K: close"));

    // A migrated rank-3 light keeps its last tier; only the replaced middle tier is missing.
    selectBranch(UP_LIGHT); rank[UP_LIGHT]=3; raised[UP_LIGHT]=1; lightGap=1; points=0;
    draw();
    int lightTile=UP_LIGHT*TILES_PER_BRANCH;
    assert(!grayDrawn[lightTile+1] && grayDrawn[lightTile+2] && !grayDrawn[lightTile+3]);
    assert(shown("Owned") && shown("Next") && !shown("Next mission") && !drawn[TILE_LOCK]);
    points=1; draw(); assert(!grayDrawn[lightTile+2] && !strstr(grayText,"Extendedillumination"));
    lightGap=0; draw(); assert(!shown("Next") && !grayDrawn[lightTile+3]);
    raised[UP_LIGHT]=0;

    jkRpg_FreeMenuArt(); assert(!jkRpg_pMenuArt);
    draw(); assert(jkRpg_pMenuArt); // rebuilt for the next HUD session
    // Shipped pictures (rpg/art/upgrades.bmp) replace the drawn ones slot by slot; an empty
    // (magenta) slot keeps the drawn picture.
    static uint16_t drawnHealth[TILE * TILE], drawnLamp[TILE * TILE];
    tilePixels(0, drawnHealth);
    tilePixels(UP_LIGHT*TILES_PER_BRANCH+2, drawnLamp);
    writeArt(); draw();
    uint16_t px[TILE * TILE];
    for (int tile = 1; tile < TILE_LOCK; tile++) {
        tilePixels(tile, px);
        if (tile == UP_LIGHT*TILES_PER_BRANCH+2) {
            // The retired battery artwork must not replace the new lamp/reach picture.
            assert(!memcmp(px, drawnLamp, sizeof(px)));
            continue;
        }
        uint8_t rgb[3] = {(uint8_t)(40 + tile), 200, 10};
        assert(px[5 * TILE + 5] == jkRpg_Pixel(rgb));
    }
    tilePixels(0, px); assert(!memcmp(px, drawnHealth, sizeof(px)));
    removeArt(); draw();
    tilePixels(5, px); assert(px[5 * TILE + 5] != jkRpg_Pixel((uint8_t[3]){45, 200, 10})); // back to drawn
    FILE* bad = fopen("rpg/art/upgrades.bmp", "wb"); fputs("BM broken", bad); fclose(bad);
    jkRpg_FreeMenuArt(); draw(); tilePixels(5, px); assert(px[5 * TILE + 5] != jkRpg_Pixel((uint8_t[3]){45, 200, 10}));
    removeArt();
    panelW=0; inMenu=0; // no menu bounds for isolated weapon-icon checks
    assert(!jkRpg_DrawShippedWeaponIcon(2,100,100,96,48));
    // Header failures must fall back before dimension arithmetic or allocation.
    const int corruptOffsets[] = {10, 14, 21, 25, 26, 28, 32};
    for(int i=0;i<7;i++) {
        writeBmp("weapons.bmp",960,192,fillWeapons);
        FILE* badHeader=fopen("rpg/art/weapons.bmp","r+b"); assert(badHeader);
        fseek(badHeader,corruptOffsets[i],SEEK_SET); fputc(i==3 ? 128 : 0, badHeader); fclose(badHeader);
        // Compression's upper byte must also be checked.
        if(i==6) { badHeader=fopen("rpg/art/weapons.bmp","r+b"); fseek(badHeader,32,SEEK_SET); fputc(1,badHeader); fclose(badHeader); }
        if(i==2) { badHeader=fopen("rpg/art/weapons.bmp","r+b"); fseek(badHeader,21,SEEK_SET); fputc(127,badHeader); fclose(badHeader); }
        jkRpg_FreeMenuArt(); assert(!jkRpg_DrawShippedWeaponIcon(2,100,100,96,48));
    }
    writeBmp("weapons.bmp",960,192,fillWeapons);jkRpg_FreeMenuArt();
    assert(!jkRpg_DrawShippedWeaponIcon(0,100,100,96,48));
    assert(!jkRpg_DrawShippedWeaponIcon(1,100,100,96,48)); // empty fist slot uses its model
    for(int weapon=2;weapon<=10;weapon++) assert(jkRpg_DrawShippedWeaponIcon(weapon,100,100,96,48));
    stdBitmap* cached=jkRpg_pWeaponArt;
    assert(jkRpg_DrawShippedWeaponIcon(2,100,100,96,48) && jkRpg_pWeaponArt==cached);
    removeArt();assert(!jkRpg_pWeaponArt && !jkRpg_weaponArtMask);
    writeBmp("weapons.bmp",959,192,fillWeapons);jkRpg_FreeMenuArt();
    assert(!jkRpg_DrawShippedWeaponIcon(2,100,100,96,48)); // malformed atlas falls back
    removeArt();
    // Fixed window coordinates require the supplied Force frame dimensions.
    writeBmp("force.bmp",136,128,fillFrame);jkRpg_FreeMenuArt();
    assert(jkRpg_ShippedArt(ARTFILE_FORCE));
    writeBmp("force.bmp",135,128,fillFrame);jkRpg_FreeMenuArt();
    assert(!jkRpg_ShippedArt(ARTFILE_FORCE));
    writeBmp("force.bmp",136,127,fillFrame);jkRpg_FreeMenuArt();
    assert(!jkRpg_ShippedArt(ARTFILE_FORCE));removeArt();
    puts("Upgrade menu: 54 upgrade pictures (shipped or drawn), three per branch, descriptions, Enter states and no numbers passed");
    return 0;
}
'''


def compile_menu(engine, checks, name):
    """Build the real jkRpgMenu.c and upgrade table against the stand-ins above, then run checks."""
    src = Path(engine) / "src"
    menu = (src / "Main/jkRpgMenu.c").read_text()
    internal = (src / "Main/jkRpgInternal.h").read_text()
    rpg = (src / "Main/jkRpg.c").read_text()
    start = rpg.index("const char* const jkRpg_aPageNames")
    table = rpg[start:rpg.index("\n};\n", rpg.index("const jkRpgUpgrade jkRpg_aUpgrades")) + 4]
    with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
        tmp = Path(tmp)
        (tmp / "Main").mkdir()
        (tmp / "types.h").write_text("#pragma once\n" + HARNESS)
        (tmp / "Main/jkRpg.h").write_text('#pragma once\n#include "types.h"\nvoid jkRpg_FreeMenuArt(void);\n')
        (tmp / "Main/jkRpgInternal.h").write_text(internal)
        (tmp / "Main/jkRpgMenu.c").write_text(menu)
        for header in re.findall(r'#include "([^"]+)"', menu):
            path = (tmp / "Main" / header).resolve() if header.startswith("..") else tmp / header
            if not path.exists() and not (tmp / "Main" / header).exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("")
        (tmp / "check.c").write_text('#include "Main/jkRpgMenu.c"\n' + table + STATE + checks)
        binary = tmp / name
        subprocess.run(["cc", "-std=gnu99", "-Wall", "-Wno-unused-function", "-I", str(tmp),
                        str(tmp / "check.c"), "-lm", "-o", str(binary)], check=True)
        subprocess.run([str(binary)], check=True, cwd=str(tmp))


if __name__ == "__main__":
    compile_menu(sys.argv[1], PREVIEW_CHECKS, "previews")
