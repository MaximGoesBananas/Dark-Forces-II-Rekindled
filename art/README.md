# Menu and HUD art

The menu and HUD assets are supplied with Rekindled and processed by the scripts in
`tools/`. The engine loads the BMP atlases from `rpg/art`, with built-in fallbacks for
missing or unreadable files. The weapon pictures have separate LucasArts attribution
in [the artwork credits](../docs/UPGRADE-ART.md).

| Shipped file | What it is | Source in `source/` |
|---|---|---|
| `weapons.bmp` | Nine cleaned official weapon pictures in a 960x192 atlas, five 192x96 slots per row; first slot is transparent for the runtime textured fist | `official-weapons/*.gif` |
| `upgrades.bmp` | 24x24 pictures for all 54 upgrades and the Health, Shields, Athletics, Endurance, Scavenger, Field Medic and Force headings, in the menu's tile order (branch x 4 + 0 heading / 1-3 upgrades, 8 per row); 72 slots in a 192x216 atlas; magenta = none | `icons-*.png` |
| `plate.bmp` | The blank level plate on the health gauge, 216x50 texels = 54x12.5 gauge pixels; the text is added at runtime and the original chain shows below | `plate.png` |
| `frame.bmp` | The menu border, 256x256 with a 20-texel border; corners kept, edges stretched | `frame.png` |
| `titlebar.bmp` | The menu title bar, 48 texels tall with 52-texel stone end caps; the middle is stretched | `titlebar.png` |
| `bacta.bmp` | The bacta tank panel beside the health gauge, 133x128 texels = 33.25x32 gauge pixels; its dark window spans texels 13-115 by 15-110, where the engine draws the textured bacta pickup model and the count | `bacta.png` |
| `force.bmp` | The selected Force power panel beside the right gauge, 136x128 texels = 34x32 gauge pixels; its window spans texels 21-115 by 19-111, with the selected power icon loaded from the player's game | `force.png` |

Sequencer source tiles keep their original Quick arm / Blast padding order. The
engine swaps those two tiles when loading the atlas so Blast padding appears first;
keep that source order when rebuilding this artwork.

## Bacta and Force panels

`source/bacta.png` and `source/force.png` are 1254x1254 RGBA
frames, with dark recessed windows on transparent backgrounds. Their opposing copper
fittings suit the left and right gauges. The engine draws the tank and count, or the
currently selected Force power, inside them at runtime.

`process_ui.py` crops each frame to alpha 128 or more and shrinks it with area averaging
to 128 texels tall, printing its window bounds. Update each panel's accepted dimensions
and drawing bounds in jkRpgMenu.c when replacing these pictures; the Force drawing
expresses its measured texels divided by `PLATE_TEXELS`. A missing or differently sized file uses the engine's drawn frame.

## Processing

`python tools/process.py` and `python tools/process_ui.py` rebuild the shipped BMPs from
`source/` exactly. The icon script finds each black tile, fits the picture into the 22x22
inside of a 24x24 tile, matches every pixel to the colours of the original icons of its
category, and adds the items' one-pixel steel frame. It reads the original icons for their
palette from `JK_ICON_REFS` (PNG copies made from the player's own Res1hi.gob with
`tools/gob.py`; they are not part of the repository). The UI script cuts the plate, frame and
bar out of their magenta backgrounds, and the Bacta and Force panels out of their transparent backgrounds, and shrinks them with area averaging.

To change a picture, supply a replacement sheet with the same tile layout,
add it to `tools/sheets.json`, rerun the scripts, and check the result at real size in the game
next to the game's own icons.

## Official weapon pictures

Weapon headings and the switching strip use LucasArts
weapon artwork from the [archived official Jedi Knight website](https://jkdf2.net/JKBot/JKArchive/JKDF2/JKDF2/Websites/Official%20Jedi%20Knight%20Website/Star%20Wars%20Jedi%20Knight%20Dark%20Forces%20II%20-%20Weapons_files/weapons.htm).
The nine original GIFs are retained under `source/official-weapons/` for reproducible
processing. They are credited to LucasArts/Lucasfilm.
The website has no fist image: that slot uses the first hand mesh of `fistv.3do`, textured
from the player's game files at runtime. It is not extracted or shipped.

`python art/tools/process_weapons.py` removes the separate web labels and olive halo,
keeps each weapon's original colours and aspect ratio, mirrors the bowcaster to point
right, and centres it within its slot. A dark edge separates the silhouette from bright
scenes. The other guns already point right.
Missing, malformed or empty slots fall back to the existing model renderer.

## Character and weapon icons

Athletics occupies slots 8-11, with Quick feet, Quick draw and Grip boots following
its heading. Endurance occupies slots 68-71, with Safer landings, Deep breath and
Stand firm following its heading. Character icons use the green palette.

Run `python art/tools/preview_character.py` from the repository root to check the
atlas dimensions and occupied Character slots. It writes a comparison image to
`art/tools/character-preview.png` showing the icons at 24x24 and at 4x size.
Check the result in the game after changing an asset.

Full spread uses `source/icons-spread-fan.png` in slot 39, with the Blasters red
palette and steel frame. Its explicit single-tile `crop` in `sheets.json` keeps the
bright central trail from splitting the automatic black-background detection.
Run `python art/tools/test_process.py` to check the crop, bounds and resulting tile.
