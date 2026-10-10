# MJSXJ05CM / IPC019 — состояние на 2026-10-10 01:32

**Кратко на 09.10 (23:31):** **Wi-Fi beta-cam: rootfs v2 записан в NOR** (STOP-2, 22:54–23:00, только 0x250000: гейт 1b23dd8c → записано crc `2ac386df`, readback и cmp.b сошлись, kernel/env не трогались). `/wpa.conf` = старая сеть + beta-cam (priority 10); после reset камера сама поднялась из NOR на beta-cam **192.168.30.53** (Cam-сегмент, статический резерв DHCP), majestic/dropbear/RTSP/ONVIF живы, cam-health следит за .30.53. Cam-сегмент protected: камера не достаёт до Pi/bigpc, Home→Cam работает; `tools/p1-put.sh` теперь push по ssh. Frigate на bigpc переключён на .30.53 (владелец, 23:31; healthy, 5.1 fps). Карта p3 переписана v2 и проверена загрузкой с карты (10.10 01:09); камера снова в NOR. Задача Wi-Fi закрыта. 10.10 04:35: звук — rtsp.audioCodec: aac (HA/HLS не играет opus), проверено.

**Кратко на 09.10 (20:43):** **OpenIPC ЗАПИСАН В SPI-NOR** (20:30–20:34; rootfs 0x250000/7733248 Б crc 1b23dd8c, ядро 0x50000/2097152 Б crc 6b5590f4, env v5 0x4F000/4096 Б crc 818e914a; readback U-Boot «were the same» по всем трём; U-Boot/config/factory/rootfs_data не тронуты; лог и гейты — uboot/STOP-nor.md «ЗАПИСАНО»). После reset env v5 выбрал карту (uImage на p1) — камера жива в sd-режиме, откат через карту доказан. Приёмка NOR-режима (`tools/boot-mode.sh nor` + reboot → `mjsxj05cm-nor`, `root=/dev/mtdblock2`) и тест без карты — следующий шаг; надзор (uart-logger, cam-health) пока на паузе.

**Кратко на 03.10 (23:09):** аптайм-тест с watchdog пройден — ~2 суток и ~28 ч без зависаний (обе остановки внешние), критерий «неделя» снят; на Pi автономный надзор `tools/health/` (cron каждые 10 мин → Telegram при смене состояния; UART-логгер — user-сервис systemd, оверлей `uart2-pi5` прописан в config.txt). Репозиторий публичный (01.10, MAC вычищен из истории). Осталось: корпус (владелец, на днях), калибровка PTZ, движение через Frigate.

**Кратко на 28.09 (23:38):** env U-Boot ЗАПИСАН в NOR и проверен (23:26, единственная запись во flash: 0x4F000/4096 Б, crc32 b8213e13); после тёплого `reset` U-Boot не прочитал карту → `norboot` → сток с NOR поднялся (откат доказан вживую); холодный старт с карты без Pi ждёт пауэр-цикла владельцем. Решение владельца: на малинке только агенты — go2rtc/Frigate с Pi убраны; HA (ONVIF) и Frigate живут на большом компе и берут поток прямо с камеры; запись вкруг — на карте (p4, majestic records), просмотр/скачивание — HTTP с камеры + Frigate (DECISIONS 23:38). Ниже — на 23:10. **Старое кратко (23:10):** RAM-репетиция env (`2a-p4-env`) ПРОЙДЕНА — env-new.bin (crc32 b8213e13) через `env import` + `run bootcmd` грузит карту, автозапуск дошёл до AUTORUN_done; STOP-запрос uboot/STOP-env.md выдан владельцу, NOR не тронут. Находка: `env import` не перезаписывает ethaddr (для `sf write` неважно). Ниже — на 22:40.

**Кратко на 28.09 (22:40):** heap-тест пройден (mma_heap 0x1800000, mma fail 0), SUB-поток и go2rtc `cam_sub` работают; движение: majestic Lite без детектора → Frigate на Pi (DECISIONS 22:20); этап записи env в NOR `nor-env-write` готов в stage.py, ещё НЕ запускался — ждёт RAM-репетиции `2a-p4-env` (перевзвод владельцем) и «да» на `uboot/STOP-env.md` (DECISIONS 22:38). Ниже — на 20:35: карта sd-stage8, автозапуск сервисов с карты подтверждён на реальной загрузке (18:05) и на ребут-тесте (20:23: `reboot -f` → stage.py на Pi сам перехватывает U-Boot, камера возвращается на OpenIPC за ≈22 с); go2rtc на Pi отдаёт MAIN (`rtsp://192.168.1.139:8554/cam_main`); флуд `MI ERR mma fail` в UART убран printk 4 (причина — буферы VPE главного потока не влезают в mma_heap 20 МБ, фикс на следующую загрузку — `sz=0x1800000`). Холодная загрузка без Pi по-прежнему требует U-Boot env в NOR (STOP-этап). Старое «кратко»: OpenIPC загружается с SD-карты (sd-stage7, RAM-only, во flash по-прежнему ничего не писали), Wi‑Fi и SSH поднимаются сами; majestic даёт видео (RTSP/ONVIF/jpg) и звук; вся периферия проверена на OpenIPC: IR‑cut, ИК‑лампа, оба мотора, динамик, микрофон (подробности — [DECISIONS.md](DECISIONS.md) записи 28.09 12:58…16:55, чек-лист — [FULL-CONTROL-ACCEPTANCE.md](FULL-CONTROL-ACCEPTANCE.md)). Камера дважды сбрасывалась (перезапуски majestic текут по MMA; просадка питания с USB-гнезда фильтра) — владельцу рекомендован адаптер 5 В ≥ 2 А. Ниже — история до 27.09. **17:40:** автозапуск с карты готов — `p4/autorun.sh` на FAT p1 (NTP со шлюза, cam-up.sh, ptz init), хук в `init4.sh` v7 (`sd-stage8.img`, карта ещё не переписана) и интерим-хук `uart/postboot.sh` из stage.py; проект в git: https://github.com/hleserg/mjsxj05cm-research (private). Холодная загрузка без Pi по-прежнему требует U-Boot env в NOR (первая запись flash, отдельный этап).

Камера владельца: `chuangmi.camera.ipc019`, stock `4.3.9_0445` (со слов владельца, с устройства не считано), IP 192.168.30.53 (beta-cam, Cam-сегмент; до 09.10 23:00 — 192.168.1.53), MAC `xx:xx:xx:xx:xx:xx`. MAC совпадает с наклейкой на SD‑слоте (наклейка: MAC без двоеточий и `IPC019 419`). Плата разобрана, с 06:42 27.09 на штатном питании и в Wi‑Fi. **Во flash ничего не писали; свой проверенный dump есть (см. Recovery).** Камера обесточена с ~21:30 27.09. Прошлая версия файла: `logs/STATUS-2026-09-22.md.bak`.

## Hardware — CONFIRMED по фото нашей платы ([фото](photos/our-unit/README.md))

| Узел | Что стоит | Фото |
|---|---|---|
| Передняя плата | **LSAM041D1-1** (в брифе было LSAM044D1-1 — для нашей платы неверно) | set1 `9cef2f28`, set2 `47fbbc51` |
| Оборот той же платы | «2015 13MV0 94V-0 E157925». Передняя и задняя — две стороны одной PCB (вывод по фото, см. DECISIONS.md) | set1 `1cea1a9a` |
| SoC | SigmaStar **SSC323** «A400190B 2012S-4MI», кварц 24 МГц, оборот платы | set1 `18402a88`, `080a64b1` |
| SPI NOR | **cFeon EN25QH128A-104HIP**, «QH128A-104HIP X902R01 1947HKT»: 128 Мбит = 16 MiB, SOP‑8, питание 2.7–3.6 В. Стоит на стороне объектива, справа от него. Pin 8 (VCC 3.3 В) — нижний левый на карте UART, напротив pin 1. Pin 1 = ▽ на шелкографии. JEDEC ожидается `1C 70 18`, **не прочитан**. flashrom: `EN25QH128` | set2 `1d9b0276`, `2e6b0629`, `7a65b8b2` |
| Wi‑Fi | MT7601UN (USB), кварц 40 МГц, антенна на U.FL | set3 |
| IR‑CUT | драйвер UTC6208, 2‑pin разъём «IR-CUT», передняя плата | set2 `18e0a75a`, `d7e992b2` |
| Моторы | UTC2803M «Y9NDDA» (SOP‑18, ULN2803‑тип) на обороте платы → 5‑pin разъём. Два шаговика «019-200423 ZD / DC 5V 1/32 / MJSXJ05C», 5‑проводные униполярные (pan, tilt) | set1 `1d4a7e4f`, set3 |
| Звук | динамик 8 Ω 1 W на разъёме «SPK» (усилитель включается GPIO 15). Микрофон — электретный диск ~4 мм, 2 провода, свой 2‑pin разъём, стоит у передней стенки за платой ИК‑диодов (фото владельца 28.09) | set3 |
| База | плата «10VO … 2019»: micro‑USB питание, кнопка reset/setup, жгут 2×3 | set3 |
| Рядом с 7 площадками у SD | SOT‑23‑6 «AL65 ABM9» | set2 `62eb80de` |

## Firmware

- Официальные `3.4.2_0062`, `3.5.1_0052` и `4.0.9_0426` скачаны и распакованы, хеши в [firmware/README.md](firmware/README.md). Образ `3.5.1_0052` у khmyznikov байт‑в‑байт совпал с официальным recovery.
- Образы — ARM uImage с корректными CRC. В `3.5.1`/`4.0.9` SquashFS на `0x200000` и JFFS2 на `0x960000` **внутри файла образа**; это не адреса во flash.
- Update `4.0.9_0426` содержит `uboot_ota.sh`: при наличии `BOOT.bin.gz` вызывает `flashcp … /dev/mtd0`. Любой OTA/SD update может переписать U‑Boot.
- Образ `4.3.9_0445` недоступен, механизм проверки подписи SD recovery на нём неизвестен.
- По boot log: ядро 4.9.84 собрано 16.01.2024 (это 4.3.9), U‑Boot — от 4.0.9_0425 (15.09.2020). **U‑Boot сам проверяет SD при загрузке** (`there's no sdcard, ignore dfu`) — Второй SD‑механизм — в Linux: `Start detecting tf_update.img`. SD в камеру не вставлять, пока оба не разобраны. `miio_ota` активен.

## UART — TX = площадка 13, RX = площадка 14, 115200 8N1; U‑Boot прерывается

- **GND (со слов владельца):** зелёные метки — кольца винтов, медь по краю передней платы и 5 отдельных площадок (G на [карте](photos/our-unit/uart-candidates-numbered.jpg)).
- **Кандидаты 1–18** на той же карте:
  - 1–5 — кластер из 7 площадок у SD‑слота, в нём 2 GND;
  - 6–12 — кластер 3×3 слева от SD, в нём 1 GND;
  - 13–18 — площадки вокруг SPI NOR, 2 GND рядом с 13.
- На 1, 5, 11, 12 видны точки — похоже на следы пого‑пинов заводского стенда. Это гипотеза, не факт.
- **Замер 2026-09-27** ([таблица](uart/pad-voltages-2026-09-27.md)): 13 = 3.3 В и прыгает 2.4–3.3 при загрузке → TX или CS# флешки (та же картина), прозвонка: 13 и 14 ни с одной ножкой NOR не звонятся → 13 = TX, 14 ≈ RX. Pad 4 при включении стоит — не TX. 14 и 12 — ровно 3.3 В. **8 и 11 — 5 В, к Pi не подключать никогда.** 15 — 1.8 В.
- **2026-09-27 06:42: полный boot log снят** RX‑only (13 → Pi GPIO15 pin 10, кольцо винта → Pi pin 6): [`uart/boot-20260927-064230.log`](uart/boot-20260927-064230.log), разбор — [`uart/boot-analysis.md`](uart/boot-analysis.md). 115200 8N1 подтверждено.
- Ядро: `console=ttyS0,115200`. U‑Boot 2015.01 из сборки `ipc019_4_0_9_0425`, `bootdelay`, похоже, 0 (строки «Hit any key» нет).
- ⚠ Первая попытка (06:37): провода стояли на pins 8 и 12, т.е. земля камеры была на GPIO14 = TXD0 (выход Pi, высокий уровень) несколько минут. Петля pin 8 ↔ pin 10 в 06:59 вернула `LOOP-8-10-OK\r\n` байт в байт — GPIO14 цел.
- **Приёмник на Pi 5:**
  - `/dev/serial0 → ttyAMA10` — это отладочный JST‑разъём Pi, и на нём консоль Pi с getty. Для захвата **не годится**.
  - На GPIO15 (pin 10) функция UART не включена. Нужно `sudo dtoverlay uart0-pi5` (без перезагрузки, пропадёт после неё), после этого появится `/dev/ttyAMA0`. GND — pin 6. **Pin 8 (GPIO14, TX) не подключать.**
  - **29.09 14:3x: с NVMe‑шапкой pin 10 верхней гребёнки НЕ соединён с GPIO15 (стоит 3.3 В при управлении GPIO15; pin 12 мигает). Переехали на uart2: `sudo dtoverlay uart2-pi5` → `/dev/ttyAMA2`; CAM TX (pad 13) → pin 29 (GPIO5 RXD2), резистор 1 кОм → pin 7 (GPIO4 TXD2) → pad 14, GND → pin 6. stage.py читает `UART_PORT` (по умолчанию `/dev/ttyAMA2`).**
  - USB‑UART к Pi не подключён. `/dev/ttyACM0` — это чужая ESP32 (Espressif USB JTAG), её не трогать.

## Flash layout — CONFIRMED по boot log (MXP_PARTS ядра)

JEDEC `1C 70 18` (EN25QH128A), 16 MiB, erase `0x10000`.

| MTD | Смещение | Размер | Имя |
|---|---|---|---|
| mtd0 | `0x000000` | 320 KiB | BOOT: IPL `0x0`, IPL_CUST `0x10000`, MXP `0x20000`, U‑Boot (XZ), env `0x4F000` (4 KiB) |
| mtd1 | `0x050000` | 2 MiB | KERNEL |
| mtd2 | `0x250000` | 7.375 MiB | ROOTFS (squashfs ro, `root=/dev/mtdblock2`) |
| mtd3 | `0x9B0000` | 6.1875 MiB | DATA (jffs2) |
| mtd4 | `0xFE0000` | 64 KiB | CONFIG |
| mtd5 | `0xFF0000` | 64 KiB | FACTORY |

Совпадает с раскладкой khmyznikov. Сигнатуры на своих смещениях подтверждены нашим dump (`dump.py check`, binwalk).

## Root / Video / Audio / PTZ / IR‑Night / Motion / SD / ONVIF / HA

**28.09:** этапы 0–2 пройдены, этап 3 (запись во flash) НЕ начат. Root по SSH со своим паролем (dropbear на карте), видео MAIN через majestic (RTSP/ONVIF/jpg; SUB `video1` пока выключен), аудио вход/выход, IR‑cut GPIO 78/79, лампа pwm0, моторы `p4/ptz.sh` (GPIO‑полушаг), всё RAM‑only с карты. Открыто: стороны моторов после сборки стойки, NTP, автостарт, motion/записи, HA. Ниже — план, как он был записан 27.09. Путь: OpenIPC профиля `ssc325_lite_chuangmi-ipc017` (то же железо: SSC323, GC2053, MT7601U, MTD, bootargs). План младшего «три этапа» проверен и переработан 27.09 ~23:50 ([DECISIONS.md](DECISIONS.md) «ревизия плана … итоговый план»), отчёт Астры учтён.
0. Стол — **сделано 28.09 ~00:40** кроме разбора grablya95 (идёт): `firmware/openipc-ipc017-20260926/sd-stage2.img` (73 MiB: p1 FAT32 с uImage, kernel/rootfs.pad.bin, стоковыми mtd-*.bin для отката и CRC.txt; p2 = rootfs.squashfs), собирается `make-sd.sh`, файлы внутри сверены по sha256; `CRC.txt` (CRC32/SHA‑256 дополненных образов, стоковых разделов и блока 0xFF); `uart/stage.py` (этапы 1/2pre/2a/2b, selftest, запрещённые команды U‑Boot отфильтрованы, консоль в Linux через FIFO `uart/console.in`).
1. Root shell стока из RAM (`init=/bin/sh`, без `saveenv`) — карта GPIO, `dmesg`, `.ko` (~45 мин, «да» есть).
2. **Полный OpenIPC с SD** (`root=/dev/mmcblk0p2`; SD‑драйвер в ядре встроен, `/init` при mmcblk flash не трогает) — сначала проверка, что ядро видит **7 разделов** NOR без `mtdparts=` в bootargs (иначе `saveenv` в BOOT — отдельное «да»), затем видео, Wi‑Fi, звук, IR, GPIO (~2 ч).
3. Единственная запись: KERNEL 0x50000/0x200000 + ROOTFS 0x250000/0x760000 из файлов, дополненных 0xFF до размера раздела (`fatload`+`sf update`), `sf erase` DATA 0x9B0000/0x630000; проверка `sf read`+`crc32` по всему разделу; откат теми же командами из dump (~1 ч + отчёт).
4. Доводка по SSH: пароль, NTP, majestic (audio, motion, записи на SD), HA/go2rtc/Frigate, свой PTZ‑демон по карте `research/stock-gpio-map.md` (PWM4..7/GPIO44–47 + выбор 80/16; в OpenIPC нужен патч DTB `pad-ctrl` или падмукс) (2–4 ч).

План Б: `tf_recovery-3.5.1_0052.img` через наш U‑Boot + grablya95 v1.2.2 (SSH, RTSP 8554, ONVIF 5000, motord, audio‑bridge). Временное видео на стоке: go2rtc `xiaomi://` — только с интернетом и аккаунтом Mi Home, не ставим без слова владельца. Критерии — [FULL-CONTROL-ACCEPTANCE.md](FULL-CONTROL-ACCEPTANCE.md).

## Cloud removal

Не начато. Сеть (2026-09-22):
- TCP закрыт весь, 0/65535.
- miIO UDP 54321 отвечает, token = `FF…`.
- Ни SSDP, ни WS‑Discovery не отвечают.

[Логи](network/README.md).

## Recovery

- **Свой проверенный backup есть (27.09 15:33):** `spi/original-01/02/03.bin`, 16 MiB, sha256 у всех трёх `46bb4058fed894763cc94a1281261ff96ec306bcd5eb1410c56d1d4a20f218ee` ([SHA256SUMS](spi/SHA256SUMS)). `cmp` 01=02=03, CRC32 `9c33df0c` = CRC U‑Boot по RAM во всех трёх `sf read`, binwalk 02/03 = 01, hexdump 4 KiB на 0x0/0x4F000/0x50000/0x250000/0x9B0000/0xFE0000/0xFF0000 совпал, `dump.py check` ок у всех.
- Разрезан по MTD: `firmware/own-4.3.9_0445/mtd-*.bin` (+ SHA256SUMS). В dump и `mtd-data/config/factory` — пароль Wi‑Fi, ключи и MAC устройства: наружу не выкладывать.
- **Копия вне Pi (27.09 21:26):** `doctor:/mnt/backup/mjsxj05cm-flash-20260927/` — три dump + SHA256SUMS, `sha256sum -c` там OK, папка 700, файлы 600. `backup-pull.sh` на докторе чистит только `world-*.tar.gz`, эту папку не трогает.
- Чужой полный SPI image (khmyznikov) не записывать: в нём чужие config/factory/MAC/calibration.
- **С 09.10 в NOR OpenIPC** (kernel 0x50000, rootfs 0x250000, env 0x4F000): «вынуть карту → сток» больше не работает. Возврат стока = запись тех же трёх областей из `firmware/own-4.3.9_0445/mtd-kernel.bin`/`mtd-rootfs.bin` (crc a5447ccc/c41c56d0) и env v4 — только через новый STOP и «да».

## Risks

- **Запрещено до трёх одинаковых собственных dump:** SD recovery, OTA, любая запись SPI, U‑Boot `sf erase/write`, `saveenv`, reset, блокировка cloud.
- Подключение VCC или TX адаптера к неизвестной площадке может сжечь плату или Pi. Сначала напряжение мультиметром, потом провод.
- Щупом под питанием можно замкнуть соседние площадки: шаг ~1.5 мм, щуп держать вертикально.
- При загрузке моторы делают калибровочный проход pan/tilt. Разобранную плату закрепить, чтобы её не дёрнуло за провода.
- Пока камера в Wi‑Fi, активен `miio_ota` — облако может прислать обновление, которое перепишет и U‑Boot (`uboot_ota.sh`). Держать включённой только на время работы с UART.
- Pi без ИБП: 27.09 ~12:52 мигнул свет, Pi перезагрузился и оборвал проход 3. `dtoverlay uart0-pi5` живёт до перезагрузки Pi, после неё его снова делает владелец (sudo).
- `uart/boot-*.log` и `uart/dump-*-raw.log` содержат пароль Wi‑Fi в открытом виде — наружу не выкладывать.
- In‑circuit чтение SPI клипсой запитает от 3.3 В программатора весь SoC. Этот путь ещё не выбран, см. [DECISIONS.md](DECISIONS.md).

## Current blocker

Нет. Три собственных dump совпали (см. Recovery). Камера ещё стоит в U‑Boot (`SigmaStar #`), в Linux и сеть не уходила с 07:38.

Проход 3 был оборван 12:52 (мигнул свет, Pi перезагрузился), перезапущен 13:52 и прошёл без повторов.

## Next action

**28.09 20:35: этот раздел устарел (этапы 0–2 пройдены, карта sd-stage8, автозапуск, go2rtc). Актуальное — в «Кратко» вверху и в [DECISIONS.md](DECISIONS.md) (последняя запись 20:35); дальше: mma_heap-эксперимент (RAM-only) → SUB → U-Boot env в NOR (STOP-этап, с владельцем).**

1. Владелец: microSD + картовод есть (28.09), вставляет в Pi; записать `sd-stage2.img` командой `sudo dd` (строку печатает `make-sd.sh`), старое содержимое карты можно стереть. UART TX через 1 кΩ — одобрен, ещё не подключён.
2. Я: дожидаюсь разбора grablya95 → `research/ptz-audio-notes.md`; после записи карты — проверить `cmp` карты с образом.
3. Этап 1 по готовности UART; этап 2 по готовности SD. Интернет камере держать закрытым (MAC `xx:xx:xx:xx:xx:xx`): `miio_ota`.
4. Первая запись во flash — только этап 3, после отчёта (что/offset/размер/sha256 старого и нового/откат) и «да» владельца.

- 29.09 15:52: **env v4 ЗАПИСАН В NOR** (offset 0x4F000, 4 КиБ, crc32 25f375ed, sha256 76f91973…; sdboot с `dcache off`). Автозагрузка с карты БЕЗ UART/Enter подтверждена: reset → `1977576 bytes read` → OpenIPC → SSH (лог `uart/stage-nor-env-write-20260929-155119.log`). Причина падений v1–v3 (D-cache ON перед bootcmd → fatload зависает, контроль `uart/stage-2a-p4-sdtest-20260929-025652.log` стр. 11878) закрыта. Откат: `env-old.bin` на p1 (сток, crc 6c1674b6) или карта вынута → сток. Остались приёмки: холодный старт, карта-вынута→сток, карта-назад→OpenIPC.
- 29.09 16:42: **ПРИЁМКА env v4 ПРОЙДЕНА (3/3)**: холодный старт → OpenIPC ✔; карта вынута → сток ✔; карта назад → OpenIPC ✔ (SSH, majestic 637, mma fail 0). Камера автономна: Pi/UART для загрузки больше не нужен. Лог `uart/stage-nor-env-write-20260929-155119.log`.
- 29.09 16:59: **p4 (данные) на карте ГОТОВ**: MBR с p4 записан с камеры (владелец «да» 16:5x), ребут — U-Boot читает карту с новой таблицей ✔, `mkfs.vfat -n DATA`, cam-up.sh на p1 монтирует /tmp/p4 и включает records majestic (split 20, maxUsage 90). Запись идёт (`/tmp/p4/2026-09-29/13-57.mp4`, время камеры UTC). majestic 640, mma fail 0. Заметка: `reboot` через camssh в фоне не срабатывает — только `reboot -f`.
- 29.09 19:38: HA-видео починено на стороне Frigate (bigpc): go2rtc тянул RTSP камеры без логина (с 28.09 RTSP требует admin/ONVIF-пароль → 404). Плейсхолдер `{FRIGATE_MJSXJ05CM_PASSWORD}` в config.yml + .env. Frigate 5.5 fps, рестрим 8554 OK. HA — ждём подтверждения владельца.
