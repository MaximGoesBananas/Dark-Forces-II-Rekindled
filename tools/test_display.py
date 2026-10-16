"""Exercise the actual desktop window recreation with SDL lifetime and sizing checks."""
from pathlib import Path
import subprocess
import sys
import tempfile

source = (Path(sys.argv[1]) / "src/Win95/Window.c").read_text()
start = source.index("void Window_RecreateSDL2Window()")
function = source[start:source.index("\n}\n", start) + 3]
harness = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
typedef unsigned int SDL_WindowFlags;
typedef struct { int x,y,w,h; } SDL_Rect;
#define SDL_WINDOW_OPENGL 1
#define SDL_WINDOW_RESIZABLE 2
#define SDL_WINDOW_BORDERLESS 4
#define SDL_WINDOW_HIGH_PIXEL_DENSITY 8
#define SDL_MESSAGEBOX_ERROR 0
#define SDL_GL_CONTEXT_MAJOR_VERSION 0
#define SDL_GL_CONTEXT_MINOR_VERSION 1
#define SDL_GL_CONTEXT_PROFILE_MASK 2
#define SDL_GL_CONTEXT_PROFILE_CORE 3
#define SDL_GL_SHARE_WITH_CURRENT_CONTEXT 4
#define SDL_GL_CONTEXT_FLAGS 5
#define SDL_GL_CONTEXT_FORWARD_COMPATIBLE_FLAG 6
static int Main_bHeadless, Window_needsRecreate, Window_bShouldPopSteamKeyboard;
static int Window_isFullscreen, Window_isHiDpi, Window_xPos, Window_yPos;
static int Window_screenXSize=1920, Window_screenYSize=1080, Window_xSize, Window_ySize;
static int jkPlayer_enableVsync, Window_resized, live, query_ok=1, created;
static void *displayWindow, *glWindowContext;
static SDL_Rect desktop, current;
static SDL_WindowFlags currentFlags;
static void stdPlatform_Printf(const char *s) {}
static int SDL_GetPrimaryDisplay(void) { return 1; }
static int SDL_GetDisplayBounds(int id, SDL_Rect *r) { *r=desktop; return query_ok; }
static SDL_WindowFlags SDL_GetWindowFlags(void *w) { assert(live); return currentFlags; }
static void SDL_GetWindowPosition(void *w,int *x,int *y) { assert(live); *x=current.x; *y=current.y; }
static void SDL_GetWindowSize(void *w,int *x,int *y) { assert(live); *x=current.w; *y=current.h; }
static void SDL_GetWindowSizeInPixels(void *w,int *x,int *y) { SDL_GetWindowSize(w,x,y); }
static void std3D_FreeResources(void) {}
static void SDL_GL_DestroyContext(void *c) {}
static void SDL_DestroyWindow(void *w) { assert(live); live=0; }
static void *SDL_CreateWindow(const char *title,int w,int h,SDL_WindowFlags flags) {
    assert(!live && w>0 && h>0); live=1; created++; current.w=w; current.h=h; currentFlags=flags; return (void*)1;
}
static const char *SDL_GetError(void) { return "test"; }
static void SDL_ShowSimpleMessageBox(int type,const char *t,const char *s,void *w) { assert(0); }
static void SDL_SetWindowPosition(void *w,int x,int y) { assert(live); current.x=x; current.y=y; }
static void SDL_SetWindowFullscreen(void *w,int v) { assert(live && !v); }
static void SDL_RaiseWindow(void *w) { assert(live); }
static void *SDL_GL_CreateContext(void *w) { assert(live); return (void*)2; }
static void SDL_GL_SetAttribute(int a,int b) {}
static void SDL_GL_MakeCurrent(void *w,void *c) {}
static void SDL_GL_SetSwapInterval(int v) {}
static void SDL_StartTextInput(void *w) {}
'''
checks = r'''
int main(void) {
    const int sizes[][2]={{640,480},{1280,720},{1920,1080},{2560,1440},{3440,1440},{3840,2160},{5120,1440}};
    for(int i=0;i<7;i++) {
        displayWindow=NULL; live=0; desktop=(SDL_Rect){-1200,40,sizes[i][0],sizes[i][1]};
        Window_RecreateSDL2Window();
        assert(Window_xSize==desktop.w && Window_ySize==desktop.h);
        assert(current.x==desktop.x && current.y==desktop.y && (currentFlags & SDL_WINDOW_BORDERLESS));
        current=(SDL_Rect){20,30,800,600}; Window_isHiDpi=1;
        Window_RecreateSDL2Window();
        assert(current.x==20 && current.y==30 && Window_xSize==800 && Window_ySize==600);
    }
    displayWindow=NULL; live=0; query_ok=0; Window_RecreateSDL2Window();
    assert(Window_xSize==640 && Window_ySize==480);
    int before=created; Main_bHeadless=1; Window_RecreateSDL2Window(); assert(before==created);
    puts("Desktop size, display offsets, resize preservation, SDL handle lifetime and fallback passed");
}
'''
scratch = Path("/mnt/d/Dev/helm/temp/rekindled-launch")
scratch.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix="display-check-", dir=scratch) as folder:
    file = Path(folder) / "display.c"
    binary = Path(folder) / "display"
    file.write_text(harness + function + checks)
    subprocess.run(["cc", str(file), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
