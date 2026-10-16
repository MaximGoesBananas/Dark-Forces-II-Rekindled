"""Render and check real launcher controls without touching the player's installation."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import json
import zipfile
import hashlib

root=Path(__file__).resolve().parents[1]
if os.name!='nt':
    script=subprocess.check_output(['wslpath','-w',str(Path(__file__).resolve())],text=True).strip()
    raise SystemExit(subprocess.call(['python.exe',script,*sys.argv[1:]]))
package=Path(sys.argv[sys.argv.index('--package')+1]) if '--package' in sys.argv else None
scratch=Path('D:/Dev/helm/temp/rekindled-launcher-audit');scratch.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(dir=scratch) as work:
    if package is None:
        package=Path(work)/'fixture.zip'
        with zipfile.ZipFile(package,'w') as archive:
            archive.writestr('manifest.json',json.dumps(dict(format=1,game='jedi-knight-rpg',version='test',
                files=[dict(path='openjkdf2-64.exe',size=0,sha256=hashlib.sha256(b'').hexdigest())])))
    binary=Path(work)/'ui-test.exe'
    subprocess.run(['C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe','/nologo','/main:LauncherUITests',f'/out:{binary}',
        '/r:System.IO.Compression.dll','/r:System.IO.Compression.FileSystem.dll','/r:System.Web.Extensions.dll',
        '/r:System.Windows.Forms.dll','/r:System.Drawing.dll',f'/resource:{root/"launcher/poster.jpg"},poster.jpg',
        f'/resource:{root/"launcher/fonts/Orbitron-Medium.ttf"},Orbitron.ttf',
        f'/win32icon:{root/"launcher/game.ico"}',
        f'/win32manifest:{root/"launcher/app.manifest"}',
        str(root/'launcher/Installer.cs'),str(root/'launcher/Program.cs'),str(root/'launcher/LauncherUITests.cs')],check=True)
    subprocess.run([str(binary),str(package),str(scratch/'screens'),str(Path(work)/'Game fixture Å'),str(root/'launcher/game.ico')],check=True)
