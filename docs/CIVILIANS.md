# More populated civilian areas

The crowd feature adds ordinary people where the campaign already has civilians.
It aims to make bars, streets and workplaces feel inhabited while keeping the
original missions, enemies, dialogue characters and routes intact.

The original game already repeats civilian models. The mod rotates between the
distinct civilian models available in each level and varies their facing direction.
The opening mission has three civilian looks, mission 2 has four, and worker areas
use their existing Ugnaught models. The escaping ship only supplies one worker look.
No character models, textures or scripts are bundled with the mod.

## Population

The initial crowd pass produces these living civilian populations on the mod's
Medium difficulty, before density reduction and the shield-booth correction:

| Mission | Original | With crowds |
|---|---:|---:|
| 1: Nar Shaddaa | 10 | 36 |
| 2: Nar Shaddaa | 5 | 15 |
| 5: Barons Hed | 34 | 102 |
| 9: Fuel station | 32 | 64 |
| 15: Escaping ship, either story branch | 3 | 9 |

Mission 9 uses one added civilian per original before the local density limit.
In dense areas with more than ten living people, 20% of the living count is
subtracted from mod-added civilians, rounded to the nearest whole person.
Original actors are preserved.

These counts cover civilian people and workers, not background droids or story
characters such as Weegee and Jan. Missions without those civilians gain none.
The opening mission has 35 living civilians after placement and density checks.
Patrons occupy the side booths, leaving the counter, window ramps, middle starting
booth and shield pickup accessible. The second enemy starts beyond the far exit.

People are added near existing civilians. The placement checks walkable floor beneath the centre and eight points around the
body, following slopes and allowing a small step. It also checks walls, doors, headroom
and separation from existing objects. Water, scripted floors
and moving platforms are excluded. If a booth or ledge cannot hold more people,
the search uses spare room around another civilian in the same mission. It is
bounded and keeps 32 object and AI slots in reserve for the original gameplay.
Custom levels or unusual saved states may therefore receive fewer additions.

The original bartender and dialogue roles stay unique. Added people use ordinary
civilian behavior; they can react to danger and give no XP when killed. Workers
remain workers instead of being replaced by city pedestrians.

The added patron next to the Barons Hed bartender uses the original `woman1` model,
animations, voice and civilian script.

Ordinary people's autonomous panic run uses speed 1.25 instead of 2.5. Only the AI
Flee instinct for `actor_mn.cog`, `actor_fn.cog`, `actor_pm.cog` and `actor_pf.cog`
receives this reduction. Normal patrols, script-issued movement, workers, merchants,
bartenders, story roles and enemies keep their speeds. The movement multiplier is
applied to the requested run speed, not repeatedly to saved actor values.

## Dark-side balance

The original alignment calculation already scales civilian kills to the population:
its civilian penalty is `100 * civilians killed / total civilians`. Increasing both
the population and the kills threefold leaves that penalty unchanged. The opening
mission's larger crowd is handled by its actual count, without a fixed threefold
discount on top. Force-power choices, the existing +20 alignment offset, the
-100/+100 limits and the story's eventual light/dark choice remain unchanged.

People and workers each contribute 1 to both counters; ordinary droids retain their
original 0.5 weighting. Each new civilian registers through its existing script.
Two stock scripts, `actor_fn.cog` and `actor_gd.cog`, accidentally call the simple
timer with four arguments intended for the extended timer. The engine corrects those
calls, so those civilians enter the population total too. No original game script
is distributed with the mod.

## Saves

Population happens once per mission, tracked in saved inventory bin 137. Saving and
loading preserves added people and their positions. The marker clears on entering
the next mission. Population counts use bin 138, and whole-body support checks use
bin 182. Compatibility handling preserves original actors, earned XP and purchases.
Unsupported additions move only when a reachable, unoccupied supported position is
available. These checks are idempotent and do not count removals as civilian kills.

## Clothing variety

Ordinary civilians, workers and
the four most common clothed enemy types each have a few subtly recoloured versions of
their original outfits. Only clothing changes: faces, skin, hair, hands, gear and
weapons keep their original art, and every model, animation and outfit design stays.

| Group | Templates | Placed in the campaign | Looks |
|---|---|---:|---|
| Gran | reeyees, reeyeesfist, reeyeesgun, reeyeescw, reeyeess | 120 | original, dark brown, khaki, olive tunic |
| Tusken | tuskan, tuskangun | 75 | original, ash grey, rust, dark umber wraps |
| Gran bounty hunter | reeyeesbh, reeyeesbhfist, reeyeesbhgun | 64 | original, dark green, dark brown, dark plum |
| Tusken bounty hunter | tuskanbh, tuskanbhgun | 63 | original, dark brown, dark blue-grey, dark olive |
| Civilian | man1, man2, woman1, woman2 and their n/m variants | | original, muted red, sage, dusty blue, ochre |
| Worker | ug, ugsit, u2 (Ugnaughts) | | original, grey, blue-grey, olive overalls |

Counts are placed enemies in all 25 maps of both story routes on the mod's Medium
difficulty (`tools/campaign_xp.py` rules). Stormtroopers (473 placed), Imperial officers,
commandos and every other Imperial type are deliberately excluded, as are droids,
creatures, bosses, Greedo, the bartender and other story roles.

Each type keeps its identity. Ordinary Gran keep a warm leather tunic, so they never
read as bounty hunters; both bounty-hunter types stay at their original darkness. Every
recoloured texel keeps its original brightness, so folds, seams and patterns remain,
and its colour moves at most 60% (civilians 30-35%) toward an earthy tint.

A person's look follows the GUID saved with that thing, so it stays the same after
saving, loading, restarting the level or loading from another level. Corpses keep the
look of the living actor. Added crowd civilians are created in the same order on every
fresh mission start and therefore keep their looks too. Nothing is stored in saves.

The recoloured textures are copies of the player's own loaded game materials, converted
in memory when a level loads; no textures are shipped. Barons Hed, with every group,
prepares 248 clothing pieces (about 1.5 MB of textures) in about 1-2 ms. Copies are
freed with the level. The software renderer and texture-pack replacements keep the
original art.

## Verification and showcase

Run `python3 tools/test_crowds.py ~/src/OpenJKDF2` in WSL for population limits,
saved-marker behavior, exclusions and failure cases. Run the progression check too,
because the population marker shares the RPG inventory registration and restore path.
Run `python3 tools/test_morality.py ~/src/OpenJKDF2` for the timer correction,
proportional alignment, normal timer behavior and one-time old-save repair.
Run `python3 tools/test_outfits.py ~/src/OpenJKDF2` for clothing variety: the covered
models, Imperial and story-role exclusions, skin and gear materials, the GUID-based look
choice, preserved brightness and dark bounty hunters. In the game, `outfitinfo` lists every
dressed actor and corpse with its look in the engine log; compare it after quicksave/load,
a fresh restart and a load from another level. `outfitinfo off`/`on` switches the colours
for a same-scene comparison and is not saved.

Build the background engine, enter each affected map, run `crowdinfo`, and verify
the counts above in `~/jktest/engine.log`. The command also writes civilian positions
for placement review, including `supported` and `authored` flags.
For new populations every added civilian must have `supported=1`; original placements
are reported but never repaired. Load a saved old population, record how many unsupported
additions move, and reload twice to verify positions, counts and marker 182 stay stable. Check both ship branches and a mission without civilians.
Quicksave and reload twice: the living count must remain unchanged and the log must
not report another population pass for a save that already contains the marker.
Load a pre-feature save separately to check the one-time addition. Inspect screenshots
and walk through the bar/nearby exits; synthetic tests do not exercise collision geometry.
Verify that the opening bar's shield pickup, side booths and exits remain accessible.
Saving and loading twice must preserve positions, living population and alignment
counters. Killing a civilian increases bin 72 by one without increasing XP or bin 73.
