"""Pack rendered PNGs into a Windows .ico and a macOS .icns (both formats can hold PNG data directly).

Usage: python3 tools/make_icons.py   (reads assets/icon-<size>.png, writes assets/icon.ico and assets/icon.icns)
"""
import struct
from pathlib import Path

A = Path(__file__).resolve().parent.parent / 'assets'


def ico(sizes):
    pngs = [(s, (A / ('icon-%d.png' % s)).read_bytes()) for s in sizes]
    head = struct.pack('<HHH', 0, 1, len(pngs))
    offset = 6 + 16 * len(pngs)
    entries, blobs = b'', b''
    for s, data in pngs:
        entries += struct.pack('<BBBBHHII', s % 256, s % 256, 0, 0, 1, 32, len(data), offset + len(blobs))
        blobs += data
    (A / 'icon.ico').write_bytes(head + entries + blobs)


def icns(types):
    chunks = b''
    for tag, s in types:
        data = (A / ('icon-%d.png' % s)).read_bytes()
        chunks += tag + struct.pack('>I', len(data) + 8) + data
    (A / 'icon.icns').write_bytes(b'icns' + struct.pack('>I', len(chunks) + 8) + chunks)


if __name__ == '__main__':
    ico([16, 32, 48, 64, 128, 256])
    icns([(b'icp4', 16), (b'icp5', 32), (b'icp6', 64), (b'ic07', 128), (b'ic08', 256), (b'ic09', 512)])
    print('wrote assets/icon.ico and assets/icon.icns')
