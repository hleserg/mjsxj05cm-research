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
