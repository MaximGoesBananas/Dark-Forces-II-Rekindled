# Rekindled code and design questions

## What is Rekindled built on?

Rekindled extends OpenJKDF2, an open-source recreation of Jedi Knight's engine.
The gameplay changes are mainly C, and the Windows launcher uses C# and WinForms.
It loads the campaign from your own copy of Jedi Knight.

[Engine and source guide](../DEVELOPING.md)

## How does progression work, and can you unlock everything?

You earn XP from combat and spend one point per level gained. There are 40 levels
and 54 upgrades across 18 branches, but only 39 points, so you cannot buy everything.
Each branch allows one purchase per mission. Most players are expected to finish
in the 30s.

[Progression and XP](PROGRESSION.md)

## Why is there only one difficulty?

The campaign is balanced around one set of combat, enemy and supply rules so
progression has a consistent baseline. Enemy ranged damage changes by campaign
phase, while upgrades give you more ways to handle encounters. Difficulty does
not automatically scale with your character level.

[Campaign balance](UPGRADES.md#other-gameplay-details)

## What changes about lightsaber combat?

You actively guard, time deflections and charge heavy swings. Charging leaves you
open, repeated hits can break your guard, and a heavy swing can damage a guarding
enemy. The upgrades improve protection, deflection timing and recovery.

[Lightsaber controls and upgrades](UPGRADES.md#weapons)

## How do weapons stay useful without one dominating the campaign?

Weapons have different trade-offs in damage, accuracy, firing speed and ammunition.
Upgrades change handling as well as power. The concussion rifle has spread, costly
ammunition and no secondary fire, while rail ammunition is capped at ten and
pickups give smaller amounts.

[Weapon balance](UPGRADES.md#weapons)

## How were the bosses changed?

Bosses retain their scripted fights, with individual adjustments to durability,
pursuit and damage. Sariss checks ordinary saber attack decisions every 250 ms,
and Boc and Jerec every 375 ms, compared with 500 ms normally. This changes
decision timing, not blade reach or swing recovery.

[Boss balance](UPGRADES.md#other-gameplay-details)

## How are the extra characters added safely?

Extra civilians reuse the level's existing character models and behavior. Placement
checks floor support, walls, doors, headroom and occupied space. Added guards use
authored positions and existing enemy types. Saved markers prevent additions from
being duplicated or killed guards from respawning after loading.

[Civilian placement](CIVILIANS.md) and [added encounters](UPGRADES.md#other-gameplay-details)

## How are saves and upgrades protected?

Progression and purchases are stored in the game's save data. Autosaves use a
separate slot, default to five minutes and can run during combat. Failed writes
preserve the previous save. Launcher updates preserve saves, settings and unrelated
files, although backing up saves is still recommended.

[Saving and progression](UPGRADES.md#points-branches-and-the-menu) and [installer code](../launcher/Installer.cs)

## Which systems and screen sizes does it support?

The release targets 64-bit Windows 10 and 11 with your own Jedi Knight files.
Steam files have been tested. GOG and disc installations remain unverified, and
multiplayer and Mysteries of the Sith are unsupported.

The game uses your primary monitor's desktop resolution, with proportional menus
and adjustable HUD scaling. The launcher scales with Windows DPI and scrolls when
space is limited. Checks cover 720p, 1080p, 4K and ultrawide layouts. Launcher checks
simulate screen sizes and scaling, rather than certifying every monitor or mixed-DPI setup.

[Compatibility](../README.md#compatibility), [display sizing](UPGRADES.md#display-sizing)
and [launcher layout checks](../launcher/LauncherUITests.cs)

## Was AI involved, and can developers inspect the code?

Yes. AI tools assisted with development and artwork, as disclosed in the README.
Maxim designed and directed Rekindled. The repository contains the engine changes
and launcher code, and releases include a matching source archive with the patched
engine and its libraries. OpenJKDF2 and other third-party contributors retain their credits.

[Credits](../README.md#credits) and [building from source](../DEVELOPING.md)
