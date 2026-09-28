#!/bin/bash
# Этап 2a-p4: следит за логом stage.py и по маркерам init4.sh шлёт строки в консоль камеры через uart/console.in.
#   uart/win4.sh uart/stage-2a-p4-<время>.log
# Окна: A/B/C/D — по одной строке через 3 с после WIN_x_START; во время HEAVY_TX_with_RX — 8 строк по одной в секунду.
# В строках нет цифр 1 и 2 (пять подряд '1' или '2' — магия драйвера ms_uart: тихий режим / отключение пада).
set -u
LOG=$1; FIFO=$(dirname "$0")/console.in
send() { echo "$1" > "$FIFO"; echo "$(date +%T) sent: $1"; }
tail -F -n0 "$LOG" 2>/dev/null | while IFS= read -r l; do
  case "$l" in
    *WIN_A_START*) sleep 3; send "echo HELLO_A" ;;
    *WIN_B_START*) sleep 3; send "echo HELLO_B" ;;
    *WIN_C_START*) sleep 3; send "echo HELLO_C" ;;
    *WIN_D_START*) sleep 3; send "echo HELLO_D" ;;
    *HEAVY_TX_with_RX_start*) for x in a b c d e f g h; do sleep 1; send "echo DURING_$x"; done ;;
    *INIT4_SHELL_forever*) sleep 3; send "echo SHELL_ALIVE"; echo "готово, выхожу"; exit 0 ;;
  esac
done
