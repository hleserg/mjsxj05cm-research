# p4 (данные) на SD-карте — план (29.09 16:5x)

Состояние: карта 32 ГБ (62521344 секторов), размечено p1 FAT 64М (uImage, cam-up.sh), p2 8М, p3 16М squashfs;
свободно с сектора 182272 до конца — ~29,7 ГБ. majestic `records.enabled: false`, path `/mnt/mmcblk0p1/%F`.
На камере есть: busybox `fdisk`, `partprobe`, `mkfs.vfat`. Нет: sfdisk, mke2fs, blockdev. Kernel: vfat есть (p1 смонтирован).

## Что делается (всё с камеры, NOR не трогается) — 16:50, после ревью

0. Сделано на Pi (без записи на карту): MBR снят с камеры (`sd/mbr-before-p4.bin`, sha256 28052040…), собран `sd/mbr-with-p4.bin` (sha256 3e761060…): изменена ТОЛЬКО запись 4 (байты 494..509: type 0x0c, start 182272, size 62339072 = до конца карты). `cmp -l` → отличия только в 496..510; `sfdisk -d`/`fdisk -l` на файле: p1 (bootable, 2048+131072), p2, p3 не изменились, p4 = 182272..62521343 (~29,7 ГБ). `mkfs.vfat` busybox: только `-n LABEL` (всегда FAT32). `/mnt` — read-only squashfs → монтировать в `/tmp/p4` (как `/tmp/p1`).
1. **Запись MBR на карту (нужно «да» владельца):** `dd if=mbr-with-p4.bin of=/dev/mmcblk0 bs=512 count=1; sync; partprobe /dev/mmcblk0; cat /proc/partitions` — ждём строку `mmcblk0p4`. Если ядро приняло таблицу, U-Boot `part_dos` (те же поля 0x55AA + LBA) примет тоже.
2. `mkfs.vfat -n DATA /dev/mmcblk0p4`; `mkdir /tmp/p4; mount -t vfat -o rw,noatime /dev/mmcblk0p4 /tmp/p4; touch /tmp/p4/ok`.
3. На p1 (remount rw→ro): в `cam-up.sh` одна строка `mkdir -p /tmp/p4; mount -t vfat -o rw,noatime /dev/mmcblk0p4 /tmp/p4`; в m.yaml `records: enabled: true, path: /tmp/p4/%F, split: 20, maxUsage: 90`. majestic НЕ рестартовать — **один `reboot` камеры** = настоящая проверка U-Boot с новой таблицей.
4. Проверка через 2 мин: SSH; `ls /tmp/p4/$(date +%F)` — mp4 по 20 с; `df /tmp/p4`; `dmesg | grep -c 'mma fail'`=0; `free`, VmRSS majestic (муксер добавляет буферы при ~17 МБ available, watchdog выкл — упавший majestic до ребута не встанет). Часы камеры UTC → папки `%F` по UTC (при желании `export TZ=` в cam-up.sh).

## Риски и откат

- Сигналы без UART (stage.py остановлен): пинг есть + SSH нет = сток (U-Boot не прочитал карту). Откат MBR: `dd if=mbr-before-p4.bin of=/dev/mmcblk0 bs=512 count=1` с камеры, если она на OpenIPC; иначе перезапись карты с Pi (`sd-stage8.img`, физика).
- U-Boot `fatload mmc 0:1` читает MBR: битая таблица → `No partition table`/`Unable to read` → norboot → сток (не кирпич). Откат: `dd if=mbr-old.bin of=/dev/mmcblk0 bs=512 count=1` (с камеры, если она загрузилась) или перезапись карты с Pi (`sd-stage8.img`, физическое действие).
- Пишется только сектор 0 (MBR); p1 (сектора 2048+) не задевается.
- Frigate на bigpc пишет свои записи сам; p4 = локальная запись «вкруг» на камере без интернета (пункт приёмки).

## Результат 16:59

Выполнено по плану: MBR записан (sha 3e761060…), U-Boot загрузил OpenIPC с новой таблицей, p4 = 31169536 блоков, FAT32 DATA, cam-up.sh на p1 (md5 2695477b…), records пишутся в /tmp/p4/%F. partprobe на камере всегда `Resource busy` → таблица применяется только ребутом. `reboot` в фоне через camssh не срабатывает, `reboot -f` — да.
