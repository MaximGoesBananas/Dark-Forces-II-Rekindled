"""Clean the official website's weapon pictures without redrawing their designs.

Run from any directory. Output: art/weapons.bmp, five 192x96 slots per row.
The first slot uses the engine's original fist model. Magenta means transparent.
"""
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

ART = Path(__file__).resolve().parents[1]
NAMES = ["bryar_pistol", "stormt_rifle", "thermdet", "bowcaster", "repeater",
         "rail_deton", "seqcharge", "concrif", "lightsaber"]


def clean_weapon(path):
    original = Image.open(path).convert("RGB")
    width, height = original.size
    mask = Image.new("L", original.size)
    # These two exact web-palette colours are the background and decorative olive halo.
    mask.putdata([255 if p not in ((0, 0, 0), (51, 51, 0)) else 0
                  for p in original.getdata()])
    mask = mask.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
    unseen = {(x, y) for y in range(height) for x in range(width) if mask.getpixel((x, y))}
    groups = []
    while unseen:
        seed = unseen.pop()
        pending, group = [seed], {seed}
        while pending:
            x, y = pending.pop()
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    point = x + dx, y + dy
                    if point in unseen:
                        unseen.remove(point)
                        group.add(point)
                        pending.append(point)
        groups.append(group)
    # Detached letters are smaller than the weapon. Preserve the actual coloured pixels.
    mask = Image.new("L", original.size)
    for point in max(groups, key=len):
        mask.putpixel(point, 255)
    mask = mask.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
    outline = mask.filter(ImageFilter.MaxFilter(3))
    result = Image.new("RGBA", original.size)
    for y in range(height):
        for x in range(width):
            if outline.getpixel((x, y)):
                colour = original.getpixel((x, y)) if mask.getpixel((x, y)) else (10, 10, 13)
                if colour == (51, 51, 0):
                    colour = (10, 10, 13)
                result.putpixel((x, y), (*colour, 255))
    result = result.crop(result.getbbox())
    return ImageOps.mirror(result) if path.stem == "bowcaster" else result


def build():
    atlas = Image.new("RGB", (960, 192), (255, 0, 255))
    for slot, name in enumerate(NAMES, 1):
        icon = clean_weapon(ART / "source" / "official-weapons" / (name + ".gif"))
        # Fit, without stretching the original aspect ratio or enlarging its pixels.
        icon.thumbnail((184, 88), Image.Resampling.LANCZOS)
        x = slot % 5 * 192 + (192 - icon.width) // 2
        y = slot // 5 * 96 + (96 - icon.height) // 2
        # The engine uses one-bit transparency; antialias edge colours against dark UI.
        for iy in range(icon.height):
            for ix in range(icon.width):
                r, g, b, alpha = icon.getpixel((ix, iy))
                if alpha >= 128:
                    atlas.putpixel((x + ix, y + iy), (r * alpha // 255, g * alpha // 255, b * alpha // 255))
    atlas.save(ART / "weapons.bmp")


if __name__ == "__main__":
    build()
