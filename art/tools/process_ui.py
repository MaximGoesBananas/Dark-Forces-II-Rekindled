"""Generated plate, frame and title bar -> shipped BMPs (magenta = transparent). Prints layout numbers."""
import os
from PIL import Image
GEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'source') + '/'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..') + '/'
PREVIEW = 'D:/Dev/helm/scratch/jk-rpg-art' if os.name == 'nt' else '/mnt/d/Dev/helm/scratch/jk-rpg-art'

def keyed(name):
    im = Image.open(GEN + name).convert('RGB')
    a = Image.new('L', im.size)
    px, ap = im.load(), a.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b = px[x, y]
            ap[x, y] = 0 if min(r, b) - g > 45 else 255
    rgba = im.convert('RGBA'); rgba.putalpha(a)
    return rgba.crop(a.getbbox())

def save(rgba, name):
    """Downscaled art with a 1-bit edge: magenta wherever less than half covered."""
    out = Image.new('RGB', rgba.size, (255, 0, 255))
    px, op = rgba.load(), out.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, a = px[x, y]
            if a >= 128:
                op[x, y] = (min(255, r * 255 // a), min(255, g * 255 // a), min(255, b * 255 // a)) if a else (0, 0, 0)
    out.save(OUT + name)
    os.makedirs(PREVIEW, exist_ok=True)
    out.resize((out.width * 3, out.height * 3), Image.NEAREST).save(PREVIEW + '/prev_' + name.replace('.bmp', '.png'))
    print(name, out.size)

def shrink(rgba, w, h):
    # premultiplied area resampling so the magenta key never bleeds into the edges
    pm = Image.new('RGBA', rgba.size); src = rgba.load(); dst = pm.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, a = src[x, y]
            dst[x, y] = (r * a // 255, g * a // 255, b * a // 255, a)
    return pm.resize((w, h), Image.BOX)

# Plate: 54 gauge pixels at 4 texels each; the game's own chain remains visible below.
plate = keyed('plate.png')
px = plate.load()
steel_rows = [y for y in range(plate.height) if sum(1 for x in range(plate.width) if px[x, y][3] and abs(px[x, y][0] - px[x, y][2]) < 30) > plate.width * 0.6]
body_h = max(steel_rows) + 1
k = 216 / plate.width
small = shrink(plate, 216, round(plate.height * k))
save(small, 'plate.bmp')
# window: the black region in the middle of the body
sp = small.load()
blk = [(x, y) for y in range(small.height) for x in range(small.width) if sp[x, y][3] > 200 and sum(sp[x, y][:3]) < 40]
xs = sorted(x for x, y in blk); ys = sorted(y for x, y in blk)
print('plate texels', small.size, 'body height texels', round(body_h * k), 'window', xs[len(xs)//50], ys[len(ys)//50], xs[-len(xs)//50], ys[-len(ys)//50])

# Frame: 256x256, border thickness printed.
frame = keyed('frame.png')
f = shrink(frame, 256, 256)
save(f, 'frame.bmp')
fp = f.load()
row = [fp[x, 128] for x in range(256)]
inner = next(x for x in range(20, 128) if sum(row[x][:3]) < 30 and row[x][3] > 200)
print('frame border texels', inner)

# Title bar: 48 texels tall, caps measured.
bar = keyed('titlebar.png')
b = shrink(bar, round(bar.width * 48 / bar.height), 48)
save(b, 'titlebar.bmp')

# Matching HUD panels with real alpha: 128 texels tall = 32 gauge pixels.
# The engine places the bacta tank/count or selected Force power inside each dark window.
for name in ('bacta', 'force'):
    panel = Image.open(GEN + name + '.png').convert('RGBA')
    panel = panel.crop(panel.getchannel('A').point(lambda a: 255 if a >= 128 else 0).getbbox())
    small = shrink(panel, round(panel.width * 128 / panel.height), 128)
    save(small, name + '.bmp')

    tp = small.load()
    mid_y, mid_x = small.height // 2, small.width // 2
    dark = lambda x, y: tp[x, y][3] > 200 and sum(tp[x, y][:3]) < 150
    left = next(x for x in range(mid_x, -1, -1) if not dark(x, mid_y)) + 1
    right = next(x for x in range(mid_x, small.width) if not dark(x, mid_y))
    top = next(y for y in range(mid_y, -1, -1) if not dark(mid_x, y)) + 1
    bottom = next(y for y in range(mid_y, small.height) if not dark(mid_x, y))
    print(name, 'window texels', left, top, right, bottom)
