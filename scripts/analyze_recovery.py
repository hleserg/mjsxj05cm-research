#!/usr/bin/env python3
"""Read-only uImage/region check for IPC019 TF recovery images."""

import argparse
from collections import Counter
import hashlib
import lzma
import math
from pathlib import Path
import re
import struct
import zlib


def entropy(data):
    counts = Counter(data)
    total = len(data)
    return -sum((n / total) * math.log2(n / total) for n in counts.values())


parser = argparse.ArgumentParser()
parser.add_argument("images", nargs="+", type=Path)
args = parser.parse_args()

for path in args.images:
    data = path.read_bytes()
    assert len(data) == 0xF90050, f"unexpected recovery size: {path}"
    header = data[:64]
    magic, hcrc, _time, size, _load, _entry, dcrc, os, arch, kind, comp, name = struct.unpack(
        ">7I4B32s", header
    )
    assert magic == 0x27051956, f"invalid uImage magic: {path}"
    calculated_hcrc = zlib.crc32(header[:4] + b"\0\0\0\0" + header[8:])
    calculated_dcrc = zlib.crc32(data[64 : 64 + size])
    assert hcrc == calculated_hcrc and dcrc == calculated_dcrc, f"uImage CRC failed: {path}"
    print(f"{path.name}: sha256={hashlib.sha256(data).hexdigest()}")
    print(f"  uImage={name.rstrip(bytes([0])).decode(errors='replace')} os={os} arch={arch} type={kind} comp={comp} CRC=OK")
    kernel = lzma.decompress(data[64 : 64 + size])
    version = re.search(rb"Linux version [^\x00\n]+", kernel)
    print(f"  kernel_version={version.group().decode(errors='replace') if version else 'not found'}")
    for label, start, end in (
        ("kernel_slot", 0, 0x200000),
        ("rootfs_slot", 0x200000, 0x960000),
        ("data_slot", 0x960000, 0xF90000),
        ("trailer", 0xF90000, 0xF90050),
    ):
        region = data[start:end]
        print(
            f"  {label} 0x{start:06x}-0x{end:06x}: "
            f"sha256={hashlib.sha256(region).hexdigest()} entropy={entropy(region):.3f}"
        )
    print(f"  squashfs_magic_offsets={[hex(i) for i in range(0x1F0000, 0x220000) if data[i:i+4] == b'hsqs']}")
