# Campaign progression

The mod adds choices and growth to the original combat, movement and exploration.
Each campaign begins with a fresh build, with enough choices to support different
play styles on later playthroughs.

## Level curve

Levels run from 1 to 40, one upgrade point per level gained: 39 points for 54 upgrades
across 18 branches, so a full clear still leaves 15 upgrades unbought and a replay can try
a different build. Each branch can take one point per mission.

Level 2 costs 100 XP. Through level 10, each later level costs 200, 205, 210 XP and so on,
increasing by 5, which gives about three levels in each of missions 1 and 2 and two in
mission 3. From level 11 each level costs 13 XP more than the one before (246, 265, 282 ...
769 for level 40). The cumulative threshold for level L >= 2 is
`100 + 200n + 5n(n-1)/2 + floor(13m^2/2)`, with n = L - 2 and m = max(0, L - 10); level 40
costs 52 XP more (the startup Rodians of missions 1 and 2) and requires 17,117 total XP.

Level 40 is meant for completionists. Every enemy and boss of either route adds up
to 17,296 XP, including 160 XP from ten added mission-17 stormtroopers and 118 XP from
seven added mission-19 guards.
The level-40 threshold remains 17,117 XP, allowing 179 XP of missed enemies. Most players finish in the 30s, which is intended.
Jerec, the final boss (mission 21 on both routes), gives no XP: the game ends with his
duel. Sariss (light route) and Yun (dark route) both give 600 XP in mission 16, so the two
routes have the same total.

The timed escape in mission 15 gives no XP on either route, including saved or spawned
actors. Mission 16 awards 600 XP, which grants at most one level from level 31 onward.
Stormtroopers in missions 17-19 receive 2 additional XP each, including scripted and
saved instances. Officers and commandos use their normal rewards.

## Existing saves

Loading a save preserves earned XP, levels, purchases and unspent points. If a saved
level exceeds the level implied by its XP, further level gains wait for the next
threshold. Levels above the cap remain saved but do not advance. Compatibility readers
handle older upgrade layouts without resetting a modern build.

## Enemy XP baseline

Run `python tools/campaign_xp.py "<Jedi Knight game folder>"` to reproduce the table.
The tool reads the player's archives in memory and outputs derived counts only;
no game files are extracted or distributed. It resolves template inheritance and
placed-thing overrides, applies the engine's Medium/single-player exclusions, excludes
civilians recognized by their death scripts and non-combat story characters, and
uses maximum health / 5, rounded down, with a minimum of 5. Missions 1 and 2 give 60%
of that, rounded down, before the minimum of 5; this also applies to their scripted
reinforcements. Bosses give fixed rewards instead: Yun 200 (mission 7), Gorc 300 and
Pic 200 (mission 11), Maw 400 (mission 14), Sariss 600 (light mission 16) and Yun 600
(dark mission 16), and Boc 500 (mission 20); Jerec (mission 21) gives none. Those duel missions do not play the level-up fanfare, because the
boss's death plays the game's goal sound at the same moment. Bowcaster Tuskens
(`actor_tk.cog`, both ordinary and bounty-hunter variants) have a minimum reward of
15 XP. Rifle variants keep their original rewards.
Mission 4 excludes the removed reservoir rifle guard (10 XP).
Mission 10 excludes the removed elevator officer (8 XP).
The placed bowcaster bonuses are mission 3: 94 XP, mission 4: 153 XP, mission 5: 42 XP.
The easy flying creatures (`actor_mailoc.cog`, placed as `mynok`) award 5 XP each.
Mission 3 contains ten on Medium, worth 50 XP for a full clear. XP is awarded after
civilian-counting scripts and before corpse cleanup, only for player-credited kills.

These are nominal XP values for placed enemies, not a verified kill-by-kill maximum.
The table includes the fixed startup Rodians but excludes other enemies created by
scripts, escaped AT-ST pilots and any health
changes made by scripts. It also assumes the player receives credit for each listed
kill; scenery, scripted encounters and other actors can prevent that in practice.
The two story branches are separate playthroughs and must not be added together.
Both routes give the same XP per mission. They differ only in maps 15, 16, 20 and 21,
which have the same placed rewards. On this baseline both reach level 40 with Boc's
500 XP in mission 20.

| Mission | Placed XP | Cumulative XP | Level |
|---|---:|---:|---:|
| 1 | 569 | 569 | 4 |
| 2 | 732 | 1,301 | 7 |
| 3 | 578 | 1,879 | 10 |
| 4 | 1,141 | 3,020 | 14 |
| 5 | 698 | 3,718 | 16 |
| 6 | 2,482 | 6,200 | 22 |
| 7 | 200 | 6,400 | 22 |
| 8 | 712 | 7,112 | 24 |
| 9 | 1,118 | 8,230 | 26 |
| 10 | 966 | 9,196 | 28 |
| 11 | 500 | 9,696 | 29 |
| 12 | 668 | 10,364 | 30 |
| 13 | 1,292 | 11,656 | 32 |
| 14 | 400 | 12,056 | 32 |
| 15 | 0 | 12,056 | 32 |
| 16 | 600 | 12,656 | 33 |
| 17 | 1,476 | 14,132 | 36 |
| 18 | 1,524 | 15,656 | 38 |
| 19 | 1,140 | 16,796 | 39 |
| 20 | 500 | 17,296 | 40 |
| 21 | 0 | 17,296 | 40 |

Killed enemies no longer come back. The original `00_replaceenemy.cog` (missions 1 and 2)
created a Rodian at a hidden spot and, ten seconds after each kill, a new one whenever the
player could not see that spot; `14_oopstroop.cog` (missions 13 and 17) replaced a killed
guard without a count limit. The mod lets the first script create only its startup enemy
and the second nothing. Outside the timed escape, every enemy gives XP, including those startup enemies (three in
mission 1 and five in mission 2, 52 XP together, included in the baseline totals above)
and any replacement already present in an older save.

Other scripted additions include the remote training sequence and water creature in
mission 4, the ambush in mission 5, generators and a squad in mission 6, and the
officer/trooper encounter in mission 8. Their triggers and the player's route make a
single exact campaign total misleading. Confirm pacing in playthroughs when changing
enemy rewards or these encounters; the table alone is not a full campaign test.
