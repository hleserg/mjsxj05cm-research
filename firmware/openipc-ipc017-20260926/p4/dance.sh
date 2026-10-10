#!/bin/sh
# dance.sh — танец камеры для подписчиков (RAM-only): ~27 с под чиптюн из собственного динамика (tools/dance/tune.py).
# Музыку шлёт Pi в POST /play_audio, этот скрипт запускает по SSH (tools/dance/dance.sh). Такт 0.4 с (150 BPM), 66 тактов.
# Хореография по тактам: качание влево-вправо, кивки, четыре диагонали, широкий проезд, «ромб», зигзаг, поклон.
# Каждая фраза возвращается в ноль — home не нужен (прогон 10.10: кадр вернулся в (−1, −7) px). Светодиоды 77/76 мигают в такт, ИК-лампа — на сильную долю.
# Замок /tmp/ptz.lock общий с HA/ONVIF: занято — выход 9. Любой выход: светодиоды, лампа, усилитель (GPIO 15) выкл, обмотки обесточены.
# Такты считаются от /proc/uptime (сотые), а не цепочкой sleep: накладные ~10 мс на ход за 66 ходов уплыли бы на полтакта.
# Длины ходов под такт: полушаг бинарником ≈2.65 мс при us=2000 (4 записи sysfs + пауза) → 130 полушагов ≈ 0.35 с.
G=/sys/class/gpio; P=/sys/class/pwm/pwmchip0; Z=/tmp/ptz
mkdir /tmp/ptz.lock 2>/dev/null || { echo "dance: PTZ занят"; exit 9; }
gpio() { [ -d $G/gpio$1 ] || echo $1 > $G/export; echo out > $G/gpio$1/direction; echo $2 > $G/gpio$1/value; }
lamp() { echo $1 > $P/pwm0/duty_cycle; }
bye() { kill $BL 2>/dev/null; gpio 77 0; gpio 76 0; lamp 0; gpio 15 0; sh /tmp/ptz.sh stop; rmdir /tmp/ptz.lock; }
trap bye EXIT; trap 'exit 1' INT TERM
sh /tmp/ptz.sh lamp 0            # pwm0: период до duty, иначе EINVAL (см. demo.sh)
gpio 15 1                        # усилитель динамика
cs() { tr -d . < /proc/uptime | cut -d' ' -f1; }   # сотые секунды с загрузки
T0=$(cs)
at() { d=$((T0 + $1 * 40 - $(cs))); [ $d -gt 0 ] && usleep $((d * 10000)); shift; "$@" >/dev/null; }
( k=0; while [ $k -lt 66 ]; do                     # мигалка фоном
    if [ $((k % 2)) = 0 ]; then at $k gpio 77 1; gpio 76 0; else at $k gpio 76 1; gpio 77 0; fi
    if [ $((k % 4)) = 0 ]; then lamp 100; else lamp 0; fi
    k=$((k + 1)); done ) &
BL=$!
# 0–7 качание
at 0 $Z h + 130; at 1 $Z h - 130; at 2 $Z h + 130; at 3 $Z h - 130; at 4 $Z h - 130; at 5 $Z h + 130; at 6 $Z h - 130; at 7 $Z h + 130
# 8–15 кивки (тилт медленнее: 4000 мкс)
at 8 $Z v + 65 4000; at 9 $Z v - 65 4000; at 10 $Z v - 65 4000; at 11 $Z v + 65 4000
at 12 $Z v + 65 4000; at 13 $Z v - 65 4000; at 14 $Z v - 65 4000; at 15 $Z v + 65 4000
# 16–23 четыре диагонали туда-обратно
at 16 $Z hv + 98 - 32; at 17 $Z hv - 98 + 32; at 18 $Z hv - 98 + 32; at 19 $Z hv + 98 - 32
at 20 $Z hv + 98 + 32; at 21 $Z hv - 98 - 32; at 22 $Z hv - 98 - 32; at 23 $Z hv + 98 + 32
# 24–31 широкий проезд (4 такта туда, 4 обратно)
at 24 $Z h - 540; at 28 $Z h + 540
# 32–39 качание с кивками вперемешку
at 32 $Z h + 130; at 33 $Z v + 65 4000; at 34 $Z h - 130; at 35 $Z v - 65 4000
at 36 $Z h - 130; at 37 $Z v + 65 4000; at 38 $Z h + 130; at 39 $Z v - 65 4000
# 40–47 ромб по часовой и обратно
at 40 $Z hv + 98 + 32; at 41 $Z hv - 98 + 32; at 42 $Z hv - 98 - 32; at 43 $Z hv + 98 - 32
at 44 $Z hv + 98 + 32; at 45 $Z hv + 98 - 32; at 46 $Z hv - 98 - 32; at 47 $Z hv - 98 + 32
# 48–55 широкий проезд в другую сторону
at 48 $Z h + 540; at 52 $Z h - 540
# 56–63 зигзаг
at 56 $Z hv + 98 + 32; at 57 $Z hv + 98 - 32; at 58 $Z hv - 98 + 32; at 59 $Z hv - 98 - 32
at 60 $Z hv - 98 + 32; at 61 $Z hv - 98 - 32; at 62 $Z hv + 98 + 32; at 63 $Z hv + 98 - 32
# 64–65 поклон на финальный аккорд
at 64 $Z v - 65 4000; at 65 $Z v + 65 4000
at 68 echo                       # дать хвосту музыки дозвучать, потом bye выключит усилитель
echo "DANCE_done $(( ($(cs) - T0) / 100 )) с"
