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
# 30.09: watchdog majestic ВКЛ (аппаратный WDT): камера зависла 30.09 ~08:15 без паники и без ребута — 3 ч мёртвая до пауэр-цикла.
# Отключали 28.09 из-за ребутов при нехватке MMA — с mma_heap 0x1800000 (mma fail 0) причина ушла. Конфиг подменяем bind-mount, /etc read-only.
# аудио включаем ДО первого старта majestic: каждый рестарт majestic течёт по MMA (сбросы 12:33 и 16:37).
# 28.09 21:52: SUB (video1 704x576@15) включаем после heap-теста (mma_heap 0x1800000) — отдельный ребут; motionDetect — ребут #3 (21:55, после SUB ОК).
# 28.09 23:55: ONVIF-логин admin + пароль с p1 (onvif-password.txt, в репо НЕТ — p4/secret/): без onvif.password majestic
# отвергает WSSE PasswordDigest (Onvifer, ODM) — в /etc/shadow только хеш, дайджест считать не из чего.
OPW=$(sed -n 1p /tmp/p1/onvif-password.txt 2>/dev/null)
# 29.09 16:55: p4 карты (FAT32 DATA, docs/p4-plan.md) — локальная запись majestic «вкруг» в /tmp/p4; нет p4 → records остаются выкл.
# 30.09: лог ядра/системы на p4 (переживает зависание; читать после пауэр-цикла), ротация 2×1 МБ.
mkdir -p /tmp/p4; mount -t vfat -o rw,noatime /dev/mmcblk0p4 /tmp/p4 && REC='/^records:/,/^[a-z]/ { s/enabled: false/enabled: true/; s|path: .*|path: /tmp/p4/%F|; s/maxUsage: 95/maxUsage: 90/ }' || REC=''
mountpoint -q /tmp/p4 && { syslogd -O /tmp/p4/syslog.log -s 1024 -b 2; klogd; }
sed -e '/^video1:/,/^[a-z]/ s/enabled: false/enabled: true/' \
    -e "/^onvif:/,/^[a-z]/ { s/^  # username: root/  username: admin/; s|^  # password: \"\"|  password: ${OPW:-changeme}| }" \
    -e '/^motionDetect:/,/^[a-z]/ s/enabled: false/enabled: true/' \
    -e "$REC" \
    -e '/^audio:/,/^[a-z]/ { s/enabled: false/enabled: true/; s/outputEnabled: false/outputEnabled: true/; s/  volume: 30/  volume: 100/; s/outputVolume: 30/outputVolume: 60/ }' /etc/majestic.yaml > /tmp/m.yaml
grep -A2 '^watchdog:' /tmp/m.yaml
mountpoint -q /etc/majestic.yaml || mount --bind /tmp/m.yaml /etc/majestic.yaml
# 28.09 18:40: majestic непрерывно (~10/с) печатает в консоль "[MI ERR] … vpe0-out0-1 … mma fail" (3-й буфер 0x2fd000 не влезает
# в mma_heap) — на UART 115200 это ~2 КБ/с и load ~9. Консоль только до KERN_ERR (уровень 4 режет флуд: замер +100 Б/с); EMERG/panic видны.
echo "4 4 1 7" > /proc/sys/kernel/printk
/etc/init.d/S95majestic start
sleep 4; ps | grep -v "sh -c" | grep "[m]ajestic"; free | head -2; cat /sys/class/watchdog/watchdog0/state 2>/dev/null
echo CAM_UP_done
