"""Check the explicit single-icon crop without private palette files or disk output."""
from unittest.mock import patch
from PIL import Image, ImageChops
import process


def main():
    name = 'icons-spread-fan.png'
    spec = process.SHEETS[name]
    source = Image.open(process.GEN + name).convert('RGB')
    atlas = Image.open(process.OUT + 'upgrades.bmp').convert('RGB')
    shipped = atlas.crop((168, 96, 192, 120))
    palette = sorted(set(shipped.getdata()))
    saved = {}

    def capture(image, path, *args, **kwargs):
        saved[path] = image.copy()

    with patch.object(process, 'SHEETS', {name: spec}), \
         patch.object(process, 'palette', return_value=palette), \
         patch.object(process, 'cells', side_effect=AssertionError('Explicit crop was ignored')), \
         patch.object(Image.Image, 'save', capture):
        process.main()
        tile = saved[process.OUT + 'upgrades.bmp'].crop((168, 96, 192, 120))
        expected = process.tile(source.crop(spec['crop']), palette)
        assert ImageChops.difference(tile, expected).getbbox() is None
        # The old dotted line and accidental half-crop both fail this width/height check.
        bright = {(x, y) for y in range(1, 23) for x in range(1, 23)
                  if tile.getpixel((x, y))[0] > 200 and tile.getpixel((x, y))[1] > 150}
        assert min(x for x, y in bright) <= 4 and max(x for x, y in bright) >= 19
        assert min(y for x, y in bright) <= 4 and max(y for x, y in bright) >= 19
        for crop in ([-1, 0, 20, 20], [0, 0, source.width + 1, 20], [20, 0, 10, 20]):
            with patch.object(process, 'SHEETS', {name: dict(spec, crop=crop)}):
                try:
                    process.main()
                except ValueError:
                    pass
                else:
                    raise AssertionError('Out-of-bounds or inverted crop accepted')
    print('Full spread crop and invalid bounds passed')


if __name__ == '__main__':
    main()
