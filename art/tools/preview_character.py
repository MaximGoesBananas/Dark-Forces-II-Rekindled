"""Preview the shipped Character tiles at 1x and 4x, without game references."""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ROWS = [
    [(0, 'Health'), (1, 'Vitality'), (2, 'Vigor'), (3, 'Slow regeneration')],
    [(4, 'Shields'), (5, 'Blast resistance'), (6, 'Better recharging'), (7, 'Stable protection')],
    [(8, 'Athletics'), (9, 'Quick feet'), (10, 'Quick draw (new)'), (11, 'Grip boots (new)')],
    [(68, 'Endurance (new)'), (69, 'Safer landings (moved)'),
     (70, 'Deep breath (recolored)'), (71, 'Stand firm (new)')],
]


def main():
    atlas = Image.open(ROOT / 'upgrades.bmp').convert('RGB')
    assert atlas.size == (192, 216), atlas.size
    preview = Image.new('RGB', (640, 730), '#17191d')
    draw = ImageDraw.Draw(preview)
    draw.text((12, 10), 'Character icons - actual 24px tiles above 4x views', fill='#eeeeee')
    for row, entries in enumerate(ROWS):
        for col, (index, label) in enumerate(entries):
            x, y = index % 8 * 24, index // 8 * 24
            icon = atlas.crop((x, y, x + 24, y + 24))
            assert all(color != (255, 0, 255) for count, color in icon.getcolors()), label
            left, top = col * 160, 40 + row * 170
            draw.text((left + 5, top), label, fill='#eeeeee')
            preview.paste(icon, (left + 68, top + 22))
            preview.paste(icon.resize((96, 96), Image.Resampling.NEAREST), (left + 32, top + 56))
    target = ROOT / 'tools' / 'character-preview.png'
    preview.save(target)
    print(target)


if __name__ == '__main__':
    main()
