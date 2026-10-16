"""Build a Windows launcher with an embedded, hash-checked mod; no original game data.

Run on Windows: python tools/build_release.py --version 1.0
The matching source archive is built beside the launcher for redistribution together.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import shutil
import tempfile
import sys
import zipfile

PROJECT = Path(__file__).resolve().parents[1]
DEFAULT_ENGINE = Path("//wsl.localhost/Ubuntu-24.04/home/maxim/src/OpenJKDF2")
RUNTIME = ("openjkdf2-64.exe", "libGameNetworkingSockets.dll", "libstdc++-6.dll",
           "libgcc_s_seh-1.dll", "libwinpthread-1.dll", "OpenAL32.dll")
NOTICES = ("LICENSE.md", "lib/GameNetworkingSockets/LICENSE", "lib/SDL/LICENSE.txt",
           "lib/SDL_mixer/LICENSE.txt", "lib/freeglut/COPYING", "lib/glew/LICENSE.txt",
           "lib/libpng/LICENSE", "lib/openal/COPYING", "lib/physfs/LICENSE.txt",
           "lib/protobuf/LICENSE", "lib/zlib/LICENSE", "src/external/libsmacker/COPYING",
           "src/external/libsmusher/LICENSE", "src/external/fcaseopen/LICENSE.txt",
           "src/external/nativefiledialog-extended/LICENSE", "3rdparty/json/LICENSE.MIT",
           "lib/SDL_mixer/external/ogg/COPYING", "lib/SDL_mixer/external/vorbis/COPYING",
           "lib/SDL_mixer/external/opus/COPYING", "lib/SDL_mixer/external/opusfile/COPYING",
           "lib/SDL/src/hidapi/LICENSE.txt", "lib/SDL/src/hidapi/LICENSE-bsd.txt",
           "lib/SDL/src/video/yuv2rgb/LICENSE", "lib/protobuf/third_party/utf8_range/LICENSE")


def git(root, *args):
    if root.as_posix().startswith("//wsl.localhost/"):
        distro, _, path = root.as_posix()[len("//wsl.localhost/"):].partition("/")
        return subprocess.check_output(["wsl", "-d", distro, "--", "git", "-C", "/" + path, *args])
    return subprocess.check_output(["git", "-C", str(root), *args])


def put(archive, name, data):
    entry = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
    entry.compress_type = zipfile.ZIP_DEFLATED
    entry.external_attr = 0o100644 << 16
    archive.writestr(entry, data)


def validate_release_engine(data):
    if b"Jedi Knight RPG location report v1" in data:
        raise RuntimeError("Development reports must not ship. Run tools/build_engine.sh --release first.")


def source_archive(engine, output):
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for root, prefix in ((engine, "OpenJKDF2/"), (PROJECT, "jk-rpg/")):
            tracked = git(root, "ls-files", "-z", "--recurse-submodules").decode().split("\0")
            if root == PROJECT:
                attributes = subprocess.check_output(
                    ["git", "-C", str(root), "check-attr", "-z", "--stdin", "export-ignore"],
                    input="\0".join(tracked).encode()).decode().split("\0")
                excluded = {attributes[i] for i in range(0, len(attributes) - 2, 3)
                            if attributes[i + 2] == "set"}
                tracked = [name for name in tracked if name not in excluded]
            for name in sorted(set(tracked) - {""}):
                if Path(name).name.upper() in ("AGENTS.MD", "CLAUDE.MD"):
                    continue
                path = root / name
                if path.is_file():
                    put(archive, prefix + name, path.read_bytes())
        put(archive, "ENGINE-COMMIT.txt", git(engine, "rev-parse", "HEAD"))
        put(archive, "ENGINE-SUBMODULES.txt", git(engine, "submodule", "status", "--recursive"))
        put(archive, "PROJECT-COMMIT.txt", git(PROJECT, "rev-parse", "HEAD"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--engine", type=Path, default=DEFAULT_ENGINE)
    parser.add_argument("--output", type=Path, help="Separate directory for the prepared download")
    parser.add_argument("--runtime", type=Path, default=Path("D:/SteamLibrary/steamapps/common/Star Wars Jedi Knight/rpg"))
    parser.add_argument("--source-archive", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.source_archive:
        source_archive(args.engine, args.source_archive)
        return
    if os.name != "nt":
        parser.error("Run with Windows Python; this uses the Windows Framework compiler.")
    if not args.version or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-" for c in args.version):
        parser.error("Version must contain only letters, digits, dots and hyphens.")
    output = args.output.resolve() if args.output else PROJECT / "dist" / args.version
    # Use the workstation storage guard when available; keep the same reserve elsewhere.
    helm = Path("D:/Dev/helm")
    if (helm / "dashboard/retention.py").is_file():
        sys.path.insert(0, str(helm))
        from dashboard.retention import require_storage_budget
        require_storage_budget(output, 600 * 1024 * 1024)
    else:
        ancestor = output
        while not ancestor.exists():
            ancestor = ancestor.parent
        if shutil.disk_usage(ancestor).free < 20 * 1024**3 + 600 * 1024**2:
            raise RuntimeError("Insufficient space for the package and 20 GiB reserve")
    output.mkdir(parents=True, exist_ok=True)
    scratch = (helm / "scratch/jk-rpg-release/build" if helm.is_dir()
               else Path(tempfile.gettempdir()) / "rekindled-release-build")
    scratch.mkdir(parents=True, exist_ok=True)
    engine_commit = git(args.engine, "rev-parse", "HEAD").decode().strip()
    # Only the explicit runtime allowlist is accepted: never package player/, GOBs or a whole game folder.
    files = {name: (args.runtime / name).read_bytes() for name in RUNTIME}
    # Package the public build, never the maintainer's installed development executable.
    files["openjkdf2-64.exe"] = (args.engine / "build_win64/openjkdf2-64.exe-6.0").read_bytes()
    validate_release_engine(files["openjkdf2-64.exe"])
    for path in sorted((PROJECT / "art").glob("*.bmp")):
        files["art/" + path.name] = path.read_bytes()
    sky = PROJECT / "jkgm/materials/rekindled-sky"
    if (sky / "metadata.json").is_file():
        for path in sorted(sky.glob("*.png")) + [sky / "metadata.json"]:
            files[path.relative_to(PROJECT).as_posix()] = path.read_bytes()
    for name in NOTICES:
        files["licenses/" + name.replace("/", "_")] = (args.engine / name).read_bytes()
    distro = args.engine.parents[3]
    for name in ("gcc-13-base", "mingw-w64-common"):
        files["licenses/" + name + ".txt"] = (distro / "usr/share/doc" / name / "copyright").read_bytes()
    files["NOTICES.txt"] = (PROJECT / "release/NOTICES.txt").read_bytes()
    files["licenses/Orbitron-OFL.txt"] = (PROJECT / "launcher/fonts/OFL.txt").read_bytes()
    files["SOURCE.txt"] = ("Matching source: Dark-Forces-II-Rekindled-" + args.version + "-source.zip\n"
                           "Distribute it alongside this launcher. Includes OpenJKDF2, its libraries,\n"
                           "the mod patches and launcher source. See release/README.md in that archive.\n"
                           "Engine commit: " + engine_commit + "\n").encode()
    manifest = dict(format=1, game="jedi-knight-rpg", version=args.version, engineCommit=engine_commit,
                    files=[dict(path=name, size=len(data), sha256=hashlib.sha256(data).hexdigest()) for name, data in sorted(files.items())])
    payload = scratch / "mod.zip"
    with zipfile.ZipFile(payload, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        put(archive, "manifest.json", json.dumps(manifest, indent=2).encode())
        for name, data in sorted(files.items()):
            put(archive, name, data)
    binary = output / ("Dark-Forces-II-Rekindled-" + args.version + ".exe")
    metadata = scratch / "ReleaseInfo.cs"
    metadata.write_text('using System.Reflection;\n'
                        '[assembly: AssemblyTitle("Dark Forces II Rekindled")]\n'
                        '[assembly: AssemblyProduct("Dark Forces II Rekindled")]\n'
                        '[assembly: AssemblyDescription("Install, update, play and remove Rekindled")]\n'
                        f'[assembly: AssemblyInformationalVersion("{args.version}")]\n', encoding="utf-8")
    subprocess.run(["C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe", "/nologo", "/target:winexe",
                    "/optimize+", "/platform:x64", f"/out:{binary}", f"/resource:{payload},mod.zip", f"/resource:{PROJECT / 'launcher/poster.jpg'},poster.jpg",
                    f"/resource:{PROJECT / 'launcher/fonts/Orbitron-Medium.ttf'},Orbitron.ttf",
                    f"/win32manifest:{PROJECT / 'launcher/app.manifest'}",
                    f"/win32icon:{PROJECT / 'launcher/game.ico'}",
                    "/r:System.IO.Compression.dll", "/r:System.IO.Compression.FileSystem.dll",
                    "/r:System.Web.Extensions.dll", "/r:System.Windows.Forms.dll", "/r:System.Drawing.dll",
                    str(PROJECT / "launcher/Installer.cs"), str(PROJECT / "launcher/Program.cs"), str(metadata)], check=True)
    source = output / ("Dark-Forces-II-Rekindled-" + args.version + "-source.zip")
    if args.engine.as_posix().startswith("//wsl.localhost/"):
        distro_name, _, engine_path = args.engine.as_posix()[len("//wsl.localhost/"):].partition("/")
        def linux_path(path):
            return subprocess.check_output(["wsl", "-d", distro_name, "--exec", "wslpath", "-a", path.as_posix()], text=True).strip()
        subprocess.run(["wsl", "-d", distro_name, "--", "python3", linux_path(Path(__file__).resolve()),
                        "--version", args.version, "--engine", "/" + engine_path,
                        "--source-archive", linux_path(source)], check=True)
    else:
        source_archive(args.engine, source)
    sums = []
    for path in (binary, source):
        sums.append(hashlib.sha256(path.read_bytes()).hexdigest() + "  " + path.name)
        print(f"{path.name}: {path.stat().st_size / (1024*1024):.1f} MiB", flush=True)
    (output / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
