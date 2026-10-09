#!/bin/bash
# Переключение режима загрузки камеры БЕЗ записи во флеш (env v4/v5 в NOR: bootcmd=run sdboot; run norboot):
#   tools/boot-mode.sh status   # откуда загружена сейчас и что будет при следующей загрузке
#   tools/boot-mode.sh sd       # следующая загрузка — с карты (uImage.ssc325 на p1 виден U-Boot)
#   tools/boot-mode.sh nor      # следующая загрузка — из NOR (uImage.ssc325 переименован в .off; fatload не находит → norboot)
# Работает по SSH камеры (uart/camssh.py). Перезагрузку НЕ делает — печатает команду; её запускает владелец.
# Режим NOR имеет смысл только после записи OpenIPC в NOR (uboot/STOP-nor.md); до неё norboot = сток Xiaomi.
set -eu
cd "$(dirname "$0")/.."
U=/tmp/p1/uImage.ssc325
ssh() { python3 uart/camssh.py "$1"; }
case "${1:-status}" in
  status)
    ssh "echo \"сейчас: \$(hostname), root=\$(sed 's/.*root=\([^ ]*\).*/\1/' /proc/cmdline)\"; [ -f $U ] && echo 'следующая загрузка: карта (uImage.ssc325 на p1)' || { [ -f $U.off ] && echo 'следующая загрузка: NOR (uImage.ssc325.off)' || echo 'p1 не смонтирован / файла нет: NOR'; }" ;;
  nor) ssh "mount -o remount,rw /tmp/p1 && mv $U $U.off && sync; mount -o remount,ro /tmp/p1; ls /tmp/p1/uImage*" ;;
  sd)  ssh "mount -o remount,rw /tmp/p1 && mv $U.off $U && sync; mount -o remount,ro /tmp/p1; ls /tmp/p1/uImage*" ;;
  *) echo "usage: $0 status|sd|nor"; exit 2 ;;
esac
[ "${1:-status}" = status ] || echo "применится после перезагрузки: timeout 12 python3 uart/camssh.py 'sync; reboot -f'   (а затем tools/boot-mode.sh status)"
