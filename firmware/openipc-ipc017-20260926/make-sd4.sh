#!/bin/bash
# sd-stage4.img = sd-stage2.img (p1 FAT, p2 OpenIPC rootfs, байт в байт) + p3 16 MiB squashfs:
# rootfs OpenIPC (rootfs.squashfs.ssc325) + /init4.sh + /wpa.conf + /shadow4 (init=/init4.sh, этап 2a-p4).
# ОБРАЗ СЕКРЕТНЫЙ (SSID/PSK владельца, хеш пароля root) — только своя карта, не публиковать. 28.09.2026.
set -euo pipefail
cd "$(dirname "$0")"
IMG=sd-stage4.img
chmod 755 p4/init4.sh
rm -rf p3.sqfs p4.root "$IMG"
mkdir p4.root
cp p4/init4.sh p4.root/init4.sh
cp p4/secret/wpa.conf p4.root/wpa.conf
cp p4/secret/shadow4 p4.root/shadow4
cp rootfs.squashfs.ssc325 p3.sqfs
mksquashfs p4.root p3.sqfs -comp xz -all-root -no-progress -quiet   # дописать в корень существующего образа
rm -rf p4.root
truncate -s 16M p3.sqfs
unsquashfs -l p3.sqfs | grep -E '^squashfs-root/(init4.sh|wpa.conf|shadow4|etc/wireless/usb|usr/sbin/dropbear|lib/modules/4.9.84/extra/mt7601sta.ko)$'
cp sd-stage2.img "$IMG"
truncate -s 89M "$IMG"
sfdisk -q "$IMG" <<'EOF'
label: dos
unit: sectors
1MiB, 64MiB, c, *
65MiB, 8MiB, 83
73MiB, 16MiB, 83
EOF
dd if=p3.sqfs of="$IMG" bs=1M seek=73 conv=notrunc status=none
rm -f p3.sqfs
cmp -i 512 -n $((73*1048576-512)) sd-stage2.img "$IMG" && echo "p1/p2 не изменились (MBR переписан sfdisk — ожидаемо)"
chmod 600 "$IMG"
sha256sum "$IMG" | tee "$IMG.sha256"
sfdisk -l "$IMG"
echo "Запись (владелец, X = буква карты из lsblk): sudo dd if=$PWD/$IMG of=/dev/sdX bs=4M conv=fsync status=progress && sudo cmp -n $(stat -c %s "$IMG") $PWD/$IMG /dev/sdX && echo CARD_OK"
