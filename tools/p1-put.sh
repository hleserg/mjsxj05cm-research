#!/bin/bash
# Положить файлы на p1 карты (FAT; init4.sh монтирует её ro в /tmp/p1) с Pi, без вынимания карты, любого размера:
#   tools/p1-put.sh файл [файл…]        # имя на карте = basename
# Pi раздаёт файлы через `python3 -m http.server` (порт 8765), камера забирает их wget'ом (BusyBox) в /tmp/p1
# (remount rw → wget → sync → ro) и печатает md5 для сравнения. По SSH через base64 нельзя: dropbear рвёт команды >8 КБ.
# Записи на p1 с камеры разрешены; NOR не трогается. Содержимое файлов не печатается (среди них могут быть секреты).
set -eu
cd "$(dirname "$0")/.."
[ $# -ge 1 ] || { echo "usage: $0 файл…"; exit 2; }
PI=${PI_IP:-$(ip -4 route get 192.168.1.53 | sed -n 's/.*src \([0-9.]*\).*/\1/p')}
PORT=${PORT:-8765}
D=$(mktemp -d); trap 'rm -rf "$D"; kill $HTTP 2>/dev/null || true' EXIT
for f in "$@"; do ln -s "$(realpath "$f")" "$D/$(basename "$f")"; done
( cd "$D" && python3 -m http.server "$PORT" --bind "$PI" >/dev/null 2>&1 ) & HTTP=$!
sleep 1
ssh() { python3 uart/camssh.py "$1"; }
ssh "mount -o remount,rw /tmp/p1 && cd /tmp/p1 && for f in $(for f in "$@"; do printf '%s ' "$(basename "$f")"; done); do wget -q -O \$f.tmp http://$PI:$PORT/\$f && mv \$f.tmp \$f || { rm -f \$f.tmp; echo \"ОШИБКА \$f\"; }; done; sync; mount -o remount,ro /tmp/p1; cd /tmp/p1 && md5sum $(for f in "$@"; do printf '%s ' "$(basename "$f")"; done)"
echo "--- ожидаю md5:"; for f in "$@"; do md5sum "$f" | sed "s| .*| $(basename "$f")|"; done
