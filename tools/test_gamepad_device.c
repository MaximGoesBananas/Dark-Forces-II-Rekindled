/* Isolated Linux gamepad fixture. Run as root in WSL with a state file and the
 * test user's UID. State: sequence, LX LY RX RY LT RT hatX hatY, button bitmask.
 * Buttons: A B X Y LB RB Back Start Guide LStick RStick. A negative sequence exits.
 * No keyboard events are synthesized; SDL reads a real kernel input device. */
#include <linux/uinput.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <glob.h>
#include <assert.h>

static void emit(int fd, int type, int code, int value) {
    struct input_event e={.type=type,.code=code,.value=value};
    assert(write(fd,&e,sizeof(e))==sizeof(e));
}
int main(int argc,char** argv) {
    assert(argc==3);
    const int axes[]={ABS_X,ABS_Y,ABS_RX,ABS_RY,ABS_Z,ABS_RZ,ABS_HAT0X,ABS_HAT0Y};
    const int buttons[]={BTN_SOUTH,BTN_EAST,BTN_NORTH,BTN_WEST,BTN_TL,BTN_TR,BTN_SELECT,BTN_START,BTN_MODE,BTN_THUMBL,BTN_THUMBR};
    int fd=open("/dev/uinput",O_WRONLY|O_NONBLOCK);assert(fd>=0);
    assert(ioctl(fd,UI_SET_EVBIT,EV_KEY)==0);
    assert(ioctl(fd,UI_SET_EVBIT,EV_ABS)==0);
    for(int i=0;i<11;i++) assert(ioctl(fd,UI_SET_KEYBIT,buttons[i])==0);
    struct uinput_user_dev device={0};
    strcpy(device.name,"Rekindled test gamepad");
    device.id.bustype=BUS_USB;device.id.vendor=0x045e;device.id.product=0x028e;device.id.version=0x0114;
    for(int i=0;i<8;i++) {
        assert(ioctl(fd,UI_SET_ABSBIT,axes[i])==0);
        device.absmin[axes[i]]=i<4?-32768:i<6?0:-1;
        device.absmax[axes[i]]=i<4?32767:i<6?255:1;
    }
    assert(write(fd,&device,sizeof(device))==sizeof(device));
    assert(ioctl(fd,UI_DEV_CREATE)==0);
    char sysname[128],pattern[256];
    assert(ioctl(fd,UI_GET_SYSNAME(sizeof(sysname)),sysname)>=0);
    snprintf(pattern,sizeof(pattern),"/sys/devices/virtual/input/%s/event*/dev",sysname);
    glob_t nodes={0};
    for(int retry=0;retry<50;retry++) {
        globfree(&nodes);memset(&nodes,0,sizeof(nodes));
        if(glob(pattern,0,NULL,&nodes)==0 && nodes.gl_pathc) break;
        usleep(20000);
    }
    assert(nodes.gl_pathc==1);
    char path[256];strcpy(path,nodes.gl_pathv[0]);*strrchr(path,'/')=0;
    char event[256];snprintf(event,sizeof(event),"/dev/input/%s",strrchr(path,'/')+1);
    for(int retry=0;retry<50 && access(event,F_OK);retry++) usleep(20000);
    assert(chown(event,atoi(argv[2]),-1)==0);assert(chmod(event,0600)==0);
    globfree(&nodes);
    printf("Ready: %s\n",event);fflush(stdout);
    int previous=-1;
    for(int tick=0;tick<60000;tick++) {
        int seq,values[8];unsigned mask;
        FILE* f=fopen(argv[1],"r");
        if(f) {
            int n=fscanf(f,"%d %d %d %d %d %d %d %d %d %u",&seq,&values[0],&values[1],&values[2],&values[3],&values[4],&values[5],&values[6],&values[7],&mask);
            fclose(f);
            if(n==10 && seq<0) break;
            if(n==10 && seq!=previous) {
                for(int i=0;i<8;i++) emit(fd,EV_ABS,axes[i],values[i]);
                for(int i=0;i<11;i++) emit(fd,EV_KEY,buttons[i],!!(mask&(1u<<i)));
                emit(fd,EV_SYN,SYN_REPORT,0);previous=seq;
                printf("Applied %d\n",seq);fflush(stdout);
            }
        }
        usleep(10000);
    }
    ioctl(fd,UI_DEV_DESTROY);close(fd);
}
