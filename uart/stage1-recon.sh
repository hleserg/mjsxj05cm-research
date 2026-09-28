# Этап 1: команды для стокового shell (init=/bin/sh), шлются построчно через uart/console.in:
#   while read -r l; do [ -n "$l" ] && [ "${l#\#}" = "$l" ] && echo "$l" > uart/console.in && sleep 2; done < uart/stage1-recon.sh
# Только чтение. DATA (/dev/mtdblock3) монтировать только ro. Ничего в /config, /data, /mnt не писать.
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t debugfs debugfs /sys/kernel/debug
cat /proc/cmdline
cat /proc/mtd
cat /proc/cpuinfo
cat /proc/meminfo
cat /proc/partitions
ls -l /dev | head -80
cat /sys/kernel/debug/gpio
ls /sys/class/gpio
cat /sys/class/pwm/*/npwm 2>/dev/null
lsmod
dmesg
cat /etc/inittab
ls -l /etc/init.d
mkdir -p /tmp/cfg && mount -t jffs2 -o ro /dev/mtdblock3 /tmp/cfg && ls -lR /tmp/cfg | head -100
sh /etc/init.d/S09mstar_ko start
lsmod
cat /sys/kernel/debug/gpio
ls -l /dev | grep -i "mi_\|mstar\|motor\|gpio\|pwm\|i2c\|spi"
# --- моторы/PWM/GPIO (карта из research/stock-gpio-map.md). export в sysfs — не запись во flash,
#     пин не переключаем (direction не трогаем, value только читаем). Числа проверить с картой.
ls -l /sys/devices/virtual/mstar/motor/ 2>/dev/null
for f in /sys/devices/virtual/mstar/motor/*; do echo "== $f"; cat "$f"; done
ls /sys/class/pwm/pwmchip0/ 2>/dev/null; cat /sys/class/pwm/pwmchip0/npwm
for g in 14 15 16 44 45 46 47 52 62 66 76 77 78 79 80; do [ -d /sys/class/gpio/gpio$g ] || echo $g > /sys/class/gpio/export; echo "gpio$g $(cat /sys/class/gpio/gpio$g/direction) $(cat /sys/class/gpio/gpio$g/value)"; done
