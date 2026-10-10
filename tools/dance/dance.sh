#!/bin/sh
# Танец камеры под чиптюн из её собственного динамика. Запуск с Pi из корня репо: sh tools/dance/dance.sh
# Музыка: tune.py → ffmpeg → 8 кГц s16le моно, −6 дБ (бип на outputVolume 60 давал −3 dBFS на микрофоне) + тишина DANCE_LEAD
# в начале; POST /play_audio (только root, Content-Type audio/L16) уходит фоном, следом по SSH стартует /tmp/dance.sh.
# DANCE_LEAD — калибровка синхронности, с: ≈ задержка SSH до старта dance.sh (0.8 с) − старт звука после POST (0.3 с); 10.10 замерено 0.5
# по RTSP-записи (звук против первого движения кадра). Пароль root читается из gitignored файла, в argv не попадает.
set -e; cd "$(dirname "$0")/../.."
CAM=${CAM:-192.168.30.53}; LEAD=${DANCE_LEAD:-0.5}
SECRET=firmware/openipc-ipc017-20260926/p4/secret/root-password.txt
[ -r $SECRET ] || { echo "нет $SECRET (пароль root камеры, одна строка)"; exit 1; }
D=tools/dance
python3 $D/tune.py $D/tune.wav >/dev/null
ffmpeg -loglevel error -y -i $D/tune.wav -af "adelay=$(printf '%.0f' "$(echo "$LEAD*1000" | bc)"):all=1,volume=0.5" -ac 1 -ar 8000 -f s16le $D/tune.pcm
python3 uart/camssh.py --put firmware/openipc-ipc017-20260926/p4/dance.sh /tmp/dance.sh >/dev/null
printf 'user = "root:%s"\n' "$(sed -n 1p $SECRET)" | curl -s -K - -H 'Content-Type: audio/L16' --data-binary @$D/tune.pcm http://$CAM/play_audio &
python3 uart/camssh.py "sh /tmp/dance.sh"
wait
