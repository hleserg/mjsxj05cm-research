# События движения → HA (разведка 28.09 21:12, только чтение с камеры)

Сборка: `majestic Lite SigmaStar (infinity6), master+17ec3ed, 2026-09-26`.

## Что есть в бинарнике (`grep -a` по /usr/bin/majestic)
- **MQTT — НЕТ** (0 совпадений `mqtt`). Mosquitto на Pi для камеры бесполезен без моста.
- **ONVIF-события — ЕСТЬ**: `CreatePullPointSubscription`, `PullPointSubscription`, `Subscribe/Notify`,
  топики `tns1:RuleEngine/CellMotionDetector/Motion`, `tns1:VideoSource/MotionAlarm`,
  `tns1:AudioAnalytics/Audio/DetectedSound`. ONVIF device_service отвечает (проверено 20:50).
- HTTP API: `/api/v1/{config,get,set,image,records,gpio,isp,osd,analytics,live,…}`.
- Конфиг сейчас: `motionDetect: enabled: false`, `records: enabled: false`.

## План (после mma_heap-эксперимента, отдельная загрузка)
1. В `p4/cam-up.sh` на p1 добавить в sed `/^motionDetect:/,/^[a-z]/ s/enabled: false/enabled: true/`
   (до первого старта majestic — рестарт majestic течёт по MMA).
2. HA: интеграция ONVIF (host 192.168.1.53, порт 80, root/пароль) → бинарный сенсор
   `CellMotionDetector/Motion` приходит через PullPoint без MQTT. Видео в HA — через go2rtc (WebRTC/RTSP).
3. Нужен MQTT (автоматизации вне HA) — мост на Pi: python-onvif-zeep PullPoint → mosquitto. Не делать, пока HA нет.

## Открытое
- Можно ли включить motionDetect на лету через `/api/v1/set` без рестарта пайплайна (и утечки MMA) — проверить
  ПОСЛЕ heap-теста, когда сброс камеры дёшев (stage.py перехватывает).
- Стоимость детектора по CPU при load ~8 (alloc-loop vpe0) — мерить только после устранения флуда.

## Секрет
`curl http://127.0.0.1:1984/api/streams` на Pi печатает URL с паролем root — вывод только через `sed "s/$PW/***/g"`.

## Проверка 28.09 22:15 (motionDetect: enabled: true с загрузки 21:53, ONVIF PullPoint через curl — `tools/onvif-pull.sh`)
- PullPoint РАБОТАЕТ: CreatePullPointSubscription → адрес `…/onvif/event_service?Idx=uuid:…`, PullMessages отдаёт начальное
  состояние (MotionAlarm=false, CellMotionDetector/Motion IsMotion=false, Face=false, DetectedSound=false). Дальше — тишина:
  ни поворот камеры на 400 полушагов, ни владелец в кадре событий не дают.
- Причина: **в этой сборке majestic (Lite SigmaStar infinity6, master+17ec3ed, 2026-09-26) детектора движения НЕТ.** Строка в
  бинарнике: «records.mode is motion, but this build has no motion detector: nothing will be recorded unless something else
  calls it». `/api/v1/analytics` → `{"src":"motion","active":false,"w":0,"h":0}`; в бинарнике нет MI_VDF, в
  /lib/modules/4.9.84/sigmastar нет mi_vdf.ko; POST/PUT на /api/v1/analytics ничего не включают. Лог majestic уходил в
  /dev/null (S95majestic, syslogd не запущен) — 22:15 запущен `syslogd -O /tmp/messages -s 512 -b 1` (RAM), пусто.
- Решение: **движение считает Pi — Frigate по `rtsp://192.168.1.139:8554/cam_sub` (704x576@15) через go2rtc**, события в
  MQTT (Mosquitto на Pi есть) → HA. На камере ничего не меняем, MMA не трогаем. ONVIF-события majestic для HA бесполезны
  (только начальное состояние). Запись клипов «по движению» на карту камеры (records.mode=motion) без внешнего триггера тоже
  не работает — запись делает Frigate на Pi (диск 117 ГБ свободно). Ultimate-сборка majestic для infinity6 — проверить позже
  (нужен mi_vdf.ko, которого в этом rootfs нет; выше риск по MMA).

- 29.09 17:01: после включения records majestic создаёт `/tmp/p4/2026-09-29/motion-2026-09-29.jsonl` (0 байт). Если файл начнёт расти — это локальный журнал motionDetect, источник событий без Frigate.
