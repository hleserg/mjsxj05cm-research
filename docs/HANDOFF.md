# HANDOFF — камера MJSXJ05CM, состояние на 29.09.2026 03:00 (стоп: владелец перебирает малинку)

## Где мы
- **Камера на СТОКЕ** (4.3.9_0445, 192.168.1.53, SSH нет), карта в камере. В NOR лежит **env v3** (crc32 `18901e20`,
  bootcmd=`run sdboot; run norboot`). Каждое включение: sdboot пробует карту → падает → norboot → сток. Кирпича нет,
  откат = вынуть карту (norboot) или `env-old.bin` с p1 (crc32 `6c1674b6`). Питание камере дёргать можно свободно.
- **Причина трёх падений автозагрузки НАЙДЕНА** (DECISIONS 02:31 + 02:52, дизасм стокового U-Boot): перед `run_command_list(bootcmd)`
  сток включает MMU + D-кэш (0x23e01038) и I-кэш (0x23e00ff8), после — выключает; перехват Enter'ом этот блок пропускает.
  В приглашении кэш выключен → репетиции по UART проходят; в автозагрузке включён → DMA-чтение карты без инвалидации → блок 0 = нули
  («bad MBR 0x0000» / «No partition table») → `Wrong Image Format` → norboot.
- **Лечение (кандидат v4):** `sdboot=dcache off; mw.l 0x22000000 0 4; fatload mmc 0:1 0x22000000 uImage.ssc325; setenv bootargs ${sdargs}; bootm 0x22000000`.
  Одно слово `dcache off;` в начале. Пишется ТОЛЬКО после эксперимента ниже, нового STOP (uboot/STOP-env.md → v4) и явного «да».

## 03:03 ЭКСПЕРИМЕНТ ВЫПОЛНЕН (DECISIONS 03:03): 13/13 проб без кэша ОК; K0 — с D-кэшем DMA-данные CPU не видит (00 00); K1 (`dcache on` + fatload = автозагрузка) — мусорная FAT-цепочка, U-Boot завис на чтении карты. Механизм доказан → v4 = `dcache off;` в начале sdboot. K2 не выполнилась (нет приглашения). Камера в U-Boot гоняет карту: питание → сток. K0 дал 00 00 / 00 00, а не 00 00 → 55 aa: объяснение (writeback-flush) — вывод, не факт; второе чтение — DMA вообще не легло при MMU on. Для v4 без разницы: с кэшем CPU данных карты не видит. Раздел ниже — история, что было запланировано:

## (выполнено) эксперимент `2a-p4-sdtest`
Этап готов в `uart/stage.py` (коммиты a01f2a5, 1c49b30), критерии заранее в DECISIONS 02:42/02:52. Не запускался (владелец остановился 02:57).
1. На малинке после перезагрузки (владелец, через `!`):
   `cd ~/mjsxj05cm-research; for p in $(pgrep -f "stage.py"); do [ "$p" != "$$" ] && kill $p; done; STAGE_WAIT=86400 nohup python3 uart/stage.py 2a-p4-sdtest > /dev/null 2>&1 &`
2. Монитор на свежий `uart/stage-2a-p4-sdtest-*.log` (фильтр в HANDOFF-строке 02:41: `grep -aE` по `IPL|bytes read in|bad MBR|Invalid partition|224001fe|dcache|Unknown command|ABORT|INIT4_START|SSH_READY_ip|CAM_UP_done`, маска MAC/ssid/psk).
3. Владелец дёргает питание камеры → stage.py ловит U-Boot → ~25 проб (~3 мин) → в конце SDBOOT построчно → OpenIPC (INIT4_START → SSH_READY → CAM_UP_done).
4. Чтение лога (`rtk proxy grep -an`): по каждой пробе `bytes read` = OK, `bad MBR|Invalid partition|Unable` = отказ.
   - **K1** (`dcache on; fatload tf; fatload uImage`) = точная автозагрузка → жду ОТКАЗ. **K2** (`… dcache off; fatload uImage`) → жду `bytes read`.
   - **K0** `md.b 0x224001fe 2`: `00 00` при dcache on, потом `55 aa` после off → некогерентность доказана.
   - Все A-пробы (без dcache) должны проходить. `sleep` — скорее «Unknown command» (в help его нет).
5. Если K1 падает, K2 проходит: STOP v4 (`uboot/STOP-env.md`: гейты `ENV_OLD_CRC=18901e20` → новый crc; `uboot/mkenv.py` с `dcache off; ` в SDBOOT;
   `env-new-v4.bin` на p1 через `tools/p1-put.sh` когда OpenIPC поднят) → AskUserQuestion «да» → владелец через `!`:
   `NOR_WRITE=yes ENV_OLD_CRC=18901e20 ENV_NEW_CRC=<v4> STAGE_WAIT=86400 nohup python3 uart/stage.py nor-env-write …` → `reboot -f` → приёмка холодным стартом.
   Если K1 тоже проходит — механизм не воспроизведён, v4 не писать; глубже в дизасм (что ещё меняет автозагрузка) или загрузка с помощью Pi.

## Следующая сессия (порядок) — обновлено 29.09 13:2x

Сделано 13:0x–13:2x: Pi перезагружена, стенд собран, `sudo dtoverlay uart0-pi5` (после каждого ребута Pi!), stage.py `2a-p4-env3` запущен
(PID 65749, лог `uart/stage-2a-p4-env3-20260929-130838.log`). В `uart/stage.py`: SDBOOT v4 = `dcache off; …`, этап `2a-p4-env4`
(= 2a-p4-env, но `dcache on` перед `run sdboot`), гейты 18901e20 → 25f375ed; selftest+dry-run ОК (коммит a183988).
`uboot/env-new-v4.bin` собран (crc32 25f375ed, sha 76f91973…, gitignored). `uboot/STOP-env.md` = черновик STOP v4 (f6d7936).

1. Владелец дёргает питание камеры → stage.py ловит U-Boot → OpenIPC в RAM (INIT4 → SSH → CAM_UP).
2. Я: `tools/p1-put.sh uboot/env-new-v4.bin` (env-new.bin на p1 = v4; md5 сверить).
3. **Перевзвод, НЕ `#stage`** (запущенный процесс этапа env4 не знает): владелец через `!`:
   `cd ~/mjsxj05cm-research; for p in $(pgrep -f "stage.py"); do [ "$p" != "$$" ] && kill $p; done; STAGE_WAIT=86400 nohup python3 uart/stage.py 2a-p4-env4 > /dev/null 2>&1 &`
   → я: монитор на новый лог, `python3 uart/camssh.py 'reboot -f'` → ожидаю `==> 25f375ed`, `sdboot=dcache off`, `bytes read` → INIT4 → SSH.
   Нет `bytes read` → ABORT, v4 не годится, не пишем; `dcache off` через FIFO `uart/console.in`.
4. Репетиция ОК → в STOP-env.md заполнить «Итог репетиции», AskUserQuestion → «да» → владелец запускает `nor-env-write` (команда в STOP-env.md).
5. Приёмка холодным стартом; без карты → сток (засечь время sf read); карту вернуть; владелец останавливает stage.py.

## После рабочего env (приёмка)
Холодный старт → INIT4/SSH/CAM_UP без Pi; карта вынута → сток; карта обратно. stage.py остановить. Потом: отмашка владельцу (HA-поток,
Onvifer автообнаружение, Frigate Face Library — «посмотри в камеру»), раздел p4 (данные) на карте (владелец «конечно да», план сначала),
STATUS.md, FULL-CONTROL-ACCEPTANCE.md.

## Что теряется при перезагрузке малинки
- stage.py, монитор UART, кроны сессии — умирают; камера при этом безопасна (сток).
- Scratchpad `/tmp/claude-1000/-home-hleserg-xiaomi360/cbe78943-…/scratchpad/` (ub.dis, uboot.bin, disasm.py, env-new-v*.bin, data-own/) — в /tmp,
  скопировать мне классификатор запретил. Всё воспроизводимо: uboot.bin = `spi/original-01.bin` со смещения U-Boot (research/uboot-env-notes.md),
  дизасм — `arm-none-eabi-objdump -D -b binary -m arm --adjust-vma=0x23E00000`, env-блоки — `uboot/mkenv.py`. Если хочется сохранить —
  владелец сам: `cp -a /tmp/claude-1000/-home-hleserg-xiaomi360/*/scratchpad ~/mjsxj05cm-research/research/disasm/scratchpad-20260929` (папка в .gitignore).

## Правила, которые нельзя забыть
Секреты (SSID/PSK/MAC/root/ONVIF-пароль) не печатать; любая запись в NOR — только владелец через `!` после STOP + «да»; stage.py запускает/убивает
только владелец через `!`; один UART — не запускать два stage.py; `tf_update.img` на карте не создавать; majestic не рестартовать (MMA).
Полный список — в верхней части этого репо: DECISIONS.md, STATUS.md, uboot/STOP-env.md.

## 29.09 15:07 — СТОП ПЕРЕД РЕБУТОМ Pi (владелец перезагружает Pi)

**Состояние.** Репетиция v4 (`2a-p4-env4`: dcache on → run sdboot) ПРОЙДЕНА 14:48, лог `uart/stage-2a-p4-env4-20260929-144726.log`. STOP v4 заполнен (`uboot/STOP-env.md`), владелец ответил **«Да, пиши env v4»** (15:0x). Запись в NOR **ЕЩЁ НЕ ДЕЛАЛАСЬ**: первая команда запуска содержала синтаксическую ошибку (`&;`), исправлена (коммит b62f35b), владелец её запустить не успел — ребут Pi. NOR = env v3 (crc 18901e20), v4 на p1 карты как `env-new.bin` (crc 25f375ed). Камера сейчас на OpenIPC из RAM (загрузка 14:48), после ребута Pi она не пострадает, но при своём следующем ребуте уйдёт в сток (norboot) — это нормально.

**После ребута Pi (по порядку):**
1. Владелец: `sudo dtoverlay uart2-pi5` (оверлей не постоянный; UART на pin 29/7/6, `/dev/ttyAMA2`). Проверка: `pinctrl get 4,5` → a2 TXD2/RXD2. GPIO4/5 через pinctrl НЕ трогать.
2. Владелец через `!` запускает этап записи (команда в `uboot/STOP-env.md`, строка «cd ~/mjsxj05cm-research; pkill -f "^python3 uart/stage.py"; … nor-env-write … & sleep 2; pgrep -a python3; ls -l /proc/…/fd | grep tty»). «Да» уже получено — повторно не спрашивать, только подтвердить, что он помнит.
3. Я: монитор «ждёт новый stage-лог» с расширенным фильтром (`SF: Detected|Read: OK|Erased|Written|were the same|differ|Fail|Error|==> |ABORT|INIT4_START|SSH_READY_ip`), крон-страховка +30 мин; проверить `pgrep -af "^python3 uart/stage.py"` = nor-env-write и fd на ttyAMA2; затем `python3 uart/camssh.py "reboot -f"` (если камера ещё на OpenIPC; если уже сток — передёрнуть питание попросить владельца).
4. Гейты: `==> 18901e20` → `Erased: OK` → `Written: OK` → `==> 25f375ed` → `were the same` → `reset` → автобут БЕЗ Enter: `bytes read` → `Starting kernel` → `INIT4_START` → `SSH_READY_ip`. Потом холодный старт (питание), карта вынута → сток, карта назад → OpenIPC. stage.py останавливает владелец.
5. Откат/обрывы — в STOP-env.md (после erase: `ENV_OLD_CRC=f154670a`; после write: просто питание; env-old.bin на p1).

**Дальше:** отмашка владельцу (HA-поток, Onvifer, Frigate Face Library — подойти к камере), план p4-раздела на карте, записи v4 в STATUS/DECISIONS/FULL-CONTROL-ACCEPTANCE. Идея владельца (15:0x): Мара-агент спрашивает «кто это?» по незнакомцам из Frigate (MQTT `frigate/events` без sub_label → фото → ответ → справочник личностей с алиасами → обучение Frigate по event_id каноническим именем) — план набросан в ответе, кода нет; нужно узнать канал и код Мары.

## 29.09 16:11 — приёмка env v4 (после ребута Pi: шаги выше выполнены, stage.py 10471)

- (1) холодный старт → OpenIPC, SSH 15:59 ✔
- (2) карта вынута → сток: `Card Detect Fail` → `Wrong Image Format for bootm command` → norboot ✔
- (3) карта назад → OpenIPC — ждём владельца.
- После п.3: владелец останавливает stage.py (`! pkill -f "^python3 uart/stage.py"`), обновить STATUS/FULL-CONTROL-ACCEPTANCE, advisor, отмашка HA/Onvifer/Frigate, план p4.
- 16:42: (3) карта назад → OpenIPC ✔ (SSH, majestic 637, mma fail 0). Приёмка 3/3. Дальше: владелец останавливает stage.py; отмашка; план p4.
- 16:59: p4 на карте готов, records majestic пишутся в /tmp/p4 (см. STATUS). Дальше: HTTP-скачивание записей (majestic /api/v1/records → 405 на GET, изучить), отмашка HA/Onvifer/Frigate-лица, Мара↔Frigate.
- 17:01: busybox sed принимает `-e ""` (ветка без p4 в cam-up.sh безопасна). Ротация records при maxUsage 90 НЕ проверена — карта заполнится ~30.09 вечером (~1 ГБ/ч); это проверка, переводящая пункт SD в [x]. В /tmp/p4/%F лежит `motion-%F.jsonl` (0 байт) — путь motionDetect majestic; если начнёт расти — локальный источник событий (research/motion-events-notes.md).
- 17:40: HA «нет» (камера в HA через интеграцию Frigate; ifeel там дважды — Frigate+Tuya), Onvifer OK. Причина: RTSP камеры с 28.09 требует логин (401 без него), а go2rtc во Frigate на bigpc (`/mnt/nvme/frigate/config/config.yml`, `mjsxj05cm`/`mjsxj05cm_sub`) прописан без логина → «user/pass not provided» → ffmpeg 404 → Frigate камеру не тянет → HA без видео. Проверено с Pi: ffprobe `stream=0` 1920x1080, `stream=1` 704x576 с логином OK. Frigate 0.18.0 (5000 только 127.0.0.1; 8554/8971 наружу). Правка config.yml/.env на bigpc и скрипт-починка запрещены классификатором → инструкция владельцу текстом (плейсхолдер `{FRIGATE_MJSXJ05CM_PASSWORD}` в .env, `docker compose up -d`). После починки: `docker logs frigate | grep mjsxj` без 404, HA — перезагрузить интеграцию Frigate при необходимости. Дальше: Мара↔Frigate (explorer ищет код Мары).
- 19:38: Frigate починен владельцем (моя строка через `!`, классификатор мне правку на bigpc запретил трижды): go2rtc `mjsxj05cm`/`mjsxj05cm_sub` → `rtsp://admin:{FRIGATE_MJSXJ05CM_PASSWORD}@192.168.1.53:554/stream=0|1`, пароль в `/mnt/nvme/frigate/.env`, бэкап `config.yml.bak-20260929-1936`. Проверено: Frigate cam_fps 5.5, лог без 404, latest.jpg 200; рестрим `rtsp://192.168.1.10:8554/mjsxj05cm(_sub)` с Pi OK. Лог HA (doctor, контейнер iot-homeassistant, custom_components.frigate): до 19:32 `stream worker … 404 … rtsp://192.168.1.10:8554/mjsxj05cm` — та же причина. Осталось: владелец подтверждает видео в HA (если нет — перезагрузить интеграцию Frigate). Мара: код `~/mara`, Telegram через Hermes-гейтвей (Mac mini), лица `faces/server.py` на bigpc:8771 (insightface, `strangers/guest-N/`), MQTT/Frigate/HA нет; HANDOVER Мары: docs/HANDOVER.md:300 «Не начато: Home Assistant».

**19:50: Frigate face: библиотека `/api/faces` пустая, arcface скачан 19:45, события person на mjsxj05cm 19:37–19:40 без sub_label; кроп из SUB (600x576) — лица не видно (засветка, размыто) → обучать по кадрам с 1–2 м при свете. Explorer #2 (Мара) готов: faces/server.py = POST /who|/enroll?name|/rename?old&new, GET /people|/health (порог 0.4, db.json на bigpc:8771); незнакомцы — файловый поток look.py→`~/mask/heard/*.txt`→plugin inject_message→Telegram, ответ = файл `strangers/guest-N/name`; MQTT/Frigate в Маре нет; справочника алиасов нет. Пишу план `research/mara-frigate-plan.md`. Крон f753af5b 20:27.**

**20:29: камера ОК (uptime 3:30, majestic 640, VmRSS 8.1 МБ, available 13.4 МБ, mma fail 0, 13 файлов, p4 4.0 ГБ/29.7); Frigate 0 ошибок, fps 5.5; HA молчит; `/api/faces` всё ещё {} — лица не было. План Мара↔Frigate v1 записан: research/mara-frigate-plan.md (триггер = попытки Frigate `train`, не MQTT; classify + sub_label; мостик `mask/frigate.py` на Mac; алиасы у Мары в docs/people.md). Ждём владельца: проход перед камерой 1–2 м при свете, пользователь `mara` в Frigate, видео в HA. Крон +40 мин (~21:08).** **21:50: будильник 21:48 обработан: камера uptime 4:51, majestic 640 (VmRSS 6.9 МБ), MemAvailable 13.4 МБ, mma fail 0, 17 файлов на p4 (6.1 ГБ); Frigate ошибок 0, cam_fps 5.5, `/api/faces` = {} (лица по-прежнему нет), users только admin; HA тихо. План v1 Мара↔Frigate уточнён фактами из исходников 0.18 (коммит f884841). Владелец молчит с ~19:40 (>2 ч) → AskUserQuestion задан 21:50: видео в HA? проход перед камерой? пользователь `mara`? где код мостика? Крон 8570a145 на 22:28 взведён. Без владельца по камере делать нечего.** **30.09 11:13: КАМЕРА ВИСИТ с ~08:15 (Frigate: 404 на stream → no route to host; ping/SSH/HTTP нет; UART молчит даже на Enter — не паника (panic=20 перезагрузил бы), а зависание или питание). Watchdog majestic ВЫКЛ (cam-up.sh, отключён 28.09 из-за MMA — причина ушла с mma_heap 0x1800000). Нужен пауэр-цикл владельцем; после подъёма: включить watchdog в cam-up.sh на p1 (+ репо), syslog на p4, потом 2–3 суток аптайма → сборка в корпус. Монитор UART b25herthn пишет uart/boot-console-20260930.log (gitignore). Крон e4fbe6b7 11:51. stage.py не запускать.**
 **30.09 16:34: владелец 13:13 «Вечером», ~16:30 «врубил» — камера поднялась 16:31 (uptime 2 мин, majestic 639, mma fail 0, p4 rw, Frigate fps 5.2). cam-up.sh (041eebf: watchdog ВКЛ + syslogd/klogd на p4) положен на p1 карты (remount rw→b64→sync→ro, md5 b6763a11 совпал), watchdog0 пока `inactive` — вступит после `reboot -f` (нужно «да» владельца → AskUserQuestion). UART-лог boot-console-20260930.log пуст (монитор не пережил ночь). DECISIONS 16:34. Дальше: ребут → проверить `watchdog0/state`=active и /tmp/p4/syslog.log → 2–3 суток аптайма → корпус (2–3 окт).**
 **30.09 16:41: владелец «да» → `reboot -f` 16:40:42, камера UP 16:41:01 (UART: Starting kernel, panic=20, sz=0x1800000), watchdog0 `active`, syslogd 633/klogd 635, /tmp/p4/syslog.log пишется (47 КБ), majestic 644, mma fail 0. ACCEPTANCE: аптайм с watchdog считаем с 16:41. Кроны: 003dff39 снят, здоровье камеры eabf08ee (:13/:53, 40 мин, 7 дней). UART-монитор b7rmnlbu8 (до ~17:04). Дальше: 2–3 суток аптайма → сказать владельцу «можно в корпус, Pi/UART отключать» (ориентир 2–3 окт). Побочно: dropbear генерит hostkey каждый ребут (/etc RAM) — известное, не срочно.**
 **30.09 17:03: здоровье ок (uptime 21 мин, watchdog active, mma 0, syslog.log 78 КБ, p4 63%, Frigate fps 5.0). UART-монитор заменён на постоянный логгер `setsid nohup cat /dev/ttyAMA2 >> uart/boot-console-20260930.log` (PID 173774, stty выставлен; проверять `pgrep -f "^cat /dev/ttyAMA2"`). Крон здоровья eabf08ee :13/:53. Позже: ротация записей на p4 (63%, 19.7 ГБ).**
 **30.09 17:33: здоровье ок (uptime 50 мин, watchdog active, mma 0, fps 5.0, UART-логгер жив). p4 66%, растёт ~1.5 ГБ/ч (split 20 мин, ~540 МБ/файл); ротация в majestic есть — `maxUsage: 90` («Past it, the oldest recordings are deleted»), порог ~22:30 → по df в кроне ждать плато ~90%, счётчик `records_cleanup_unlinks_total` в /metrics majestic.**

**18:47: ПУБЛИКАЦИЯ РЕПО (задача владельца 18:3x): здоровье 18:02/18:31 ОК (uptime 1:50, p4 71%). Коммит f396592: README.md переписан по-человечески (что/как/развернуть/статус/итог/фото/спасибо/MIT), LICENSE MIT (hleserg), docs/img/ 6 фото платы (наклейка MAC/QR замазана, проверено глазами), STATUS.md MAC с наклейки убран, uart/README.md распиновка ttyAMA2, sources/mindsolo-24929.html удалён, gh description без PRIVATE. Аудит: паролей/SSID/PSK в истории нет; MAC (без двоеточий) остался в ИСТОРИИ STATUS.md (78 коммитов). Открыт AskUserQuestion: чистить историю git-filter-repo + force-push (рекомендую) или оставить; после ответа — `gh repo edit --visibility public --accept-visibility-change-consequences`. Репо ещё PRIVATE.**

**21:41: РЕПО ПУБЛИЧНЫЙ https://github.com/hleserg/mjsxj05cm-research — владелец ответил «почистить историю и открыть»: git bundle бэкап в scratchpad, git-filter-repo заменил MAC (6 форм) на xxx в 7 местах истории STATUS.md, force-push main (c70b432 → c5df71b, 80 коммитов, хеши изменились), `gh repo edit --visibility public`. Проверено: visibility PUBLIC, 6 фото docs/img отдают 200, tree чистое. Старый SHA c70b432 ещё виден по API (dangling до GC GitHub), но репо был приватным — SHA никому не известен. Дальше: кроны здоровья камеры (аптайм с 16:41), 2–3 дня → «можно в корпус».**
**21:43: уточнение: старый SHA c70b432 ВИДЕН в Activity репо (force_push before) → MAC достижим для того, кто откроет вкладку Activity. Не блокер (MAC малоценен, владелец выбрал скраб+открыть), но решение владельца: (а) запрос в GitHub Support на purge dangling-коммитов, (б) удалить репо и запушить чистую историю в новый с тем же именем. Бандл старой истории (с MAC) только в scratchpad. Публичны только sd/mbr-*.bin (512 Б, таблица разделов, секретов нет); reference-photos и sources не отслеживаются.**
**03.10 01:52: ПРОПУСК 30.09 22:02→03.10 01:47 (сеть/Pi): Pi ребутилась 2.10 11:07/11:16/11:20, оверлей uart2-pi5 слетел (/dev/ttyAMA2 нет), UART-логгер умер 2.10 00:53; камера ПЕРЕЗАГРУЗИЛАСЬ 2.10 ~18:28 MSK (uptime 7:19 на 01:47, причина неизвестна — syslog p4 ротируется по 1 МБ, UART не писался), сейчас ок (majestic, watchdog active, mma 0, p4 87%, fps 5.2). Аптайм-приёмка идёт заново с 2.10 18:28. По просьбе владельца сделан автономный надзор: tools/health/cam-health.sh в crontab */10 (лог ~/.local/state/cam-health/health.log, Telegram при смене состояния, если владелец создаст ~/.config/cam-health/env) + user-сервис uart-logger (enabled, крутится в auto-restart пока нет /dev/ttyAMA2). Владельцу: `sudo dtoverlay uart2-pi5` сейчас и `echo 'dtoverlay=uart2-pi5' | sudo tee -a /boot/firmware/config.txt` навсегда. Перед stage.py/dump.py — `systemctl --user stop uart-logger`.**

## 09.10 15:37 — задача NOR: подготовка (бюджет bet-6ac8dbbb-cbe7)

Владелец: «делай nor» + «оба способа прошивки в git, в README как сделать какой, автоматизировано». Советник: это разрешение ГОТОВИТЬ, не писать. Запись — новый STOP (`uboot/STOP-nor.md`) + явное «да» + stage.py запускает владелец через `!`.

Решено (вариант b): rootfs для NOR = свой squashfs как p3 карты (vanilla + init4.sh + wpa.conf + shadow4) + `/opt/p1/` (autorun/cam-up/ptz/demo.sh, onvif-password.txt) — работает и без карты. DATA 0x9B0000 не трогаем. Переключение режимов без записи flash: есть `uImage.ssc325` на p1 → карта, переименован/карты нет → NOR (`bootcmd=run sdboot; run norboot` уже в env v4).

Сделано: `p4/init4.sh` v8 (hostname по root= в cmdline, autorun из /tmp/p1 или /opt/p1), `p4/cam-up.sh` OPW fallback, `make-rootfs-nor.sh` → rootfs-nor.squashfs 4923392 Б (63 % раздела), rootfs-nor.pad.bin crc32 1b23dd8c (строки в CRC.txt; файлы секретные, в git нет).

Дальше: 1) mkenv.py `--nor=openipc` → env v5 (norargs = sdargs с root=/dev/mtdblock2); 2) stage.py: таймаут на команду, WRITE_STAGES, `nor-openipc-write` (rootfs → kernel → env, каждый: erase/write/read/crc/cmp.b), `nor-stock-restore`, репетиция `2a-p2`; 3) tools/boot-mode.sh, tools/p1-put.sh через http.server+wget; 4) STOP-nor.md, README «Два режима», DECISIONS; 5) файлы на p1; коммит.

### 15:43 — всё подготовлено, файлы на карте, сессия перезапускается (владелец обновляет Claude)
Сделано и закоммичено: env v5 (`uboot/mkenv.py --nor=openipc`, crc 818e914a), stage.py (таймаут на команду, WRITE_STAGES, билдер `nor_write`, этапы `nor-openipc-check` / `nor-openipc-write` / `nor-stock-restore` / `2a-p2`, selftest ok), `tools/boot-mode.sh`, `tools/p1-put.sh` (http+wget), `uboot/STOP-nor.md`, README «Два режима» + шаг 6, DECISIONS 09.10. На p1 карты лежат (md5 сошлись): rootfs-nor.pad.bin, env-new.bin (= v5), env-new-v4.bin, cam-up.sh v8. **NOR не писался.**
Дальше (новая сессия, `resume bet-6ac8dbbb-cbe7`): 1) советник — ревью STOP-nor.md и stage.py; 2) репетиции `nor-openipc-check` и `2a-p2` (dd rootfs-nor.squashfs на p2 — сказать владельцу; stage.py запускает владелец через `!`); 3) STOP владельцу → «да» → запись; 4) приёмка по STOP, `task-budget end`.

### 09.10 16:25 — ревью советника перед STOP: 4 пункта закрыты
1. `root=/dev/mtdblock2` подтверждён на живой камере под ядром OpenIPC (/proc/mtd: mtd2 rootfs 7552k @0x250000, разметка зашита в ядро).
2. Строки U-Boot `Erased: OK` / `Written: OK` / `Total of N byte(s) were the same` сверены с логом записи env 29.09; cmp.b теперь ждёт точный N.
3. BIG 600 → 1800 с (erase 0x760000 по 4К-секторам до ~566 с по даташиту); по таймауту ABORT, U-Boot доделывает сам.
4. `EXTRA_OLD_CRC=…` в stage.py — гейт под фактический crc полузаписанной области; в STOP-nor.md: карта остаётся вставленной, sdboot = откат на полпути.
Дальше: показать владельцу план репетиций (nor-openipc-check → 2a-p2 с dd на p2 с его OK) → STOP → «да». NOR не писался.

### 09.10 16:46 — репетиции 1 и 2 пройдены, NOR не писался

1. **Репетиция 1 (nor-openipc-check, 16:38–16:40):** все гейты прошли — NOR = сток (env crc 25f375ed), файлы на p1 = CRC.txt, fatload 7.4 MiB за 1017 мс, ABORT нет.
2. **Репетиция 2 (2a-p2, 16:43–16:46):** p2 карты перезаписан rootfs-nor.pad.bin (md5 ee8ab35f… сверен), перевзвод через FIFO (`#stage 2a-p2` + `reset`), ядро с p1, `root=/dev/mmcblk0p2` → VFS смонтирован (179:2), INIT4_START → udhcpc .53 → dropbear → SSH_READY_ip → postboot ок. По ssh: hostname mjsxj05cm-sd (ожидаемо, root≠mtdblock2), /init4.sh md5 = репо, majestic и dropbear живы, /tmp/p1 ro + /tmp/p4 rw, RTSP/ONVIF отвечают 401 (авторизация, сервисы живы). **Содержимое образа NOR рабочее.**
3. **Сейчас:** камера работает с p2 (образ NOR), stage.py (PID 1853270) всё ещё держит ttyAMA2, uart-logger остановлен, cam-health на паузе (`~/.local/state/cam-health/pause`) — снять ПОСЛЕ записи NOR.
4. **Дальше:** владелец убивает stage.py → советник → STOP-nor.md владельцу → «да» → `NOR_WRITE=yes … nor-openipc-write` → reboot с согласия → 3× «were the same» → заполнить «ЗАПИСАНО», приёмка boot-mode.sh nor/sd, тест без карты (физически владелец) → снять паузу cam-health → STATUS/DECISIONS → task-budget end.

### 09.10 20:41 — NOR ЗАПИСАН (OpenIPC), камера жива с карты

1. **Запись 20:30–20:34:** владелец перезагрузил камеру, взведённый `nor-openipc-write` (PID 1862492) прошёл все гейты (старые crc c41c56d0/a5447ccc/25f375ed), записал rootfs 0x250000 (7733248), kernel 0x50000 (2097152), env v5 0x4F000 (4096); readback crc 1b23dd8c/6b5590f4/818e914a, три «were the same». Лог `uart/stage-nor-openipc-write-20261009-165513.log`. Подробно: `uboot/STOP-nor.md` → «ЗАПИСАНО».
2. **После reset:** env v5 → sdboot → карта p3, `mjsxj05cm-sd`, ssh/majestic/dropbear/RTSP/ONVIF ок, postboot ок 20:34. stage.py в пассивном режиме (только лог), uart-logger стоп, cam-health на паузе.
3. **Дальше:** приёмка NOR-режима: `tools/boot-mode.sh nor` → reboot (владелец) → ждём `root=/dev/mtdblock2`, hostname `mjsxj05cm-nor`, majestic/RTSP/ONVIF → обратно `boot-mode.sh sd` → физический тест без карты (владелец) → вернуть надзор (pkill stage.py, uart-logger start, снять паузу) → STATUS/DECISIONS/README → советник → budget end.

### 09.10 21:34 — ПРИЁМКА NOR-РЕЖИМА ПРОЙДЕНА

1. 21:33 владелец перезагрузил (uImage.ssc325 → .off на p1): U-Boot sdboot → «Wrong Image Format» → norboot → `root=/dev/mtdblock2`, `mjsxj05cm-nor`, /init4.sh md5 4fc97a6f = репо, p1/p4 смонтированы, majestic, dropbear, RTSP/ONVIF 401, postboot ок. Load average ~9 в sd-режиме (IspDriverThread 35 %, majestic 28 %) — так же было и до записи, не признак беды.
2. Камера оставлена в NOR-режиме (образ новее p3: init4 v8), карта как данные. Обратно: `tools/boot-mode.sh sd` + reboot. Физический тест без карты — за владельцем, когда удобно.
3. Осталось владельцу: вернуть надзор — `pkill -f "^python3 uart/stage.py"; systemctl --user start uart-logger; rm ~/.local/state/cam-health/pause`.
4. Новая просьба владельца 21:3x: «перевести камеру на другой wifi». Факт: SSID/PSK зашиты в `/wpa.conf` внутри squashfs (и p3, и NOR) — смена через пересборку rootfs = ещё одна запись NOR (STOP). Без флеша: autorun.sh/файл на карте → `wpa_cli add_network/set_network/enable_network` при старте. Решение за владельцем (какая сеть, PSK на карте ок?).

### 09.10 21:43 — надзор восстановлен

Владелец 21:50: `pkill stage.py; systemctl --user start uart-logger; rm pause`. Проверено 21:43: stage.py нет, uart-logger active, паузы нет, камера отвечает. Крон-проверка 555de45f снята. Ждём ответ владельца по Wi-Fi (сеть по роли, PSK на карте?) — отдельная задача.

### 09.10 22:37 — Wi-Fi beta-cam: живой тест пройден, rootfs v2 готов, ждём «да» (STOP-2)

1. 22:28 RAM-тест: `wpa_cli add_network` (psk 64-hex, priority 10) → COMPLETED, freq 2442, 192.168.30.53/24 via .30.1 (резерв DHCP владельца, name Beta360Cam), ssh/80/554 с Pi открыты. Откат-таймер (300 с) отменён 22:32 — камера остаётся на beta-cam до reboot (RAM-only).
2. Факт сегмента: Cam protected — камера НЕ достаёт до Pi (.1.139) и bigpc (.1.10); Home→Cam работает (ssh, RTSP). Поэтому `tools/p1-put.sh` v2 = push по ssh (`camssh.py --put`, stdin, 7.7 МБ за 10 с), http.server убран.
3. Собран rootfs v2: `p4/secret/wpa.conf` = старая сеть + beta-cam (v1 сохранён как `wpa.conf.v1`); `rootfs-nor.pad.bin` crc **2ac386df**, залит на p1 (md5 сошёлся). CRC.txt: строка v1 переименована в `rootfs-nor-v1.pad.bin` (1b23dd8c, гейт «в NOR сейчас»). stage.py: `nor-rootfs-check`/`nor-rootfs-write` (только 0x250000), selftest ok, `nor-stock-restore` принимает v1 и v2.
4. Инструменты на .30.53: `uart/camssh.py` (CAM_HOST, умолчание .30.53), `cam-health.sh` (export CAM_HOST), `onvif-pull.sh`. Пауза cam-health снята 22:37.
5. **Дальше:** «да» владельца → STOP-2 команды (`uboot/STOP-nor.md`, через `!`) → reboot → проверка (ssh .30.53, wpa_cli status, RTSP/ONVIF) → надзор (pkill stage.py, uart-logger start) → владелец: Frigate rtsp .1.53→.30.53 на bigpc, ONVIFer по IP → STATUS/README (.53 → .30.53) → budget end. Отдельно: карта p3 (sd-режим) со старым wpa.conf.

### 09.10 23:06 — STOP-2 ВЫПОЛНЕН: rootfs v2 в NOR, камера на beta-cam

1. Владелец запустил `nor-rootfs-write` 22:53:58 + reboot. Лог `uart/stage-nor-rootfs-write-20261009-225358.log`: гейт NOR `==> 1b23dd8c` (v1), файл p1 `==> 2ac386df`, Erased/Written OK @0x250000, readback `2ac386df`, «Total of 7733248 byte(s) were the same», reset. ABORT нет, другие области не трогались.
2. После reset: Linux из `root=/dev/mtdblock2`, `mjsxj05cm-nor`, /wpa.conf = 2 сети (md5 = репо a1040f33), wpa_state COMPLETED на beta-cam, 192.168.30.53, majestic/dropbear ок, 554/80 открыты, ONVIF 401. cam-health 23:00: «ПЕРЕЗАГРУЗИЛАСЬ» — ожидаемо, дальше ok.
3. Владельцу: `pkill -f "^python3 uart/stage.py"; systemctl --user start uart-logger` (stage.py ещё держит ttyAMA2); Frigate на bigpc rtsp .1.53 → .30.53; ONVIFer по IP .30.53. Отдельно потом: карта p3 (sd-режим) — старый wpa.conf, пересобрать p3 при случае.

Надзор восстановлен владельцем 23:15: stage.py нет, uart-logger active, камера .30.53 отвечает. Будильник a7722289 снят. Осталось владельцу: Frigate rtsp → .30.53.

## 09.10 23:31 — Frigate переключён на 192.168.30.53

Владелец выполнил sed+restart через `ssh bigpc "wsl -e bash -c ..."` (первая попытка с `nc` упала: `ssh bigpc` попадает в Windows cmd, `nc` нет, цепочка `&&` оборвалась — ничего не изменилось). Проверено мной через API Frigate в WSL: контейнер healthy, camera_fps 5.1, ошибок ffmpeg нет. Задача Wi-Fi закрыта полностью. Осталось только необязательное: карта p3 (sd-режим) со старым wpa.conf.

Заметка на будущее для команд на bigpc: пайпы/кавычки через cmd ломаются, рабочий приём — `B=$(printf %s '<скрипт>' | base64 -w0); ssh bigpc "wsl -e bash -c \"echo $B | base64 -d | bash\""`.

## 10.10 00:03 — карта p3 переписана образом v2

«Давай доделывать все» (23:4x) = согласие на p3. Проверено до записи: p3 на карте = область p3 из sd-stage8.img (md5 9a0b9f24…, резерв на Pi). Владелец через `!` (классификатор запретил мне dd в раздел и даже boot-mode.sh): гейты (NOR-режим, p3 не смонтирован, размер 32768 секторов, md5 источника) → `dd if=/tmp/p1/rootfs-nor.pad.bin of=/dev/mmcblk0p3 bs=1M conv=fsync` → drop_caches → md5 head 7733248 = 430bf02c…, head 4923392 = 51bbcfb7… (= rootfs-nor.squashfs v2). p2 (v1 с репетиции 2a-p2) не трогали — не в пути загрузки. Дальше: тест sd-режима (boot-mode.sh sd + reboot, владелец) → `mjsxj05cm-sd`, root=/dev/mmcblk0p3, .30.53 → boot-mode.sh nor + reboot.

### 10.10 01:09 — тест sd-режима с p3 v2 ПРОЙДЕН

Владелец 01:08: `tools/boot-mode.sh sd` + reboot. Через ~60 с: hostname `mjsxj05cm-sd`, `root=/dev/mmcblk0p3`, `init=/init4.sh` (md5 4fc97a6f = репо), majestic/dropbear живы, wpa_state COMPLETED на beta-cam (freq 2442), ssh/RTSP 554/HTTP 80 на 192.168.30.53. Оба режима (NOR и карта) теперь на новом Wi-Fi. Дальше: владелец возвращает NOR (`boot-mode.sh nor` + reboot), затем закрытие задачи.

### 10.10 01:32 — камера возвращена в NOR, задача Wi-Fi закрыта полностью

Владелец 01:31: `boot-mode.sh nor` + reboot → `mjsxj05cm-nor`, root=/dev/mtdblock2, majestic/dropbear, beta-cam, RTSP ок. Итог: NOR = rootfs v2, карта p3 = v2, Frigate на .30.53, cam-health на .30.53, uart-logger активен. p2 карты — v1 (старый Wi-Fi), не в пути загрузки, оставлен. Владельцу (его сторона): ONVIF-интеграция в HA, если есть, → host 192.168.30.53.

## 10.10 01:38 — пароль ONVIF сменён

Владелец: «а пароль onvif можем поменять?». Пароль = первая строка `onvif-password.txt` на p1 карты (cam-up.sh → majestic.yaml onvif.password, логин admin; копия в /opt/p1 внутри NOR — только запасная без карты, там остался старый). Новый 16-значный в `p4/secret/onvif-password.txt` (старый — `.old`), на p1 положен владельцем через `!` (p1-put, md5 9dffc4d6…), reboot 01:37. Проверено: majestic.yaml содержит новый, WSSE PasswordDigest admin+новый → GetDeviceInformation 200; старый отвергнут. Владельцу: вбить новый пароль в HA (ONVIF, host .30.53) и Onvifer. Чтобы обновить запасную копию в NOR — при следующей пересборке rootfs (STOP), не срочно.

02:00: владелец вбил новый пароль ONVIF в HA — «работает». Соединения к камере с .1.x видны как 192.168.30.1 (роутер между сегментами). Открытых пунктов по Wi-Fi/ONVIF нет.

## 10.10 02:19 — «почему нет звука»: причина найдена, правка ждёт p1-put + ребут владельца
- Камера отдаёт h264 + **opus** 48k (ffprobe). go2rtc во Frigate принимает opus; **записи Frigate со звуком** (последний mp4: aac 48k stereo, mean −38.9 dB — тихая комната). `audio_rms: 0` в stats — роль `audio` в Frigate не включена, это не «тишина».
- Без звука — **карточка ONVIF в HA**: компонент `stream` (HLS) пропускает только AAC/MP3, opus выбрасывает. Frigate live по умолчанию muted; Safari/iOS MSE+opus — тоже тишина.
- majestic (Lite, master+17ec3ed) умеет AAC без смены кодера: схема `rtsp.audioCodec: aac` («Audio codec for RTSP & ONVIF»), проверено живьём: `rtsp://…/stream=0&audio=aac` → `aac,audio` (именно `&`, не `?`). `audio.codec`/srate 8000 не трогаем («Cannot run AAC with srate» в бинарнике — не проверено).
- Правка: `p4/cam-up.sh` — одна строка `-e 's/^rtsp:/rtsp:\n  audioCodec: aac/'` в цепочке sed; busybox-sed на камере проверен во временный файл. Живой apply через /api/v1/config НЕ делал (возможный рестарт пайплайна = MMA-утечка).
- `tools/p1-put.sh cam-up.sh` — классификатор отказал (Remote Shell Writes) → владелец через `!`: p1-put + `sync; reboot -f`. init4.sh берёт autorun/cam-up с p1 (без карты — /opt/p1: NOR-копия теперь тоже устарела, вместе с onvif-password — в тот же STOP при пересборке).
- Проверка после ребута: `ffprobe rtsp://…/stream=0` без параметров → `aac,audio`; в HA при тишине — перезагрузить интеграцию ONVIF один раз. Frigate `preset-record-generic-audio-aac` перекодирует aac→aac — работает, `…-audio-copy` сэкономил бы CPU (конфиг владельца, не трогаю).

## 10.10 04:35 — звук: ИСПРАВЛЕНО, камера отдаёт AAC
- 04:3x владелец через `!`: `tools/p1-put.sh cam-up.sh` (md5 ff611bb8 совпал) + `sync; reboot -f`. Камера поднялась за ~1 мин, `/etc/majestic.yaml:64 audioCodec: aac`.
- ffprobe `stream=0` без параметров: `h264 / aac 8000`. go2rtc во Frigate переподключился сам: main и sub — `MPEG4-GENERIC/8000` (AAC), fps 5.3. HA (HLS) теперь получает AAC — владельцу глянуть карточку; при тишине один раз перезагрузить интеграцию ONVIF.
- Не срочно (в STOP при пересборке NOR): `/opt/p1/cam-up.sh` и `/opt/p1/onvif-password.txt` в rootfs NOR устарели (нужны только без карты).

## 10.10 04:51 — OSD дата/время (время с роутера), backchannel: ПРАВКА ГОТОВА, ждёт p1-put + reboot

Владелец: «роутер будет раздавать время, надо брать и добавлять на метку». Время камера уже берёт NTP со шлюза
(autorun.sh, ntpd -p gw; на роутере option 42 → .30.1). Часы камеры UTC, /etc/TZ=GMT0, /etc — tmpfs, S95majestic
экспортирует TZ из /etc/TZ. Правка cam-up.sh (коммит f65719c): `echo MSK-3 > /etc/TZ` до старта majestic,
osd.enabled: true (шаблон по умолчанию %d.%m.%Y %H:%M:%S, слева сверху), rtsp.backchannel: true (обратный звук
в динамик по ONVIF/RTSP). bash -n и sed-прогон на копии majestic.yaml с камеры — ОК. На карте p1 пока старая
версия (ff611bb8, только audioCodec).

Команда владельцу: `tools/p1-put.sh firmware/openipc-ipc017-20260926/p4/cam-up.sh && timeout 12 python3 uart/camssh.py "sync; reboot -f"`.

Проверка после ребута: md5 /tmp/p1/cam-up.sh = локальному; `date` на камере — MSK; /etc/majestic.yaml osd enabled,
rtsp backchannel; /image.jpg → время на кадре (кадр приватный, не публиковать); free, `dmesg | grep -ci mma`
(до ребута 5), go2rtc fps ~5 и AAC. Откат: убрать строку osd в sed-цепочке, p1-put, reboot.

Риск: бегущие секунды в OSD на detect-потоке = вечное движение в Frigate → владельцу нарисовать маску движения
поверх метки (Frigate UI → Settings → Motion masks, камера mjsxj05cm). Динамик: штатный есть, audio.outputEnabled
уже true; majestic имеет /play_audio (strings /usr/bin/majestic) — быстрый тест после подключения динамика.
dmesg: `[AUDIO ERROR]DrvAudStartDma error status 4` ×2 — не разобрано, перепроверить с динамиком. Зум: объектив
фиксированный, оптического зума в стоке нет (только цифровой в Mi Home). В ~/router-migration/HANDOFF.md
записано: NTP-сервер на Cam-сегменте NC-1012 оставить.

## 10.10 05:18 — OSD/TZ/backchannel: СДЕЛАНО, проверено

Владелец запустил p1-put + reboot 05:16 (md5 fe3b487d совпал). Проверено 05:17–05:20: /etc/TZ=MSK-3, у процесса
majestic TZ=MSK-3; majestic.yaml osd enabled: true, rtsp audioCodec: aac + backchannel: true; кадр /image.jpg —
метка «10.10.2026 05:17:46» (MSK, совпадает с Pi). ffprobe RTSP: aac 8000. Frigate: fps 5.3, det 5.3, skip 0.
free: available 14 МБ; dmesg mma 8 (до ребута 5 — на свежей загрузке, следить). ptz.sh init отработал (gpio44–47/80/16
экспортированы). Владельцу: маска движения поверх OSD в Frigate UI. Задача закрыта.

Моторы (вопрос владельца «точно будут работать в корпусе?»): электрически да — оба крутятся через ptz.sh (28.09),
init при каждой загрузке без движения. НЕ сделано: калибровка (стороны +/-, число полушагов до упора), лимитов
в ptz.sh нет (концевиков у камеры нет, сток калибруется проходом до упора при старте), интеграции в HA/Frigate
нет (majestic Lite без ONVIF PTZ). Тест после сборки: `python3 uart/camssh.py "sh /tmp/ptz.sh h + 200"`,
затем `h - 200`, `v + 100`, `v - 100` — по короткому шагу, не упираться.
Доп. 05:21: load average 8.6/4.9/2.1 при idle 36% (majestic 27%, vpe0/Isp в D-state — load считает их), avail 13 МБ, mma 7–8 (ровно), AUDIO ERROR 0 на этой загрузке, Frigate 5.2 fps без skip. Базы по load до OSD нет — контрольный замер в 05:56 (одноразовый крон).

## 10.10 05:29 — план после сборки корпуса (решения владельца)

Владелец собирает корпус и «попробует» вывести UART наружу (GND, TX, RX через 1 кОм; пады 13/14). После сборки:
1) калибровка PTZ (~1 ч с владельцем у камеры: стороны +/-, полушаги до упоров → лимиты в ptz.sh);
2) управление из HA (~2–3 ч): busybox httpd + cgi → ptz.sh на камере, rest_command + кнопки в HA; Frigate/ONVIF PTZ
невозможен (majestic Lite);
3) OTA без UART: U-Boot не перезаписывается, bootcmd = sdboot→norboot; схема обновления NOR — включить загрузку с карты
(uImage.ssc325 на p1 по ssh) → ребут с карты → flashcp в NOR (сейчас запрещено, снять отдельным STOP с «да») →
выключить загрузку с карты. Скрипты/конфиги на p1/p3 — по ssh как сейчас.
Доп. 05:57: контрольный замер не снят — камера НЕ ОТВЕЧАЕТ (cam-health: 05:30 ok up 13 мин, 05:40 down; Frigate fps 0). На UART после 05:31:38 тишина: нет «Restarting system», паники и баннера U-Boot (watchdog при зависании дал бы ребут) → похоже, снято питание (владелец собирает корпус). Будильник 06:3x: если вернулась — снять замер (load/mma/avail/fps).

## 10.10 06:10 — UART ПОТЕРЯН: владелец сорвал пад 13 (TX камеры)

Фото владельца: пад 13 оторван, рядом капли припоя и флюс, в 5 мм — SOP-8 (по виду SPI NOR, маркировка 25Q…).
Другой точки цепи UART0 TX в исследованиях нет (research/uart0-padmux-notes.md). Рекомендация: НЕ восстанавливать
(ещё одно отслоение рядом с флешкой дороже, чем консоль). Последствия: stage.py/dump.py по UART больше не работают,
U-Boot-консоль только «вслепую» через пад 14 (RX, не рассчитывать). Восстановление после сбоя NOR — только карта:
U-Boot (никогда не пишется) → sdboot → uImage.ssc325 на p1. Перед следующей сборкой NOR — обязательно проверить
загрузку с карты. Перед включением: смыть флюс/капли изопропилом, проверить ножки SOP-8 на перемычки.
uart-logger на Pi можно остановить (нечего слушать) — по слову владельца.

## 10.10 07:38 — корпус собран, моторы/динамик/ИК проверены, PTZ откалиброван

- 07:10 камера включена в корпусе, загрузилась из NOR (rootfs v2) на 192.168.30.53. OSD с временем на кадре, Frigate 5.3 fps / skip 0 при load 10–11 во время моторов.
- Моторы: `h +` = против часовой (как видит владелец), `v +` = вверх. Упор в механический стоп безвреден.
- Динамик: GPIO15=1 + `POST /play_audio` (`Content-Type: audio/L16`, s16le mono 8 кГц, basic auth **root-паролем**, ONVIF-пароль даёт 401) — пищит.
- ИК-лампа: горела с загрузки (pwm0 не настроен → пад высокий, 6 диодов, фото владельца). Погашена: period 8333, duty 0, enable 1. В RAM, не персистентно.
- Калибровка по кадрам RTSP (2 fps, PIL diff): пан ≈ **4100** полушагов упор-упор (≈360°, 4096 = оборот редуктора 28BYJ-типа → ≈11.4 полушага/°), тилт ≈ **700** (≈96° → ≈7.3 полушага/°), точность ±30.
- Скорость ≈ **28 полушагов/с** при PTZ_US 8000 и 20000 одинаково: ~22 мс накладных на состояние (4 sysfs-записи + fork usleep, nofork-апплетов в busybox нет). Владелец трижды: «медленно». Ускорение — PWM-группа pwm4..7 или маленький бинарник; отдельная задача.
- Центрирование сделано (`h - 2050; v - 350` от упоров, лог `/tmp/ptz.log`: оба ок).
- Правки репо: `p4/ptz.sh` — комментарий калибровки, PTZ_US по умолчанию 8000, команда `lamp %`, `init` гасит лампу (→ при автозапуске лампа будет выключена). **На карту p1 не залито** — нужен `tools/p1-put.sh` + перезагрузка владельцем.
- Долгие моторные задания: только `nohup sh -c '…' > /tmp/ptz.log 2>&1 &` на камере (camssh exec 120 с), `pkill` на камере нет.
- Дальше: быстрый PTZ; залить ptz.sh на p1; кнопки PTZ в HA; маска движения Frigate поверх OSD.
- 07:52: владелец залил ptz.sh на p1 (md5 5571690a) и перезагрузил; через 36 с uptime pwm0 duty 0 / enable 1 — лампа выключена с загрузки, AUTORUN_done, image.jpg 200, Frigate fps 4.5 skip 0.3 (стрим только поднялся).

## 10.10 08:12 — быстрый PTZ: бинарник

- `tools/ptz/ptz.c` + `tools/ptz/build.sh` (zig в `~/.local/zigenv`), результат `p4/ptz`. Проверен на Pi (armhf-совместимость, каталог-заглушка вместо sysfs) и на камере.
- Скорость: 375 полушагов/с при 2000 мкс (по умолчанию); 1000 мкс — подёргивается. Полный оборот ≈11 с, тилт край-край ≈2 с. Владелец подтвердил возврат в точку по обеим осям (тилт 150 полушагов при 2000 мкс — чисто).
- В RAM камеры уже новые `/tmp/ptz` (md5 74977316) и `/tmp/ptz.sh` (3da46b6e). Залито на p1 владельцем (md5 совпали). Перезагрузка для проверки autorun — в удобный момент.
- Дальше: кнопки PTZ в HA (httpd+cgi на камере → ptz.sh; rest_command в HA), маска движения Frigate поверх OSD.
- 08:17: `ptz.sh home` (h −4300 → +2050, v +800 → −350) = центрирование как у стока, 19.7 с бинарником; в autorun после init, только если есть /tmp/ptz. Прогнано на камере. Залито на p1 (md5 8c2007a9 / e1f48901).

## 10.10 08:27 — кнопки PTZ в HA (камера готова, HA ждёт reload)

- Камера (RAM): `httpd -p 8080 -h /tmp/www`, CGI `/tmp/www/cgi-bin/ptz` = `p4/ptz-cgi.sh` (md5 c636443a).
  Тесты: `left=abc`/`up=99999`/`x=1` → bad, `home` → ok, повтор сразу → busy, замок снимается.
  Доступ с doctor (:8080) проверен. Направления: `h +` = влево (кадр уезжает вправо), `v +` = вверх.
- autorun.sh в репо получил строки httpd (после `home`, чтобы кнопка не перебила центрирование); залито на p1 08:50 (ptz-cgi c636443a, autorun 6a099d9e) — **в репо тоже**
  (`tools/p1-put.sh`), перезагрузка не нужна.
- HA: `tools/ha/mjsxj05cm_ptz.yaml` скопирован на doctor в `packages/`, `check_config` чистый.
  Владельцу: Developer tools → YAML → «REST commands» и «Template entities» (или рестарт HA),
  потом `./scripts/normalize-entity-ids.sh` не нужен — entity_id заданы через `default_entity_id`.
- Дальше: владелец жмёт «влево» и говорит, туда ли уехала картинка. Потом по желанию: basic auth, переключатель ИК-лампы.

## 10.10 09:20 — дашборд «Камеры» в HA; Onvifer: разведка

- Владелец не нашёл «влево»: кнопки — сущности без карточки. Сделан дашборд `tools/ha/dashboards/cameras.yaml` (live `camera.mjsxj05cm` + крестовина из `button.mjsxj05cm_ptz_*`, ifeel, кормушка), скопирован на doctor в `dashboards/cameras.yaml`, зарегистрирован в `configuration.yaml` как `iot-cameras` (бэкап `configuration.yaml.bak-20261010-cams`), check_config EXIT=0. **Нужен перезапуск HA владельцем**, потом проверка направления «Влево».
- Onvifer (ONVIF PTZ): majestic «Lite SigmaStar master+17ec3ed» отвечает на /ptz «No motor driver»; моторы у него только через плагин `/usr/lib/majestic-af.so` (актуатор gpiostep = модуль ядра gpiostep.ko, Goke) — на камере плагина нет, пересборка прошивки + NOR не вариант. План: onvif_simple_server (roleoroleo, клон в scratchpad oss/) как CGI под уже поднятым busybox httpd :8080; сервис выбирается по basename argv[0]; PTZ-команды конфига → `/tmp/ptz h|v ± N` в фоне, stop = kill (у ptz обработчик SIGTERM обесточивает обмотки). Открыто: путь `/onvif/...` зашит в ответах (device_service.c:52–56) — либо прокси-правило `P:` в httpd.conf, либо sed по исходникам; статическая сборка zig + mbedtls/json-c.

## 10.10 09:45 — ONVIF PTZ для Onvifer работает с Pi (RAM), ждёт p1-put и проверки в Onvifer

- Сделано: `tools/onvif/build.sh` (статический onvif_simple_server 95c17f7, патчи путей/конфига, USE_ZLIB) → `p4/onvif.tgz` (257 КБ);
  `p4/onvif-ptz.sh` (left/right/up/down/stop/home/moving/pos → `/tmp/ptz`, замок `/tmp/ptz.lock`), `p4/onvif.conf.tpl` (`__PW__` ←
  `onvif-password.txt`, профили `rtsp://%s/stream=0|1`, `snapurl http://%s/image.jpg`, PTZ 360°/96°), блок в `p4/autorun.sh` перед httpd.
- Проверено с Pi `tools/onvif/soap-test.py`: GetSystemDateAndTime/GetDeviceInformation/GetCapabilities/GetServices/GetProfiles/GetStreamUri/
  GetSnapshotUri/GetNodes/GetStatus — 200; ContinuousMove влево/вверх → MOVING, Stop → IDLE, замок снят, катушки 0; GotoHome центрирует.
  XAddr: `http://192.168.30.53:8080/cgi-bin/onvif/device_service`. Память камеры после: 11,4 МБ available, httpd pid 1209 жив.
- На камере сейчас всё в RAM (положено вручную с Pi). Ждёт владельца: `tools/p1-put.sh` onvif.tgz, onvif-ptz.sh, onvif.conf.tpl,
  autorun.sh → после перезагрузки поднимется само. В Onvifer: добавить устройство вручную по URL выше, admin + ONVIF-пароль.
  Открытый вопрос: примет ли Onvifer URL с путём `/cgi-bin/onvif/device_service` (в вебе ответа нет). Если нет — план B: второй
  httpd на другом порту с правилом `P:/onvif/:http://127.0.0.1:8080/cgi-bin/onvif/` (прокси на ДРУГОЙ httpd, не на себя — само-прокси
  вешало httpd). Симлинк `/onvif/` в другом корне не вариант: busybox исполняет CGI только под `/cgi-bin/`.
- DECISIONS.md: раздел «ONVIF PTZ для Onvifer». HA-дашборд «Камеры» по-прежнему ждёт рестарта HA владельцем.

## 10.10 09:49 — блок autorun.sh для ONVIF прогнан на камере, снимок admin'у не отдаётся

- Новый блок autorun.sh (распаковка onvif.tgz, 3 симлинка, onvif-ptz.sh, подстановка пароля в conf) прогнан на камере
  в отдельном каталоге (`D=/tmp/stage`, `/tmp/www2`): md5 сгенерированного conf = рабочему (4e46aaa6…), права и симлинки
  на месте. После перезагрузки autorun поднимет ONVIF так же, как сейчас в RAM.
- `GET /image.jpg` с `admin:<ONVIF-пароль>` → 401 (majestic пускает только root). В Onvifer превью/снимок будет пустым,
  live-видео и PTZ не затронуты. Если мешает — в conf.tpl убрать `snapurl` или настроить majestic на admin (не трогать без владельца).
- `events_service` в GetCapabilities объявлен, но не выложен (404) — PTZ не влияет; при жалобе клиента добавить симлинк +
  `events_service_files` в onvif.tgz.

## 10.10 10:24 — Onvifer: «движение не работает» → добавлен RelativeMove, на камере логгер запросов

- Владелец: в Onvifer движение не работает. С Pi всё отвечало; RelativeMove отвечал 500 (ActionFailed -3): у onvif_simple_server
  нет `jump_to_rel`. Добавил: conf.tpl `jump_to_rel=/tmp/onvif-ptz.sh rel %f %f %f`, в onvif-ptz.sh подкоманда `rel dx dy`
  (1.0 = 180° пан / 48° тилт, awk, под тем же замком). Проверено на камере: мотор едет, замок снимается. В RAM уже стоит.
- На камере (RAM) симлинки сервисов заменены обёртками: `bin/<svc>` — жёсткие ссылки на бинарник, обёртка пишет
  `/tmp/onvif/req.log` (время, REMOTE_ADDR, сервис, len) и `/tmp/onvif/body.log` (тела через tee). Всё из Home приходит
  как 192.168.30.1 (NAT Home→Cam на роутере) — телефон от Pi по IP не отличить, только по времени. После отладки обёртки
  уйдут при перезагрузке (autorun ставит симлинки). Лог не коммитить: в телах WS-Security digest.
- soap-test.py: добавлены GetNode/GetConfigurations/GetConfigurationOptions/RelativeLeft, `RAW=1` печатает тело ответа.
- Ждёт: владелец повторяет попытку в Onvifer → читать req.log/body.log (какие операции, какие ответы).
