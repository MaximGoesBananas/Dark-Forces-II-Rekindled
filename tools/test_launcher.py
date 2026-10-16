"""Compile and exercise the actual Windows installer in an isolated disposable folder."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

PROJECT = Path(__file__).resolve().parents[1]
if os.name != "nt":
    script = subprocess.check_output(["wslpath", "-w", str(Path(__file__).resolve())], text=True).strip()
    raise SystemExit(subprocess.call(["/mnt/c/Windows/py.exe", "-3", script]) if Path("/mnt/c/Windows/py.exe").exists()
                     else subprocess.call(["python.exe", script]))

scratch = Path("D:/Dev/helm/scratch/jk-rpg-release")
scratch.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix="installer-test-", dir=scratch) as work:
    binary = Path(work) / "installer-test.exe"
    subprocess.run(["C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe", "/nologo",
                    f"/out:{binary}", "/r:System.IO.Compression.dll", "/r:System.IO.Compression.FileSystem.dll",
                    "/r:System.Web.Extensions.dll", str(PROJECT / "launcher/Installer.cs"),
                    str(PROJECT / "launcher/InstallerTests.cs")], check=True)
    package = [sys.argv[sys.argv.index("--package") + 1]] if "--package" in sys.argv else []
    subprocess.run([str(binary), str(Path(work) / "Game with spaces"), *package], check=True)
