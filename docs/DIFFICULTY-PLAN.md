# Campaign difficulty

Rekindled uses one difficulty. Enemy ranged damage reaching health scales by
campaign phase, after shields and protection upgrades:

| Missions | Share of original ranged damage |
|---|---:|
| 1-4 | 50% |
| 5-10 | 60% |
| 12-13 | 70% |
| 15-19, excluding boss duels | 80% |
| Boss duels | 75% |

Melee, saber, Force, environmental and self-inflicted damage use their own rules.
Shields absorb damage before the ranged multiplier. `jkRpg_RangedShare` implements
these phases; `tools/test_ranged_damage.py` checks the affected attack types.

The lightsaber arrives at the end of mission 4. Its frontal guard and Blaster
protection change how players handle ranged encounters from mission 5 onward.
Upgrades improve survival and weapon handling without scaling enemy health to the
player's level. See [the upgrade reference](UPGRADES.md) for weapon and boss values.

`tools/enemy_threat.py` reads the player's game archives to compare placed enemies
and supplies. Its estimates assume sustained engagement and cannot predict exact
damage taken or replace campaign playtesting.
