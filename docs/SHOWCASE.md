# Gameplay showcases

The README uses real gameplay footage. Single-view clips show Rekindled; comparisons
show original OpenJKDF2 gameplay on the left and Rekindled on the right. Original
comparisons use upstream OpenJKDF2 at `9c0844d1`, rather than the 1997 executable.

| File in `docs/media` | Feature | Layout |
|---|---|---|
| `progression.gif` | Leveling and purchasing an upgrade | Single view |
| `balanced-gameplay.gif` | Rebalanced campaign gameplay | Single view |
| `saber-guard.gif` | Manual lightsaber blocking | Comparison |
| `saber-heavy.gif` | Charged heavy swings | Comparison |
| `saber.gif` | Saber appearance and colors | Comparison |
| `civilians.gif` | Cantina, market and plaza crowds | Comparison |
| `setup.gif` | Main menu and settings | Comparison |
| `crosshair.gif` | Crosshair options | Comparison |
| `sky.gif` | Sky movement and distant stars | Comparison |
| `weapons.gif` | Weapon selection display | Comparison |

## Updating footage

Capture from an isolated game profile. Keep camera position, movement, field of view
and display settings matched between comparison views. Do not change gameplay rules
for filming. `tools/capture_showcase.py` provides the capture helper.

Preserve the source colors, playback speed and aspect ratio. GIFs are displayed using
`width="1200"` in the README, allowing GitHub to fit every clip to the same available
width. Review the rendered page at desktop and phone widths after replacing a clip.
The GIF files loop; playback also depends on the viewer's GitHub animation setting.
