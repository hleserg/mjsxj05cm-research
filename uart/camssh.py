#!/usr/bin/env python3
"""SSH на камеру (dropbear на карте, root по паролю из p4/secret/root-password.txt — пароль не печатается).
   uart/camssh.py 'cmd; cmd2'     — выполнить и напечатать stdout+stderr
   uart/camssh.py --put src dst   — файл на камеру через stdin (dropbear рвёт команды >8 КБ, stdin не ограничен); печатает md5
   uart/camssh.py --get src dst   — файл с камеры на Pi двоично (дампы mtd)
   uart/camssh.py --pipe 'cmd' dst — stdout команды в файл на Pi двоично (tar потоком: /tmp камеры мал)
   Адрес: CAM_HOST (по умолчанию 192.168.30.53 — beta-cam, Cam-сегмент; старый адрес 192.168.1.53).
"""
import sys, pathlib, paramiko
import os
HOST = os.environ.get("CAM_HOST", "192.168.30.53")
PW = (pathlib.Path(__file__).resolve().parents[1] / "firmware/openipc-ipc017-20260926/p4/secret/root-password.txt").read_text().strip()
c = paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", password=PW, timeout=10, allow_agent=False, look_for_keys=False)
if sys.argv[1] == "--put":
    src, dst = sys.argv[2:4]
    i, out, err = c.exec_command(f"cat > '{dst}.tmp' && mv '{dst}.tmp' '{dst}' && md5sum '{dst}'", timeout=900)
    with open(src, "rb") as f:
        for b in iter(lambda: f.read(65536), b""): i.write(b)
    i.channel.shutdown_write()
elif sys.argv[1] in ("--get", "--pipe"):          # --get src dst — файл с камеры двоично; --pipe 'cmd' dst — stdout команды в файл
    src, dst = sys.argv[2:4]
    _, out, err = c.exec_command(src if sys.argv[1] == "--pipe" else f"cat '{src}'", timeout=900)
    with open(dst, "wb") as f:
        for b in iter(lambda: out.read(65536), b""): f.write(b)
    sys.stdout.write(err.read().decode("utf-8", "replace")); c.close(); sys.exit(0)
else:
    _, out, err = c.exec_command(sys.argv[1], timeout=120)
sys.stdout.write(out.read().decode("utf-8", "replace")); sys.stdout.write(err.read().decode("utf-8", "replace"))
c.close()
