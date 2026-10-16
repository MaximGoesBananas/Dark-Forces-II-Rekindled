# Sky artwork

The campaign's nine cloud textures have 1254 x 1254 RGB PNG restorations in
[`jkgm/materials/rekindled-sky/`](../jkgm/materials/rekindled-sky/).
The repeating textures preserve the original palette and cloud layout, except for
`13cnsky2.png`, which uses low-contrast gray overcast. They are not cubemap faces.

## Campaign coverage

`tools/sky_references.py GAME OUTPUT` examines every horizon/ceiling sky surface in
all 25 JK1 campaign maps, decodes all material cels with their sector palettes,
and writes private references, hashes, a contact sheet and `summary.json` to OUTPUT.
Use a budgeted scratch folder; never commit extracted original textures or archives.
Each cloud material has one cel and one distinct decoded RGB image. The two palettes
used by `13cnsky2` produce the same image.

| Replacement | Maps using this artwork |
|---|---|
| `03sky09k.png` | `03katarn` |
| `04sky01.png` | `04escapehouse` |
| `06sky01.png` | `06abarons` |
| `06sky02.png` | `06abarons`, `06bbarons` |
| `09skyb.png` | `09fuelstation` |
| `10sky2.png` | `10cargo` |
| `12sky3.png` | `12escape` |
| `13cnsky2.png` | `15maw`, `17asarris`, `17bsarris`, `18ascend` |
| `14sky.png` | `14tower` |

`00starry` and `00stars2` already use a procedural star field at the rendered
resolution. `00wgril6` is a transparent metal grille in mission 10's shaft, despite
its ceiling-sky flag; it is architectural art and stays unchanged. Another 115
sky-flagged surfaces have no material. There are no omitted cloud cels or palette variants.

## Loading and verification

The existing JKGM loader uses exact material-name/cel mappings in `metadata.json`.
Installers copy this directory beneath `rpg/`; missing files fall back to original
textures. Source material dimensions still control sky scale and authored offsets.
PNG upload alignment supports RGB rows at the native 1254-pixel width.

Run `tools/test_sky.py` with the engine checkout after loader, shader or packaging
changes. It covers projection, texture-size independence, metadata precedence,
missing-image fallback, unaffected materials, RGB row alignment and package contents.
In game, check landscape movement, overhead views, both resolution and FOV
endpoints, and procedural stars.
For artwork changes, also inspect every replacement in its listed map, including
both Barons Hed textures. The extractor's candidate camera positions need live
verification before reuse. Keep ceiling views away from the level's virtual sky
plane: a camera almost touching that plane magnifies a tiny part of any texture.
Reject new texture seams, scale changes, broken colors,
missing textures or shader errors before installation.

The renderer marks only ceiling faces using `12sky3.mat` or `13cnsky2.mat` with `RD_FF_RPG_CLOUD_TILE` and blends
6.25% overlap strips in the RGB texture sampler. The sampler leaves the PNG unchanged;
clouds are 6.7% larger within each repeat. Paletted fallback, other skies and ordinary
surfaces keep their existing sampling. No extra textures or allocations are needed.

`test_sky.py` compiles the actual shader blend body against a discontinuous source
ramp and checks continuity in both axes, negative coordinates and corners, along with
uniform reset on ordinary surfaces. Inspect the reported view at
`warp 0.193638 -3.783750 2.007517 43.145817 122.034088 0`, overhead and reverse views,
and 640x480/1920x1080. Mission 12's fresh autostart ends on a timer; collect the views
immediately after loading and reject screenshots showing the results screen.

### Inspection positions

In an isolated 800 x 600 session, disable AI with `whiteflag 1` and enable fly mode
with the `eriamjh` chat cheat before warping. Look upward if the input update centers
the requested pitch. Use these positions to inspect the artwork:

| Map / texture | `warp` arguments |
|---|---|
| `03katarn` / `03sky09k` | `-0.7645 -4.738 -0.2034 0 -90 0` |
| `04escapehouse` / `04sky01` | `0.53684 -0.28568 1.03 35.25658 -46.13926 0` |
| `06abarons` / `06sky01` | `23.00656 41.21871 2.35 -4.35498 173.12628 0` |
| `06abarons` / `06sky02` | `5.28889 12.63147 1.90006 24.80337 0 0` |
| `09fuelstation` / `09skyb` | `2.29999 5.65 1.125 74.39248 -44.99903 0` |
| `10cargo` / `10sky2` | `-3.11341 14.06251 2.22629 6.33960 89.19245 0` |
| `12escape` / `12sky3` | `1.21159 -8.37512 3.1 35 5.71059 0` |
| `17asarris` / `13cnsky2` | Opening scene; its camera overrides warp |
| `14tower` / `14sky` | `-3.04807 -5.04653 3.03792 80 150.94540 0` |

For a matched original-texture comparison, stop the isolated game and disable both
`bEnableJkgm` in the profile JSON and `r_bEnableJkgm` in the player and root CVAR JSON
files where present. Restart, reproduce the camera, and verify actual saved settings;
a remaining CVAR override can silently re-enable the replacements. Restore all three
settings afterward. Never perform this comparison with the player's own profile.

## Gray canyon overcast

`13cnsky2.png` is a low-contrast neutral gray redesign, replacing pronounced cloud banks
with faint broad atmospheric variation. It is shared by Maw, both mission-16 duels and
mission 17. Its repeat edges use the same overlap sampler as mission 12. The original
material remains the missing-image fallback.

The reported ascent view is `warp 3.624611 -9.041580 -8.079897 0 -170.312439 0`,
looking up about 71 degrees. Check the canyon opening, overhead and opposite views
at 640x480 and 1920x1080, plus the shared duel maps.
