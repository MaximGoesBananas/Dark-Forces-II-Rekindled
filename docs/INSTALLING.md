# Installation and saves

The Rekindled launcher is one Windows 10/11 64-bit application with the game changes inside it. It uses
the Windows .NET Framework, without Python, build tools, an account or an online
connection.

## Install and play

1. Download the launcher from Releases. Keep it somewhere
   convenient; it is also your Play and Uninstall application.
2. Open it. It searches Steam's registered libraries for Dark Forces II. If needed,
   use Browse to select the game folder containing `Resource` and `Episode`.
   You can also paste its full path from Explorer, including surrounding quotes.
3. Close the game, select Install, then Play. A full installed copy of Jedi Knight:
   Dark Forces II is required. The launcher does not supply the original game.

## Game editions

Steam is not required by the launcher. Automatic discovery searches Steam libraries;
**Browse** accepts another installation containing `Resource/Res1hi.gob`,
`Resource/Res2.gob`, `Resource/jk_.cd` and `Episode/JK1.gob`. Play starts Rekindled
directly and uses the selected folder, without starting a store client.

Rekindled has been tested with Steam's game files. [OpenJKDF2 explicitly supports
GOG's files](https://github.com/shinyquagsire23/OpenJKDF2#openjkdf2), so GOG is expected
to work through Browse, but a genuine GOG installation has not yet been tested with
Rekindled. Original disc installations are also unverified. Accepting a folder is
not proof that a particular edition's missions, music and movies work correctly.

The installer has been checked against a store-neutral folder layout and rejects
an incomplete copy. To verify another edition, use its actual installed game files
and check launcher install, Play, a campaign mission, music, movies, save/load and
uninstall. Keep its saves separate from an existing playthrough.

## Display

Rekindled opens a borderless window at your primary monitor's desktop resolution,
including 4K and ultrawide layouts. It does not change your display mode. The upgrade
menu stays centered and keeps its proportions. Fresh profiles choose a HUD size for
that resolution; existing profiles keep their saved size, adjustable in Setup.
Exclusive fullscreen remains disabled because it caused black menus and stalled loading.


## Installation behavior

It writes the mod to `<game>/rpg`, leaving original executables and archives alone.
Steam's Play button still starts the original. No Steam launch options or services
are changed. If Windows denies writing to the chosen folder, use an installation
your account can write to; the launcher does not silently elevate or change permissions.

## Update or repair

Open a newer launcher, choose the same folder and select Update. Select Repair in
the same version to restore missing files. It verifies
the package, prepares the complete replacement, then switches folders. Failed preparation
keeps the previous installation. Missing mod files can be repaired.

If an installed file was modified, the launcher names it and stops before overwriting
it. Back up that customization and restore the original file before updating. Custom
reports and files that do not conflict with the package are carried forward. A matching
manual installation can be adopted; differing files are not silently replaced.

Verified old files are removed after a successful update. If cleanup cannot complete,
the launcher reports a retained `.rpg-previous-*` folder. Keep it until you confirm the
new installation and custom files. After a power loss during the folder switch, the old
installation may be in that folder; restore it to `rpg` before retrying.

## Saves and controls

Saves and profiles remain in `<game>/player`, outside the mod folder. The launcher
preserves them on install, update and uninstall. The mod uses the existing game's
profiles and save names: make a separate named save before trying it, and keep an
original-game save if you want to return to the original campaign. Uninstalling does
not convert RPG saves back into original-game saves or undo settings changed in game.

Fresh profiles default to WASD movement, Mouse1 primary fire, **Mouse2 secondary fire**,
Space jump, Ctrl crouch, E use and K upgrades. Existing custom bindings are preserved.
Change them in Setup > Key bindings.

## Uninstall

Close the game and select Uninstall. It removes only managed files whose contents
still match the installed package. Modified files, reports, saves and the original
game stay where they are. A manual installation without the launcher's record is
not removed automatically.

The selected folder is remembered in `%LocalAppData%/Jedi Knight RPG/game-folder.txt`.
This small preference is kept after uninstall so a later reinstall can find the game.

## Report a problem

Include the launcher version, mission and what happened. A normal screenshot can help.
Embedded location reports are a development tool and are not included in the release.
