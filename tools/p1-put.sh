#!/bin/bash
# Положить на p1 карты (FAT; init4.sh монтирует её ro в /tmp/p1) файлы с Pi через SSH камеры (uart/camssh.py), без вынимания карты:
#   tools/p1-put.sh <env-new.bin из uboot/mkenv.py>
# Кладёт: env-new.bin (блок env для nor-env-write), p4/cam-up.sh, p4/secret/onvif-password.txt (в репо НЕТ). Печатает md5 на карте и ожидаемые.
# Записи на p1 с камеры разрешены (remount rw → write → sync → ro); NOR не трогается.
set -eu
cd "$(dirname "$0")/.."
ENV=${1:?путь к env-new.bin}
P4=firmware/openipc-ipc017-20260926/p4
b64() { base64 -w0 "$1"; }
put() { echo "echo $(b64 "$1") | base64 -d > /tmp/p1/$2"; }
# одной командой (~8 КБ b64) dropbear рвёт сессию (EOFError 29.09 00:21) — по одному файлу на вызов
ssh() { python3 uart/camssh.py "$1"; }
ssh "mount -o remount,rw /tmp/p1 && $(put "$ENV" env-new.bin)"
ssh "$(put $P4/cam-up.sh cam-up.sh)"
ssh "$(put $P4/secret/onvif-password.txt onvif-password.txt); sync; mount -o remount,ro /tmp/p1; md5sum /tmp/p1/env-new.bin /tmp/p1/cam-up.sh; ls -l /tmp/p1 | grep -v onvif-password"
echo "--- ожидаю md5:"; md5sum "$ENV" $P4/cam-up.sh
