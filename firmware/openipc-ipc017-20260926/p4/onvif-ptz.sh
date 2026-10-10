#!/bin/sh
# onvif-ptz.sh — PTZ-команды от onvif_simple_server (ContinuousMove/Stop/GotoHomePosition → system()) к /tmp/ptz.
# $1 = left|right|up|down [скорость 0..1] | stop | home | rel dx dy | pos | moving. Таймаут (%s) игнорируем.
# Скорость → пауза полушага: us = 2000/s в [2000..20000]: слайдер «PTZ чувствительность» Onvifer шлёт 0.2/0.5/1.0 (1.0 = как было).
# Диагональ: OSS зовёт move_x и move_y двумя system() подряд. Первый вызов берёт замок, пишет ось в /tmp/ptz.lock/h|v и 100 мс
# ждёт вторую; второй вызов видит замок с ожидающей осью и дописывает свою. Потом один `ptz hv` (обе оси вперемежку).
# Замок /tmp/ptz.lock общий с ptz-cgi.sh (кнопки HA): занято — молча выходим. Всегда exit 0, иначе сервер отдаст SOAP Fault.
# Движение фоном без наследования pipe CGI (иначе httpd ждёт EOF и SOAP-ответ виснет). stop = killall ptz: бинарник на SIGTERM
# обесточивает катушки и выходит 143 → цепочка `&&` в ptz.sh home тоже останавливается; замок снимает trap в субшелле.
# ponytail: stop между чтением осей и exec ptz (окно ~мс) пропустит ход — Onvifer шлёт Stop перед каждым Move, следующий добьёт.
L=/tmp/ptz.lock
case "$1" in
  left|right|up|down)
    case "$1" in left) X="+ 4300" ;; right) X="- 4300" ;; up) Y="+ 800" ;; down) Y="- 800" ;; esac   # h+ = влево, v+ = вверх (калибровка 10.10)
    US=$(awk -v s="${2:-1}" 'BEGIN{u=(s>0)?2000/s:20000; if(u>20000)u=20000; if(u<2000)u=2000; printf "%d",u}')
    if mkdir $L 2>/dev/null; then
      echo "${X:-$Y}" > $L/${X:+h}${Y:+v}
      ( trap 'rmdir $L' EXIT; sleep 0.1; H=$(cat $L/h 2>/dev/null); V=$(cat $L/v 2>/dev/null); rm -f $L/h $L/v
        if [ -n "$H" ] && [ -n "$V" ]; then /tmp/ptz hv $H $V $US
        elif [ -n "$H" ]; then /tmp/ptz h $H $US; elif [ -n "$V" ]; then /tmp/ptz v $V $US; fi ) </dev/null >/dev/null 2>&1 &
    elif [ -f $L/h ] || [ -f $L/v ]; then echo "${X:-$Y}" > $L/${X:+h}${Y:+v}; fi
    exit 0 ;;
  stop)  rm -f $L/h $L/v; killall ptz 2>/dev/null; exit 0 ;;
  moving) [ -d /tmp/ptz.lock ] && echo 1 || echo 0; exit 0 ;;   # is_moving для GetStatus
  pos)   echo 0,0,0; exit 0 ;;   # get_position: позицию не считаем (ponytail); без обеих команд GetStatus = Fault NoStatus
  home)  ;;
  rel)   # RelativeMove dx dy (GenericSpace -1..1): 1.0 = 180° по горизонтали / 48° по вертикали.
         # ponytail: масштаб на глаз, подкрутить 2050/350 если шаг в Onvifer велик/мал. x<0 = влево = h+, y>0 = вверх = v+
         H=$(awk -v d="$2" 'BEGIN{s=-d*2050; if(s<0){s=-s;printf "- %d",s}else printf "+ %d",s}')
         V=$(awk -v d="$3" 'BEGIN{s=d*350;   if(s<0){s=-s;printf "- %d",s}else printf "+ %d",s}')
         mkdir /tmp/ptz.lock 2>/dev/null || exit 0
         ( trap 'rmdir /tmp/ptz.lock' EXIT; [ "${H#* }" != 0 ] && /tmp/ptz h $H; [ "${V#* }" != 0 ] && /tmp/ptz v $V ) </dev/null >/dev/null 2>&1 &
         exit 0 ;;
  *)     exit 0 ;;
esac
mkdir $L 2>/dev/null || exit 0
( trap 'rmdir $L' EXIT; sh /tmp/ptz.sh home ) </dev/null >/dev/null 2>&1 &
exit 0
