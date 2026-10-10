#!/bin/sh
# CGI для кнопок PTZ (HA rest_command). Живёт на p1 как ptz-cgi.sh, autorun кладёт в /tmp/www/cgi-bin/ptz и
# поднимает `httpd -p 8080 -h /tmp/www`. /tmp/www — ТОЛЬКО этот каталог: в /tmp лежат секреты (p4/secret, p1).
# Запросы: ?left=N ?right=N ?up=N ?down=N (полушаги, 1..4300) ?home. Без auth: сегмент Cam достижим только из Home/WG.
# Ответ сразу (`ok`/`busy`/`bad`), движение — фоном; замок /tmp/ptz.lock не даёт двум нажатиям переплести обмотки.
echo "Content-Type: text/plain"; echo
q=$QUERY_STRING; k=${q%%=*}; n=${q#*=}
case "$k" in left) m="h +";; right) m="h -";; up) m="v +";; down) m="v -";; home) m=home; n=;; *) echo bad; exit 0;; esac
if [ -n "$n" ]; then case "$n" in ''|*[!0-9]*) echo bad; exit 0;; esac; [ "$n" -ge 1 ] && [ "$n" -le 4300 ] || { echo bad; exit 0; }; fi
mkdir /tmp/ptz.lock 2>/dev/null || { echo busy; exit 0; }
( trap 'rmdir /tmp/ptz.lock' EXIT; sh /tmp/ptz.sh $m $n ) </dev/null >/dev/null 2>&1 &
echo ok
