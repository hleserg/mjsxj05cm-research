#!/bin/bash
# Интерим-хук: stage.py запускает его, увидев в UART «SSH_READY_ip» (init4.sh поднял dropbear).
# Гоняет autorun.sh с p1 карты по SSH — пока карта без init4.sh v7 (там тот же хук внутри init). Лог uart/postboot.log.
cd "$(dirname "$0")/.."
for i in $(seq 1 12); do
  sleep 10
  if python3 uart/camssh.py 'mkdir -p /tmp/p1; mountpoint -q /tmp/p1 || mount -o ro -t vfat /dev/mmcblk0p1 /tmp/p1; [ -f /tmp/p1/autorun.sh ] && sh /tmp/p1/autorun.sh || echo "autorun.sh на p1 нет"' >> uart/postboot.log 2>&1; then
    echo "$(date +%T) postboot ок (попытка $i)" >> uart/postboot.log; exit 0
  fi
  echo "$(date +%T) ssh не ответил (попытка $i)" >> uart/postboot.log
done
exit 1
