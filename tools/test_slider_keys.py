"""Compile the actual shared slider handler and dispatcher; exercise keyboard bounds."""
import os
import tempfile
import subprocess
import sys
from pathlib import Path

source = (Path(sys.argv[1]) / "src/Gui/jkGUIRend.c").read_text()

def function(signature):
    start = source.index(signature)
    return source[start:source.index("\n}\n", start)+3]

# Keep the real element routing: only the slider slot reaches this handler.
table_start = source.index("static jkGuiElementHandlers jkGuiRend_elementHandlers[8]")
table = source[table_start:source.index("};", table_start)+2]
assert table.count("jkGuiRend_SliderEventHandler") == 1
code = r"""
#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
typedef struct {struct {int width;} format;} Surface;
typedef struct {Surface** mipSurfaces;} stdBitmap;
typedef struct {int x,y,width,height;} Rect;
typedef struct jkGuiElement {
    int type,bIsVisible,enableHover;
    union {int32_t extraInt; void* unistr;};
    union {int32_t selectedTextEntry; intptr_t otherDataPtr;};
    Rect rect;int32_t* uiBitmaps;
    struct {int textHeight,numTextEntries;} texInfo;
} jkGuiElement;
typedef struct {stdBitmap* ui_structs[2];jkGuiElement* focusedElement;} jkGuiMenu;
typedef int32_t (*jkGuiEventHandlerFunc_t)(jkGuiElement*,jkGuiMenu*,int32_t,int32_t);
typedef struct {jkGuiEventHandlerFunc_t fnEventHandler;void* draw;void* fnClickHandler;} jkGuiElementHandlers;
enum {JKGUI_EVENT_INIT=0,JKGUI_EVENT_2=2,JKGUI_EVENT_MOUSEMOVED=3,
      JKGUI_EVENT_MOUSEDOWN=4,JKGUI_EVENT_KEYDOWN=5,VK_LEFT=37,VK_RIGHT=39,
      ELEMENT_LISTBOX=4,ELEMENT_TEXTBOX=5,ELEMENT_SLIDER=6};
static int draws,otherEvents,mouseX,mouseY;
static jkGuiElement* drawn;
static void jkGuiRend_GetMousePos(int32_t* x,int32_t* y){*x=mouseX;*y=mouseY;}
static void stdBitmap_EnsureData(stdBitmap* bitmap){assert(bitmap);}
static void jkGuiRend_UpdateAndDrawClickable(jkGuiElement* e,jkGuiMenu* menu,int redraw){assert(menu && redraw==1);draws++;drawn=e;}
static int other_handler(jkGuiElement* e,jkGuiMenu* m,int32_t type,int32_t key){otherEvents++;return 17;}
#define jkGuiRend_TextButtonEventHandler other_handler
#define jkGuiRend_PicButtonEventHandler other_handler
#define jkGuiRend_ListBoxEventHandler other_handler
#define jkGuiRend_TextBoxEventHandler other_handler
#define jkGuiRend_TextButtonDraw NULL
#define jkGuiRend_PicButtonDraw NULL
#define jkGuiRend_TextDraw NULL
#define jkGuiRend_CheckBoxDraw NULL
#define jkGuiRend_ListBoxDraw NULL
#define jkGuiRend_TextBoxDraw NULL
#define jkGuiRend_SliderDraw NULL
#define jkGuiRend_PlayClickSound NULL
#define jkGuiRend_DrawClickableAndUpdatebool NULL
#define jkGuiRend_ClickSound NULL
""" + function("int jkGuiRend_SliderEventHandler(") + table + function("int32_t jkGuiRend_InvokeEvent(") + function("void jkGuiRend_RenderFocused(") + r"""
static void key(jkGuiElement* slider,jkGuiMenu* menu,int key,int expected){
    jkGuiElement before=*slider;
    int count=draws;
    assert(jkGuiRend_InvokeEvent(slider,menu,JKGUI_EVENT_KEYDOWN,key)==0);
    assert(slider->selectedTextEntry==expected);
    before.selectedTextEntry=expected;
    assert(!memcmp(slider,&before,sizeof(before))); // maximum and every unrelated field preserved
    assert(draws==count+1 && drawn==slider);
}
int main(void){
    jkGuiMenu menu={0};int32_t images[]={0,1};
    // A mouse click focuses its actual element; subsequent keys use the menu's focus.
    jkGuiElement textbox={.type=ELEMENT_TEXTBOX,.bIsVisible=1,.selectedTextEntry=12};
    jkGuiElement clicked={.type=ELEMENT_SLIDER,.bIsVisible=1,.extraInt=999,.selectedTextEntry=250};
    menu.focusedElement=&textbox;
    assert(jkGuiRend_InvokeEvent(menu.focusedElement,&menu,JKGUI_EVENT_KEYDOWN,VK_LEFT)==17);
    int textEvents=otherEvents;
    jkGuiRend_RenderFocused(&menu,&clicked);
    assert(menu.focusedElement==&clicked && draws==2 && drawn==&clicked);
    key(menu.focusedElement,&menu,VK_LEFT,249);
    key(menu.focusedElement,&menu,VK_RIGHT,250);
    assert(otherEvents==textEvents && textbox.selectedTextEntry==12);
    int focusDraws=draws;
    jkGuiRend_RenderFocused(&menu,&clicked);
    assert(draws==focusDraws); // clicking the focused slider does not change focus again
    for(int excluded=0;excluded<4;excluded++){
        jkGuiElement blocked=clicked;
        if(excluded==0)blocked.bIsVisible=0;
        if(excluded==1)blocked.enableHover=1;
        if(excluded==2)blocked.type=0; // buttons keep their previous focus behavior
        jkGuiRend_RenderFocused(&menu,excluded==3?NULL:&blocked);
        assert(menu.focusedElement==&clicked && draws==focusDraws);
    }
    // Text fields and lists still take focus normally after leaving a slider.
    jkGuiRend_RenderFocused(&menu,&textbox);
    assert(menu.focusedElement==&textbox);
    assert(jkGuiRend_InvokeEvent(menu.focusedElement,&menu,JKGUI_EVENT_KEYDOWN,VK_LEFT)==17);
    assert(otherEvents==textEvents+1 && clicked.selectedTextEntry==250);
    jkGuiElement list={.type=ELEMENT_LISTBOX,.bIsVisible=1};
    jkGuiRend_RenderFocused(&menu,&list);assert(menu.focusedElement==&list);
    int limits[]={0,4,49,100,200,999};
    for(unsigned i=0;i<sizeof(limits)/sizeof(*limits);i++){
        int maximum=limits[i];
        jkGuiElement slider={.type=6,.bIsVisible=1,.extraInt=maximum,
            .selectedTextEntry=maximum/2,.rect={10,20,200,30},.uiBitmaps=images,
            .texInfo={3,27}};
        for(int n=maximum/2-1;n>=0;n--)key(&slider,&menu,VK_LEFT,n);
        for(int n=0;n<5;n++)key(&slider,&menu,VK_LEFT,0);
        for(int n=1;n<=maximum;n++)key(&slider,&menu,VK_RIGHT,n);
        for(int n=0;n<5;n++)key(&slider,&menu,VK_RIGHT,maximum);
        for(int n=maximum-1;n>=0;n--)key(&slider,&menu,VK_LEFT,n);
        if(maximum)for(int n=0;n<20;n++){key(&slider,&menu,VK_RIGHT,1);key(&slider,&menu,VK_LEFT,0);}
        jkGuiElement before=slider;int count=draws;
        jkGuiRend_InvokeEvent(&slider,&menu,JKGUI_EVENT_KEYDOWN,65);
        assert(!memcmp(&slider,&before,sizeof(before)) && draws==count);
        slider.bIsVisible=0;before=slider;
        jkGuiRend_InvokeEvent(&slider,&menu,JKGUI_EVENT_KEYDOWN,VK_RIGHT);
        assert(!memcmp(&slider,&before,sizeof(before)) && draws==count);
        slider.bIsVisible=1;slider.enableHover=1;before=slider;
        jkGuiRend_InvokeEvent(&slider,&menu,JKGUI_EVENT_KEYDOWN,VK_RIGHT);
        assert(!memcmp(&slider,&before,sizeof(before)) && draws==count);
    }
    for(int type=0;type<8;type++)if(type!=6){
        jkGuiElement other={.type=type,.bIsVisible=1,.extraInt=100,.selectedTextEntry=50};
        jkGuiElement before=other;int count=draws,events=otherEvents;
        int hasHandler=type==0 || type==1 || type==4 || type==5;
        assert(jkGuiRend_InvokeEvent(&other,&menu,JKGUI_EVENT_KEYDOWN,VK_LEFT)==(hasHandler?17:0));
        assert(!memcmp(&other,&before,sizeof(before)) && draws==count && otherEvents==events+hasHandler);
    }
    puts("Slider keys: clicked focus, text/list focus, repeated arrows, bounds, preserved maximum and disabled controls passed");
}
"""
scratch = Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-slider-keys"
scratch.mkdir(parents=True, exist_ok=True)
cfile, binary = scratch/"slider.c", scratch/"slider"
try:
    cfile.write_text(code)
    subprocess.run(["cc", "-std=gnu11", str(cfile), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
finally:
    cfile.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)
