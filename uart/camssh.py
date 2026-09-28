#!/usr/bin/env python3
"""SSH на камеру (dropbear на карте, root по паролю из p4/secret/root-password.txt — пароль не печатается).
   uart/camssh.py 'cmd; cmd2'     — выполнить и напечатать stdout+stderr
"""
import sys, pathlib, paramiko
HOST = "192.168.1.53"
PW = (pathlib.Path(__file__).resolve().parents[1] / "firmware/openipc-ipc017-20260926/p4/secret/root-password.txt").read_text().strip()
c = paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username="root", password=PW, timeout=10, allow_agent=False, look_for_keys=False)
_, out, err = c.exec_command(sys.argv[1], timeout=120)
sys.stdout.write(out.read().decode("utf-8", "replace")); sys.stdout.write(err.read().decode("utf-8", "replace"))
c.close()
