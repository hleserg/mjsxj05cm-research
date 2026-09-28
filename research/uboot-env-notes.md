# U-Boot env в NOR — заметки к будущему этапу «загрузка с SD без Pi» (28.09.2026, разведка по своим документам)

**Этап ещё не начат. Любая запись env = ПЕРВАЯ запись во flash = STOP-протокол (DECISIONS.md).**

## Факты (источники — свои логи/документы)
- Стоковый env: смещение **0x4F000**, размер **0x1000** (4 КиБ), внутри раздела BOOT 0x0–0x50000 (`uart/boot-analysis.md:11`, `uart/uboot-20260927-073616.log:37`). Одна копия, без redundant. Занято 621/4092 байт (`…073616.log:125`) → формат стандартный: 4 байта CRC32 + строки `name=value\0` → в 4092 байтах данных.
- Стоковые переменные (`uart/uboot-20260927-073616.log:104–123`, MAC/IP не копировать):
  - `bootcmd=sf probe 0;sf read 0x22000000 ${sf_kernel_start} ${sf_kernel_size};bootm 0x22000000`
  - `bootargs=console=ttyS0,115200 root=/dev/mtdblock2 rootfstype=squashfs ro init=/linuxrc LX_MEM=0x3fc6000 mma_heap=mma_heap_name0,miu=0,sz=0x1400000`
  - `bootdelay=0`, `sf_kernel_start=50000`, `sf_kernel_size=200000`, `sf_part_start=950000`, `sf_part_size=6b0000`, `ethaddr`, `ipaddr/serverip/gatewayip/netmask` (172.17.190.x), `ethact=sstar_emac`.
- Что stage.py шлёт U-Boot для карты (`uart/stage.py:25–55`): `mmc dev 0; mmc rescan; fatload mmc 0:1 0x22000000 uImage.ssc325; setenv bootargs console=ttyS0,115200 root=/dev/mmcblk0p3 rootwait rootfstype=squashfs init=/init4.sh LX_MEM=… mma_heap=…; bootm 0x22000000`.
- Дампы NOR: `spi/original-01|02|03.bin`, sha256 `46bb4058…f218ee`, все три идентичны (`spi/SHA256SUMS`, STATUS.md:84).
- OpenIPC-раскладка (НЕ наша): env = последние 64K DATA (0xFD0000), fw_setenv (DECISIONS.md:112,157). Мы U-Boot не меняем → env остаётся стоковый по 0x4F000.

## Кандидат на план (обсудить с советником перед STOP-запросом)
1. Вырезать env из дампа: `dd if=spi/original-01.bin bs=1 skip=$((0x4F000)) count=4096` → проверить CRC32 первых 4 байт против данных (python `zlib.crc32`) — подтверждает формат и точное смещение.
2. Новый env = стоковый + `bootcmd=mmc dev 0; mmc rescan; if fatload mmc 0:1 0x22000000 uImage.ssc325; then setenv bootargs …mmcblk0p3 init=/init4.sh…; bootm 0x22000000; fi; sf probe 0; sf read …; bootm 0x22000000` — без карты падает на стоковую загрузку (откат вынимая карту). `bootargs` стоковый не трогать (fallback). Пересчитать CRC32, дополнить 0xFF до 4096.
3. Проверить RAM-only ДО записи: `setenv bootcmd '…'; run bootcmd` (без saveenv) — уже «класс bootm», разрешён владельцем «да, но позже».
4. STOP-запрос владельцу: смещение 0x4F000, размер 0x1000, sha256 старого/нового блока, откат = `sf write` старого блока из дампа (или полный BOOT-раздел), что ломается: неверный env → U-Boot берёт default env (проверить в бинарнике u-boot, есть ли `default_environment` с bootcmd) — камера не кирпич, пока U-Boot цел; brick-recovery = SPI-программатор, ~15 мин.
5. Способ записи: из U-Boot `sf erase 0x4F000 0x1000; sf write <ram> 0x4F000 0x1000` ИЛИ `saveenv` после `setenv bootcmd` — saveenv проще (U-Boot сам считает CRC), но пишет весь env-сектор; проверить `sf read` + `crc32` после.

## Не найдено
- Есть ли redundant env / `default_environment` в стоковом u-boot — смотреть в бинарнике (`spi/original-01.bin` 0x0–0x4F000, strings).
- Стирает ли `saveenv` только 4 КиБ или сектор 64 КиБ (зависит от CONFIG_ENV_SECT_SIZE) — критично: 64 КиБ сектор с 0x40000 по 0x4FFFF задел бы конец U-Boot? U-Boot лежит в 0x0–0x4F000, значит сектор 0x40000–0x50000 содержит хвост U-Boot → `saveenv` с sect 64K = перезапись хвоста U-Boot из RAM-копии. Выяснить до любого решения.

## 28.09 20:50 — разбор собственного дампа (только чтение; спорить не о чем, всё из `spi/original-01.bin`)
- Раздел BOOT: 0x0–0x50000. XZ-потоки: IPL_CUST по 0x13b09, **U-Boot по 0x30040** (заголовок 0x40 байт с 0x30000). Поток U-Boot: 0x1a270 байт сжатых → **кончается по 0x4a2b0**, распакованный 0x47ab8 (`U-Boot 2015.01 (Sep 15 2020 - 15:53:02)`). Байты 0x4a2b0–0x4F000 не FF (хвост/мусор — при стирании не критичны, но и не проверялись). Env 0x4F000–0x50000: CRC32 сходится (0xea110cd3), 20 переменных (список выше).
- **Вывод про сектор:** env лежит в том же 64-КиБ блоке 0x40000–0x4FFFF, что и хвост U-Boot (0x40000–0x4a2b0). Если saveenv стирает блоком 64 КиБ — U-Boot теряется = кирпич (восстановление только программатором). Если сектором 4 КиБ — трогается только env.
- В строках U-Boot есть ОБА примитива: `MDrv_SERFLASH_SectorErase` (4K) и `MDrv_SERFLASH_BlockErase` (64K) + `MDrv_SERFLASH_AddressErase` (по адресу/размеру) и стандартный env_sf («Erasing SPI flash…/Writing to SPI flash…»). Литерала 0x4F000 в бинарнике НЕТ — смещение env берётся из таблицы MXP (0x20000) в рантайме (печать `env_offset=0x%X env_size=0x%X`). Размер стирания статически (без дизассемблера) не определяется.
- **Безопасный нулевой шаг для STOP-этапа (предложение):** проверить гранулярность стирания на заведомо пустом месте: блок **0x240000–0x250000 (хвост раздела kernel) целиком 0xFF** в дампе (данные ядра кончаются по 0x1cf674, дальше 0x8098c байт FF). `sf erase 0x24F000 0x1000` → если U-Boot ответит «not multiple of erase size» / сотрёт 64K — узнаём гранулярность; данные при этом НЕ меняются (FF→FF), проверка `sf read` + `crc32` до/после. Это всё равно запись во flash → STOP-протокол и «да» владельца; но риска для данных нет. Если гранулярность 4K — `sf erase 0x4F000 0x1000; sf write <RAM> 0x4F000 0x1000` (или saveenv) безопасны для U-Boot.
- Альтернатива без env вообще: нет — bootcmd живёт только в env; менять kernel-раздел (2 МиБ) хуже.
