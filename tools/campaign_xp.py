"""Count placed enemy XP in a player's JK1 campaign, without extracting game files.

This is a balancing baseline, not a maximum: scripts can spawn more enemies,
including endlessly replaced guards. See docs/PROGRESSION.md for limitations.
Usage: python tools/campaign_xp.py "<Jedi Knight game folder>"
"""
import re
import sys
from pathlib import Path

from gob import read_index


def archive_text(path):
    with path.open("rb") as stream:
        for name, offset, size in read_index(path):
            if name.lower().endswith((".jkl", ".cog", "episode.jk")):
                stream.seek(offset)
                yield name.lower(), stream.read(size).decode("latin1")


def properties(line):
    return dict(re.findall(r"(\w+)=([^\s]+)", line.lower()))


# Same rules as jkRpg_KillXp: bosses pay fixed amounts, Jerec nothing; missions 1-2 pay 60% before the minimum.
BOSS_XP = {("07yun.jkl", "yun"): 200, ("11gorc.jkl", "gorc"): 300, ("11gorc.jkl", "pic"): 200,
           ("15maw.jkl", "maw"): 400, ("17asarris.jkl", "sariss"): 600, ("17bsarris.jkl", "yun2"): 600,
           ("20aboc.jkl", "boc"): 500, ("20bboc.jkl", "boc"): 500,
           ("21ajerec.jkl", "jerec"): 0, ("21bjerec.jkl", "jerec"): 0}
REDUCED_MAPS = ("01narshadda.jkl", "02narshadda.jkl")
MAX_LEVEL = 40
SCRIPT_ENEMY_XP = 52  # jkRpg_XpForLevel: the startup Rodians of 00_replaceenemy.cog


def xp_for_level(level):
    """jkRpg_XpForLevel; test_progression.py checks both agree at every level."""
    if level <= 1:
        return 0
    n, late = level - 2, max(0, level - 10)
    return (100 + 200 * n + 5 * n * (n - 1) // 2 + 13 * late * late // 2
            + (SCRIPT_ENEMY_XP if level >= MAX_LEVEL else 0))


def level_for(xp):
    level = 1
    while level < MAX_LEVEL and xp >= xp_for_level(level + 1):
        level += 1
    return level


def placed_enemies(text, files, name=""):
    parts = re.split(r"(?im)^section:[ \t]*", text)[1:]
    sections = {part.splitlines()[0].strip().lower(): part.splitlines()[1:]
                for part in parts}
    templates = {}
    for line in sections["templates"]:
        words = line.lower().split()
        if len(words) < 2 or words[0].startswith("#") or words[0] in ("world", "end"):
            continue
        templates[words[0]] = {**templates.get(words[1], {}), **properties(line)}
    count = xp = 0
    for line in sections["things"]:
        words = line.lower().split()
        if not words or not re.fullmatch(r"\d+:", words[0]):
            continue
        # The reservoir gunman is removed by jkRpg_ThinReservoirEncounter.
        if name == "04escapehouse.jkl" and words[0] == "116:" and words[1] == "tuskangun":
            continue
        # The ordinary officer blocking mission 10's lift is removed on fresh and loaded worlds.
        if name == "10cargo.jkl" and words[0] == "266:" and words[1] == "iofficer2":
            continue
        # Keep only the first of Mission 19's two placed Kell dragons.
        if name == "19b.jkl" and words[0] == "15:" and words[1] == "kelldragon":
            continue
        # The two courtyard walkers are disabled by jkRpg_RetireCourtyardWalkers.
        if name == "06bbarons.jkl" and words[0] in ("107:", "256:") and words[1] == "iatst":
            continue
        props = {**templates[words[1]], **properties(line)}
        # Same exclusions as sithThing_ReadStaticThingsListText on Medium, single player.
        if props.get("type") != "actor" or int(props.get("thingflags", "0"), 0) & 0x12000:
            continue
        script = files.get("cog\\" + props.get("cog", ""), "")
        if re.search(r"(?i)changeinv\s*\([^,]+,\s*72\s*,", script):
            continue  # The RPG kill hook excludes civilians counted by these scripts.
        if words[1] in ("8t88", "max", "weegee", "jan"):
            continue  # Story characters, not ordinary killable enemies.
        count += 1
        gain = int(float(props.get("maxhealth", props.get("health", "100"))) / 5)
        if props.get("cog") == "actor_tk.cog":
            gain = max(15, gain)
        if name == "06bbarons.jkl" and words[1] == "iatst":
            gain = (gain * 5 + (2 if words[0] == "308:" else 0)) // 3  # jkRpg_WalkerXp
        if name in REDUCED_MAPS:
            gain = gain * 60 // 100
        if name in ("18ascend.jkl", "19a.jkl", "19b.jkl") and words[1] in ("stormtroop", "stormtroop2", "stormtroop3", "stormtroop4"):
            gain = max(5, gain) + 2
        boss = BOSS_XP.get((name, words[1]))
        xp += boss if boss is not None else 5 if props.get("cog") == "actor_mailoc.cog" else max(5, gain)
    # 00_replaceenemy.cog creates one enemy each at startup (missions 1 and 2); the mod stops its
    # replacements, so each is a one-time enemy worth normal XP.
    for line in sections.get("cogs", []):
        match = re.match(r"\s*\d+:\s*00_replaceenemy\.cog\s+\d+\s+(\S+)", line, re.I)
        if match:
            props = templates[match.group(1).lower()]
            gain = int(float(props.get("maxhealth", props.get("health", "100"))) / 5)
            if name in REDUCED_MAPS:
                gain = gain * 60 // 100
            count += 1
            xp += max(5, gain)
    # Ten fixed valley guards added once per mission by jkRpg_AddValleyTroopers.
    if name == "18ascend.jkl":
        props = templates["stormtroop2"]
        count += 10
        xp += 10 * (max(5, int(float(props.get("maxhealth", props.get("health", "100"))) / 5)) + 2)
    if name == "19b.jkl":
        for template in ("stormtroop2", "stormtroop2", "stormtroop3", "stormtroop4", "icommando",
                         "icommandorpt", "icommandorpt"):
            props = templates[template]
            count += 1
            xp += max(5, int(float(props.get("maxhealth", props.get("health", "100"))) / 5)) + (2 if template.startswith("stormtroop") else 0)
    return count, 0 if name.lower() in ("16aescapeship.jkl", "16bescapeship.jkl") else xp


def main():
    root = Path(sys.argv[1])
    files = {}
    for archive in ("Resource/Res2.gob", "Resource/Res1hi.gob", "Episode/JK1.GOB"):
        files.update(archive_text(root / archive))
    episode = next(text for name, text in files.items() if name.endswith("episode.jk"))
    sequence = re.findall(r"(?im)^\s*(\d+)\s*:\s*.*?([\w]+\.jkl)", episode)
    common = [name.lower() for entry, name in sequence if int(entry) < 151]
    for route, branch in (("Light", lambda entry: 151 <= entry < 600),
                          ("Dark", lambda entry: entry >= 600)):
        maps = common + [name.lower() for entry, name in sequence if branch(int(entry))]
        total = 0
        print(f"\n{route} route: placed enemies only; excludes reinforcements and farming")
        print("Mission | Map | Enemies | XP | Cumulative XP | Level")
        for mission, name in enumerate(maps, 1):
            count, xp = placed_enemies(files["jkl\\" + name], files, name)
            total += xp
            print(f"{mission} | {name} | {count} | {xp} | {total} | {level_for(total)}")


if __name__ == "__main__":
    main()
