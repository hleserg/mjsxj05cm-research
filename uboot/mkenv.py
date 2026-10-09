#!/usr/bin/env python3
"""Собрать новый 4K-блок U-Boot env (0x4F000) из стокового дампа: bootcmd = карта (SD p3, init4.sh), откат на NOR.
Только готовит файл и печатает sha256 старого/нового блока для STOP-запроса. ВО FLASH НИЧЕГО НЕ ПИШЕТ.
  python3 uboot/mkenv.py [out.bin]      # out по умолчанию — /tmp/env-new.bin (содержит MAC → не в репо)
  python3 uboot/mkenv.py uboot/env-new-v5.bin --nor=openipc   # 09.10: v5 — norargs для OpenIPC из NOR (root=/dev/mtdblock2); без --nor → v4
  MMA_SZ=0x1800000 python3 uboot/mkenv.py   # куча как в uart/stage.py
Факты (research/uboot-env-notes.md 28.09): env @0x4F000 размер 0x1000, CRC32 первых 4 байт по остальным 4092,
переменные 'k=v\\0', конец '\\0\\0', хвост нулями (так пишет saveenv); saveenv стирает только этот 4K-сектор;
парсер U-Boot простой (без if/then): команды через ';' идут все подряд, поэтому mw.l гасит magic перед fatload,
чтобы без карты bootm не подхватил старое ядро из DRAM, а прошёл дальше к NOR.
Оговорка: `saveenv` после fatload запишет ещё fileaddr/filesize из RAM-env → блок в NOR не совпадёт побайтово с этим
файлом; побайтовое совпадение даёт только `sf write` этого файла. Репетиция в RAM: этап 2a-p4-env в uart/stage.py
(fatload env-new.bin с p1 → env import -c → run bootcmd).
"""
import hashlib, os, re, struct, sys, zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "uart"))
from stage import SD_ARGS, SDBOOT, NORBOOT, NOR_ARGS  # noqa: E402  — единый источник с uart/stage.py (MMA_SZ учитывается там)

OFF, SIZE = 0x4F000, 0x1000


def parse(blk):
    crc, = struct.unpack("<I", blk[:4])
    assert crc == zlib.crc32(blk[4:]) & 0xFFFFFFFF, "CRC стокового env не сходится"
    end = blk.find(b"\0\0", 4)
    return dict(kv.decode().split("=", 1) for kv in blk[4:end].split(b"\0"))


def build(env):
    body = b"".join(f"{k}={v}".encode() + b"\0" for k, v in sorted(env.items())) + b"\0"
    assert len(body) <= SIZE - 4, "env не влезает в 4092 байта"
    body = body.ljust(SIZE - 4, b"\0")
    return struct.pack("<I", zlib.crc32(body) & 0xFFFFFFFF) + body


def mask(s):
    return re.sub(r"([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}", "MAC", re.sub(r"(\d+\.){3}\d+", "IP", s))


def main(out, nor="stock"):   # 09.10: nor=openipc → norargs для OpenIPC из NOR (env v5); stock → v4 (воспроизводимо)
    old = (ROOT / "spi/original-01.bin").read_bytes()[OFF:OFF + SIZE]
    env = parse(old)
    assert build(env) == old, "пересборка стокового env не побайтовая — формат понят неверно"
    new_env = dict(env, bootcmd="run sdboot; run norboot", sdboot=SDBOOT, norboot=NORBOOT,
                   sdargs=SD_ARGS, norargs=env["bootargs"] if nor == "stock" else NOR_ARGS)
    new = build(new_env)
    Path(out).write_bytes(new)
    # crc32 по всем 4096 байтам — то, что печатает U-Boot `crc32 <addr> 0x1000` (после sf read / fatload): единственная проверка внутри U-Boot.
    print(f"смещение 0x{OFF:X} размер 0x{SIZE:X}\nsha256 старого: {hashlib.sha256(old).hexdigest()}  crc32(4096) {zlib.crc32(old) & 0xFFFFFFFF:08x}"
          f"\nsha256 нового:  {hashlib.sha256(new).hexdigest()}  crc32(4096) {zlib.crc32(new) & 0xFFFFFFFF:08x}"
          f"\nфайл: {out} ({len(new)} Б, занято {new.find(b'\0\0', 4) + 2} Б)")
    for k in sorted(new_env):
        if new_env[k] != env.get(k):
            print(f"  {'+' if k not in env else '~'} {k}={mask(new_env[k])}")
    print("Проверка формата: parse(build(new)) == new_env:", parse(new) == new_env)


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    main(a[0] if a else "/tmp/env-new.bin", next((x[6:] for x in sys.argv[1:] if x.startswith("--nor=")), "stock"))
