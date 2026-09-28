#!/bin/sh
# Поднять видеостек OpenIPC на камере после загрузки с карты (RAM, NOR не трогает).
# Запуск: autorun.sh с p1 карты (автоматически) или с Pi: python3 uart/camssh.py "$(cat firmware/openipc-ipc017-20260926/p4/cam-up.sh)"
# Порядок insmod = /usr/bin/load_sigmastar (сам load_sigmastar НЕ запускать: fw_setenv sensor).
# Защита: majestic уже работает → выходим. Повторный старт majestic течёт по MMA (headroom ноль) — сбросы 12:33 и 16:37.
pidof majestic > /dev/null && { echo "majestic уже работает — второй старт не делаем (MMA)"; exit 0; }
M=/lib/modules/4.9.84/sigmastar
for m in mhal mi_common "mi_sys logBufSize=256 default_config_path=/usr/bin" mi_rgn mi_ai mi_ao mi_sensor mi_shadow mi_divp mi_vif mi_vpe mi_venc; do
  set -- $m; n=$1; shift; lsmod | grep -q "^$n " || insmod $M/$n.ko "$@" || echo "FAIL insmod $n"
done
lsmod | grep -q "^sensor_gc2053_mipi " || insmod $M/sensor_gc2053_mipi.ko chmap=1 || echo "FAIL sensor"
# watchdog majestic ВЫКЛ (ребут 28.09 12:33 при нехватке MMA); конфиг подменяем bind-mount, /etc read-only.
# аудио включаем ДО первого старта majestic: каждый рестарт majestic течёт по MMA (сбросы 12:33 и 16:37).
# 28.09 21:52: SUB (video1 704x576@15) включаем после heap-теста (mma_heap 0x1800000) — отдельный ребут; motionDetect — следующим ребутом.
sed -e '/^video1:/,/^[a-z]/ s/enabled: false/enabled: true/' \
    -e '/^watchdog:/,/^[a-z]/ s/enabled: true/enabled: false/' \
    -e '/^audio:/,/^[a-z]/ { s/enabled: false/enabled: true/; s/outputEnabled: false/outputEnabled: true/; s/  volume: 30/  volume: 100/; s/outputVolume: 30/outputVolume: 60/ }' /etc/majestic.yaml > /tmp/m.yaml
grep -A2 '^watchdog:' /tmp/m.yaml
mountpoint -q /etc/majestic.yaml || mount --bind /tmp/m.yaml /etc/majestic.yaml
# 28.09 18:40: majestic непрерывно (~10/с) печатает в консоль "[MI ERR] … vpe0-out0-1 … mma fail" (3-й буфер 0x2fd000 не влезает
# в mma_heap) — на UART 115200 это ~2 КБ/с и load ~9. Консоль только до KERN_ERR (уровень 4 режет флуд: замер +100 Б/с); EMERG/panic видны.
echo "4 4 1 7" > /proc/sys/kernel/printk
/etc/init.d/S95majestic start
sleep 4; ps | grep -v "sh -c" | grep "[m]ajestic"; free | head -2; cat /sys/class/watchdog/watchdog0/state 2>/dev/null
echo CAM_UP_done
