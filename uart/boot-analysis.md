# Разбор boot log, 2026-09-27

Источник: `uart/boot-20260927-064230.log` — первая удачная загрузка. Захват RX‑only: площадка 13 (TX камеры) → Pi GPIO15, земля → Pi pin 6. Скорость 115200 8N1 подтверждена: текст читается. Предыдущий `boot-20260927-063719.log` пустой (0 байт): провода стояли на соседних штырях (pins 8 и 12).

## Загрузчики (строки 1–60)

- **IPL** `g2cd6de2`, DRAM 64 MB, BIST OK. IPL_CUST грузится с NOR по смещению `0x10000`, MXP (таблица разделов SigmaStar) — на `0x20000`, размер `0x1000`.
- **U‑Boot 2015.01 (Sep 15 2020 - 15:53:02), Build: jenkins-ipc019_4_0_9_0425-4**, Version `I6g46ec744`. Хранится XZ‑сжатым (`0x1a270` байт, распакован `0x47ab8`), CRC32 OK.
  - U‑Boot на камере — **из сборки 4.0.9_0425**, не 4.3.9: его ставил `uboot_ota.sh` в OTA 4.0.9 (см. `firmware/`).
- **SPI NOR:** `Flash is detected (0x090F, 0x1C, 0x70, 0x18)` — JEDEC **1C 70 18** = EN25QH128A, 16 MiB. Совпадает с маркировкой.
- **env:** `env_offset=0x4F000 env_size=0x1000` (внутри BOOT).
- **MMC:** `MStar SD/MMC: 0` — драйвер SD в U‑Boot есть. При загрузке U‑Boot сам проверяет SD: `there's no sdcard, ignore dfu`. **Значит, механизм обновления с SD живёт в U‑Boot**: любую SD в камеру при загрузке вставлять только после разбора, какие файлы он ищет.
- **Автозагрузка:** строки «Hit any key to stop autoboot» нет — похоже, `bootdelay=0`. Можно ли прервать, неизвестно: нужен TX адаптера (отдельное «да» владельца).
- Ядро: `SF: 2097152 bytes @ 0x50000 Read: OK`, uImage «MVX2##I6g6cdcdf5KL_LX409####[BR:», LZMA/XZ, 1570356 байт, load/entry `0x20008000`.

## Ядро

- `Linux version 4.9.84 ... #3 PREEMPT Tue Jan 16 17:05:35 CST 2024` — сборка 2024 года, т.е. прошивка 4.3.9 (не 4.0.9 из скачанных).
- `OF: fdt:Machine model: INFINITY6 SSC009A-S01A QFN88` (SSC323 = Infinity6).
- `Kernel command line: console=ttyS0,115200 root=/dev/mtdblock2 rootfstype=squashfs ro init=/linuxrc LX_MEM=0x3fc6000 mma_heap=mma_heap_name0,miu=0,sz=0x1400000`
- Консоль ядра на ttyS0 включена.

## Карта flash — CONFIRMED (ядро, MXP_PARTS)

| MTD | Смещение | Конец | Размер | Имя |
|---|---|---|---|---|
| mtd0 | `0x000000` | `0x050000` | 320 KiB | BOOT (IPL `0x0`, IPL_CUST `0x10000`, MXP `0x20000`, U‑Boot, env `0x4F000`) |
| mtd1 | `0x050000` | `0x250000` | 2 MiB | KERNEL |
| mtd2 | `0x250000` | `0x9B0000` | 7.375 MiB | ROOTFS (squashfs, ro) |
| mtd3 | `0x9B0000` | `0xFE0000` | 6.1875 MiB | DATA (jffs2) |
| mtd4 | `0xFE0000` | `0xFF0000` | 64 KiB | CONFIG |
| mtd5 | `0xFF0000` | `0x1000000` | 64 KiB | FACTORY |

Erase size `0x10000`. Совпадает с раскладкой khmyznikov (boot 192K + U‑Boot 128K = BOOT 320K).

## Юзерспейс (коротко)

- Wi‑Fi MT7601U, драйвер `JEDI.MP1.mt7601u.v1.12.1.2`; `MT7601 E2PROM: WRONG VERSION 0xc, should be 9` — предупреждение драйвера, связь есть.
- miio: активируются `miio_client`, `miio_cloud`, `miio_ota`, `miio_miss`, `miio_record`, `miio_sdcard`, `miio_nas` и др. **`miio_ota` активен** — пока камера в сети, OTA возможно.
- `wifi_start.sh: line 573: iptables: not found`.
- DHCP: `192.168.1.53`, DNS `192.168.1.1`, SSID из `wpa_cli`. Время `1970` до NTP — RTC нет (`hctosys: unable to open rtc device`).

## Загрузка userspace и консоль (дочитано 06:50)

- Перед init: `+ source /etc/hooks/pre-init`, затем `exec chroot . /bin/busybox linuxrc`. Хук в ro‑squashfs, но может читать что‑то с DATA/SD — посмотреть в dump.
- `S12copylog`: при загрузке пытается смонтировать SD (`/dev/mmcblk0p1` → `/mnt/sdcard`) и скопировать логи.
- `Start detecting tf_update.img mount sdcard agagin` — **второй механизм обновления с SD, уже в Linux** (помимо `dfu` в U‑Boot). SD в камеру не вставлять до разбора обоих.
- Сторожевой таймер `imi watchdog: reset=10, timeout=40` — если убить его процесс, камера перезагрузится через ~40 с.
- Службы: `fetch_av`, `miio_agent/algo/client/client_helper/cloud/devicekit/miss/nas/ota/record/sdcard`, `mortox`, `crond`. `miio_qrcode` деактивирован (камера уже привязана).
- Лог кончается на `end_time: ... 1970` (строка ~988). **Приглашения login/shell на ttyS0 нет**, строки «Please press Enter» тоже. Консоль, видимо, только вывод; проверить можно только с TX адаптера.
- ⚠ **В логе в открытом виде пароль Wi‑Fi владельца** (`wpa_supplicant.conf` печатается при старте, строки ~618–625). Лог никуда не выкладывать; для публикации — только редактированная копия.

## Можно ли прервать U‑Boot (веб, 27.09 06:55)

- [saramlove/cmsxj19e-hacks SERIAL_CONSOLE.md](https://github.com/saramlove/cmsxj19e-hacks/blob/dev/SERIAL_CONSOLE.md): **Chuangmi IPC019E**, SoC строкой `INFINITY6 SSC009A-S01A QFN88` — как у нас. Способ: держать Enter и включить питание → приглашение `SigmaStar #`. `printenv` там: `bootdelay=0`, `bootcmd=sf probe 0;sf read 0x22000000 ${sf_kernel_start} ${sf_kernel_size};bootm 0x22000000` — совпадает с нашим логом (`2 MiB @ 0x50000` → `0x22000000`).
- Это соседняя модель (019E), не наш экземпляр. Проверено страницей, остальное из отчёта сабагента (MJSXJ02CM, MJSXJ09CM) не сверено.
- Для нас: с Pi слать `\r` непрерывно **до** подачи питания, одновременно читать порт.

## U‑Boot остановлен (27.09 07:38) — `uart/uboot-20260927-073616.log`

- Провод Pi pin 8 → резистор → площадка 14 (RX камеры). `uart/uboot-ro.py` слал `\r` с момента включения; приглашение **`SigmaStar # `**. Выполнены только `version`, `help`, `printenv`, `bdinfo` (последней в сборке нет).
- `printenv`: `bootdelay=0`, `bootcmd=sf probe 0;sf read 0x22000000 ${sf_kernel_start} ${sf_kernel_size};bootm 0x22000000`, `sf_kernel_start=50000`, `sf_kernel_size=200000`; стоп‑строки нет. Env 621/4092 байт. `ethaddr=xx:xx:xx:xx:xx:xx` и сетевые адреса `172.17.190.x` — заводские, не наши.
- `help`, что важно для dump:
  - **`fatwrite` нет** → способ 1 (sf read → fatwrite на SD) невозможен как есть.
  - есть `sf`, `md`, `cmp`, `crc32`, `mmc`, `fatls/fatload/fatread`, `sfbin` (TFTP‑выгрузка flash, но сети в U‑Boot нет: `No ethernet found`).
  - `dstar` — «script via SD/MMC»: вероятно, это и есть механизм SD‑обновления U‑Boot. SD не вставлять.
  - опасные, не трогать: `saveenv`, `setenv`, `sf erase/write`, `mw`, `mm`, `nm`, `reset`, `run`, `go`, `mxp`, `dstar`, `estar`, `mstar`.
