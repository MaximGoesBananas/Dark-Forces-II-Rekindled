"""Read location data embedded by F12 in an RPG screenshot; no game files needed."""
from pathlib import Path
import struct
import sys
import zlib


def read_report(path):
    with Path(path).open("rb") as stream:
        if stream.read(8) != b"\x89PNG\r\n\x1a\n":
            raise ValueError("Not a PNG screenshot")
        while True:
            header = stream.read(8)
            if len(header) != 8:
                raise ValueError("Incomplete PNG")
            size, kind = struct.unpack(">I4s", header)
            if size > 64 * 1024 * 1024:
                raise ValueError("PNG chunk is too large")
            data, crc = stream.read(size), stream.read(4)
            if len(data) != size or len(crc) != 4 or zlib.crc32(kind + data) != struct.unpack(">I", crc)[0]:
                raise ValueError("Damaged PNG chunk")
            if kind == b"tEXt" and data.startswith(b"Jedi Knight RPG report\0"):
                return data.split(b"\0", 1)[1].decode("latin1")
            if kind == b"IEND":
                raise ValueError("This picture has no RPG location data; use the original F12 PNG")


if __name__ == "__main__":
    try:
        print(read_report(sys.argv[1]), end="")
    except (OSError, ValueError, IndexError) as error:
        sys.exit(f"Could not read report: {error}")
