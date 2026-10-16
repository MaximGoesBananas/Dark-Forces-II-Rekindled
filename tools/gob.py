"""Read and write Jedi Knight GOB archives.

Format: "GOB " + u32 version (0x14) + u32 index offset.
Index: u32 count, then count * (u32 offset, u32 length, char[128] name).
"""
import os
import struct
import sys


def read_index(path):
    with open(path, "rb") as f:
        magic, ver, idx = struct.unpack("<4sII", f.read(12))
        if magic != b"GOB " or ver != 0x14:
            raise ValueError(f"{path}: not a JK GOB")
        f.seek(idx)
        (count,) = struct.unpack("<I", f.read(4))
        out = []
        for _ in range(count):
            off, size, name = struct.unpack("<II128s", f.read(136))
            out.append((name.split(b"\0", 1)[0].decode("latin-1"), off, size))
        return out


def extract(path, dest, pattern=""):
    with open(path, "rb") as f:
        for name, off, size in read_index(path):
            if pattern.lower() not in name.lower():
                continue
            target = os.path.join(dest, *name.replace("\\", "/").split("/"))
            os.makedirs(os.path.dirname(target), exist_ok=True)
            f.seek(off)
            with open(target, "wb") as o:
                o.write(f.read(size))


def pack(src, out):
    """Pack every file under src; stored names use backslashes, relative to src."""
    files = []
    for root, _, names in os.walk(src):
        for n in sorted(names):
            full = os.path.join(root, n)
            files.append((os.path.relpath(full, src).replace("/", "\\"), full))
    with open(out, "wb") as o:
        o.write(b"\0" * 12)
        entries = []
        for name, full in files:
            data = open(full, "rb").read()
            entries.append((o.tell(), len(data), name))
            o.write(data)
        idx = o.tell()
        o.write(struct.pack("<I", len(entries)))
        for off, size, name in entries:
            o.write(struct.pack("<II128s", off, size, name.encode("latin-1")))
        o.seek(0)
        o.write(struct.pack("<4sII", b"GOB ", 0x14, idx))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "list":
        for name, off, size in read_index(sys.argv[2]):
            print(f"{size:>10} {name}")
    elif cmd == "extract":
        extract(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "")
    elif cmd == "pack":
        pack(sys.argv[2], sys.argv[3])
