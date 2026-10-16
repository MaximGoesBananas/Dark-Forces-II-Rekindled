#!/bin/bash
# Resolve offsets against the exact installed binary, including its development/release settings.
# Set JKRPG_CRASH_EXE to a preserved crash binary when the installed game has since changed.
set -e
python3 - "$@" <<'PY'
import bisect
import os
import subprocess
import sys
exe = os.environ.get("JKRPG_CRASH_EXE", "/mnt/d/SteamLibrary/steamapps/common/Star Wars Jedi Knight/rpg/openjkdf2-64.exe")
header = subprocess.check_output(["x86_64-w64-mingw32-objdump", "-p", exe], text=True)
base = int(next(line.split()[1] for line in header.splitlines() if line.startswith("ImageBase")), 16)
symbols = []
for line in subprocess.check_output(["x86_64-w64-mingw32-nm", "-n", "-C", exe], text=True).splitlines():
    fields = line.split(None, 2)
    if len(fields) == 3 and fields[1] in ("t", "T"):
        symbols.append((int(fields[0], 16), fields[2]))
for entry in sys.argv[1:]:
    offset = entry.removeprefix("openjkdf2-64.exe+")
    if not offset.startswith("0x"):
        continue
    address = base + int(offset, 16)
    index = bisect.bisect_right(symbols, (address, chr(0x10ffff))) - 1
    if index < 0:
        raise SystemExit("No matching symbol for " + entry)
    start, name = symbols[index]
    print(f"{offset} {name} +{address-start:#x}")
PY
