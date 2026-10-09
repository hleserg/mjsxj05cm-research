#!/bin/bash
# Положить файлы на p1 карты (FAT; init4.sh монтирует её ro в /tmp/p1) с Pi, без вынимания карты, любого размера:
#   tools/p1-put.sh файл [файл…]        # имя на карте = basename; адрес камеры — CAM_HOST (см. uart/camssh.py)
# v2 09.10: Pi сам шлёт файл по ssh (camssh.py --put, stdin → cat): камера в Cam-сегменте (protected) не достаёт до Pi,
# прежний http.server+wget оттуда не работает. Через base64 в команде нельзя: dropbear рвёт команды >8 КБ, stdin — без предела.
# p1: remount rw → файлы → sync → ro; печатает md5 камеры и ожидаемый. Записи на p1 с камеры разрешены; NOR не трогается.
set -eu
cd "$(dirname "$0")/.."
[ $# -ge 1 ] || { echo "usage: $0 файл…"; exit 2; }
ssh() { python3 uart/camssh.py "$@"; }
ssh "mount -o remount,rw /tmp/p1"
for f in "$@"; do ssh --put "$f" "/tmp/p1/$(basename "$f")"; done
ssh "sync; mount -o remount,ro /tmp/p1"
echo "--- ожидаю md5:"; for f in "$@"; do md5sum "$f" | sed "s| .*| /tmp/p1/$(basename "$f")|"; done
