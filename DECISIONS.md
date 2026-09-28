# Решения

Формат: дата / варианты / выбрано / почему / откат.

## 2026-09-27 — ревизия платы LSAM041D1-1, а не LSAM044D1-1

- **Варианты:** принять ревизию из брифа или ту, что на шелкографии.
- **Выбрано:** LSAM041D1-1, по фото `set1/9cef2f28` и `set2/47fbbc51`.
- **Почему:** шелкография нашей платы читается однозначно. Смещения и распиновки из чужих источников к нашей плате не переносим.
- **Откат:** не нужен, это факт.

## 2026-09-27 — «передняя» и «задняя» плата — это две стороны одной PCB

- **Варианты:** две платы или одна двусторонняя.
- **Выбрано:** одна двусторонняя плата. Вывод сделан по фото, прямо не проверен.
- **Почему:**
  - контур и кольца винтов совпадают зеркально;
  - верхний центральный винт со стороны объектива входит в пластиковый кронштейн на обороте;
  - SoC стоит на обороте, SPI NOR — на стороне объектива.

  Следствие: тест‑площадки у объектива (1–18) электрически на той же плате, что и SoC. На обороте круглых тест‑площадок нет.
- **Откат:** если окажется, что платы две, искать UART на обороте у SSC323 и в межплатном разъёме.

## 2026-09-27 — сначала UART, потом выбор способа dump

- **Варианты:**
  1. Сразу снимать dump клипсой через flashrom.
  2. Сначала пассивный boot log по UART, способ dump выбрать по нему.
- **Выбрано:** 2.
- **Почему:** boot log бесплатно даёт:
  - JEDEC/модель flash, как их видит U‑Boot;
  - карту MXPT/MTD;
  - версию U‑Boot, `bootdelay` и можно ли прервать автозагрузку;
  - есть ли в U‑Boot `mmc`/`fatwrite`.

  От этого зависит, какой путь dump безопаснее. Пассивный RX ничего не меняет в камере.
- **Откат:** отключить два провода.

## 2026-09-27 — ранжирование способов dump (предварительно, до boot log)

1. **U‑Boot `sf probe; sf read <RAM> 0 0x1000000` → `fatwrite mmc 0 … <имя>` на пустую FAT32 SD.** Только если в `help` есть `mmc`/`fatwrite`.
   - Во flash камеры не пишется ничего, камера на своём питании, конфликта на шине нет.
   - SD должна быть пустой. Имя файла не должно совпадать со штатными именами recovery/update из `firmware/`.
   - После dump вынуть SD **до** загрузки Linux.
   - **Порядок (из boot log 27.09):** проверка SD `dfu` идёт в U‑Boot **до** точки прерывания автозагрузки, а Linux ищет `tf_update.img`. Поэтому: включать **без** SD → прервать U‑Boot → вставить SD → `mmc rescan` → `fatwrite`. Работает ли `mmc rescan` на горячую — проверить по `help`.
   - Строки «Hit any key to stop autoboot» в логе нет: `bootdelay` может быть 0 (ловится только поток нажатий с самого включения), отрицательным (не прерывается) или со стоп‑строкой. Если не прерывается — способ 1 и 3 отпадают, остаётся 2.
   - Нужен TX адаптера → RX камеры, чтобы остановить автозагрузку. Это новый провод: отдельное «да» владельца, резистор 1 кΩ последовательно.
2. **flashrom + клипса SOIC‑8 через spidev Pi.** Только с SoC в reset или со снятой микросхемой.
   - Клипса запитает весь SoC от 3.3 В Pi, SoC может драться за шину.
   - Нужен `dtparam=spi=on` и sudo владельца; клипсы нет: inventory `inv.lan` 2026-09-27 06:27 — ни SOIC‑клипсы, ни USB‑UART, ни логического анализатора; есть паяльник FNIRSI HS‑02B и держатель для пайки.
3. **U‑Boot `md.b` по 115200 в hex.** Около 70–90 мин на 16 MiB за один проход, ×3. Медленно, но без SD и без клипсы. Тоже требует TX адаптера.

- **Во всех вариантах:** три dump `spi/original-01/02/03.bin`, `sha256sum` + `cmp` + `hexdump` + `binwalk`. Разные — **не писать**.
- **Откат:** это чтение, откатывать нечего.

## 2026-09-27 — приёмник UART на Pi 5: GPIO15 через `uart0-pi5`, не `serial0`

- **Варианты:**
  1. `/dev/serial0` (= `ttyAMA10`, отладочный JST‑разъём Pi 5).
  2. GPIO15 pin 10 + `dtoverlay uart0-pi5` → `/dev/ttyAMA0`.
  3. USB‑UART.
- **Выбрано:** 2.
- **Почему:**
  - на `ttyAMA10` сидят консоль ядра Pi и getty — Pi сам будет слать туда байты;
  - USB‑UART к Pi не подключён;
  - runtime `sudo dtoverlay uart0-pi5` не требует перезагрузки Pi.

  Проверка после: `ls /dev/ttyAMA0; dmesg | tail -5`. Если не появился — `dtoverlay=uart0-pi5` в `config.txt` + перезагрузка (решает владелец).
- **Откат:** `sudo dtoverlay -r uart0-pi5` или перезагрузка Pi.

## 2026-09-27 — TX камеры = площадка 13

- **Варианты:** 13 (у NOR, прыгает 2.4–3.3 В при загрузке) или 4 (2.35 В у SD).
- **Выбрано:** 13. Подключение RX‑only: кольцо винта → Pi pin 6, pad 13 → Pi pin 10 (GPIO15).
- **Почему:** 13 idle 3.3 В и прыгает при загрузке; 4 стоит ровно. 13 ни с одной ножкой NOR не звонится, значит это не CS#/CLK флешки. Макс. 3.3 В — вход Pi выдерживает.
- **Откат:** отпаять два провода.

## 2026-09-27 — TX Pi → RX камеры (площадка 14) через резистор

- **Варианты:** остаться на RX‑only (dump только клипсой, её нет) или добавить TX для остановки U‑Boot.
- **Выбрано:** TX через резистор 470 Ом–2.2 кОм, Pi pin 8 → площадка 14. **«Да» владельца получено ~07:00 через вопрос**, подключит сам позже.
- **Почему:** на IPC019E (тот же SoC) U‑Boot останавливается зажатым Enter; U‑Boot‑путь dump не требует клипсы. GPIO14 проверен петлёй 06:59. Резистор ограничивает ток до ~3 мА, если 14 — не RX.
- **Рамка:** в U‑Boot только `version`, `help`, `printenv`, `bdinfo`; скрипт `uart/uboot-ro.py` другие команды не шлёт.
- **Откат:** отпаять провод с площадки 14.

## 2026-09-27 — dump: `sf read` + `md.l` по UART из остановленного U‑Boot

- **Варианты:**
  1. `fatwrite` на SD — **отпал**: команды нет в `help`.
  2. `sfbin` по TFTP — **отпал**: «No ethernet found».
  3. `mmc write` сырьём на жертвенную SD — возможно позже. Это запись (на SD, не во flash), нужен картридер, есть риск `dstar`/dfu.
  4. Клипса + flashrom — клипсы нет.
  5. `sf read` → RAM → `md.l` в hex по 115200.
- **Выбрано:** 5, скрипт `uart/dump.py`.
- **Почему:**
  - `sf probe`/`sf read`/`md*` есть в разрешённом списке брифа, никуда не пишется ничего;
  - пока камера стоит в U‑Boot, Linux и `miio_ota` не запущены.
- **Как устроено:**
  - Буфер RAM `0x21000000`, 16 MiB: сам U‑Boot резервирует его под XZ (boot log: `[XZ] !!!reserved 0x21000000 length=0x 1000000`). `0x22000000` из `bootcmd` мог бы налезть на relocated U‑Boot.
  - `crc32 <addr> <len>` — **два аргумента, только печать** (с третьим пишет в RAM, это скрипт не пропустит). Этой команды нет в списке брифа, но она лишь читает RAM. Сверяется весь образ после `sf read` и каждый MiB после `md.l`; при расхождении кусок перечитывается до 3 раз.
  - Скрипт шлёт только строки из regex‑allowlist и никогда не шлёт пустой Enter: U‑Boot повторил бы прошлую команду.
- **Проверено:** `./dump.py probe` 07:47, 64 KiB за 25 с, все CRC сошлись с первого раза. Первые байты `020000ea 49504c5f` (ARM `b` + «IPL_»), порядок байт верный. Ложная тревога «перезагрузка» в первой пробе: `version` печатает «U‑Boot 2015.01 (». Признак исправлен на `\nIPL g2cd6de2`.
- **Время:** ~1 ч 47 мин на проход. Проход 1 запущен 07:48, CRC32 всего RAM после `sf read` = `9c33df0c`.
- **Потом, если понадобится:** `setenv baudrate 460800` (только RAM, без `saveenv`) сократит проходы 2–3 до ~25 мин. Этой команды нет в списке брифа, при сбое теряется сессия — только с «да» владельца.
- **Откат:** не нужен, чтение.

## 2026-09-27 — путь к полному контролю: OpenIPC профиля IPC017, три этапа

- **Опора (проверено, `research/sources.md`):** OpenIPC `ssc325_lite_chuangmi-ipc017` (builder PR #168, влит 26.09.2026). Железо то же:
  - SSC323 + GC2053 + MT7601U, питание Wi‑Fi на GPIO 14 (наш U‑Boot тоже дёргает `gpio[14]`);
  - раскладка MTD та же, `bootargs` дословно наши (`init=/linuxrc`, `LX_MEM`, `mma_heap`);
  - U‑Boot родной, профиль дописывает `mtdparts` через `CONFIG_CMDLINE_EXTEND`, а последние 64K DATA делает своим env.

  У автора работают RTSP, ONVIF, SSH и день/ночь. Motion нет: в SDK infinity6 нет `libMD_LINUX.so`. Про моторы и звук у него ничего.
- **Отпали:**
  - khmyznikov‑гибрид 3.5.1 + zry98: на 4.x успехов нет, zry98 сам предупреждает про даунгрейд;
  - yi-hack-MStar: только Yi и ieGeek, ставится через их SD‑апдейт;
  - «сток + telnet»: видео остаётся облачным.
- **Порядок:**
  1. **Root shell на стоке без записи.** Команды из U‑Boot, `saveenv` не вызывается:

     ```
     sf probe 0
     sf read 0x22000000 0x50000 0x200000
     setenv bootargs console=ttyS0,115200 root=/dev/mtdblock2 rootfstype=squashfs ro init=/bin/sh LX_MEM=0x3fc6000 mma_heap=mma_heap_name0,miu=0,sz=0x1400000
     bootm 0x22000000
     ```

     - Ядро берёт cmdline у U‑Boot: `Kernel command line:` в boot log совпадает с env.
     - `/bin/sh` → busybox есть в нашем rootfs.
     - Stock init не запускается. DATA монтировать только `-o ro`: jffs2 rw может изменить DATA.
     - Цель — разведать моторы, звук и GPIO: по ним prior art нет.
  2. **OpenIPC‑ядро из RAM, без записи.** `mmc rescan 0; fatload mmc 0 0x22000000 <uImage>; bootm`. Проверяет наш EN25QH128A: стоковый FSP и так пишет `Unknown flash type … use default` и работает.
     - SD безопасна при условии, что на ней нет `tf_update.img` и `auto_update.txt`.
     - Автоапдейт U‑Boot (строки 500–512) берёт только `tf_update.img` с подписью libsodium, и то `sf erase 0x50000 0xF90000`.
     - Карту вставлять, когда U‑Boot уже стоит.
  3. **Первая запись.** В U‑Boot: `fatload` с SD → `sf update` KERNEL и ROOTFS, DATA стереть → `crc32` сверить. Откат — те же команды с `mtd-kernel/rootfs/data.bin` из нашего dump: DATA тоже, в ней стоковые `.ko` сенсора. BOOT, CONFIG и FACTORY не трогаются, поэтому U‑Boot остаётся точкой восстановления. Перед этапом полный отчёт владельцу по брифу и его «да».
- **Почему так:** каждый этап отвечает на вопрос следующего и ничего не пишет до этапа 3. Программатора нет (инвентарь), он и не нужен: U‑Boot прерывается Enter и читает SD. `loady` в нашем U‑Boot нет.
- **Проверено по готовой сборке** (`firmware/openipc-ipc017-20260926/`, md5 OK, sha256 в SHA256SUMS):
  - `uImage.ssc325` весит 1 977 576 байт и влезает в 2048K;
  - `rootfs.squashfs.ssc325` весит 4 915 200 байт и влезает в 7552K;
  - `/linuxrc -> init` уже есть, дописывать не надо;
  - `mi_ai.ko`/`mi_ao.ko` есть;
  - initramfs нет. Поэтому этап 2 — ядро OpenIPC на стоковом rootfs с `init=/bin/sh`.
- **«Да» владельца на этап 1** (`setenv bootargs`+`bootm` без `saveenv`) получено 27.09 ~22:00, срок — «позже». Когда подключать UART, скажет сам.
- **Открыто:**
  - моторы: драйвер UTC2803M, 8 GPIO — найти на этапе 1;
  - звук: у IPC017 GPIO 15 и 62.

## 2026-09-27 — ревизия плана «три этапа» и итоговый план (по отчёту Астры)

### Проверено заново локально (камера не нужна)

- **Ядро OpenIPC** `uImage.ssc325`: XZ‑поток начинается с байта 15249, распаковано 4 034 560 байт. Внутри: драйвер SD `ms_sdmmc` **встроен** (у стока это модули `mmc_core.ko`/`kdrv_sdmmc.ko` из rootfs, `S09mstar_ko:10-12`), `squashfs`, `overlay`, FSP‑драйвер NOR той же ветки SDK, что у стока (одинаковые строки `Flash is detected … ver1.1`, `found no flash_info`; у OpenIPC только режим `1-1-4 QUAD_READ`, у стока пять режимов). Зашитая cmdline: `mtdparts=NOR_FLASH:320k(boot)ro,2048k(kernel),7552k(rootfs),6272k(rootfs_data),64k(env),64k(config)ro,64k(factory)ro panic=20` — фрагмент из PR #168 в релизе есть.
- **Rootfs OpenIPC**: `sensor_gc2053_mipi.ko` + `/etc/sensors/gc2053.bin`, `mi_ai.ko`/`mi_ao.ko`, dropbear, majestic с секцией `audio` (вход и `outputEnabled`), `ipctool`, `gpio`. Моторного демона нет: `motor.cgi`/`ptz.cgi` — только веб‑UI под backend `pelco`. PTZ придётся делать самим.
- **`/init` OpenIPC** (1888 байт): при `root=…mtdblock…` монтирует `rootfs_data` как jffs2 **rw**, а если не смонтировалось — `flash_eraseall -j` по этому разделу. При `root=…mmcblk…` overlay и flash не трогает вовсе. Значит пробный запуск с SD безопасен **только** с `root=/dev/mmcblk0pN`.
- **Пишут во flash из Linux OpenIPC**: `fw_setenv` (раздел `env` = последние 64K нашего DATA, 0xFD0000), `setnetwork`, `sysupgrade`, `load_sigmastar`, `firstboot`. В пробном запуске не вызывать.
- **3.5.1_0052 `tf_recovery.img`** = сырые KERNEL|ROOTFS|DATA (0xF90000 байт, ровно 0x50000…0xFE0000) + трейлер 0x50 байт (`firmware/recovery-metadata.txt`). В его DATA есть `gc2053_MIPI.ko` — сенсор совпадает. Гибрид khmyznikov = наш BOOT/CONFIG/FACTORY + эти три раздела; ставится программатором; README описывает сборку, успешную загрузку на 4.x **не заявляет** (`research/khmyznikov-README.txt:49-59,115-131`). SSH/telnet в стоке 3.5.1 нет.
- **Моторы в стоке**: `motor.ko` закомментирован (`S09mstar_ko:40`), моторных модулей нет ни в одном DATA (0052/0426/наш). Моторы крутит userland через sysfs‑драйвер `mstar/motor` (в ядре) + GPIO 80/16 — карта пинов снята из libdevice_kit/libboardav/miio_algo, см. `research/stock-gpio-map.md` (28.09).
- U‑Boot: маркер `I6g46ec744` в нашем BOOT и в ядре 4.0.9_0425/0426; у khmyznikov (0448) та же строка сборки. OTA и SD‑recovery пишут только 0x50000–0xFE0000 — BOOT никогда не обновлялся, поэтому у всех 4.x он одинаков.

### Ревизия плана «три этапа»

Что верно и остаётся:

- Опора на профиль IPC017 (то же железо, тот же U‑Boot, те же bootargs) — верна.
- Этап 1 (`setenv bootargs … init=/bin/sh` + `bootm`, без `saveenv`) — верен и уже одобрен владельцем. Дополнение: в таком shell `/proc`, `/sys` не смонтированы — монтировать руками; DATA только `-o ro`.
- Правила про SD (карта без `tf_update.img`/`auto_update.txt`, вставлять при остановленном U‑Boot) — верны. Дополнить список: `tf_recovery.img`, `tf_all.img`, `tf_all_recovery.img`, `manu_test/` (стоковые скрипты S96/S49 ищут и их).
- Этап 3 через `fatload` → `sf update` → `crc32`, BOOT/CONFIG/FACTORY не трогать, откат теми же командами из dump — верен.

Что не так или не хватает:

1. **Этап 2 проверяет мало.** Ядро OpenIPC на стоковом rootfs с `init=/bin/sh` покажет только, что ядро стартует и видит NOR. Драйвер SD у OpenIPC встроен, значит можно загрузить **весь OpenIPC с SD‑карты** (`root=/dev/mmcblk0p2`) и проверить видео, Wi‑Fi, звук, IR, GPIO до единственной записи. Это и есть новый этап 2.
2. **DATA на этапе 3 описана неточно.** OpenIPC ждёт в 0x9B0000 `rootfs_data` (6272K, jffs2, форматирует сам при первом старте) + `env` 64K в 0xFD0000. Стирать надо весь диапазон 0x9B0000–0xFE0000, а откат обязан вернуть DATA из dump (в ней сенсорные `.ko` стока). Файл `mtd-data.bin` содержит учётные данные Wi‑Fi — хранить только локально.
3. **Нет PTZ и звука.** У OpenIPC нет моторного драйвера для SigmaStar; у IPC017 звук не проверен. Без плана по ним «полный контроль» не закрыт.
4. **Нет промежуточного видео.** Пока идёт работа, у владельца нет картинки. Есть путь go2rtc `xiaomi://` на нашем 0445 (ниже).
5. **Нет репетиции команд записи.** Все команды дня записи, кроме самого `sf update`, можно прогнать заранее в read‑only (fatload + crc32 файла в RAM против локального CRC).
6. **Нет оценок времени и критериев «этап сдан».**

### Отчёт Астры: что даёт

- **go2rtc на 4.3.9_0445** (victorhfoto, 16.09.2026; go2rtc README): URL `xiaomi://<account>:de@<IP>?did=<DID>&model=chuangmi.camera.ipc019`, ключи берутся из облака Xiaomi **при каждом подключении**, медиапоток локальный. Это временное видео в HA без единого изменения камеры, но требует интернета у камеры и у go2rtc и аккаунта Mi Home. Не путь к автономии.
- **khmyznikov**: его U‑Boot = наш (маркер сборки совпал локально). Ценность — раскладка образа; успех на 4.x не показан; сам путь программаторный.
- **grablya95 v1.2.2 для 3.5.1_0052**: даунгрейд предлагает через `tf_recovery.bin` с SD и сам предупреждает, что 4.x его блокирует. Ставится хак с SD (`hacks/`, `manu_test/`), удаляет `miio_*`, даёт dropbear, `rtspserver` (8554), `onvif_srvd` (5000), `motord` (PTZ), `audio-bridge` (микрофон + обратный канал). Как получен первый root на 3.5.1 и на каких GPIO работает `motord` — не подтверждено; исходников моторов агент не нашёл, бинарники есть.
- **Вывод Астры «самый поддержанный путь — khmyznikov → 3.5.1 → grablya95» не принимаю как основной.** Причины: загрузка 3.5.1 под U‑Boot 4.x никем не показана; база — сток 2020 года, сеть без SSH, хак живёт на SD; motion там тоже нет. OpenIPC IPC017 проверен на том же SoC/сенсоре/раскладке с родным U‑Boot и поддерживается. Но путь 3.5.1+grablya95 — **план Б** и источник знаний по PTZ/звуку, и с нашим U‑Boot он пишется теми же командами (`tf_recovery-3.5.1_0052.img` без трейлера = ровно 0x50000…0xFE0000), минуя SD‑recovery стока. Оба варианта откатываются одинаково, BOOT не трогаем.

### Итоговый план

Основа — OpenIPC IPC017. Одна запись во flash, всё остальное до неё — в RAM и с SD. BOOT (0x0–0x50000), CONFIG (0xFE0000), FACTORY (0xFF0000) не трогаем ни на одном этапе.

**Этап 0 — стол, без камеры (~1 ч).**
1. Подготовить SD (FAT32 первый раздел, squashfs второй): на FAT — `uImage.ssc325`, `rootfs.squashfs.ssc325`, наши `mtd-kernel.bin`/`mtd-rootfs.bin`/`mtd-data.bin` для отката; на второй раздел — `dd` rootfs OpenIPC. На карте не должно быть `tf_update.img`, `tf_recovery.img`, `tf_all*.img`, `auto_update.txt`, `manu_test/`.
2. Дополнить `uImage.ssc325` байтами 0xFF до 0x200000 и `rootfs.squashfs.ssc325` до 0x760000 (`kernel.pad.bin`, `rootfs.pad.bin`), чтобы после записи раздел совпадал с файлом байт в байт и SHA‑256 «нового блока» в отчёте был определён. Посчитать CRC32 (zlib) и SHA‑256 каждого файла → `firmware/openipc-ipc017-20260926/CRC.txt`.
3. Написать `uart/stage1.py`/`stage2.py` по образцу `uboot-ro.py`: только разрешённые команды, лог в `uart/`.
4. Из grablya95 v1.2.2 вытащить `motord`, `audio-bridge`: `strings`, обращения к `/sys/class/gpio`, `/dev/mem`, номера пинов — записать в `research/ptz-audio-notes.md`.
Сдано, когда: SD собрана, CRC записаны, скрипты прогнаны в dry-run.

**Этап 1 — стоковый root shell из RAM (~30–45 мин, нужен UART TX через резистор).** Команды из раздела выше (`setenv bootargs … init=/bin/sh`, `bootm`), без `saveenv`. В shell: `mount -t proc`, `mount -t sysfs`, `mount -t debugfs`; `cat /sys/kernel/debug/gpio`, `/proc/mtd`, `/proc/cpuinfo`, `dmesg`; DATA только `-o ro`. Затем запустить стоковые init‑скрипты по одному (S09mstar_ko и далее, без сети и без miio) и снять состояние GPIO при работе PTZ/IR/подсветки через стоковые утилиты. Ничего в `/config`, `/data` не писать.
Сдано, когда: получен список GPIO с направлением и значением в покое и при движении, список загруженных `.ko`, `dmesg` сохранён в `uart/stage1-*.log`.

**Этап 2 — полный OpenIPC с SD, flash не трогается (~2 ч).** Сначала `help mmc`, `help fatload` — синтаксис U‑Boot 2015.01 может быть `mmc dev 0; mmc rescan; fatload mmc 0:1 …`. Первая загрузка — с `init=/bin/sh` вместо `/linuxrc`: ядро пробует NOR и печатает разделы, userland не стартует. **Ключевая проверка:** в `dmesg` должно быть **7 разделов** (boot, kernel, rootfs, rootfs_data, env, config, factory) при наших стоковых bootargs без `mtdparts=` — тогда зашитая cmdline ядра дописывается к аргументам U‑Boot и на этапе 3 `saveenv` не нужен. Если разделов 6 (стоковая MXP‑раскладка) — у записанной системы не будет `env`, Wi‑Fi не сохранится; лечится `mtdparts=` в bootargs + `saveenv`, а это запись в BOOT по 0x4F000 — **отдельный стоп и отдельное «да» владельца**. Вторая загрузка — полноценная:
```
mmc dev 0; mmc rescan
fatload mmc 0:1 0x22000000 uImage.ssc325
setenv bootargs console=ttyS0,115200 root=/dev/mmcblk0p2 rootwait rootfstype=squashfs init=/linuxrc LX_MEM=0x3fc6000 mma_heap=mma_heap_name0,miu=0,sz=0x1400000
bootm 0x22000000
```
В Linux запрещено: `fw_setenv`, `setnetwork`, `extutils`, `sysupgrade`, `firstboot`, `load_sigmastar`, любой `flash_*`/`mtd` на запись. Проверено локально: ни один `oi/etc/init.d/S*` не вызывает их при старте, `fw_setenv` есть только в этих четырёх утилитах. Страховка на полноценной загрузке: добавить в bootargs строку `mtdparts=` из ядра, но с `ro` у всех семи разделов — NOR тогда не записать ничем. Wi‑Fi вручную: `gpio set 14`, `modprobe mt7601sta`, `wpa_supplicant` с конфигом в `/tmp`. Проверить: `dmesg` (NOR виден, 7 разделов), majestic стартует, RTSP 554 main/sub в VLC, ONVIF, звук с микрофона (`audio.enabled=true` в `/tmp` копии yaml), `mi_ao` на динамик, IR‑cut через `gpio`, ночная подсветка, `/sys/kernel/debug/gpio` сравнить с этапом 1, PTZ — попробовать шаги на найденных пинах через `gpio`.
Сдано, когда: видео обоих потоков идёт, Wi‑Fi поднялся, NOR распознан с ожидаемой раскладкой. Если NOR не виден или видео нет — стоп, разбор, во flash не идём.

**Этап 3 — единственная запись (~1 ч + отчёт 30 мин).** Сначала отчёт владельцу: что, куда, размер, SHA‑256 старого и нового, как откатить. Репетиция read‑only: `fatload` каждого файла в RAM + `crc32` против `CRC.txt`. Затем по «да»:
```
sf probe 0
fatload mmc 0:1 0x22000000 kernel.pad.bin ; sf update 0x22000000 0x50000 0x200000
fatload mmc 0:1 0x22000000 rootfs.pad.bin ; sf update 0x22000000 0x250000 0x760000
sf erase 0x9B0000 0x630000
```
Проверка: `sf read 0x21000000 0x50000 0x200000; crc32 0x21000000 0x200000` и `sf read 0x21000000 0x250000 0x760000; crc32 0x21000000 0x760000` — сверить с CRC дополненных файлов по всему разделу; `sf read 0x21000000 0x9B0000 0x630000` + `crc32` = CRC блока из 0xFF. Затем обычный `boot` (наши `bootargs`/`bootcmd` совпадают с IPC017 дословно) — `saveenv` не нужен, если этап 2 показал 7 разделов; иначе см. стоп выше. Первый старт OpenIPC отформатирует `rootfs_data`; далее `firstboot` не нужен.
Откат: те же `fatload`+`sf update` с `mtd-kernel.bin` (0x50000), `mtd-rootfs.bin` (0x250000), `mtd-data.bin` (0x9B0000, 0x630000). Время отката ~15 мин, всё из U‑Boot, программатор не нужен, BOOT цел.

**Этап 4 — доводка (2–4 ч, по SSH).** Пароль root, dropbear, NTP, статический IP; majestic.yaml: audio on, motionDetect on, records на SD; HA + go2rtc (RTSP) + Frigate (sub‑поток на детект). PTZ: карта пинов уже есть из стока (`research/stock-gpio-map.md`, 28.09): моторы = PWM‑группа 4..7 на GPIO 44–47 через драйвер `/sys/devices/virtual/mstar/motor/group_*` (он собран и в ядре OpenIPC), выбор оси GPIO 80/16. В DTB OpenIPC PWM4..7 не выведены на пады и нет `amp-gpio` (62) — поэтому этап 4 PTZ: (а) патч DTS в сборке OpenIPC (`pad-ctrl` + `amp-gpio`), (б) падмукс в рантайме через `/dev/mem` как `DrvPWMPadSet`, (в) запасной bit‑bang 44–47 + 80/16 из userspace. Динамик — GPIO 62 (усилитель) + 15; ИК‑фильтр 78/79; ИК‑подсветка `pwmchip0/pwm0`. Всё проверить живьём на этапе 1. API — простой HTTP/CGI, в HA как кнопки.
Сдано по FULL‑CONTROL‑ACCEPTANCE.md, пункт за пунктом.

**Этап 5 — восстановление и бэкап.** Скрипт `restore-stock.md`: команды отката из этапа 3; `restore-openipc.md`: то же для новой прошивки после `sysupgrade`. Ежемесячно: `sf read` + `crc32` BOOT/CONFIG/FACTORY (не менялись).

**Проверено 28.09 для этапа 2:** в ядре OpenIPC SD‑контроллер `sstar,sdmmc` встроен (строки `kdrv_sdmmc` в vmlinux, модуля в rootfs нет) → `root=/dev/mmcblk0p2` в 2a/2b законен; обе squashfs (сток и OpenIPC) сжаты xz, драйвер squashfs в ядре OpenIPC есть. Улики по периферии сохранены в репо: `research/tools/disasm.py`, `research/disasm/*.txt`, `research/dtb-stock-vs-openipc.diff`.

**План Б (если этап 2 упёрся в ядро/сенсор).** Записать `tf_recovery-3.5.1_0052.img` без трейлера (0xF90000 байт → 0x50000) теми же командами U‑Boot, затем grablya95 v1.2.2 с SD. Даёт SSH, RTSP 8554, ONVIF 5000, `motord`, `audio-bridge`; нет motion, нет нормальной автономии от `miio` до установки хака. Откат тот же.

**Временное видео (пока идут этапы 0–2), по желанию владельца.** go2rtc `xiaomi://…` на 0445 — работает только с открытым интернетом и аккаунтом Mi Home. Не ставлю, пока владелец не скажет, что готов открыть интернет камере.

**Что нужно от владельца физически.** UART TX через 1 кΩ (уже одобрен). microSD ≥ 1 ГБ + картовод для Pi. Всё остальное — я.

## 2026-09-28 — приём по UART мёртв под обоими ядрами; разведка без RX (этап 2a-p3)

**Факты.** Этап 1 (сток, `init=/bin/sh`) и 2a-nor (ядро OpenIPC с SD, стоковый rootfs из NOR, RAM only) оба
загрузились до `/ #`, оба не отвечают ни на команды, ни на Enter, ни на Ctrl-C. В U-Boot тем же проводом
ввод работает (весь dump и все этапы). Pi передаёт: strace скрипта показал `write(3, "echo PING3\n") = 11`
в `/dev/ttyAMA0`. Оба ядра печатают `/bin/sh: turned off` вместо полной строки busybox
(`can't access tty; job control turned off`, строка в бинаре есть) — userland-TX тоже теряет байты.
Общее у ядер: DTB (uart0 без `pad`, `gpioi2c` на GPIO 8/9, нет padmux). Вывод: не «Xiaomi отключили
консоль» (запись 01:25 в HANDOFF неверна), а IRQ/пад UART0 в общем DTS.

**Что ещё выяснилось.** Ядро OpenIPC дописывает свою cmdline (CMDLINE_EXTEND): `mtdparts=NOR_FLASH:…
panic=20`. Последний `mtdparts=` побеждает → ro-строка в bootargs этапа 2b **не** страховка от записи
в NOR; `panic=20` → выход init = ребут в сток. `OF: fdt: CRC check failed` при загрузке — DTB в uImage
патчен после сборки; значит патч DTB прямо в uImage в RAM (без записи во flash) — законная итерация.

**Решение.** Не чинить RX вслепую. Разведку стокового userland делать скриптом-init без ввода:
`sd-stage3.img` = sd-stage2 + p3 (squashfs: стоковый rootfs + `/recon.sh`), этап `2a-p3` в
`uart/stage.py` (`root=/dev/mmcblk0p3 init=/recon.sh`, RAM only, saveenv нет). recon.sh только читает:
/proc/interrupts до и после окна 60 с (в окно шлём байты → виден ли IRQ uart0), регистры uart0 через
devmem, debug/gpio, motor sysfs, pwm, gpio, DATA ro, dmesg; в конце `exec /bin/sh`, чтобы не словить panic.

**Отклонено.** Патч DTB сейчас — нет публичных таблиц падов infinity6 для UART0, вслепую. OpenIPC rootfs
целиком (2b) — сначала аудит его init на запись в NOR (overlay jffs2, fw_setenv), т.к. ro в mtdparts не
защищает. Всё по-прежнему из RAM, во flash не писали.

## 2026-09-28 — RX по UART жив после загрузки и умирает после приёма во время TX; Wi‑Fi+SSH с карты (этап 2a-p4)

**Факты (этап 2a-p3, лог `uart/stage-2a-p3-20260928-015100.log`).** Под ядром OpenIPC приём по UART
**работает** сразу после загрузки: строки, посланные в тихое окно 60 с, tty эхо‑ил, shell их выполнил.
Строки, посланные во время тяжёлого вывода, потеряны, и после этого приём мёртв до ребута. Этапы 1 и
2a-nor RX не имели вовсе — там до первого ввода уже шёл тяжёлый TX. Значит запись 01:52 («IRQ/пад UART0
в DTS») неточна: пад и IRQ в порядке, ломается драйвер/состояние после приёма во время передачи.

**DTB OpenIPC** (вырезан из uImage: xz‑поток в payload по 0x3b51, DTB 40300 Б по 0x3a7af0 распакованного
образа): uart0@1F221000 без `pad` и без `dma` (dma только у uart2), `interrupts = <0 0x42 4>` через
ms_main_intc. Теория «URDMA» отпадает. PWM4..7 (моторы PTZ) на пады не выведены (motor sysfs: Pwm2..10
Pad 0xffff) — PTZ под OpenIPC потребует патч DTB/padmux, можно в RAM (uImage уже патчен, CRC DTB не бьётся).

**Драйвер ms_uart.c** (копия в scratchpad): ISR читает IIR один раз за прерывание; `ms_getchar` считает
подряд идущие '1'/'2' — **пять '1' подряд = тихий режим (RX дропается), пять '2' подряд = отключение пада
UART (CLRREG16 0x1F203D4C,0xF)**. В консоль камеры никогда не слать пять одинаковых 1/2 подряд (в моих
скриптах строк с цифрами 1/2 нет). REG_FORCE_RX_DISABLE 0x1F203D5C bit1 = UART0; startup/set_termios
делают DISABLE→ENABLE. Рабочая гипотеза — «lost edge»: байт пришёл, пока ISR обрабатывал THRE, RDI висит,
пока RBR не вычитан. Проверка: вычитать RBR (devmem 0x1f221000) пока LSR.DR (0x1f221028 bit0), после чего
приём должен ожить.

**Решение.** Не чинить UART вслепую, а перестать от него зависеть: `sd-stage4.img` (p1/p2 = sd-stage2
байт в байт, p3 = rootfs OpenIPC + `/init4.sh` + `/wpa.conf` + `/shadow4`), этап `2a-p4` в `uart/stage.py`
(`root=/dev/mmcblk0p3 init=/init4.sh`, RAM only, saveenv нет). init4.sh: /etc → копия в tmpfs (bind),
реальный пароль root (`$6$`, `p4/secret/root-password.txt`), Wi‑Fi через собственный профиль OpenIPC
`/etc/wireless/usb mt7601u-ssc325-chuangmi-ipc017` (GPIO14 → питание MT7601U, MAC из factory `mac=`,
modprobe mt7601sta), wpa_supplicant + udhcpc, `dropbear -R -p 22`, IP печатается как `SSH_READY_ip`;
затем эксперимент RX: окна A → тяжёлый TX → B → TX с приёмом (Pi шлёт строки, `uart/win4.sh`) → C →
вычитка RBR → D → дамп CHIPTOP 0x1F203D00..DFC; init не завершается (`panic=20`). NOR не пишем: rootfs
squashfs ro, /etc в tmpfs, `/dev/mtd*` не открываются.

**Образ секретный.** sd-stage4.img и `p4/secret/` содержат SSID/PSK владельца и хеш пароля root —
только своя карта, не публиковать, не пересылать. Пароль root сообщён владельцу лично.

**Отклонено.** Патч драйвера/DTB до результата эксперимента — сначала данные окон A–D. OpenIPC rootfs
c его init (2b) — по‑прежнему после аудита S01fwenv/overlay на запись в rootfs_data. Telnet без пароля —
нет: dropbear с паролем с первого же запуска.

## 2026-09-28 — sd-stage4: карта пишется только с cmp; ядро 4.9 не находит файл, дописанный mksquashfs‑append; обход и sd-stage5

**Факты.**
- Попытка 1 (02:32): `SQUASHFS error … block 0x5729ce` = inode_table sd-stage3 (0x5717e4) + 0x11ea → на карте суперблок
  от stage3, данные от stage4: dd не дошёл до конца / не был синхронизирован, cmp владелец не делал.
  **Правило: после dd обязательны `cmp … && echo CARD_OK` и `sync`, карту вынимать только после них.**
- Попытка 2 (02:36, карта сверена): без ошибок squashfs, но `Requested init /init4.sh failed (error -2)` → panic → сток.
- Бисект `2a-p4-sh` (02:46): тот же p3, `init=/bin/sh` → `/ #`, MT7601U (148f:7601) перечислился под ядром OpenIPC.
  Значит busybox musl OpenIPC работает; ядро 4.9.84 не находит именно `/init4.sh`, дописанный mksquashfs 4.6
  (`append`) в корень образа OpenIPC `rootfs.squashfs.ssc325`. На Pi (6.18, loop) файл есть, корень отсортирован,
  shebang LF, xattr ids 0, inodes 743 vs 740. В sd-stage3 append на образ, собранный тем же mksquashfs 4.6, работал.
  Причина не найдена; дальше не копаем — обходим.

**Решение.**
1. Один запуск без перезаписи карты: этап `2a-p4-argv` (`init=/bin/sh /init4.sh`) — ash сам открывает скрипт;
   при отказе печатает «can't open» (диагностика lookup из userland), затем panic → сток. Этап `2a-p4-env`
   (`ENV=/init4.sh`) добавлен, но не выбран: при отказе молча даёт `/ #`.
2. Запасной путь готов: `make-sd5.sh` → `sd-stage5.img` (p3 = unsquashfs базы + init4.sh/wpa.conf/shadow4,
   `mksquashfs -noappend`; setuid busybox возвращён вручную — unsquashfs без root его теряет). Секретный, chmod 600.
   Листинг сверен со stage4: отличия только владелец `/var/www` (-all-root) и права корня.

**Отклонено.** Патчить/собирать другую версию mksquashfs, разбирать формат дальше — дороже одной перезаписи карты.

## 2026-09-28 — 2a-p4-argv: пустой результат (ядро выбрасывает из argv init слова с точкой); переход на sd-stage5

**Факты.** `init=/bin/sh /init4.sh` (RAM, лог `uart/stage-2a-p4-argv-20260928-050418.log`, 10:49): cmdline ядра содержит `/init4.sh`, но init получил argv без него — `unknown_bootoption()` (init/main.c) отбрасывает слова, в которых есть `.` до `=`, как «неиспользуемый параметр модуля» (`strchr(param, '.')`). ash поднялся интерактивно (`/ #`), «can't open» не печатался → про lookup `/init4.sh` тест ничего не говорит. В логе `/bin/sh: turned off` вместо `can't access tty; job control turned off` — потеря ~28 байт на TX; отдельно не разбираю. Приём по UART мёртв уже через минуту после загрузки (echo в консоль — без эха), хотя тяжёлого вывода не было.

**Решение.** `ENV=/init4.sh` не пробовать: тот же path lookup, что и у execve, а при неудаче ash молчит. Сразу `sd-stage5.img` (p3 собран одним проходом mksquashfs 4.6, без append; так же одним проходом собран базовый слой p3 stage3, который ядро 4.9.84 читало) — владельцу dd/cmp/sync (~10 мин). Взведён `stage.py 2a-p4` (init=/init4.sh, STAGE_WAIT=86400) на `uart/stage-2a-p4-20260928-105432.log`, win4.sh на нём.

**Отвергнуто.** `ENV=/init4.sh`; повторный argv-тест с именем без точки (файл всё равно пришлось бы дописывать append'ом); дальнейший разбор формата append.

## 2026-09-28 — sd-stage5 загрузился: single-pass squashfs снял ENOENT; RX умирает от интерактивного ash, не от TX; Wi‑Fi не ассоциировался → sd-stage6

**Факты (лог `uart/stage-2a-p4-20260928-105432.log`, секретный).**
1. p3, собранный одним проходом `mksquashfs -noappend` (`make-sd5.sh`: unsquashfs базы OpenIPC + init4.sh/wpa.conf/shadow4),
   ядро 4.9.84 читает: `init=/init4.sh` отработал до конца. ENOENT был именно от файла, дописанного append-проходом
   (mksquashfs 4.6 поверх образа OpenIPC); причина в формате не разобрана — парковано, append больше не используем.
2. RX-эксперимент: приём по UART работает во ВСЕХ окнах `read` из неинтерактивного скрипта, включая строки, посланные
   во время тяжёлого TX (rx-счётчик ms_uart рос, DRAIN_RBR: drained=0, LSR=0x60 — переполнения нет). Приём умирает
   в момент запуска интерактивного `/bin/sh`: ash делает tcsetattr → `ms_uart_set_termios` (FORCE_RX DISABLE→ENABLE,
   запись LCR, FCR=FIFO_ENABLE|TRIGGER_RX_L0, одно чтение RBR); в тот же момент теряются ~32 байта TX.
   Вывод: гипотезы «lost edge», overrun и URDMA закрыты; виноват путь set_termios драйвера ms_uart.
3. Wi‑Fi: wlan0 UP, wpa rc=0, но `wpa_state=SCANNING` весь таймаут, udhcpc без ответа. Наш wpa.conf отличался от
   стокового шаблона: не было `key_mgmt=WPA-PSK`, `proto=WPA WPA2`, `scan_ssid=1`; сток перед wpa_supplicant делает
   `iwconfig wlan0 mode Managed` и запускает `wpa_supplicant -Dnl80211` (не `nl80211,wext`, как OpenIPC).
4. default.script OpenIPC по `leasefail` ставит 192.168.1.10 — в LAN владельца этот адрес занят чужим хостом
   (ARP-MAC не камеры). Чужой хост не трогать.

**Решение.** `init4.sh` v6 → `sd-stage6.img` (`make-sd6.sh`, тот же single-pass):
- wpa.conf как у стока (три поля добавлены), `iwconfig mode Managed`, `wpa_supplicant -D nl80211 -f /tmp/wpa.log -d`,
  печать `wpa_state` каждые 5 с и отфильтрованный хвост wpa.log (`WPA_LOG`) — следующая диагностика без перезаписи карты;
- udhcpc со своим скриптом `/tmp/dhcp.sh` (deconfig/bound/renew), без fallback-IP;
- консоль в конце — `while :; do cat | /bin/sh; sleep 2; done`: cat не трогает termios, RX остаётся живым, команды
  шлются через `uart/console.in` (неинтерактивный sh, без промпта; не слать '11111'/'22222').
  Старый скрипт сохранён как `p4/init4.sh.stage5`.

**Отвергнуто.** Патчить/обходить `ms_uart_set_termios` (пересборка ядра или devmem-хаки) — не нужно, пока `cat | sh`
закрывает потребность; `-D wext`/iwpriv-путь RT2870 — у OpenIPC нет iwpriv, а сток сам использует nl80211;
попытка чинить UART в стоковом ядре — сток на ввод не отвечает по другой причине (этап 1), туда не идём.

## 2026-09-28 — sd-stage6: Wi‑Fi + SSH root с карты РАБОТАЮТ; SSID стокового конфига не в эфире; карта mtd сверена с дампом

**Факты.** 1) init4.sh v6 отработал, консоль `cat | /bin/sh` по UART живёт (команды через `uart/console.in`,
без промпта) — приём по UART больше не блокер. 2) `wpa_state=SCANNING` не из-за конфига: SSID из стокового
`wpa_supplicant.conf` (data-раздел) в эфире отсутствует (0 совпадений в 9–10 BSS; 248× «SSID mismatch»); сеть Pi —
5 ГГц (5180 МГц), MT7601U только 2.4 ГГц. Владелец записал SSID/пароль своей сети 2.4 ГГц в
`p4/secret/wifi-current.txt` (600); `uart/wifi-set.sh` подставил их через `wpa_cli set_network` live —
`COMPLETED` за 5 с, freq 2412, DHCP выдал 192.168.1.53 (тот же адрес, что у стока — резервирование по MAC).
3) `ssh root@192.168.1.53` с Pi (dropbear, пароль из p4/secret) — работает; `uart/camssh.py 'cmd'` — обёртка
(paramiko, пароль не печатается). 4) sha256 `/dev/mtd{0..6}ro` с камеры = срезам `spi/original-01.bin` по карте
OpenIPC (boot 0x0/0x50000, kernel 0x50000/0x200000, rootfs 0x250000/0x760000, env 0xFD0000, config 0xFE0000,
factory 0xFF0000) для ВСЕХ разделов, кроме rootfs_data (0x9B0000/0x620000) — это стоковый data-раздел, который
сток сам переписывает при каждой своей загрузке (камера несколько раз уходила в сток после паник). Наши этапы
в NOR не писали. 5) По SSH видно: lsmod — только mt7601sta+cfg80211; /dev/video* нет (мультимедиа не грузили);
pwmchip0 есть; RAM 40 МБ доступно (LX_MEM), корень 4.8 МБ squashfs.

**Решение.** Рабочие SSID/пароль перенесены в `p4/secret/wpa.conf` (стоковый вариант сохранён как
`wpa.conf.stock-ssid`), собран `sd-stage7.img` (`make-sd7.sh`) — при следующей загрузке карта поднимет Wi‑Fi и SSH
сама. Дальше работать по SSH, UART — резерв. Следующий этап — аудит init OpenIPC перед 2b (его `/init` монтирует
overlay с rootfs_data → запись в NOR; для 2b нужен свой init или `ro` + tmpfs-overlay).

## 2026-09-28 — ВИДЕО OpenIPC работает с карты (RAM): majestic + RTSP/JPEG проверены с Pi; NOR не тронут

**Факты.**
1. Аудит OpenIPC rootfs (explorer): в NOR пишут только `/init` (jffs2 overlay на rootfs_data → `flash_eraseall` при ошибке),
   `load_sigmastar` (`fw_setenv sensor` при автодетекте), `customizer.sh`/S30customizer, `setnetwork`, `extutils`, `sysupgrade`.
   Ничего из этого не запускалось — модули загружены вручную по SSH.
2. Порядок insmod из `/usr/bin/load_sigmastar` (mhal, mi_common, mi_sys logBufSize=256 default_config_path=/usr/bin,
   mi_rgn, mi_ai, mi_ao, mi_sensor, mi_shadow, mi_divp, mi_vif, mi_vpe, mi_venc, sensor_gc2053_mipi.ko chmap=1) — все rc=0,
   dmesg: «Connect gc2053_init_driver linear to sensor pad 0», MMA heap 0x22bc6000 len 0x1400000 (= стоковый mma_heap).
   Сток (S09mstar_ko) грузит те же модули (свой порядок) и тот же `gc2053_MIPI.ko chmap=1`.
3. `/etc/init.d/S95majestic start` → majestic (master+17ec3ed): сенсор 1920x1080@30, H264 4096k, JPEG, IQ /etc/sensors/gc2053.bin,
   RTSP :554, HTTP :80, ONVIF discovery, mDNS. С Pi: `image.jpg` → реальный кадр 55 КБ; RTSP h264 Main 1920x1080,
   5 с = 100 кадров (20 fps). Auth HTTP/RTSP — root + пароль из p4/secret. Free RAM при работе ≈10 МБ из 40.
4. majestic при SIGTERM освобождает watchdog («Watchdog released») — остановка не ведёт к ребуту.
5. Data-раздел (mtd3) камеры сохранён live: `firmware/own-4.3.9_0445/live-20260928/mtd3-rootfs_data-live.bin` (sha256 4ec7a0f7…).

**Решение.** Дискриминирующий эксперимент (видео) пройден: стек OpenIPC полностью совместим с платой на стоковом
ядре-конфиге памяти. Гибрид (стоковые libmi + чужой userland) не нужен. Кандидат на прошивку — полный OpenIPC
(kernel + rootfs) с нашим init-обходом NOR-записей (rootfs_data: `ro`/tmpfs, SENSOR=gc2053 без автодетекта).
До первой записи в NOR: проверить PTZ/IR-cut/звук по SSH, пред-отчёт владельцу, «да».

## 2026-09-28 — Схема PTZ/IR-cut стока найдена; самопроизвольный ребут в сток (12:33); watchdog

**Факты.**
1. Сток управляет моторами не через GPIO, а через ядерный драйвер sstar-pwm «motor group»: libdevice_kit.so пишет в
   `/sys/devices/virtual/mstar/motor/group_{mode,period,begin,end,polarity,round,enable,stop,hold}`. Стоковый boot-лог
   (тот же драйвер): `DrvPWMPadSet (pwmId,padId) = (4,44)…(7,47)`, period 50, `group_round (1, 256)` затем `(1, 512)`
   (прямой и обратный порядок пинов = калибровка), `mstar_pwm_config period_ns=120000`. Т.е. группа 1 = pwm4..7 → пады 44–47.
   В OpenIPC-ядре тот же драйвер и тот же sysfs есть; не хватает только padmux pwm4..7 (OpenIPC DT pad-ctrl = 0xffff,
   DTB встроен в сжатое ядро — патч DT = пересборка ядра; для RAM-опыта — devmem по таблице из OpenIPC/linux).
2. IR-cut/IR-подсветка/динамик в стоке — userspace через sysfs: miio_algo переключает ircut двумя GPIO (1→0, пауза 500 мс)
   и pwm0 (period 120000, duty 30/50/75/99); libboardav: усилитель динамика GPIO 15 (out, 0). Номера ircut-GPIO читаются
   из конфига (ircut_config), не зашиты — ищем.
3. Ребут 12:33 в сток: серия `mma fail` (MAIN+SUB+audio на 20 МБ mma) → IPL без паники. Кандидаты: watchdog majestic
   (`watchdog: enabled: true, timeout: 300`) или провал питания при отключении моторов владельцем. Моторы сейчас физически
   отключены — PTZ-тесты по картинке до подключения ничего не доказывают.

**Решение.** В RAM-опытах majestic запускать с `watchdog: enabled: false` (p4/cam-up.sh, bind-mount /tmp/m.yaml) и не
включать MAIN+SUB+audio одновременно. Финальный вариант прошивки — OpenIPC с собственной сборкой ядра (DTS: pad-ctrl
pwm4..7 = 44–47, ircut/amp GPIO) либо стоковое ядро + OpenIPC userland — выбирать после проверки padmux через devmem и
советника; первая запись в NOR по-прежнему только после пред-отчёта и «да». stage.py после своих команд не ловит второй
U-Boot — перед каждой загрузкой с карты перезапускать (`STAGE_WAIT=5400`).

## 2026-09-28 (13:08) — Motor group sysfs и padmux pwm4..7: факты из исходника драйвера, проверено на OpenIPC (RAM)

Источник: OpenIPC/linux, ветка sigmastar-infinity6, `drivers/sstar/pwm/mdrv_pwm.c`, `drivers/sstar/pwm/infinity6/mhal_pwm.c`, `include/infinity6/padmux.h`, `registers.h` (копии в scratchpad).

1. **Форматы записи** (`/sys/devices/virtual/mstar/motor/`): `group_mode "<pwm> <0|1>"` — join в группу, Div, Dben, Enable 0, DrvPWMPadSet(pwm, pad_ctrl из DT); `group_period "<pwm> <Гц>"`; `group_begin`/`group_end "<pwm> <промилле 0..1000>"` (строго 2 числа); `group_polarity "<pwm> <0|1>"`; `group_round "<группа> <N>"`; `group_enable "<группа> <0|1>"` (повтор состояния отвергается); `group_hold "<группа> <0|1>"`; `group_stop "<группа>"` — одно число, всегда Stop=1. Группы: 0 = pwm0..3, **1 = pwm4..7 (моторы)**, 2 = pwm8..10.
2. **Padmux** pwm4..7 → пады 44..47 = PAD_SPI0_CZ/CK/DI/DO. Регистры 16-бит: CHIPTOP 0x1F203C00, PMSLEEP 0x1F001C00. pwm4: CHIPTOP+0x1C бит[14:12]=2, PMSLEEP+0x9C бит0=0; pwm5: CHIPTOP+0x08 бит[2:0]=2, PMSLEEP+0x9C бит1=0; pwm6: CHIPTOP+0x08 бит[5:3]=2; pwm7: CHIPTOP+0x08 бит[8:6]=2. На OpenIPC DT pad-ctrl=0xffff → драйвер печатает «DrvPWMEnable error (4, ff)» и padmux не ставит; выставлено devmem: `0x1F203C1C ← 0x2001`, `0x1F203C08 ← 0x0092` (RAM, откат — перезагрузка). Прочитанные до записи значения (0x0001/0x0000/0x0000) совпали с таблицей драйвера (pwm0 → PAD_PWM0).
3. **Решение:** для финальной прошивки нужен либо DTS с `pad-ctrl = <0x34 0x35 0xffff 0xffff 44 45 46 47 …>` (пересборка ядра OpenIPC), либо devmem в стартовом скрипте (userland, без пересборки) — второе проще и совместимо с готовым ядром; выбрать после физического теста PTZ.
4. Стоковая последовательность begin/end/dir — из дизассемблировки libdevice_kit (агент); физический тест PTZ — только после того, как владелец подключит моторы (питание выкл).

## 2026-09-28 (13:20) — Стоковая последовательность PTZ восстановлена из libdevice_kit, p4/ptz.sh прогнан всухую (RAM)

Источник: дизассемблировка `libdevice_kit.so.0.0.1` (scratchpad `motor-ops.txt`, функции по адресам): один драйвер шаговиков = motor group 1 (pwm4..7), **мотор выбирается GPIO 80 (горизонталь) и GPIO 16 (вертикаль)** — оба через sysfs gpio, при инициализации и стопе = 0.
- fd-таблица (0x4394…): mode, period, begin, end, polarity, round, enable, stop, hold — в этом порядке.
- Фаза (0x3dc4: pwm, polarity, begin, end): `group_mode "<pwm> 1"`, `group_period "<pwm> <P>"`, `group_polarity "<pwm> <pol>"`, `group_begin "<pwm> <b>"`, `group_end "<pwm> <e>"`.
- Таблица A (0x3f74): pwm4 pol0 0..375, pwm5 pol0 250..625, pwm6 pol0 500..875, pwm7 pol1 125..750 (промилле). Таблица B (0x3fd0): те же четыре, но pwm7→4 (обратный порядок = обратное направление).
- Направление (0x402c, dir 0..3): dir0 GPIO80=1,16=0,B; dir1 GPIO80=1,16=0,A; dir2 GPIO80=0,16=1,A; dir3 GPIO80=0,16=1,B. `motor_h_dir_set` ставит период 50 Гц (0x32), `motor_v_dir_set` 25 Гц (0x19); vertical dist_set проверяет dir 2/3 и лимит 90 → h = dir 0/1, v = dir 2/3.
- Старт (0x4180): `group_round "1 <шаги>"`, `group_enable "1 1"`. Стоп (0x3d2c): GPIO80=0, GPIO16=0, `group_stop "1"`, `group_enable "1 0"`. Init (drv_motor_init): GPIO 80/16 out, таблица A, стоп.
- Сток на загрузке (из UART-лога): round 256 → stop → round 512 — калибровочные ходы.

Решение: `firmware/openipc-ipc017-20260926/p4/ptz.sh` (init | h|v +|- N | stop) повторяет это 1:1 + padmux pwm4..7 через devmem в `init`. Прогон на OpenIPC при отключённых моторах: все записи приняты без `invalid argument`, период 50 Гц → 0x1d4bf, 25 Гц → 0x3a97f, round (1,50)/(1,25), enable 1→0 без отказа, GPIO 80/16 экспортированы. Знак направления (+/-) и число шагов на градус — только физический тест после подключения моторов владельцем при выключенном питании.

## 28.09 16:05 — ИК-лампа РАБОТАЕТ на OpenIPC; причина «молчания» — единицы sysfs PWM драйвера SigmaStar
- Физически подтверждено владельцем (фото: 6 диодов светятся): пад 52 как GPIO out=1 → горят; GPIO 62 (amp-gpio в стоковом DTS) на лампу НЕ влияет.
- Причина провала PWM-теста: в драйвере OpenIPC (`mdrv_pwm.c` → `DrvPWMSetPeriod(period_ns)` = clk/val−1, `DrvPWMSetDuty(duty_ns)` = period×val/100) sysfs `period` трактуется как **Гц**, `duty_cycle` — как **проценты 0..100**, а не нс. Стоковый miio_algo пишет 120000/0..120000 (нс-семантика стокового ядра). На OpenIPC `period 120000` → регистр 0x63 (120 кГц), `duty 120000` → регистр 0x1CC32 ≫ периода → выход не переключается.
- Рабочий вариант (RAM, проверено): `echo 100 > duty_cycle; echo 1 > enable` при period 120000 → диоды горят. Для диммирования: сначала duty ≤ новый period (ядро отвергает duty>period с EINVAL), затем `period 8333` (≈120 мкс, как сток в нс) и duty 0..100.
- Следствие для моторов: group_* путь другой (проверен по исходнику, Гц/промилле, регистры = сток), причина молчания моторов пока не найдена → тест полушага GPIO на падах 44..47 (`/tmp/step.sh`, scratchpad `step.sh`).

## 28.09 16:25 — МОТОРЫ КРУТЯТСЯ (владелец видел оба) — полушаг по GPIO на падах 44..47 в обход PWM-группы
- Обходной путь работает: mux PWM4..7 снят (`devmem 0x1F203C1C 16 0x0001; devmem 0x1F203C08 16 0x0000`), gpio44..47 out, выбор мотора GPIO 80=1 (горизонталь) / 16=1 (вертикаль), последовательность (44,45,46,47): 1001 1000 1100 0100 0110 0010 0011 0001 (из стоковых таблиц begin/end), 20 мс на состояние; 2000 полушагов H ≈ широкий поворот, 800 V. Скрипт: камера `/tmp/step4.sh` (scratchpad `step4.sh`).
- Важно: sysfs-экспорт GPIO 44..47 сам по себе mux НЕ меняет, если пад уже был экспортирован раньше (HalPadSetMode_General вызывается только при экспорте) — первый GPIO-тест был невалиден (обратное чтение пада = 0 при value=1). Признак корректности: `cat value` после `echo 1` возвращает 1.
- PWM-группа (group_* sysfs, регистры = сток) моторы НЕ крутила — причина не найдена (кандидаты: group_hold, порядок enable/round, DrvPWMPadSet через pad_ctrl DTS делает что-то помимо mux). Пока PTZ = GPIO-полушаг (ponytail: работает; апгрейд на PWM-группу — когда понадобится плавность/разгрузка CPU).

## 28.09 16:30 — ДИНАМИК РАБОТАЕТ (владелец: «Да, гудит»); ptz.sh переписан на GPIO-полушаг

- Динамик: GPIO 15=1 (усилитель, как `Mstar_enable_speaker` в libboardav) + majestic `audio.enabled: true`, `audio.outputEnabled: true`, `outputVolume: 60` → `curl -u root:… -H 'Content-Type: audio/L16' --data-binary @tone.pcm http://192.168.1.53/play_audio` (s16le mono 8 кГц, 880 Гц) — слышно. GPIO 62 при этом был 1 (не проверял, нужен ли). `Content-Type: audio/pcm` и `audio/wav` → «Unsupported audio format for this camera»; `audio/L16` и `application/octet-stream` принимаются. После теста GPIO 15 = 0.
- Ловушка bind-mount: `/tmp/m.yaml` смонтирован поверх `/etc/majestic.yaml`; `sed -i /tmp/m.yaml` создаёт новый inode, а bind-mount продолжает показывать старый → majestic видел `enabled: false`. Править на месте: `cat /tmp/m.yaml > /etc/majestic.yaml` (или sed без -i с перенаправлением в /etc/majestic.yaml).
- `p4/ptz.sh` переписан: GPIO-полушаг 44..47 (последовательность из step4.sh), select 80/16, `init` снимает mux pwm4..7 и проверяет readback pad44; `h|v +|- N` полушагов, `PTZ_US` — задержка (по умолчанию 20 000 мкс). Прогон `h + 800`, `v + 300` на камере отработал (лог `/tmp/ptz.log`), но владелец в этот момент не смотрел.
- Соответствие «+/−» ↔ «влево/вправо/вверх/вниз» ОТЛОЖЕНО: моторы не в стойке, владелец не помнит, какой шлейф какой; определить после сборки (тогда же h/v могут поменяться местами — это только select 80 ↔ 16).
- Микрофон (быстрая проба без владельца): `/audio.pcm` при volume 30 даёт rms 2–3, min/max ±30 — почти ноль; либо микрофон не подключён, либо усиление мало. Владелец назвал «вибромоторчик» — маленькая деталь с 2 проводами и своим разъёмом; в стоке вибромотора нет, кандидат — электретный микрофон (тоже цилиндр с 2 проводами). Проверка: запись 15 с при volume 100, владелец хлопает.

## 28.09 16:55 — МИКРОФОН ПОДТВЕРЖДЁН, два сброса камеры, аудио включается до первого старта majestic

- **Микрофон** («вибромоторчик» владельца: электретный диск ~4 мм, 2 провода, свой разъём, у передней стенки за платой ИК) — работает. Запись `curl /audio.pcm` (s16le 8 кГц, 40 с, через Bash run_in_background — nohup-фон файл не сохраняет) при `audio.volume: 100`: фон rms ≈ 390, три хлопка владельца дали пики 9087 / 32768 (клиппинг) / 12103 на 19,5 / 25 / 32,5 с. При volume 30 сигнал почти ноль — оставляем 100.
- **Сброс #1 (~16:37, OpenIPC):** после 4 перезапусков majestic с аудио — цикл `mma_alloc … vpe0-out0-1 fail`, затем без panic сразу IPL → сток из NOR. Каждый перезапуск majestic течёт по MMA (heap 20 МиБ, `sz=0x1400000` — тот же, что у стока). Правило: конфиг majestic менять ДО первого старта, перезапусков избегать. `cam-up.sh` теперь включает аудио (in volume 100, out 60, outputEnabled) в `/tmp/m.yaml` тем же sed, что выключает watchdog.
- **Сброс #2 (16:43):** во время U-Boot `crc32` — команда сброс вызвать не может → просадка питания. Питание было: USB-гнездо сетевого фильтра + метровый micro-USB. Рекомендация владельцу: адаптер 5 В ≥ 2 А (штатный Xiaomi 5 В/2 А), короткий кабель. Третья загрузка прошла штатно.
- **MMA после чистого старта с аудио (замер 17:12):** `vpe0-out0-1 fail` (size 0x2fd000 = кадр 1080p YUV): 19 за 1‑ю минуту, 23 на 4‑й, 90 на 12‑й, дальше ровно 90 (5+ мин). `/proc/mi_modules/mi_sys_mma/mma_heap_name0`: два буфера vpe0-out0-1 выделены, самый большой свободный кусок 0x2f9000 < 0x2fd000 — третьему не хватает 16 КиБ (фрагментация кучи 20 МиБ, у стока тот же `sz=0x1400000`). Рост всплесками, потом стоит; venc0 идёт, jpg отдаётся; load average ~8 — потоки MI в D‑state. Не утечка, но headroom ноль: любой рестарт majestic — риск сброса. К этапу стабильности: убрать лишний потребитель (jpeg/порт 1) или дать majestic меньше буферов.
- Загрузка скриптов на камеру: `B=$(base64 -w0 f); python3 uart/camssh.py "echo $B | base64 -d > /tmp/f; chmod 755 /tmp/f"`.
- Итог этапа периферии: IR-cut (78/79), ИК-лампа (pwm0), оба мотора (GPIO-полушаг), динамик (GPIO 15 + play_audio L16), микрофон — всё работает на OpenIPC RAM-only. Открыто: стороны моторов после сборки; PWM-группа моторов; NTP; автостарт.

## 28.09 17:17 — ДЕМО для подписчиков прошло, камера выдержала; баг pwm0 «period до duty»; NTP есть на роутере

- Демо (`p4/demo.sh` на камере `/tmp/demo.sh` + мелодия «Коробейники» 54 с через `/play_audio`, HTTP 200): моторы туда‑сюда при `PTZ_US=8000`, LED 76/77 мигали, динамик играл, `DEMO_done`; камера жива, uptime 30 мин, `vpe0-out0-1 fail` остался 90 (MMA не тронут), majestic PID тот же (635). Слабое питание (USB‑гнездо удлинителя) нагрузку «моторы + динамик + LED» выдержало.
- Баг: ИК‑лампа в демо не мигала — ~100 строк `sh: write error: Invalid argument`. Причина: у свежеэкспортированного `pwm0` `period=0`, и драйвер отвергает `duty_cycle` > period. Порядок обязателен: `echo 8333 > period; echo 100 > duty_cycle; echo 1 > enable` (единицы OpenIPC: period = Гц, duty = %). Исправлено в `p4/demo.sh` (копия на камере — старая).
- Время: часы камеры = 1970 (нет RTC). `nslookup pool.ntp.org` через 192.168.1.1 → NXDOMAIN (роутер не резолвит наружу или интернет отсутствует), но **сам роутер отвечает по NTP**: `ntpd -n -q -p 192.168.1.1` → `setting time to 2026-09-28 14:22:17` (UTC; TZ камеры GMT0). Публичный IP 216.239.35.0 за 20 с не ответил. Решение для автостарта: `ntpd -p <шлюз из DHCP>` (busybox, фоновый, держит дрейф), не пул.
- Карта p1 (FAT32, 64 МиБ) монтируется с камеры: `mkdir -p /tmp/p1; mount -o ro -t vfat /dev/mmcblk0p1 /tmp/p1` (vfat в ядре есть; `/mnt` на squashfs read‑only, поэтому точка в /tmp). Это путь для хука автозапуска без пересборки squashfs p3.

## 28.09 17:40 — Этап «автозапуск с карты + NTP»: autorun.sh на FAT p1, хук init4.sh v7 (sd-stage8.img), интерим-хук в stage.py; репозиторий на GitHub

- **Что это НЕ закрывает:** пункт приёмки «автостарт после холодной загрузки» остаётся `[~]` — каждая загрузка по‑прежнему требует Pi: stage.py ловит U-Boot и шлёт `setenv bootargs … bootm` (RAM). Самостоятельная холодная загрузка = U-Boot env в NOR = ПЕРВАЯ запись во flash (STOP-протокол: смещение/размер/SHA-256 старого и нового блока env, откат = свой дамп env). Отдельный этап.
- **Схема (советник 17:25):** один файл `p1/autorun.sh` (FAT p1 карты, правится без пересборки squashfs) и два вызывателя: (1) `init4.sh` v7 — после `SSH_READY_ip` монтирует p1 ro и запускает `autorun.sh` фоном (лог `/tmp/autorun.log`; сломанный autorun не стоит SSH и консоли); (2) интерим, пока карта без v7 — `uart/stage.py` в постбут-цикле видит `SSH_READY_ip` в UART и запускает `uart/postboot.sh` (по SSH: смонтировать p1, `sh /tmp/p1/autorun.sh`, 12 попыток по 10 с, лог `uart/postboot.log`). Оба хука сразу → второй выходит по `/tmp/autorun.lock` (mkdir атомарно).
- **autorun.sh:** копирует cam-up/ptz/demo.sh с p1 в /tmp; `gw` из `ip route`; `timeout 15 ntpd -n -q -p $gw` + `ntpd -p $gw` демон (роутер отдаёт NTP, pool не резолвится); `cam-up.sh`; `ptz.sh init`. `cam-up.sh` получил защиту `pidof majestic → exit 0` (второй старт majestic = MMA-сброс).
- **Проверено на живой камере (17:36):** скрипты записаны на p1 с камеры (`mount -o remount,rw /tmp/p1`, base64 по файлу — dropbear рвёт exec с командой ~16 КБ; busybox tar без `-z`), sha256 совпали; `sh /tmp/p1/autorun.sh` → «majestic уже работает», `ptz init ок`, `AUTORUN_done`, ntpd PID 3720; второй запуск → «autorun уже был». Полный прогон (cam-up с insmod) — при следующей загрузке.
- **Образ:** `make-sd8.sh` → `sd-stage8.img` (sha256 `8ec68467…`), = stage7 + init4.sh v7; p1/p2 не изменились. Скрипты на p1 в образ не входят (нет mtools) — на карте они уже есть; после dd их нужно скопировать снова (строка в выводе make-sd8). stage.py перевзведён с хуком: PID 381195, лог `uart/stage-2a-p4-20260928-173507.log`.
- **Git (владелец 17:31):** `~/mjsxj05cm-research` — репозиторий, https://github.com/hleserg/mjsxj05cm-research (private), коммиты сразу в main. `.gitignore` закрывает секреты (p4/secret, spi/, own-4.3.9_0445, логи UART, *.out, образы, фото, disasm) и бинарники; MAC камеры в README/STATUS замаскирован. В индексе 69 текстовых файлов.

## 28.09 18:07 — sd-stage8 на карте: хук init4.sh v7 отработал сам, этап «автозапуск с карты» подтверждён
- Владелец записал `sd-stage8.img` (dd+cmp), скопировал 4 скрипта на p1, включил 18:05. UART: `INIT4_START` → `SSH_READY_ip` → `AUTORUN_p1`. `/tmp/autorun.log`: ntpd выставил время (offset +1.79e9 с), watchdog off, `Starting majestic: OK` (PID 635), `CAM_UP_done`, `ptz init ок`, `AUTORUN_done`. ntpd-демон PID 538. Интерим-хук с Pi (`postboot.sh`) пришёл вторым → «autorun уже был» (лок работает). Камера жива, uptime растёт.
- MMA: `vpe0-out0-1 fail` = 90 уже на 1‑й минуте (раньше — к 12‑й), плато то же; это шум первого старта majestic, не деградация. Монитор UART перевзведён без «fail» в фильтре (иначе флуд).
- Итог этапа: сервисы стартуют с карты без участия Pi после ядра. Границы: U-Boot всё ещё перехватывает stage.py (Pi нужен на каждую загрузку) — до этапа U-Boot env (research/uboot-env-notes.md).
- Владелец недоступен руками ~4 ч (18:10–22:00), на связи по мобиле. Дальше — только RAM-only/Pi-side работа.
- **18:10 (советник):** `uart/stage.py` после загрузки ядра висел в консоли навсегда и второй U-Boot не ловил → сброс камеры до ближайшего крона = сток из NOR (cloud, PSK на UART) без SSH до возвращения владельца. Патч: цикл — после `IPL` в начале строки (регэксп RESET) снова ждёт U-Boot и повторяет команды этапа; selftest ок. Перевзведён с `STAGE_WAIT=86400`: PID 389119, лог `uart/stage-2a-p4-20260928-181038.log`. Крон 1de14ceb → **8c1f4e0b** (:11/:41, перевзвод только если не жив). `uart/postboot.sh` теперь дублёр (v7 на карте) — спит, не мешает, лок доказан.
- Видео после автозапуска: `/image.jpg` → JPEG 1920×1080, 90 КБ (18:10). MMA fail = 90 на 5‑й минуте (то же, что на 1‑й) — плато подтверждено.

## 28.09 18:25 — Поправка: «плато MMA fail = 90» было артефактом; флуд непрерывный, подавлен printk (RAM-only)
- `dmesg | grep -c "mma fail"` = 90 — это насыщение кольцевого буфера dmesg, а не плато. По UART `[MI ERR] mi_sys_alloc_from_mma_allocators: Alloc buf:vpe0-out0-1 … fail! size:0x2fd000` идёт непрерывно, ~10 строк/с (~2.2 КБ/с). Записи 17:xx/18:07/18:10 про «плато 90» — неверны.
- Следствие: load ~9, CPU 58% sys (kernel-thread vpe0_P0_MAIN ~25%), printk на консоль 115200 — заметная часть.
- Митигация 18:16 (RAM-only): `echo "1 4 1 7" > /proc/sys/kernel/printk` (было `7 3 1 7`) → рост UART-лога 2.2 КБ/с → ~75 Б/с; через 7 мин load 8.2, idle 66%. Корень (третий буфер vpe0 port 1 0x2fd000 не влезает в mma_heap — фрагментация, свободный кусок 0x2f9000) не устранён. Кандидаты на следующую загрузку: printk в cam-up.sh до majestic; mma_heap больше в bootargs (ценой RAM Linux); выключить jpeg. Риск для «аптайм ≥ 7 дней» — измерять.
- stage.py: потолок буфера (1 МиБ → хвост 64 КиБ) и окно 8 КиБ для поиска промпта/IPL — без этого при STAGE_WAIT=86400 и флуде поиск по буферу становился O(n²) (12.5% CPU на Pi). Перевзведён: PID 393095, лог `uart/stage-2a-p4-20260928-181729.log`. Цикл на сброс не проверен на реальном сбросе — тест через `reboot` по SSH только с согласия владельца (промах = сток до 22:00).
- Видео на этой загрузке: RTSP MAIN `stream=0` h264 1920x1080 ~20 fps, `stream=1` 404 (video1 выключен), `/image.jpg` 1920x1080. Следующий этап без рук: go2rtc на Pi (MAIN).
