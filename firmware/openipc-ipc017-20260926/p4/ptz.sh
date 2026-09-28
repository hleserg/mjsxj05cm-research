#!/bin/sh
# PTZ MJSXJ05CM на OpenIPC (RAM-only): программный полушаг по GPIO 44..47 (пады PAD_SPI0_CZ/CK/DI/DO,
# у стока это pwm4..7 motor group 1). Мотор выбирается GPIO 80 (горизонталь) / GPIO 16 (вертикаль).
# Оба мотора КРУТЯТСЯ так (владелец, 28.09 16:25), полностью бесшумно. Группа PWM на OpenIPC моторы
# не двигает (причина не найдена) — ponytail: полушаг из шелла, 20 мс/состояние; апгрейд на PWM-группу
# когда понадобится плавность или разгрузка CPU.
#   ptz.sh init         — снять mux pwm4..7 с падов (devmem, RAM), gpio out, всё 0, проверка readback
#   ptz.sh h + 300      — горизонталь, 300 полушагов (+ = последовательность f; сторону см. DECISIONS.md)
#   ptz.sh v - 100      — вертикаль
#   ptz.sh stop
# PTZ_US=20000 — задержка на состояние, мкс (калибровочная ручка: меньше = быстрее, слишком мало = пропуск шагов).
G=/sys/class/gpio; US=${PTZ_US:-20000}
gpio() { [ -d $G/gpio$1 ] || echo $1 > $G/export; echo out > $G/gpio$1/direction; echo ${2:-0} > $G/gpio$1/value; }
set4() { echo $1 > $G/gpio44/value; echo $2 > $G/gpio45/value; echo $3 > $G/gpio46/value; echo $4 > $G/gpio47/value; }
stop() { set4 0 0 0 0; echo 0 > $G/gpio80/value; echo 0 > $G/gpio16/value; }
case "$1" in
init)
  for g in 44 45 46 47 80 16; do gpio $g 0; done
  devmem 0x1F203C1C 16 0x0001   # pwm4 mux снят; bit0 = pwm0 → pad52 (ИК-лампа) оставлен
  devmem 0x1F203C08 16 0x0000   # pwm5/6/7 mux снят
  echo 1 > $G/gpio44/value
  if [ "$(cat $G/gpio44/value)" = 1 ]; then echo "ptz init ок"; else echo "ptz init: pad44 не в GPIO-режиме"; fi
  stop ;;
h|v)
  N=${3:-100}; stop
  if [ "$1" = h ]; then echo 1 > $G/gpio80/value; else echo 1 > $G/gpio16/value; fi
  n=0; while [ $n -lt $N ]; do
    if [ "$2" = + ]; then
      set4 1 0 0 1; usleep $US; set4 1 0 0 0; usleep $US; set4 1 1 0 0; usleep $US; set4 0 1 0 0; usleep $US
      set4 0 1 1 0; usleep $US; set4 0 0 1 0; usleep $US; set4 0 0 1 1; usleep $US; set4 0 0 0 1; usleep $US
    else
      set4 0 0 0 1; usleep $US; set4 0 0 1 1; usleep $US; set4 0 0 1 0; usleep $US; set4 0 1 1 0; usleep $US
      set4 0 1 0 0; usleep $US; set4 1 1 0 0; usleep $US; set4 1 0 0 0; usleep $US; set4 1 0 0 1; usleep $US
    fi
    n=$((n+8)); done
  stop; echo "ptz $1$2 $N ок" ;;
stop) stop ;;
*) echo "ptz.sh init | h|v +|- полушаги | stop"; exit 1 ;;
esac
