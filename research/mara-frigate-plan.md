# Мара ↔ Frigate: «кто это?» по незнакомцам с камеры

29.09 20:28. План v1, ленивый: Frigate сам ловит лицо и сам его узнаёт, Мара
только спрашивает хозяина и записывает ответ обратно в Frigate.

## Шаг 0 — ворота: Frigate должен поймать хоть одно лицо

Факт 20:27: `clips/faces/` на bigpc **нет**, `/api/faces` = `{}` — за всё время
Frigate ни одного лица не нашёл. Детект идёт по SUB 704x576@5, события person
19:37–19:40 — засветка, спина, размыто (кроп смотрел). Пока лица нет, трубу
строить не по чему.

Проверка: хозяин проходит мимо камеры в 1–2 м при свете → на bigpc
`curl -s 127.0.0.1:5000/api/faces` должен показать ключ `train` с файлом.
Если через 2–3 прохода пусто → лица мелкие для 704x576: перевести `detect`
камеры mjsxj05cm на MAIN 1920x1080 (GPU bigpc потянет; правка config.yml —
владелец через `!`).

## Триггер: не «person без sub_label», а «лицо найдено, но не узнано»

Отклонение от исходной формулировки (MQTT `frigate/events` без sub_label):
в тот набор попадает каждая спина и засвеченное пятно — по ним никто не
ответит «кто это». У Frigate есть готовый список ровно нужных случаев:
попытки распознавания (`face_recognition.save_attempts: 200`), папка
`clips/faces/train/`, список — ключ `train` в `GET /api/faces`.

MQTT для v1 не нужен вовсе → без paho, без пользователя mosquitto
(анонимный доступ на doctor закрыт, `allow_anonymous false`; Frigate к
doctor подключён как клиент `frigate` с 19:36:50). `frigate/events`
оставить на потом — для «кто-то вошёл» уведомлений.

Из исходников 0.18 (`data_processing/real_time/face.py`, explorer 21:2x):
файл `{event_id}-{timestamp}-{sub_label}-{score}.webp`, туда падают и
узнанные, и неузнанные — у неузнанных `sub_label = unknown` (score ниже
`unknown_score` 0.8). Фильтр мостика: `-unknown-` в имени. Старые файлы
Frigate сам чистит сверх `save_attempts`. Сверить формат на первом реальном
файле.

## Обучение: classify попытки, а не заливка кропа человека

Эндпоинты Frigate 0.18 (openapi, проверено): `GET /faces`,
`POST /faces/train/{name}/classify` (тело: `training_file`),
`POST /faces/{name}/register` (загрузка картинки), `POST /faces/{name}/create`,
`POST /faces/recognize`, `PUT /faces/{old}/rename`,
`POST /events/{event_id}/sub_label`, `GET /events/{id}/snapshot.jpg?crop=1`.
`classify` принимает `training_file` ИЛИ `event_id` («a training file or
event_id must be passed») — то есть «обучить по event_id» есть, и event_id
виден в имени файла попытки. Путь v1: `classify` с `training_file` (лицо уже
вырезано и проверено Frigate); `register` кропа person хуже — перепрогоняет
детектор. Плюс `POST /events/{id}/sub_label`, чтобы событие в UI/HA показало
имя.

Роли (`api/classification.py`, `api/event.py`): classify и recognize — без
роли; register, create, sub_label — admin. Значит пользователь `mara` —
admin (или без sub_label — тогда хватит viewer; v1: admin, проще).

## Где живёт и что нужно от хозяина

Мостик — на Mac mini, рядом с `look.py`: там же `~/mask/heard/` (вопросы),
`~/mask/strangers/` (ответы), мостик Hermes `inject_message`. Файл в репо
Мары `mask/frigate.py` — попадает в карту `mask/deployed.sh` автоматически
(`mask/*.py → ~/mask/`), кладётся с Pi (`ssh mac-mini`).

С Mac Frigate доступен только по `https://192.168.1.10:8971` с логином
(5000 — loopback bigpc). От хозяина одно действие: завести в Frigate
пользователя `mara` (UI: Settings → Users → Add; роль — по итогу проверки
выше), пароль положить на Mac в `~/mask/.env` как `FRIGATE_MARA_PASSWORD=…`
(look.py читает настройки из env: `MARA_FACES`; так же). Никаких значений
Frigate/MQTT в репо и доках.

## Поток v1

1. Раз в 10 с `GET /api/faces` (логин `POST /api/login` `{user,password}`,
   пароль ≥12 символов; JWT из cookie `frigate_token` можно слать как
   `Authorization: Bearer`; срок — `JWT_SESSION_LENGTH`, перелогин по 401).
2. Новый файл в `train`, не узнанный, ещё не спрошенный → скачать в
   `~/mask/strangers/frigate-<id>/01.webp`, написать вопрос в `heard/` тем же
   текстом, что `Guests._ask` (MEDIA:-путь к файлу, «запиши `echo 'имя' >
   …/name`»). Одна попытка = один вопрос; повтор через REASK как у гостей.
3. `sweep`: появился `name` → это каноническое латинское имя (регэксп
   `^[a-z0-9_]+$`; дефис Frigate сам меняет на `_`, кириллицу
   `pathvalidate` пропустит, но имя = папка и sub_label — латиница проще) → `classify` попытки под ним (+ `create`,
   если такого лица нет) → `sub_label` события → маркер `named`. Frigate
   обучен — следующие проходы этого человека узнаёт сам.

## Алиасы: ноль кода

«сын» / «Ванька» / «заяц» = один человек — это знает Мара, а не мостик. Файл в
репо Мары `docs/people.md`: `vanya — сын, Ванька, заяц` (в её контекст).
Хозяин отвечает как угодно, Мара переводит в slug и пишет его в `name`.
Мостик slug только валидирует.

## Не трогаю в v1

- `faces/server.py` (/who, insightface, db.json) — маска на K210 живёт на нём.
  Две базы лиц — дубль; потом: `POST /faces/recognize` Frigate вместо `/who`,
  одна библиотека.
- MQTT `frigate/events` — потом, для «кто-то вошёл».

## Проверка

- Половину «к Frigate» гоняю с bigpc WSL против `127.0.0.1:5000`
  (`--dry-run`: логин не нужен, список попыток, что бы спросил).
- Половина `heard/`→Telegram→`name` проверяется только на Mac после
  укладки `mask/deployed.sh --положить` — честно помечаю непроверенной.

## Дальше по порядку

1. Хозяин: пройти перед камерой (шаг 0), завести пользователя `mara` в Frigate.
2. Я: по первому файлу в train — сверить формат имени (остальное известно).
3. Я: `mask/frigate.py` + `docs/people.md` в репо Мары, dry-run с bigpc.
4. Хозяин: `mask/deployed.sh --положить`, ответить на первый вопрос в Telegram.
