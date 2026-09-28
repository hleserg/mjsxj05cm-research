# Firmware inventory и сравнение

Состояние на 2026-09-22. SHA-256 рассчитан локально; прямые URL — [downloads.md](downloads.md), оценка источников — [sources.md](../research/sources.md). Байты `4.3.9_0445` и `4.3.9_0448` не получены: их kernel, rootfs, bootloader, подпись и anti-downgrade остаются неизвестны.

| Файл | SHA-256 |
|---|---|
| `tf_recovery-3.4.2_0062-github.img` | `53271c2d932d1b8f278f0ee815837ea52b838e1afe3d2150587daa7f94ee2e72` |
| `IPC019_3.5.1_0052.zip` | `adb5190ff5550e3073e79f1f2a4901d24cc0a2fc72d52a511e8e72c5019b0c03` |
| `tf_recovery-3.5.1_0052.img` | `c787e781729cbdbc60f95aa54f84aea2149015277b521a3385cd161b79ec034a` |
| `tf_recovery-khmyznikov.img` | **тот же** `c787e781729cbdbc60f95aa54f84aea2149015277b521a3385cd161b79ec034a` |
| `IPC019_4.0.9_0426.zip` | `a93aef24961360548f21191cc09f5916ca660a699ab07c5eee2810780e004e3f` |
| `extracted-4.0.9_0426-images/tf_recovery.img` | `cfc2517048cb88d85ea6bc65bc726a8aa8b14c2b181b76ba14720716589d0412` |
| `extracted-4.0.9_0426-images/tf_update.img` | `d940159a12c6c45928e84db5de84a6a1156bf4bb5602cb4ea4bd6f19fec728f2` |

Оба файла `mahendraplus-tf_*.img` байт-в-байт совпали с официальными `4.0.9_0426` recovery/update: это независимый mirror для хешей, не доказательство успеха SD recovery.

| Образ | Маркер и ядро | SquashFS | JFFS2 | Версия в JFFS2 |
|---|---|---:|---:|---|
| 3.4.2_0062 | I3/LX318, Linux 3.18.30 | `0x210000` | `0x960000` | не извлекали |
| 3.5.1_0052 recovery | I6/LX409, Linux 4.9.84 | `0x200000` | `0x960000` | `3.5.1_0052` |
| 4.0.9_0426 ZIP / recovery | I6/LX409, Linux 4.9.84 | `0x200000` | `0x960000` | **`4.0.9_0425`** |
| 4.0.9_0426 ZIP / update | I6/LX409, Linux 4.9.84 | `0x200000` | `0x960000` | `4.0.9_0426` |
| 4.3.9_0445 / 0448 | каталог 2024, bytes недоступны | ? | ? | ? |

Все четыре образа — ARM uImage с действительными header/data CRC, LZMA/XZ kernel, SquashFS 4.0/XZ и JFFS2. Размер каждого recovery/update `0xF90050` байт. Последние 80 байт не идентифицированы как подпись; отсутствие явной подписи не доказывает отсутствие проверки. `3.4.2_0062` имеет другой hardware marker и rootfs offset, поэтому не подходит как прямое основание для I6/LX409.

В `3.5.1_0052` есть `miio_stream`; в `4.0.9_0426` update вместо него `miio_miss`. Это различие файлов, а не доказанная причина закрытия RTSP/root. Только update содержит `S99uboot_check` и `uboot_ota.sh`: при наличии `BOOT.bin.gz` скрипт проверяет MD5 и вызывает `flashcp` в `/dev/mtd0`. Наличие кода не доказывает, что конкретный пакет содержит bootloader или что bootloader нашей камеры такой же.

`S96rename_firmware` в 0052/0425 ищет `tf_recovery.img` на `/mnt/sdcard`, `/mnt/media/mmcblk0p1`, `/mnt/media/mmcblk0` и переименовывает в `.bak`. В 0426 update он обрабатывает также `tf_update.img`, `tf_all.img`, `tf_all_recovery.img`. Это post-boot обработка; она не описывает порядок bootloader SD recovery, FAT/FAT32, проверку версии или подпись. FAT32 в публичных инструкциях — полевое требование, не проверенное на нашей камере. `S49factory` проверяет RSA+MD5 для `manu_test`, отдельно от OTA.

`strings` по `miio_ota` 0052 и 0426 update показал X.509/EVP verification и сообщение «download md5 ... sigin verify ... start to write flash». Поэтому OTA-путь явно содержит проверки MD5/подписи; точный алгоритм и применимость к SD recovery/anti-downgrade `0445` статическими строками не установлены. [Вывод strings](strings-summary-2026-09-22.txt).

Выводы инструментов: [analysis-2026-09-22.txt](analysis-2026-09-22.txt), [file-binwalk-2026-09-22.txt](file-binwalk-2026-09-22.txt). JFFS2 извлечён локально `jefferson`; `unsquashfs` извлёк обычные файлы, но без root не создал `/dev/console`. Это не влияет на анализ скриптов.
