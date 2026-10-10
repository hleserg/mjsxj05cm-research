#!/bin/sh
# autorun.sh — лежит на p1 карты (FAT32) рядом с cam-up.sh/ptz.sh/demo.sh. Запускают: init4.sh v7 (хук после SSH_READY,
# фоном) или uart/postboot.sh с Pi по SSH (интерим, пока карта без v7). RAM-only, NOR не трогает.
# Идемпотентен: второй запуск (оба хука сразу) выходит по /tmp/autorun.lock — повторный cam-up.sh = рестарт majestic = MMA-сброс.
# Менять без пересборки squashfs: на камере `mount -o remount,rw /tmp/p1; cp …; sync; mount -o remount,ro /tmp/p1`.
mkdir /tmp/autorun.lock 2>/dev/null || { echo "autorun уже был"; exit 0; }
D=$(dirname "$0")
cp "$D"/cam-up.sh "$D"/ptz.sh "$D"/demo.sh "$D"/dance.sh "$D"/ptz /tmp/ 2>/dev/null; chmod 755 /tmp/*.sh /tmp/ptz
gw=$(ip route | awk '/^default/{print $3}')
# время: роутер отдаёт NTP, pool.ntp.org из LAN не резолвится (28.09). Разово со сдвигом, затем демон от дрейфа.
[ -n "$gw" ] && { timeout 15 ntpd -n -q -p "$gw"; ntpd -p "$gw"; }
date
sh /tmp/cam-up.sh
sh /tmp/ptz.sh init
[ -x /tmp/ptz ] && sh /tmp/ptz.sh home   # центрирование как у стока; только бинарником (шеллом это 4 минуты)
# кнопки PTZ для HA — после home, чтобы кнопка не перебила центрирование: httpd отдаёт ТОЛЬКО /tmp/www (в /tmp секреты), см. ptz-cgi.sh
mkdir -p /tmp/www/cgi-bin; cp "$D"/ptz-cgi.sh /tmp/www/cgi-bin/ptz; chmod 755 /tmp/www/cgi-bin/ptz
# ONVIF для Onvifer (у majestic нет мотор-драйвера): onvif_simple_server как CGI на том же httpd, PTZ → onvif-ptz.sh → /tmp/ptz.
# p1 — FAT (нет симлинков и +x), поэтому tgz + ln после распаковки; пароль admin берётся из onvif-password.txt, в конфиг на RAM.
O=/tmp/www/cgi-bin/onvif; mkdir -p $O /tmp/onvif; zcat "$D"/onvif.tgz | tar x -C $O && chmod 755 $O/onvif_simple_server
for s in device_service media_service ptz_service; do ln -sf onvif_simple_server $O/$s; done
cp "$D"/onvif-ptz.sh /tmp/; chmod 755 /tmp/onvif-ptz.sh
sed "s|__PW__|$(sed -n 1p "$D"/onvif-password.txt)|" "$D"/onvif.conf.tpl > /tmp/onvif/onvif_simple_server.conf
# Onvifer принимает только host+port (путь /onvif/device_service), httpd CGI только под /cgi-bin/ → свой порт 8082: tcpserve + onvif-serve.sh
# (шапки обоих). nc -ll -e не годится: vfork-ребёнок виснет в futex, родитель в D — порт умирает после десятка соединений.
cp "$D"/onvif-serve.sh "$D"/tcpserve /tmp/; chmod 755 /tmp/onvif-serve.sh /tmp/tcpserve; setsid /tmp/tcpserve 8082 /tmp/onvif-serve.sh </dev/null >/dev/null 2>&1 &
httpd -p 8080 -h /tmp/www
echo AUTORUN_done
