"""Run existing checks once, sequentially, with timings and a failure exit status.

WSL: python3 tools/run_checks.py ~/src/OpenJKDF2 [bindings ui ...] [--windows]
No names means all test_*.py checks. --windows also runs the Windows binding check.
"""
import argparse
from pathlib import Path
import subprocess
import sys
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("engine", type=Path)
parser.add_argument("checks", nargs="*")
parser.add_argument("--windows", action="store_true")
args = parser.parse_args()
available = {p.stem.removeprefix("test_"): p for p in Path(__file__).parent.glob("test_*.py")}
names = args.checks or sorted(available)
unknown = set(names) - available.keys()
if unknown:
    parser.error("Unknown checks: " + ", ".join(sorted(unknown)))
jobs = [(name, []) for name in dict.fromkeys(names)]
if args.windows:
    jobs.append(("bindings", ["--windows"]))
started = time.monotonic()
failed = []
for name, extra in jobs:
    before = time.monotonic()
    result = subprocess.run([sys.executable, str(available[name]), str(args.engine), *extra],
                            capture_output=True, text=True)
    label = name + (" (Windows)" if extra else "")
    print(f"{'PASS' if result.returncode == 0 else 'FAIL'} {label}: {time.monotonic() - before:.2f}s", flush=True)
    if result.returncode:
        failed.append(label)
        print(result.stdout + result.stderr, flush=True)
print(f"{len(jobs) - len(failed)}/{len(jobs)} passed in {time.monotonic() - started:.2f}s", flush=True)
sys.exit(bool(failed))
