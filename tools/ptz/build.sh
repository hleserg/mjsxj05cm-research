#!/bin/bash
# Сборка ptz для камеры (armv7 musl armhf, Cortex-A7). zig: ~/.local/zigenv (pip install ziglang).
set -eu; cd "$(dirname "$0")"
~/.local/zigenv/bin/python -m ziglang cc -target arm-linux-musleabihf -mcpu=cortex_a7 -Os -s -static -o ../../firmware/openipc-ipc017-20260926/p4/ptz ptz.c
file ../../firmware/openipc-ipc017-20260926/p4/ptz
