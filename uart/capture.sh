#!/bin/sh
# RX-only захват boot log камеры. Ничего не шлёт в порт.
# Запуск ДО подачи питания на камеру: ./capture.sh [baud] [секунд]
PORT=${PORT:-/dev/ttyAMA0}; BAUD=${1:-115200}; T=${2:-180}
DIR=$(dirname "$0"); OUT=$DIR/boot-$(date +%Y%m%d-%H%M%S).log
[ -c "$PORT" ] || { echo "нет $PORT: сначала sudo dtoverlay uart0-pi5"; exit 1; }
stty -F "$PORT" "$BAUD" cs8 -parenb -cstopb -ixon -ixoff -crtscts -hupcl raw -echo || exit 1
echo "$(date -Is) $PORT $BAUD ${T}s -> $(basename "$OUT")" >> "$DIR/captures.txt"
echo "пишу $OUT, включай камеру"; timeout "${T}s" cat "$PORT" | tee "$OUT"
echo; echo "байт: $(wc -c < "$OUT")"
