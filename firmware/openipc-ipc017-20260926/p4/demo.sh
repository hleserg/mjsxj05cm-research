#!/bin/sh
# Демо для подписчиков (RAM-only, OpenIPC): ~50 с — мигают жёлтый (77) и красный (76) светодиоды и ИК-лампа (pwm0),
# моторы бодро крутятся туда-сюда, динамик включён (GPIO 15) — мелодию шлёт Pi через /play_audio параллельно.
# Запуск: /tmp/demo.sh (после /tmp/ptz.sh init). Требует /tmp/ptz.sh. PTZ_US=8000 — быстрее обычных 20 мс (ponytail:
# пропуск шагов не страшен, это демо; если моторы не крутятся — поднять до 12000).
G=/sys/class/gpio; P=/sys/class/pwm/pwmchip0
led() { [ -d $G/gpio$1 ] || echo $1 > $G/export; echo out > $G/gpio$1/direction; echo $2 > $G/gpio$1/value; }
lamp() { echo $1 > $P/pwm0/duty_cycle; }
led 15 1; led 76 0; led 77 0
[ -d $P/pwm0 ] || echo 0 > $P/export
# период ставить ДО duty: у свежеэкспортированного pwm0 period=0 и `echo 100 > duty_cycle` даёт EINVAL
# (демо 17:17 — лампа не мигала, 100 строк «write error»). Единицы драйвера OpenIPC: period = Гц, duty = %.
echo 8333 > $P/pwm0/period; echo 100 > $P/pwm0/duty_cycle; echo 1 > $P/pwm0/enable; lamp 0
# мигалка фоном: жёлтый/красный попеременно 0.25 с, лампа — каждый второй такт
( i=0; while [ $i -lt 100 ]; do
    led 77 1; led 76 0; lamp 100; usleep 250000
    led 77 0; led 76 1; lamp 0;   usleep 250000
    i=$((i+1)); done; led 77 0; led 76 0; lamp 0 ) &
BL=$!
export PTZ_US=${PTZ_US:-8000}
/tmp/ptz.sh h + 400; /tmp/ptz.sh h - 400
/tmp/ptz.sh v + 200; /tmp/ptz.sh v - 200
/tmp/ptz.sh h + 200; /tmp/ptz.sh v + 100; /tmp/ptz.sh h - 200; /tmp/ptz.sh v - 100
/tmp/ptz.sh h - 400; /tmp/ptz.sh h + 400
wait $BL
led 77 0; led 76 0; lamp 0; echo 0 > $P/pwm0/enable; led 15 0; /tmp/ptz.sh stop
echo DEMO_done
