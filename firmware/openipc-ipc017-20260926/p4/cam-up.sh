# Поднять видеостек OpenIPC на камере после загрузки с карты (RAM, NOR не трогает).
# Запуск с Pi:  python3 uart/camssh.py "$(cat firmware/openipc-ipc017-20260926/p4/cam-up.sh)"
# Порядок insmod = /usr/bin/load_sigmastar (сам load_sigmastar НЕ запускать: fw_setenv sensor).
M=/lib/modules/4.9.84/sigmastar
for m in mhal mi_common "mi_sys logBufSize=256 default_config_path=/usr/bin" mi_rgn mi_ai mi_ao mi_sensor mi_shadow mi_divp mi_vif mi_vpe mi_venc; do
  set -- $m; n=$1; shift; lsmod | grep -q "^$n " || insmod $M/$n.ko "$@" || echo "FAIL insmod $n"
done
lsmod | grep -q "^sensor_gc2053_mipi " || insmod $M/sensor_gc2053_mipi.ko chmap=1 || echo "FAIL sensor"
# watchdog majestic ВЫКЛ (ребут 28.09 12:33 при нехватке MMA); конфиг подменяем bind-mount, /etc read-only.
# аудио включаем ДО первого старта majestic: каждый рестарт majestic течёт по MMA (сбросы 12:33 и 16:37).
sed -e '/^watchdog:/,/^[a-z]/ s/enabled: true/enabled: false/' \
    -e '/^audio:/,/^[a-z]/ { s/enabled: false/enabled: true/; s/outputEnabled: false/outputEnabled: true/; s/  volume: 30/  volume: 100/; s/outputVolume: 30/outputVolume: 60/ }' /etc/majestic.yaml > /tmp/m.yaml
grep -A2 '^watchdog:' /tmp/m.yaml
mountpoint -q /etc/majestic.yaml || mount --bind /tmp/m.yaml /etc/majestic.yaml
/etc/init.d/S95majestic start
sleep 4; ps | grep -v "sh -c" | grep "[m]ajestic"; free | head -2; cat /sys/class/watchdog/watchdog0/state 2>/dev/null
echo CAM_UP_done
