"""Turn generated icon sheets into 24x24 game-style tiles and the shipped atlas.

process.py            -> builds art/upgrades.bmp + preview images
Tile slots follow jkRpgMenu.c: tile = branch * 4 + k (k 0 heading, 1-3 upgrades).
"""
import json, os
from PIL import Image

GEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'source') + '/'
REF = os.environ.get('JK_ICON_REFS', 'D:/Dev/helm/scratch/jk-rpg-ref/art/big/')  # extracted from the player's own game, never committed
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..') + '/'
PREV = os.path.dirname(os.path.abspath(__file__)) + '/'
UPS = ["HEALTH", "SHIELDS", "ATHLETICS", "SCAVENGER", "MEDIC", "BACTA", "LIGHT", "BRYAR", "RIFLE",
       "BOWCASTER", "REPEATER", "THERMAL", "RAIL", "SEQUENCER", "CONCUSSION", "SABER", "FORCE", "ENDURANCE"]
TILE, COLS = 24, 8
BOOST = 1.3  # generated art is darker than the game's glowing icons
ROWS = (len(UPS) * 4 + COLS - 1) // COLS

# Palette sources: the original icons whose colours each category uses (study copies, not shipped).
PALETTES = {
    'purple': ['icbacta16', 'icfield16', 'icirgog16', 'icdatad16', 'icwrchy16'],
    'green': ['icf_hea16', 'icf_abs16', 'icf_pro16', 'icf_per16', 'icf_see16'],
    'red': ['icf_lig16', 'icf_gri16', 'icf_des16', 'icf_thr16', 'icf_dea16'],
    'blue': ['icf_spe16', 'icf_jum16', 'icf_pul16'],
}
PALETTES['combat'] = PALETTES['blue'] + PALETTES['red'] + PALETTES['green']

# sheet file -> (grid, palette, [slot name per cell or None])
SHEETS = json.load(open(PREV + 'sheets.json'))


def palette(name):
    cols = set()
    for n in PALETTES[name]:
        im = Image.open(REF + n + '.png').convert('RGB').resize((24, 24), Image.NEAREST)
        for y in range(1, 23):
            for x in range(1, 23):
                cols.add(im.getpixel((x, y)))
    cols.add((0, 0, 0))
    return sorted(cols)


def nearest(c, pal):
    r, g, b = c
    best, bd = None, 1e9
    for p in pal:
        d = 2 * (r - p[0]) ** 2 + 4 * (g - p[1]) ** 2 + 3 * (b - p[2]) ** 2
        if d < bd:
            best, bd = p, d
    return best


def runs(counts, need, n):
    """The n longest runs of indices whose count reaches need, in order."""
    out, start = [], None
    for i, c in enumerate(counts + [0]):
        if c >= need and start is None:
            start = i
        elif c < need and start is not None:
            out.append((start, i)); start = None
    out = sorted(sorted(out, key=lambda r: r[1] - r[0])[-n:])
    return out


def cells(im, grid):
    """Black tile interiors, found from rows and columns that are mostly black, in reading order."""
    cols, rows = grid
    w, h = im.size
    px = im.load()
    dark = [[sum(px[x, y]) < 30 for x in range(w)] for y in range(h)]
    colc = [sum(dark[y][x] for y in range(h)) for x in range(w)]
    rowc = [sum(dark[y]) for y in range(h)]
    xr = runs(colc, h * 0.05, cols)
    yr = runs(rowc, w * 0.05, rows)
    return [im.crop((x0, y0, x1, y1)) for (y0, y1) in yr for (x0, x1) in xr]


def tile(interior, pal):
    """Fit the object into the 22x22 inside of a framed 24x24 tile, in the original palette."""
    rgb = interior.convert('RGB')
    w, h = rgb.size
    inset = max(2, w // 40)
    rgb = rgb.crop((inset, inset, w - inset, h - inset))   # drop the generated frame
    px = rgb.load()
    xs = [x for x in range(rgb.width) for y in range(rgb.height) if sum(px[x, y]) > 60]
    ys = [y for x in range(rgb.width) for y in range(rgb.height) if sum(px[x, y]) > 60]
    if xs:
        x0, x1, y0, y1 = min(xs), max(xs) + 1, min(ys), max(ys) + 1
        side = max(x1 - x0, y1 - y0) * 1.06
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        rgb = rgb.crop((int(cx - side / 2), int(cy - side / 2), int(cx + side / 2), int(cy + side / 2)))
    small = rgb.resize((22, 22), Image.LANCZOS).point(lambda v: min(255, int(v * BOOST)))
    out = Image.new('RGB', (TILE, TILE), (0, 0, 0))
    for y in range(22):
        for x in range(22):
            c = small.getpixel((x, y))
            out.putpixel((x + 1, y + 1), (0, 0, 0) if sum(c) < 36 else nearest(c, pal))
    for i in range(TILE):  # the items' 1-pixel steel frame: lit top/left, shaded bottom/right
        out.putpixel((i, 0), (80, 84, 104)); out.putpixel((0, i), (72, 76, 92))
        out.putpixel((i, TILE - 1), (48, 56, 72)); out.putpixel((TILE - 1, i), (48, 56, 72))
    return out


def main():
    atlas = Image.new('RGB', (COLS * TILE, ROWS * TILE), (255, 0, 255))  # magenta: no art, use the fallback
    done = {}
    pals = {}
    for sheet, spec in SHEETS.items():
        im = Image.open(GEN + sheet).convert('RGB')
        pal = pals.setdefault(spec['palette'], palette(spec['palette']))
        if 'crop' in spec:
            left, top, right, bottom = spec['crop']
            if len(spec['slots']) != 1 or not (0 <= left < right <= im.width and 0 <= top < bottom <= im.height):
                raise ValueError(f'{sheet}: crop must describe one tile within the image')
            interiors = [im.crop(spec['crop'])]
        else:
            interiors = cells(im, spec['grid'])
        for slot, interior in zip(spec['slots'], interiors):
            if not slot or interior is None:
                continue
            up, k = slot.split(':')
            t = UPS.index(up) * 4 + int(k)
            done[t] = tile(interior, pal)
            atlas.paste(done[t], ((t % COLS) * TILE, (t // COLS) * TILE))
    os.makedirs(OUT, exist_ok=True)
    atlas.save(OUT + 'upgrades.bmp')
    atlas.resize((atlas.width * 4, atlas.height * 4), Image.NEAREST).save(PREV + 'atlas_4x.png')
    print('tiles', len(done), 'in', len(UPS) * 4, 'slots')


if __name__ == '__main__':
    main()
