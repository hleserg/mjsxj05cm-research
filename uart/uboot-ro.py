#!/usr/bin/env python3
"""Остановить U-Boot камеры зажатым Enter и дать ТОЛЬКО команды чтения.

Запуск ДО подачи питания на камеру:  ./uboot-ro.py [команды...]
По умолчанию: version help printenv bdinfo. Другие команды скрипт не пошлёт.
Весь приём пишется в uart/uboot-YYYYMMDD-HHMMSS.log.
Самопроверка разбора приглашения: ./uboot-ro.py --selftest
"""
import re, sys, time
from pathlib import Path

ALLOWED = ("version", "help", "printenv", "bdinfo")
PROMPT = re.compile(rb"\n([^\r\n#]{1,24})# ")


def prompt_of(buf):
    """Строка приглашения, если она повторилась >= 3 раз (эхо наших Enter)."""
    seen = {}
    for m in PROMPT.finditer(buf):
        seen[m.group(1)] = seen.get(m.group(1), 0) + 1
        if seen[m.group(1)] >= 3:
            return m.group(1) + b"# "
    return None


def selftest():
    assert prompt_of(b"\r\nSigmaStar # \r\nSigmaStar # \r\nSigmaStar # ") == b"SigmaStar # "
    assert prompt_of(b"\r\n##  Booting kernel\r\n##  x\r\n##  y\r\n") is None
    assert prompt_of(b"\r\nSigmaStar # \r\nSigmaStar # ") is None
    print("selftest ok")


def main(cmds):
    import serial
    bad = [c for c in cmds if c not in ALLOWED]
    if bad:
        sys.exit(f"запрещено: {bad}; можно только {ALLOWED}")
    port = serial.Serial("/dev/ttyAMA0", 115200, timeout=0.02)
    out = Path(__file__).parent / time.strftime("uboot-%Y%m%d-%H%M%S.log")
    log = open(out, "wb")
    buf = b""

    def rx():
        nonlocal buf
        d = port.read(4096)
        if d:
            log.write(d); log.flush(); buf += d
            sys.stdout.write(d.decode("latin-1")); sys.stdout.flush()

    print(f"пишу {out}\nшлю Enter — ВКЛЮЧАЙ КАМЕРУ (жду 300 с)", flush=True)
    end, prompt = time.time() + 300, None
    while time.time() < end:
        port.write(b"\r")
        rx()
        if b"Starting kernel" in buf:
            break
        prompt = prompt_of(buf)
        if prompt:
            break
    if not prompt:
        t = time.time() + 3
        while time.time() < t:
            rx()
        sys.exit("\nU-Boot не остановился (ушёл в ядро или нет ответа)")

    time.sleep(0.3); rx()
    for c in cmds:
        mark = len(buf)
        port.write(c.encode() + b"\r")
        t = time.time() + 20
        while time.time() < t and buf.rfind(prompt) <= mark + len(c):
            rx()
    print(f"\nготово, приглашение {prompt!r}; камера стоит в U-Boot. Лог: {out}")


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        selftest()
    else:
        main(sys.argv[1:] or list(ALLOWED))
