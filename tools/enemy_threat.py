"""Estimate how hard each campaign mission hits the player, from the player's own game files.

A balancing baseline: placed enemies only (no scripted reinforcements), steady fire while
engaged, the mod's enemy aim and ranged-damage rules. Use it to compare missions and spot
enemies whose single hits are far above the rest, not as a prediction of real damage taken.
Usage: python tools/enemy_threat.py "<Jedi Knight game folder>" [--enemies]
"""
import re
import sys
from pathlib import Path

from gob import read_index
import campaign_xp as cx

MOD_ACCURACY = 0.75   # jkRpg_TuneAIClass closes 75% of the gap to perfect aim
MOD_FIRE_RATE = 1.4   # jkRpg_TuneAIClass: hostile direct fire 40% more often (not melee, lobs or turrets)
ENEMY_RANGED = 0.75   # jkRpg_ModifyDamage: enemy energy/fire reaching health; melee is unchanged
# jkRpg_RangedShare: the share above by campaign phase; boss duels and other maps keep 0.75
RANGED_SHARE = {**dict.fromkeys(("01narshadda.jkl", "02narshadda.jkl", "03katarn.jkl", "04escapehouse.jkl"), 0.5),
                **dict.fromkeys(("06abarons.jkl", "06bbarons.jkl", "08escape88.jkl", "09fuelstation.jkl", "10cargo.jkl"), 0.6),
                **dict.fromkeys(("12escape.jkl", "14tower.jkl"), 0.7),
                **dict.fromkeys(("16aescapeship.jkl", "16bescapeship.jkl", "18ascend.jkl", "19a.jkl", "19b.jkl"), 0.8)}
BOSS_MELEE = 1.25     # jkRpg_ModifyDamage: campaign bosses' saber/melee hits
ORIGINAL_AIM = {"probedroid"}  # jkRpg_AIAccuracy keeps their original aim


def load(root):
    files = {}
    for archive in ("Resource/Res2.gob", "Resource/Res1hi.gob", "Episode/JK1.GOB"):
        path = root / archive
        with path.open("rb") as stream:
            for name, offset, size in read_index(path):
                lower = name.lower()
                if lower.endswith((".jkl", ".cog", ".ai", "episode.jk")):
                    stream.seek(offset)
                    files[lower] = stream.read(size).decode("latin1")
    return files


def ai_class(files, name):
    text = files.get("misc\\ai\\" + name, "")
    accuracy = re.search(r"accuracy=([-\d.]+)", text)
    instincts = {}
    for line in text.splitlines():
        match = re.match(r"\s*(\w+)\s+([-\d.,\s]+)$", line)
        if match:
            instincts[match.group(1).lower()] = [float(x) for x in re.split(r"[,\s]+", match.group(2).strip()) if x]
    return float(accuracy.group(1)) if accuracy else 0.0, instincts


def enemies(files, name):
    parts = re.split(r"(?im)^section:[ \t]*", files["jkl\\" + name])[1:]
    sections = {part.splitlines()[0].strip().lower(): part.splitlines()[1:] for part in parts}
    templates = {}
    for line in sections["templates"]:
        words = line.lower().split()
        if len(words) >= 2 and not words[0].startswith("#") and words[0] not in ("world", "end"):
            templates[words[0]] = {**templates.get(words[1], {}), **cx.properties(line)}
    found = {}
    for line in sections["things"]:
        words = line.lower().split()
        if not words or not re.fullmatch(r"\d+:", words[0]):
            continue
        if name == "04escapehouse.jkl" and words[0] == "116:" and words[1] == "tuskangun":
            continue  # removed by jkRpg_ThinReservoirEncounter
        props = {**templates[words[1]], **cx.properties(line)}
        if props.get("type") != "actor" or int(props.get("thingflags", "0"), 0) & 0x12000:
            continue
        script = files.get("cog\\" + props.get("cog", ""), "")
        if re.search(r"(?i)changeinv\s*\([^,]+,\s*72\s*,", script) or words[1] in ("8t88", "max", "weegee", "jan"):
            continue
        entry = found.setdefault(words[1], {"count": 0, "props": props})
        entry["count"] += 1
        weapon = templates.get(props.get("weapon", ""), {})
        blast = templates.get(weapon.get("explode", ""), {})
        entry["damage"] = float(weapon.get("damage", 0))
        entry["blast"] = float(blast.get("damage", 0))
        entry["impact"] = weapon.get("damageclass", "") == "0x1"
        entry["accuracy"], entry["instincts"] = ai_class(files, props.get("aiclass", ""))
    return found


def profile(template, e, ranged=ENEMY_RANGED):
    """Largest single hit on the player, expected damage per second while engaged, and kind."""
    inst = e["instincts"]
    if "saberfighting" in inst:
        sf = inst["saberfighting"]
        attacks = [(sf[2], sf[3] / 1000)] + ([(sf[5], sf[6] / 1000)] if len(sf) > 6 else [])
        return (max(a[0] for a in attacks) * BOSS_MELEE,
                sum(a[0] / a[1] for a in attacks) / len(attacks) * BOSS_MELEE, "boss melee")
    if "turretfire" in inst:
        hit = e["damage"] * ranged
        return hit, hit / (inst["turretfire"][0] / 1000), "turret"
    fire = inst.get("primaryfire")
    if not fire:
        return e["damage"], 0.0, "scripted"
    if "lobfire" in inst or e["blast"]:
        hit = (e["damage"] + e["blast"]) * ranged
        lob = inst.get("lobfire", fire)
        return hit, hit / (lob[0] / 1000) * 0.5, "lobbed"
    interval, reach, burst, spacing = fire[0] / 1000, fire[2], fire[8], fire[9] / 1000
    if reach <= 0.5 or e["impact"]:
        return e["damage"], e["damage"] / interval, "melee"
    interval /= MOD_FIRE_RATE
    accuracy = e["accuracy"]
    if template not in ORIGINAL_AIM:
        accuracy += (1 - accuracy) * MOD_ACCURACY
    hit = e["damage"] * ranged
    return hit, hit * (1 + burst) / (interval + burst * spacing) * accuracy, "ranged"


def main():
    root = Path(sys.argv[1])
    files = load(root)
    episode = next(text for name, text in files.items() if name.endswith("episode.jk"))
    sequence = re.findall(r"(?im)^\s*(\d+)\s*:\s*.*?([\w]+\.jkl)", episode)
    maps = [name.lower() for entry, name in sequence if int(entry) < 600]
    print("Light route (dark differs only in missions 15, 16, 20, 21). Shields never absorb melee.")
    print("Mission | Map | Enemies | Engaged DPS total | Per enemy | Biggest hit")
    catalog = {}
    for mission, name in enumerate(maps, 1):
        found = enemies(files, name)
        count = sum(e["count"] for e in found.values())
        total, biggest = 0.0, (0.0, "")
        for template, e in found.items():
            hit, dps, kind = profile(template, e, RANGED_SHARE.get(name, ENEMY_RANGED))
            catalog.setdefault(template, (hit, dps, kind, mission))
            total += dps * e["count"]
            if hit > biggest[0]:
                biggest = (hit, f"{template} ({kind})")
        print(f"{mission} | {name} | {count} | {total:.0f} | {total / max(count, 1):.1f} | {biggest[0]:.1f} {biggest[1]}")
    if "--enemies" in sys.argv:
        print("\nEnemy | Kind | Biggest hit | Engaged DPS | First mission")
        for template, (hit, dps, kind, mission) in sorted(catalog.items(), key=lambda kv: -kv[1][0]):
            print(f"{template} | {kind} | {hit:.1f} | {dps:.1f} | {mission}")


if __name__ == "__main__":
    main()
