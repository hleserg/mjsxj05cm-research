#!/bin/sh
# autorun.sh — лежит на p1 карты (FAT32) рядом с cam-up.sh/ptz.sh/demo.sh. Запускают: init4.sh v7 (хук после SSH_READY,
# фоном) или uart/postboot.sh с Pi по SSH (интерим, пока карта без v7). RAM-only, NOR не трогает.
# Идемпотентен: второй запуск (оба хука сразу) выходит по /tmp/autorun.lock — повторный cam-up.sh = рестарт majestic = MMA-сброс.
# Менять без пересборки squashfs: на камере `mount -o remount,rw /tmp/p1; cp …; sync; mount -o remount,ro /tmp/p1`.
mkdir /tmp/autorun.lock 2>/dev/null || { echo "autorun уже был"; exit 0; }
D=$(dirname "$0")
cp "$D"/cam-up.sh "$D"/ptz.sh "$D"/demo.sh "$D"/ptz /tmp/ 2>/dev/null; chmod 755 /tmp/*.sh /tmp/ptz
# кнопки PTZ для HA: httpd отдаёт ТОЛЬКО /tmp/www (в /tmp секреты), см. ptz-cgi.sh
mkdir -p /tmp/www/cgi-bin; cp "$D"/ptz-cgi.sh /tmp/www/cgi-bin/ptz; chmod 755 /tmp/www/cgi-bin/ptz; httpd -p 8080 -h /tmp/www
gw=$(ip route | awk '/^default/{print $3}')
# время: роутер отдаёт NTP, pool.ntp.org из LAN не резолвится (28.09). Разово со сдвигом, затем демон от дрейфа.
[ -n "$gw" ] && { timeout 15 ntpd -n -q -p "$gw"; ntpd -p "$gw"; }
date
sh /tmp/cam-up.sh
sh /tmp/ptz.sh init
[ -x /tmp/ptz ] && sh /tmp/ptz.sh home   # центрирование как у стока; только бинарником (шеллом это 4 минуты)
echo AUTORUN_done
