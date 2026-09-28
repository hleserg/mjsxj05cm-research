#!/usr/bin/env python3
"""Полный dump SPI NOR из стоящего U-Boot (`SigmaStar # `) через sf read + md.l по UART.

Только чтение: sf probe / sf read / md.l / crc32 (2 аргумента, печать) / version.
Любая другая строка в порт не уйдёт (ALLOW). Голый Enter не шлётся никогда:
U-Boot повторил бы прошлую команду.

  ./dump.py --selftest   разбор md.l и allowlist
  ./dump.py probe        64 KiB пробно: формат, crc32, приглашение
  ./dump.py N            полный проход N -> spi/original-0N.bin (~1 ч 45 мин)
  ./dump.py check F...   env/uImage/squashfs на своих смещениях
"""
import re, struct, sys, time, zlib
from pathlib import Path

RAM, SIZE, CHUNK = 0x21000000, 0x1000000, 0x100000  # 0x21000000: XZ-буфер U-Boot, 16 MiB
PROMPT = b"SigmaStar # "
H = r"0x[0-9a-f]+"
ALLOW = [re.compile(p) for p in (
    r"version", r"sf probe 0", rf"sf read 0x21[0-9a-f]{{6}} {H} {H}",
    rf"md\.l 0x21[0-9a-f]{{6}} {H}", rf"crc32 0x21[0-9a-f]{{6}} {H}")]
LINE = re.compile(rb"^([0-9a-f]{8}):((?: [0-9a-f]{8}){4})    ", re.M)
REBOOT = (b"\nIPL g2cd6de2", b"\nStarting kernel")  # с \n: в ASCII-колонке md его нет
ROOT = Path(__file__).resolve().parent.parent


def allowed(cmd):
    return any(p.fullmatch(cmd) for p in ALLOW)


def parse_md(text, start, length):
    """Байты из вывода md.l; None, если адреса не подряд или не хватает."""
    out, addr = bytearray(), start
    for m in LINE.finditer(text):
        if int(m.group(1), 16) != addr:
            return None
        out += b"".join(struct.pack("<I", int(w, 16)) for w in m.group(2).split())
        addr += 16
    return bytes(out) if len(out) == length else None


def selftest():
    t = b"21000000: 56190527 aabbccdd 00000000 ffffffff    '..V............\r\n" \
        b"21000010: 00000001 00000002 00000003 00000004    ................\r\n"
    d = parse_md(t, 0x21000000, 32)
    assert d[:4] == b"\x27\x05\x19\x56" and d[4:8] == b"\xdd\xcc\xbb\xaa" and len(d) == 32
    assert parse_md(t, 0x21000010, 32) is None and parse_md(t, 0x21000000, 48) is None
    assert allowed("md.l 0x21100000 0x40000") and allowed("crc32 0x21000000 0x100000")
    for bad in ("sf write 0x21000000 0 0x1000", "sf erase 0 0x1000", "saveenv", "",
                "crc32 0x21000000 0x100 0x22000000", "md.l 0x21000000 0x40; reset"):
        assert not allowed(bad), bad
    print("selftest ok")


class Uboot:
    def __init__(self, raw):
        import serial
        self.p = serial.Serial("/dev/ttyAMA0", 115200, timeout=0.05)
        self.raw = open(raw, "ab")

    def cmd(self, c, idle=15):
        if not allowed(c):
            sys.exit(f"не в allowlist: {c!r}")
        self.p.reset_input_buffer()
        self.p.write(c.encode() + b"\r")
        buf, last = bytearray(), time.time()
        while True:
            d = self.p.read(65536)
            if d:
                self.raw.write(d); buf += d; last = time.time()
                if any(r in buf[-len(d) - 20:] for r in REBOOT):
                    sys.exit(f"камера перезагрузилась во время {c!r} — стоп")
                if buf.endswith(PROMPT):
                    return bytes(buf)
            elif time.time() - last > idle:
                sys.exit(f"нет ответа {idle} с на {c!r}")

    def crc(self, addr, n):
        m = re.search(rb"==> ([0-9a-f]{8})", self.cmd(f"crc32 {addr:#x} {n:#x}"))
        return int(m.group(1), 16)

    def md(self, addr, n):
        for attempt in range(3):
            data = parse_md(self.cmd(f"md.l {addr:#x} {n // 4:#x}"), addr, n)
            if data and zlib.crc32(data) == self.crc(addr, n):
                return data
            print(f"  {addr:#x}: повтор {attempt + 1}", flush=True)
        sys.exit(f"{addr:#x}: crc не сошёлся 3 раза")


def run(tag):
    probe = tag == "probe"
    size = 0x10000 if probe else SIZE
    u = Uboot(ROOT / f"uart/dump-{tag}-raw.log")
    u.cmd("version")
    u.cmd("sf probe 0")
    print(u.cmd(f"sf read {RAM:#x} 0x0 {size:#x}", idle=60).decode("latin-1").strip(), flush=True)
    full = u.crc(RAM, size)
    print(f"crc32 flash->RAM {size:#x}: {full:08x}", flush=True)
    out, t0 = bytearray(), time.time()
    step = 0x1000 if probe else CHUNK
    for off in range(0, size, step):
        out += u.md(RAM + off, step)
        print(f"  {off + step:#09x}/{size:#x}  {time.time() - t0:.0f} с", flush=True)
    assert zlib.crc32(out) == full, "crc всего образа не сошёлся с U-Boot"
    if probe:
        print(f"probe ok: первые байты {out[:16].hex()}")
        return
    f = ROOT / f"spi/original-{int(tag):02d}.bin"
    f.parent.mkdir(exist_ok=True)
    f.write_bytes(out)
    print(f"готово: {f}  crc32 {full:08x}")


def check(path):
    """Структура dump по карте MTD из boot log; печатает, что нашла."""
    d = Path(path).read_bytes()
    env = d[0x4F000:0x50000]
    ok = [len(d) == SIZE,
          b"bootcmd=sf probe 0;sf read 0x22000000" in env and b"bootdelay=0" in env,
          d[0x50000:0x50004] == b"\x27\x05\x19\x56",
          d[0x250000:0x250004] == b"hsqs"]
    print(f"{path}: size={len(d):#x} env={ok[1]} uImage={ok[2]} "
          f"name={d[0x50020:0x50040].rstrip(bytes(1))!r} squashfs={ok[3]} "
          f"MXP@0x20000={d[0x20000:0x20010].hex()} zlib.crc32={zlib.crc32(d):08x}")
    return all(ok)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a == ["--selftest"]:
        selftest()
    elif a[:1] == ["check"] and len(a) > 1:
        sys.exit(0 if all([check(f) for f in a[1:]]) else 1)
    elif a and a[0] in ("probe", "1", "2", "3"):
        run(a[0])
    else:
        sys.exit(__doc__)
