# p4 (данные) на SD-карте — план (29.09 16:5x)

Состояние: карта 32 ГБ (62521344 секторов), размечено p1 FAT 64М (uImage, cam-up.sh), p2 8М, p3 16М squashfs;
свободно с сектора 182272 до конца — ~29,7 ГБ. majestic `records.enabled: false`, path `/mnt/mmcblk0p1/%F`.
На камере есть: busybox `fdisk`, `partprobe`, `mkfs.vfat`. Нет: sfdisk, mke2fs, blockdev. Kernel: vfat есть (p1 смонтирован).

## Что делается (всё с камеры, NOR не трогается)

1. Бэкап MBR: `dd if=/dev/mmcblk0 bs=512 count=1 of=/tmp/mbr-old.bin` → копия на p1 (`/tmp/p1/mbr-old.bin`, remount rw→ro) и на Pi (`uboot/`-нет, в `sd/` репо не кладём: содержит только таблицу, MAC нет — можно в репо как `sd/mbr-before-p4.bin`).
2. **Изменение таблицы разделов (нужно «да» владельца):** `fdisk /dev/mmcblk0`: `n` → `p` → `4` → первый сектор `182272` → последний по умолчанию → `t 4 c` (W95 FAT32 LBA) → `w`. p1–p3 не меняются (проверка: `fdisk -l` до/после, отличается только строка p4; MBR-сигнатура и bootable-флаг p1 сохраняются).
3. `partprobe /dev/mmcblk0` (p1 смонтирован ro — если ядро откажет, `reboot` с камеры: автозагрузка теперь без UART).
4. `mkfs.vfat -F 32 -n DATA /dev/mmcblk0p4`.
5. В `cam-up.sh` на p1: `mkdir -p /mnt/data; mount -t vfat -o rw,noatime /dev/mmcblk0p4 /mnt/data`; majestic (bind-mount /tmp/m.yaml) `records: enabled: true, path: /mnt/data/%F, split: 20, maxUsage: 90`. majestic НЕ рестартовать (MMA-утечка) — применить ребутом камеры.
6. Проверка: через 1 мин `ls /mnt/data/$(date +%F)` — файлы mp4 по 20 с; `df /mnt/data`; `dmesg | grep -c 'mma fail'` = 0; скачать кусок по HTTP majestic (`/records/...` если есть) или `scp`.

## Риски и откат

- U-Boot `fatload mmc 0:1` читает MBR: битая таблица → `No partition table`/`Unable to read` → norboot → сток (не кирпич). Откат: `dd if=mbr-old.bin of=/dev/mmcblk0 bs=512 count=1` (с камеры, если она загрузилась) или перезапись карты с Pi (`sd-stage8.img`, физическое действие).
- fdisk busybox пишет только сектор 0 (MBR); p1 (сектора 2048+) не задевает.
- Frigate на bigpc пишет свои записи сам; p4 = локальная запись «вкруг» на камере без интернета (пункт приёмки).
