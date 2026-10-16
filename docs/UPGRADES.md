# Upgrade guide

Player progression uses numbered levels. The menu is headed Upgrades.

Upgrades affect weapon handling, movement, survival and exploration. Each branch
offers three purchases, allowing different builds across campaign playthroughs.

The Bacta panel has a metal frame. A matching panel to the left of the right
gauge shows the currently selected Force power from the original game icons, without
changing its rank, energy cost or effects. It switches to grayscale while preserving its brightest color channel, so blue and red icons stay readable. This applies while that power cannot be
used: not enough Force energy, or the power is already running (such as Speed). It stays hidden before Force is learned.

Health, shields and XP share one integrated HUD: the familiar health gauge combines
survival information with a gold outer arc showing progress toward the next level.
The green inner shield arc fills along its length in proportion to the shield limit.
A gunmetal nameplate on top of the gauge shows "LEVEL n" in gold; while points are
waiting it shows a pulsing arrow and the key that opens the menu instead ("SETUP" when
the menu key is unbound). The wider steel plate leaves the original copper chain visible,
with room between the arrow, lettering and window edges.

A small riveted copper panel to the right of the gauge, level with its bottom, shows the
game's own bacta tank icon (loaded from the player's install) and the number carried,
0 to 5, in its dark window. With no tanks the icon and count are dimmed and the frame darkened. **Use Bacta Tank** (R by
default, rebindable in Setup > Key bindings) uses one tank through the tank's original
script, so it does nothing at full health; tanks are left out of Next/Previous Item.
The legacy Next Item binding on ] is retained but hidden from Setup. Older profiles
get R for the bacta key when R is unused or is one of several Next Item keys
(the original R/] pair); R on anything else stays.
The pickup message adds "Press <key> to use a bacta tank." for the playthrough's first
tank, and for a tank picked up at 25% health or less until the key has been used, at
most once every 30 game seconds. An unbound key says to bind Use Bacta Tank in Setup.

The presentation improvements also include distant space skies: the Nar Shaddaa missions
and escape from 8t88 have finer stars that remain fixed in the distance as you move.
All nine campaign cloud backgrounds have higher-resolution restorations that preserve
their original colors, cloud patterns, and atmosphere. Landscape skies project from world directions, so
looking up no longer drags the clouds with the crosshair; a blended cap avoids distortion overhead.
Mission 12's repeating cloud edges blend smoothly.

Ordinary civilians, Ugnaught workers, Gran, Tuskens and their bounty hunters also have
subtle clothing colour variants. This is cosmetic: upgrades, enemy abilities, skin and
gear stay unchanged; Stormtroopers and other Imperials keep their original appearance.

Switching weapons briefly shows a centered gold strip of owned weapons, their current
key bindings, ammo counts and the selected weapon name. The icons use the original
official website weapon pictures, cleaned and facing right, with original models as fallback.
The fists use the game's textured hand; the Bryar reads "Unlimited", and fists/lightsaber read "Melee".
Full spread's icon shows seven bright bolts fanning outward in the red/orange/yellow
blaster palette, with thick trails that remain visible at menu size. The actual volley
still fires in a horizontal row.
The vertical FOV defaults to 90 degrees, with a bounded 70-100 range in Setup. Cutscenes follow the music
volume independently of the effects setting. Rahn's in-game narration follows the effects
slider without the local mixer's extra 25% attenuation, a 2.5 dB increase.
Mute still works; recordings and dialogue timing are unchanged.

The lightsaber color slider runs green, blue, purple, yellow, then red. Green remains
the original default. Blue keeps the original blade shape and white core, with a stronger
blue gradient; existing saved color choices remain the same.

## Points, branches and the menu

Setup's Autosave slider offers Off or 1-15 minutes, defaulting to 5 minutes of gameplay.
The bottom controls remain visible when moving the mouse between settings.
Autosaves follow the selected gameplay interval, including combat, low health,
swimming and backtracking. Menus, cutscenes, death, level transitions and a pending
save/load pause saving; an overdue save runs when normal gameplay resumes.
Loading a save or changing the interval starts a fresh timer.
The separate Autosave entry in Load Game replaces only the
previous timed autosave; quicksave and level-start saves remain separate. Failed
writes keep the last good autosave and retry after 30 seconds.
Restarting after death loads the save you made or loaded last, as in the original game;
a timed autosave counts once it is written. Loading or making a quicksave after an
autosave makes that quicksave the restart point, so dying never skips ahead to the
autosave's progress. An autosave older than the latest level-start checkpoint is
ignored. If the autosave is missing or cannot be loaded, the save before it and the
level-start checkpoint remain available as fallbacks. F9 continues to load your quicksave explicitly.

Fresh profiles use left-click for primary fire and right-click for secondary fire;
Space jumps. Existing custom bindings remain as saved. Resetting mouse controls restores
these same defaults.

A brief yellow screen flash accompanies a level-up and fades through the normal
damage/pickup effect system. Multiple levels from one XP award produce one flash.

There are 18 upgrade branches with three upgrades each: 54 upgrades in total. You get one
point per level; levels run from 1 to 40, giving 39 points. Level 2 costs 100 XP; later
levels cost 200, 205, 210 XP and so on through level 10. From level 11, costs rise more steeply
(246, 265, 282 ... 769), reaching level 40 at 17,117 total
XP. Either route offers 17,296 XP, including the added mission-17 and mission-19 troopers.
Kills give enemy maximum health / 5 XP, at least 5. In missions 1 and 2, kills give 60%
of that, rounded down, before the minimum of 5. Bosses give fixed amounts: Yun 200
(mission 7), Gorc 300 and Pic 200 (mission 11), Maw 400 (mission 14), Sariss 600 (mission
16, light route), Yun 600 (mission 16, dark route) and Boc 500 (mission 20).
The timed escape in mission 15 gives no XP on either route. Stormtroopers in missions 17-19 give 2 extra XP each. Jerec, the final boss, gives no XP
because the game ends with his duel. The level-up fanfare stays silent in
these duel missions because the boss's death already plays the game's goal sound; the
message and point still arrive. Existing saves preserve XP, levels, points and purchases. If a saved level exceeds
the level implied by its XP, the next level waits for the matching threshold.
Easy flying creatures give 5 XP per player-credited kill, including mission 3's ten
creatures (50 XP for a full clear).
Bowcaster Tuskens give 15 XP instead of 10/12. Enemies that the original level scripts used
to bring back endlessly (missions 1, 2, 13 and 17) no longer return; enemies outside
the timed escape still give XP. See [Progression](PROGRESSION.md) for
campaign timing. The three upgrades of a branch are
bought in order, each adds to the ones before it, and each branch can take only one
point per mission. Even at level 40 a player owns 39 of the 54 upgrades, so a replay
can try a different build. Existing saves retain their earned levels and points.

The menu (K by default; rebind **Upgrade Menu** in Setup > Key bindings) pauses the game.
It is a skill tree with one page per category, in this fixed order:

| Category | Branches |
|---|---|
| Character | Health, Shields, Athletics, Endurance |
| Supplies | Scavenger, Field Medic, Bacta tank, Field light |
| Blasters | Bryar pistol, Stormtrooper rifle, Bowcaster, Imperial repeater |
| Heavy weapons | Thermal detonators, Rail detonator, Sequencer charges, Concussion rifle |
| Jedi | Lightsaber, Force |

Each branch is one row: its heading picture and name, then its three upgrades as framed
pictures joined by a line that turns gold once owned. Below the rows, the selected branch
lists all three upgrades with their gameplay descriptions and Owned, Next or Later.
Descriptions explain effects without numbers; the values are recorded below.
Up/Down or W/S choose a branch; Left/Right, A/D, Q/E or Tab change page; Enter or Space
buys the next upgrade or takes back one bought since the menu opened. Closing the menu,
earning a point or starting a mission locks purchases in. An upgrade waiting for the next
mission shows a small lock, and the selected branch explains it.
See the [Character page](showcase/upgrade-menu.png) and the
[Blasters page](showcase/weapon-upgrade-preview.png); the artwork and its references
are recorded in [Upgrade menu artwork](UPGRADE-ART.md).
The border remains visible at 640x480. The three firing-rate upgrades use distinct trigger,
mechanism and accelerating-fire pictures; the saber pictures separate blue blades from red bolts.

### Discovery

General skills (Health, Shields, Athletics, Endurance, Scavenger, Field Medic) are always
available.
A weapon's or item's branch unlocks when the player first holds it; starting equipment
counts (fists are not upgradeable; the Bryar and field light are available from the
start). Force unlocks with the story's Force powers. The game remembers obtained equipment
in the save, so a branch stays after ammo runs out or an item is used, and across saves
and missions. Finding gear only opens choices; it never buys an upgrade.

Sequencer charges are the exception: their branch also opens at the start of mission 4,
the first mission with armed proximity charges, even without owning charges. Blast padding
is first, allowing one point to buy protection before reaching the traps. Discovery
persists normally; it grants no ammo or free upgrade. All other equipment keeps its
first-acquisition rule.

The menu hides undiscovered equipment entirely, and a category page has no tab and no
keyboard stop until one of its branches is unlocked. The Field light branch uses the field light icon.

### Save compatibility

Loading preserves purchased upgrades, unspent points and mission purchase limits.
Compatibility conversions refund only replaced purchases and run once per save.
Inventory amounts above carrying limits are clamped without changing purchases.

## Upgrades

| Branch | First upgrade | Second upgrade | Third upgrade |
|---|---|---|---|
| Health | Vitality: 125 maximum health | Vigor: 150 maximum health | Slow regeneration: 0.5 health per second after three seconds without health or shield damage |
| Shields | Blast resistance: explosions drain 25% fewer shields | Better recharging: shield recharges give 18 instead of 12 | Stable protection: full absorption of blaster and explosion damage until shields run out |
| Athletics | Quick feet: the original movement speed instead of about 13% slower | Quick draw: weapons holster and draw in half the time | Grip boots: roughly halves stopping time after running |
| Endurance | Safer landings: 50% less ordinary landing damage; deadly falls stay deadly | Deep breath: +25% underwater air time and 50% less drowning damage | Stand firm: explosions and weapon hits push you half as far |
| Scavenger | Emergency supplies: +25% of the original amount when that ammo supply is below 25% | Weapon salvage: +25% from weapons dropped by enemies | Better scavenging: ordinary ammo pickups give 100% instead of 75% |
| Field Medic | Emergency care: +5 health from packs below 25% maximum health | Better treatment I: packs restore 18 instead of 15 | Better treatment II: packs restore 20 |
| Bacta tank | Stronger treatment: 30 immediate health | Lasting recovery: another 20 health over six seconds | Automatic treatment: a carried tank is used after a hit leaves you below 25% maximum health; 10-second cooldown |
| Field light | Supply finder: nearby visible pickups glint while the light is on | Extended illumination: 50% farther light reach | Power efficiency: half the battery drain |
| Bryar pistol | Hot bolts: +25% damage | Focused bolts: half the damage loss over distance | Quick trigger: +25% firing rate |
| Stormtrooper rifle | Accelerated bolts: +25% projectile speed | Stabilizer: half the spread | Rapid cycler: +25% firing rate |
| Bowcaster | Strong draw: +25% damage over its reduced base | Fast charge: charge in half the time | Full spread: a full charge adds a bolt outside each edge of the spread |
| Imperial repeater | Cell recycler: every fourth projectile is free | Accelerated rounds: +25% projectile speed | Sustained fire: holding the trigger raises the firing rate to +100% |
| Thermal detonators | Safer handling: half damage from your own detonators | Bigger charge: +25% blast radius | Double throw: two detonators at once |
| Rail detonator | Booster rockets: +25% projectile speed | Autoloader: +25% firing rate | Cluster warhead: smaller follow-up blasts around each explosion |
| Sequencer charges | Blast padding: take less damage from sequencer explosions | Quick arm: +50% placement rate | Charge recovery: proximity charges ignore you and can be picked up |
| Concussion rifle | Safer blasts: half damage from your own concussion blasts | Efficient chamber: 25% cheaper ammo | Wide shockwave: +25% blast radius |
| Lightsaber | Blaster protection: a quarter less blaster damage while drawn | Accurate deflection: a longer timing window for sending bolts straight back | Quicker recovery: the guard returns 0.25 instead of 0.5 seconds after a swing |
| Force | Deep reserves: +25% Force capacity | Steady recovery: +25% natural Force recovery outside Persuasion | Inner calm: +50% natural Force recovery in total outside Persuasion |

A 25% firing-rate increase means 1.25 times as many shots per second (delay divided by
1.25). Damage and protection changes that affect the player apply before shields absorb
a hit, so they protect both shields and health, and never change damage to enemies.

### Weapons

Fists, the Bryar pistol and the stormtrooper rifle use primary fire only; their
duplicate secondary attacks are disabled. All other weapons keep their distinct
secondary modes. Fire bindings stay configurable, and primary fire is unchanged.

Weapon headings and the switching strip use cleaned official weapon artwork in its original
colours, with right-facing guns. Fists use the textured game model; model icons also provide
a fallback when artwork is missing or damaged.

Each weapon keeps the mod's adjusted base: the Bryar has unlimited ammo, deals 60% of the
original damage and converges on the crosshair in first person; the stormtrooper rifle
fires 25% slower and hits 25% softer; the repeater fires 1.5 times slower and hits 15%
softer; the rail detonator fires 1.6 times slower and the concussion rifle 1.25 times
slower. Rail detonator ammunition is limited to 10, including when loading older saves.
Without upgrades, ammo packs and enemy launcher drops average 1.125 rockets
(usually 1, occasionally 2); placed launchers average 2.25 (2 or 3).
Fractional rockets accumulate across pickups rather than being lost.
Mission 18 (the Valley descent) also halves power cells from pickups, including
enemy weapon drops and Scavenger bonuses. These cells are shared by the concussion
rifle, bowcaster and repeater. Held ammunition is not reduced. Without Scavenger,
dropped repeaters give 4 or 5 cells instead of 9, carrying the fractional remainder
between pickups during play.
The main menu opens New Game and Load directly, and cancelling Load returns there.
The bowcaster's base damage is 25% lower than the original game for both modes and all bolts.

- **Bryar pistol:** damage goes from 0.6 to 0.75 of the original. Focused bolts halve the
  loss at every flight distance: the bolt's 30 damage falls toward 20 instead of 10, at
  half the rate. The damage bonus applies to the resulting damage. Quick trigger: 0.5 to
  0.4 seconds between shots.
- **Stormtrooper rifle:** each shot shows a brief red flash at the muzzle. Projectile speed 6 to 7.5; spread +/-2.5 to +/-1.25 degrees on
  each axis; 0.267 to 0.213 seconds between shots.
- **Bowcaster:** while it charges, a green light grows at the barrel's tip and pulses at a full
  charge (Fast charge and Full spread change how soon it is full). Close-range centre/alternate bolts deal 45 before upgrades and 56.25 with
  Strong draw; side bolts 30 and 37.5. Fast charge halves the charge thresholds (0.6/1.2 to
  0.3/0.6 seconds); the recovery delay and alternate fire are unchanged. Full spread
  keeps the original horizontal row at 0, +/-6 and +/-12 degrees, adding an outer
  bolt at each side (+/-18 degrees). Each bolt in either fire mode also varies by
  up to two degrees per axis, reducing reliable long-range hits. Stages: tap, centre;
  0.3 s, inner pair; 0.6 s, original outer pair; 0.9 s, added pair. A full volley still
  costs seven cells (2, 2, 2 and 1), including when exactly seven cells remain.
- **Imperial repeater:** Cell recycler counts projectiles, not trigger pulls, across main
  and alternate fire (the count is not saved). Sustained fire ramps linearly over one
  second of held main fire, from the mod's normal 0.15 seconds between rounds to 0.075;
  releasing the trigger resets it. Alternate fire is unchanged.
- **Thermal detonators:** the carry limit is 10. Player throws launch along the aim
  direction, removing the original 36.87-degree upward offset that could send steep
  throws backward. Gravity still curves the flight; charge strength, impact/timed
  modes and collision behavior are unchanged. This also applies to Double throw.
  Enemy throws keep their original trajectories. Safer handling halves your own blast
  damage. Blast radius 0.45 to 0.5625 world units without more peak damage. Double throw
  releases a second real detonator with the same throw strength and impact/timed mode,
  the two turned 3 degrees apart each way, consuming two. With one left, it is thrown
  normally.
- **Rail detonator:** projectile speed 2.5 to 3.125 in both modes; 1.6 to 1.28 seconds
  between shots. Cluster warhead adds four small blasts 0.15, 0.25, 0.35 and 0.45 seconds
  after impact and sticky detonations, each about 0.3 units out in a random direction
  (walls stop them), with 30% of the main damage and 60% of its radius. They use the game's
  small debris explosion, are credited to the player, do not hurt the player and never
  start further clusters.
- **Sequencer charges:** 0.8 to 0.533 seconds between placements. Blast padding cuts
  damage from sequencer explosions by 65%; shrapnel from
  mines is not counted as a sequencer explosion. Charge recovery: you never set off an armed
  proximity charge; touching one recovers it as a usable charge, subject to the carry limit
  of 10. At full capacity the mine stays and still ignores you. Other actors, gunfire and
  explosions trigger mines normally, timed charges still explode, and a mine already set
  off behaves normally. Recovered charges are added directly, never through a pickup, so
  Scavenger bonuses cannot turn mines into ammunition.
- **Concussion rifle:** primary fire only; secondary fire is disabled. Shots vary randomly
  by up to +/-2.5 degrees in pitch and yaw after auto-aim. Safer blasts halves your own
  blast damage. Efficient chamber reduces each shot from 8 to 6 power cells, allowing
  firing with exactly 6 cells. Wide shockwave increases blast radius from 0.8 to 1.0
  world units without more peak damage.
- **Lightsaber:** click primary fire to swing; the swing starts on release. Holding
  primary fire draws the saber back over one second; releasing it after that swings
  heavy (100 damage instead of the original 160) with its original two-second recovery
  and reach, continuing from the drawn-back pose. A successful enemy guard reduces the hit
  to 60 base damage instead of stopping it. Hits outside the guard's front arc or when
  the guard fails retain 100. The usual campaign-boss bonus makes those hits 90 and 150
  (75 and 125 against Maw, 120 and 200 against Sariss).
  Releasing earlier is a normal swing. Normal swings keep their original damage. Holding secondary
  fire raises a guard instead of the original automatic blocking. It covers about 75
  degrees to either side of where you face and stops blaster bolts and saber blows,
  but drops while attacking, charging or recovering. Blocked saber blows strain the
  guard: their damage adds up, recovering 10 per second, and 100 breaks the guard for
  1.5 seconds. Calm light blows take about half a minute; quick heavy blows break it
  within three to five. Explosions, Force powers and attacks from the sides or behind
  still hurt.
  Blaster protection cuts blaster shots that get through by a quarter while the saber is drawn.
  A guard raised at most 0.5 seconds before a bolt arrives sends it straight back to
  its shooter with 50% more than its original damage, kept for the whole flight back; Accurate deflection widens that window to 0.8 seconds. A guard that was
  already up glances the bolt 20-45 degrees aside instead, and the bolt strains the guard
  by its damage like a saber blow; a timed block costs nothing. Under steady fire from one
  stormtrooper-class gunman, a held guard first breaks after about eight seconds.
  Quicker recovery raises the guard 0.25 instead of 0.5 seconds after a swing starts.

#### Campaign proximity-mine count

A static inspection of the installed JK1 campaign, using inherited template
properties and the mod's Medium/single-player placement filters, finds:

| Mission | Pre-placed armed proximity charges |
|---|---:|
| 4 | 3 |
| 6 | 14 |
| 13 | 13 |
| 15 | 9 |
| 17 | 1 |
| Total per campaign route | 40 |

Both light and dark versions of mission 15 contain nine; do not add the two
routes together. Other missions contain no pre-placed armed proximity charges on
this setting. Exclude ammo pickups, difficulty-excluded mines and player-deployed
mines. The campaign script scan found no additional enemy mine-spawning scripts;
this is a level-data count, not a guarantee that every mine survives until reached.
Charge recovery therefore offers situational trap bypass and potentially up to 40
recovered charges if bought before all placements and enough inventory space remains.

### Skills and items

- **Health:** maximum health 100, 125, then 150. Slow regeneration restores 0.5 health
  per second while alive and below maximum, after three seconds without health or shield
  damage. Each damaging hit restarts the delay, including hits absorbed entirely by shields.
  The remaining delay is saved, and pauses with the game. Fractions carry over across frames.
  Health packs, bacta and Force Healing treat the upgraded maximum as full.
- **Shields:** the limit stays 100 at every rank. Blast resistance makes explosions cost
  25% fewer shields for the same protection; without shields the hit is unchanged.
  Better recharging applies only to regular shield recharges (12 to 18); armor vests,
  Super Shield, backpacks and Revive keep their 60% share. Stable protection removes the
  original weakening below 50 shields for blaster fire and explosions: remaining shields
  absorb those hits fully and only the excess reaches health. Saber and other damage keep
  the original shield rules.
- **Athletics:** Kyle's movement thrust starts at about 1.74 (the original 2.0 divided
  by 1.15, about 13% slower) for running, walking, crouching and swimming alike; Quick
  feet restores the original 2.0. Normal jump height is unchanged. Force Speed multiplies
  the current running speed and Force Jump the current jump speed (see Force powers below).
  Quick draw makes all ten weapons holster and draw in half the original time (see
  [Other gameplay details](#other-gameplay-details)); without it switching keeps the
  original speed. Grip boots: when the controls are released on a normal floor while
  moving at 85% or more of top running speed (Force Speed included), surface drag is twice
  as strong until Kyle stops, reducing stopping time by roughly half.
  Taps, short runs, walking and anything slower keep the original slide, as do
  later pushes once he has stopped; jumping and movement in the air are unaffected.
- **Endurance:** Safer landings halves landing damage ((impact speed - 2.5)^2 * 45) on
  floors only, below the original 100-health lethal threshold; harder landings, wall and
  ceiling impacts and scripted death floors (1000 damage) are unchanged. Deep breath gives
  the original 20 seconds underwater before drowning starts, instead of the reduced
  base reserve of 16 seconds, and halves drowning hits
  from 10 health to 5. Hits retain their two-second interval; surfacing restores the air
  reserve. It grants no permanent underwater immunity. Stand firm halves the push the
  player receives from explosions and weapon hits; damage is unchanged, and enemies and
  other objects are pushed as before.
- **Scavenger:** ammo pickups give 75% of the original amount, 100% with Better
  scavenging. Emergency supplies adds 25% of the original amount when the receiving ammo
  supply is strictly below a quarter of its limit before collection. Weapon salvage adds
  25% for weapons dropped by enemies (the game's "+d" drop templates, which only enemy
  death scripts create; a pickup keeps its template through saves). Bonuses add: an
  original 20-ammo pickup gives 15 unupgraded, 20 with Better scavenging; an enemy weapon
  gives 20 with Weapon salvage and 25 with all three, plus 5 when ammo is low. Leftover
  fractions carry over per ammo type. Rocket gains, including these bonuses, are halved.
  Health, shields, bacta and batteries are not ammo.
- **Field Medic:** health packs restore 15, 18 with Better treatment I and 20 with Better
  treatment II; Emergency care adds 5 when health is strictly below a quarter of the
  maximum before collection (20, 23 and 25). Packs are only taken below full health.
- **Bacta tank:** 18 immediate health unupgraded, 30 with Stronger treatment; Lasting
  recovery adds 20 over six seconds. Automatic treatment uses one carried tank after a
  damaging hit leaves the player alive and strictly below 25% of the current maximum,
  evaluated after shields and every reduction, applying both owned healing upgrades. It
  cannot prevent a fatal hit. The 10-second cooldown runs in game time from a successful
  use, pauses with the game and is kept in saves along with any healing still to come.
  After it ends another qualifying hit is needed. Manual use with the bacta key is
  unaffected and does not reset it. The carry limit stays five.
- **Field light:** Supply finder draws a small pulsing gold glint on pickups within 2.5
  units that the player can see while the light is on and has power. Walls, closed
  doors and solid objects hide them; only collectable models drawn in the view qualify.
  Extended illumination extends the field light's reach by 50% without increasing its
  source brightness, changing other lights or compounding across frames/save loads.
  Battery pickups restore the original 25 power, up to 200. Power efficiency halves
  drain, giving about ten minutes of light from a full supply instead of five.
  Goggles are removed from inventory and all eight campaign placements (missions
  1, 2, 4, 5 and 6). Each location retains other rewards in the same or adjoining area.
  Existing active goggles shut down through their original script, clearing their
  tint and drain while preserving Force Seeing and the battery supply.
- **Force:** Deep reserves raises capacity to 1.25 times the story's Jedi rank * 50.
  Natural recovery
  (force_well.cog, Jedi rank / 2 per second) is multiplied by 1.25 with Steady recovery
  and 1.5 with Inner calm, except while Persuasion is active, when the original rate
  applies; the bonus returns when it ends, including after loading. An empty meter refills
  in about 125 seconds with Deep reserves, 100 with Steady recovery and 83 with Inner
  calm (100 in the original). The game's own Force limits (natural recovery, Force
  pickups, the level-start refill and Surge pickups) follow the upgraded capacity, and the
  HUD meter fills at it. Force pickups, Absorb and Surge otherwise follow their original rules.
- **Force Healing** (the original power, not an upgrade) restores 40/45/50/60 health at
  its four power ranks instead of 20/40/60/80, for the unchanged 200 energy, up to the
  upgraded maximum. At full health it does nothing and costs nothing. Field Medic and
  Bacta bonuses do not apply to it.
- **Force powers** (the original powers, bought with the game's Force stars) follow Force
  Speed: each rank adds a modest step, and timed powers mostly gain time. Energy costs are
  unchanged. Values for power ranks 1/2/3/4:
  - Speed: always 1.5 times the current running speed (originally 1.5 to 2.25 times),
    lasting 7.5/10/12.5/15 seconds as in the original.
  - Jump: a tap or full hold reaches approximately 3.0/3.6/4.4/4.9 times normal jump
    height at ranks 1/2/3/4, under normal campaign gravity. These are height ratios,
    not launch-speed ratios. A partial hold gives less boost; the cost remains 20
    Force energy. Existing Force ranks and RPG upgrades are preserved.
  - Seeing, Persuasion, Blinding and Absorb last 7.5/10/12.5/15 seconds (originally
    Seeing 10-25, Persuasion 10-40, Blinding and Absorb 5-20). Seeing still reveals more
    at ranks 3 and 4, Persuasion still flickers less and Blinding still reaches farther with
    rank. Absorb always takes half of Force damage as energy (originally 25-100%).
  - Grip: four squeezes for 40/45/50/60 damage to a stormtrooper (originally 10/40/90/160).
  - Destruction: a 40/45/50/60 blast over 1.2/1.3/1.4/1.5 units (originally 15/30/45/60
    over 0.5 to 2), plus its unchanged 20 on a direct hit.
  - Protection (granted only at full rank, for the light path without dark powers) blocks
    75 damage, fully for 7.5 seconds and then wearing off over 7.5 (originally 300, about
    a minute). Deadly Sight (its dark-path counterpart) burns every enemy in view for 10
    damage twice a second for 3 seconds, 60 in total (originally 240 over 6 seconds).
  - Pull, Throw and Lightning keep their original rules.

Ordinary Force pickups restore 50 energy in single player (pow_mana.cog). On Medium
single player the placed ordinary Force pickups are mission 14: 2, mission 19: 1,
mission 20: 4 on either route, and mission 21: 1 on the light route only: eight on the
light route, seven on the dark route. Separate Surge placements are mission 14 (one Light
and one Dark), mission 16 (one matching the route) and mission 21 light route (one Light).
Counts come from JK1.GOB Things sections with inherited templates and instance flags;
mission numbers follow episode.jk. Persuasion keeps its original cost of 250 energy and lasts
7.5/10/12.5/15 seconds by power rank; at story Jedi rank 8 it allows 4 energy per second while
invisible instead of 6. The larger pool still allows more uses than the original.

## Gameplay showcases

See the [project page](../README.md) for progression clips and comparisons with the
original game, and the [installation guide](INSTALLING.md) for launcher instructions.

## Other gameplay details

Campaign bosses take 50% more damage from the player's attacks, effectively reducing
their durability by one third while keeping scripted health thresholds, healing and
saved health intact. Their melee and saber hits deal 25% more damage to health.
Force attacks retain their existing damage. This applies to Yun, Gorc, Pic, Maw,
Sariss, Boc and Jerec, including both campaign routes.
Maw takes 1.25 times original player damage and has 10% greater pursuit thrust.
His three scripted stages use their original health thresholds.
Sariss takes twice the original player damage and uses 1.625 times the original
pursuit thrust. Her saber and melee hits deal 1.5625 times original health damage
after shields. Her Force damage is unchanged. Her 600 XP reward grants at most
one level from level 31 onward.
Pic takes 5/3 times original player damage without changing scripted health.
Sariss checks normal saber attack decisions every 250 ms; Boc and Jerec check every
375 ms. These delays do not change swing recovery, attack distance or blade reach.

The canyon sky shared by Maw, Sariss/Yun and the ascent uses low-contrast gray overcast
with softened tile edges, avoiding prominent painted cloud shapes overhead.

Yun's "better than I thought" line in his first duel (mission 7) plays once, when he falls to
half health. The original played it the first time he used a Force power while Kyle had under
50 health, often as the duel began. His Force Blinding, in both duels, darkens the world view
for its five seconds instead of whitening it and ends without a white flash; the HUD keeps its
normal colours.

Solid campaign windows show translucent glass from inside, using the original
texture, so they no longer look like open passages. This includes the control-room
window in `12escape.jkl`, which originally had no texture on either side, and the
observation window in both routes of mission 15. The latter gains glass on its missing
inside face while retaining its authored outer wall. Existing saves receive the change.

Mission 10's elevator officer is removed, including from existing saves, so he cannot
block the lift. He has no mission-script or unlock role.

Mission 4's reservoir encounter has one fewer rifle guard: the gunman on the ledge
opposite the approach walkway. The melee guard and other nearby actors remain.

Mission 6 has three AT-ST walkers instead of five: the two that patrol the open courtyard
are taken out of the mission, including in saves where they are still alive. The other
three give their XP: 133, 133 and 134 instead of 80 each, so the mission still totals
2,482 XP. The level's own scripts keep working, because the two walkers stay disabled in
place rather than deleted.

Mission 6's tower squad, the stormtroopers gathered behind the stair hall's third door
that rush out together, has at most eight instead of ten, including in saves where all
ten are waiting. These troopers are created by the level script and were never part of
the placed-enemy XP totals.
Normal Windows launches open no command window; `-console` enables it for debugging.
If the game crashes, a short note in `rpg/reports/crash-log.txt` records where it broke and in
which level; the file is trimmed so it stays under 32 KB.

Setup uses a 1.0-10.0 sensitivity slider, from slow to fast, with 0.1 steps.
New and reset mouse controls start at 5.0. Existing profiles retain their current
mouse response until the slider is changed; opening Setup does not round their
saved values. Click the slider and use the left/right arrow keys for fine adjustments.
The mouse's hardware DPI also affects physical turning speed.

G toggles the field light. It reports "Battery empty. Pick up a battery to recharge."
when no charge remains. The key can be rebound; older profiles receive G when free
or when it is a spare Next Weapon key. Bacta stays on R. Next item, Previous item,
Use item, multiplayer scores, redundant direct item shortcuts and the ambiguous
combined skill/item action are hidden from remapping. Saved bindings are retained.
Force selection, Force use and other useful weapon controls remain available.
An occasional reminder shows the currently assigned key. General reminders stop
after a successful use; before that, battery pickups can remind you at most once
every two minutes. Mission 3 also gives one reminder at the mansion entrance,
even if the key has been used before. Entering with the light already
on quietly satisfies that reminder. Its state persists through saves and reloads.
An unbound action points to Setup instead.

The fists key (1 by default) selects fists until the lightsaber is acquired. Once
available, it prefers the lightsaber when switching from another weapon; pressing
it again switches between the saber and fists. Fists remain available, and the
existing direct lightsaber binding still works. The weapon display follows the
shared key's current binding.

Close-range object collision keeps the nearest valid hit distance, fixing Bryar
shots that could be diverted away from an aimed barrel.

The added woman obstructing mission 2's cargo walkway is removed, including in
older saves. Nearby civilians remain, and removal does not count as a kill.

The Barons Hed supply alcove has an open walking route out: its lower right wooden
crate is removed without an explosion. The repair also applies when loading an
existing save. The remaining stacked crates, supplies and level geometry stay intact.

The chosen crosshair appears in first and third person. Third-person lightsaber use
hides it; Off and existing first-person crosshair preferences still apply.
Small, Dot and Circle use the selected color without a dark outline. Circle keeps
its smooth edges; Classic keeps its original shape.

Setup's **Weapon switcher HUD** checkbox controls the brief weapon reminder. It is
enabled by default, remembers the choice between sessions and does not change weapon
selection or key bindings. OK and Escape keep the choice; Cancel discards it.

Weapons holster and draw at the original speed until Athletics' Quick draw is bought.
With it, all ten weapons holster and draw in half the original time; their first- and
third-person animations, script timers and switching lockouts speed up together.
Firing cooldowns, charge/release timing and saber recovery upgrades are unchanged.

Successful lightsaber hits add a brief glowing slash using the original spark material.
It also appears on killing blows and does not change damage or rewards. In mission 4,
Tuskens stranded in the opening reservoir move to supported dry walkway space when
available, retaining their health and rewards. The repair also applies to older saves.

F12 takes an ordinary game screenshot.

Ordinary ranged enemies (stormtroopers, armed Tuskens, Gran, Trandoshans and Rodian gunmen
and grenadiers) and ordinary melee enemies (Rodian brawlers and Gamorreans) notice a
quiet player at half their original visual distance. Hearing gunfire, being
hit, an explicit scripted fire target or existing combat restores the original range.
Droids, wildlife and creatures, bosses and civilians keep their original sight.
Hearing distance, line-of-sight obstruction, combat range and pursuit are unchanged.
Already-alerted enemies in existing saves remain alerted.
Hits from the player wake sleeping ordinary armed enemies and make them turn toward
the shooter and engage, even when struck from behind. Projectile/explosion ownership
identifies the attacker; they do not turn toward the impact point. Walls, firing
range and firing delays still apply. Explicit scripted targets and disabled AI are
preserved, with no changes to civilians, bosses, wildlife or droids.

Enemies look for the player and fire their
first shot in 60% of the original Medium time (for example every 0.3 seconds instead
of 0.5, and a stormtrooper's first shot after 0.18 seconds instead of 0.3). Direct-fire
accuracy closes 75% of the gap to always: a stormtrooper's original 20% becomes
80%. This is the share of shots without added random
aim error, not a guaranteed hit rate; movement and cover still matter. Thrown grenades
keep the original aim. Enemy bolts and blasts do less damage to the player's health,
after shield absorption and protection upgrades, and the share rises through the campaign:
half in missions 1-4 (before the lightsaber), 60% in missions 5-10 (Barons Hed to the
cargo ship), 70% in missions 12-13 (the cargo ship escape and the tower) and 80% in the
final act from the escape ship on. Boss duels keep 75%. A hit that would remove 20 health
removes 10 in the first missions and 16 at the end. Shields still absorb the same amount. Melee, saber, Force, environmental
and self-inflicted damage are unchanged, as are enemy health and pursuit time.
Concussion-rifle Trandoshans, including sentries introduced in mission 9, use a
3.5-second direct-fire pause with 20% timing variation. Direct shots and blind fire
share a minimum 2.8-second cooldown, preventing rapid follow-up shots when they
switch firing behavior. The cooldown uses the existing saved AI attack timer,
which also delays a melee swipe after firing. Damage and knockback are unchanged;
Stand firm halves the knockback. Existing saves receive the fix when loaded.
Other hostile enemies with direct-fire weapons shoot 40% more often: the pause between bursts and
between the shots of a burst is 1/1.4 of the original (a stormtrooper's 2 seconds becomes about
1.4, and 0.5 seconds within a burst about 0.36). Burst size, melee attacks, grenade throws and
turrets keep their original pace.

Enemy detonators hurt a quarter less before shields absorb anything, so they drain shields
and health alike less: the rail detonator's direct hit (20) and enemy rail and thermal
detonator blasts (50 each). A detonator the player sends back with the saber counts as the
player's own. Enemy thermal detonator explosions also deal a further 35% less health damage after
shields and the existing reduction. A full 50-point blast with no shields
deals 24.375 health damage in a boss duel and 16.25 to 26 across the campaign phases. Player-thrown detonators and their
self-damage are unchanged; the thermal carrying limit is 10.

Hostile enemies whose only attack is melee (a primary attack
reaching no farther than 0.5 units and no ranged, lobbed, blind or turret fire, such as
Gamorreans and the bare-fisted Gran) move 10% faster so they can catch up.
Ordinary brawlers stuck directly below a player on a ledge can move away to safe
ground. They wait there while the player remains overhead, then resume pursuit
when the player comes within reach or moves away.

Civilian speech cannot start another copy of a line already playing. This covers
both their actor sounds and scripted touch dialogue, without lowering individual
voice volume or affecting footsteps, enemy calls or story characters.

Dense civilian areas with more than 10 living people are reduced by 20%, rounded
to the nearest whole person. Groups of 10 or fewer stay as they are. Only added
civilians are removed; original characters remain. This happens once in each
mission, including older saves, without counting removals as kills.

Mission 9 targets twice the original civilian population before the local density limit.

The crowd feature adds civilian people, not extra XP targets: killing them gives no XP.
The added patron beside the Barons Hed bartender is a woman, including in existing
saves. Ordinary civilian panic-running speed is halved; normal routes and scripted
movement keep their original speeds, as do workers, merchants and story characters.
Opening-bar patrons use the side booths; the second enemy starts beyond the exit.
The shield-side booth keeps one patron so the shield pickup stays accessible;
the extra man is also removed from existing saves while he is still in that booth.
Added civilians need floor under the whole body. Older campaign saves repair unsupported
added ordinary people where nearby safe space permits, preserving original placements,
story roles and enemies. Their dark-side effect scales with the share of civilians killed; the larger population
is counted accordingly.

Four energy-cell pickups on the ledge behind the window-side table provide extra
stormtrooper-rifle ammo. They use the normal pickup behavior, including Scavenger.

The tower level's wall shelf near (12.25, 8.6, 2.63) has two bacta tanks instead of four.
Both tanks on the upper shelf near (7.75, 12.82, 5.63) are removed.
These removed pickups stay removed in existing saves; collected supplies are not restored.

Ammunition carrying limits apply to pickups, recovered mines and existing saves:

| Ammunition | Weapons | Carry limit |
|---|---|---:|
| Energy cells | Stormtrooper rifle | 200 |
| Power cells | Bowcaster, repeater, concussion rifle (shared) | 100 |
| Rail charges | Rail detonator | 10 |
| Thermal detonators | Thermal detonator | 10 |
| Sequencer charges | Sequencer charge | 10 |

Loaded saves above these ceilings are trimmed, without refilling lower supplies or changing upgrades.
The Bryar remains unlimited. No upgrade raises these limits. Scavenger's low-ammo
threshold stays below one quarter of the current capacity: below 50 energy cells,
25 power cells, 2.5 rail charges or 2.5 thermal detonators/sequencer charges
(so 0-2 whole explosives). Full supplies leave ammo
pickups in the world; acquiring a weapon you do not own still works at full ammo.


### Save reliability

Loading clears temporary saber guard and wind-up poses, including in older saves.
Saving handles empty body and first-person animation tracks. A failed or interrupted write preserves the previous save.

### Display sizing

The desktop window starts borderless at the primary monitor's current resolution.
Upgrade menus keep their proportions on 4:3, 16:9 and ultrawide screens.
Fresh/reset profiles choose a HUD scale from screen height, rounded to 0.25 and
clamped to Setup's 1-4 range (2 at 1080p, 4 at 2160p). Saved HUD choices still win.

Mission 17 adds six ordinary blaster stormtroopers on the southern exterior platform
and four on the northern platform. They spawn once and stay dead after save/load.
The reinforcement tunnel stays closed. The ten guards add 160 XP; existing
earned XP, purchased upgrades and level thresholds are unchanged.

The lower Valley control-room window also shows glass on both sides in missions
18 and 19, including existing saves.
Mission 18's upper control-room window shows translucent glass on both sides
of its two solid panes. Collision and shooting rules are unchanged.

Mission 19's temple entrance hall has six troopers instead of three: four blaster
troopers and two repeater troopers. The lower chamber and counterweight hallway
each rise from two enemies to four using their existing types. Added guards persist
in saves and do not respawn.

Mission 19 keeps one Kell dragon instead of two, including existing saves. Removing
the second dragon reduces available campaign XP by 100 without removing earned XP.
