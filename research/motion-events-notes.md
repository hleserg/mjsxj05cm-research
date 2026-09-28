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
