#!/bin/sh
# onvif-ptz.sh — PTZ-команды от onvif_simple_server (ContinuousMove/Stop/GotoHomePosition → system()) к /tmp/ptz.
# $1 = left|right|up|down|stop|home; скорость (%f) и таймаут (%s) игнорируем — ponytail: одна скорость (PTZ_US=2000).
# Замок /tmp/ptz.lock общий с ptz-cgi.sh (кнопки HA): занято — молча выходим. Всегда exit 0, иначе сервер отдаст SOAP Fault.
# Движение фоном без наследования pipe CGI (иначе httpd ждёт EOF и SOAP-ответ виснет). stop = killall ptz: бинарник на SIGTERM
# обесточивает катушки и выходит 143 → цепочка `&&` в ptz.sh home тоже останавливается; замок снимает trap в субшелле.
case "$1" in
  left)  A="h + 4300" ;;   # h+ = влево (калибровка 10.10)
  right) A="h - 4300" ;;
  up)    A="v + 800" ;;    # v+ = вверх
  down)  A="v - 800" ;;
  stop)  killall ptz 2>/dev/null; exit 0 ;;
  moving) [ -d /tmp/ptz.lock ] && echo 1 || echo 0; exit 0 ;;   # is_moving для GetStatus
  pos)   echo 0,0,0; exit 0 ;;   # get_position: позицию не считаем (ponytail); без обеих команд GetStatus = Fault NoStatus
  home)  A=home ;;
  *)     exit 0 ;;
esac
mkdir /tmp/ptz.lock 2>/dev/null || exit 0
if [ "$A" = home ]; then ( trap 'rmdir /tmp/ptz.lock' EXIT; sh /tmp/ptz.sh home ) </dev/null >/dev/null 2>&1 &
else ( trap 'rmdir /tmp/ptz.lock' EXIT; /tmp/ptz $A ) </dev/null >/dev/null 2>&1 & fi
exit 0
