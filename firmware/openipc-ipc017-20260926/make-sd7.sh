#!/bin/bash
# sd-stage7.img = sd-stage5.img (single-pass p3), но init4.sh v6: Wi-Fi с логом wpa_supplicant, без fallback-IP,
# консоль в конце — `cat | sh` (интерактивный ash убивал приём UART: sd-stage5, 28.09 11:10).
# ОБРАЗ СЕКРЕТНЫЙ (SSID/PSK владельца, хеш пароля root) — только своя карта, не публиковать. 28.09.2026.
set -euo pipefail
cd "$(dirname "$0")"
IMG=sd-stage7.img
chmod 755 p4/init4.sh
rm -rf p3.sqfs p7.root "$IMG"
unsquashfs -q -n -d p7.root rootfs.squashfs.ssc325 2>&1 | grep -v -i xattr || true   # в базе нет dev-узлов, root не нужен
cp p4/init4.sh p7.root/init4.sh
cp p4/secret/wpa.conf p7.root/wpa.conf
cp p4/secret/shadow4 p7.root/shadow4
chmod 4755 p7.root/bin/busybox   # unsquashfs без root теряет setuid
mksquashfs p7.root p3.sqfs -comp xz -all-root -noappend -no-progress -quiet
rm -rf p7.root
truncate -s 16M p3.sqfs
unsquashfs -l p3.sqfs | grep -E '^squashfs-root/(init4.sh|wpa.conf|shadow4|etc/wireless/usb|usr/sbin/dropbear|lib/modules/4.9.84/extra/mt7601sta.ko)$'
cp sd-stage2.img "$IMG"
truncate -s 89M "$IMG"
sfdisk -q "$IMG" <<'EOT'
label: dos
unit: sectors
1MiB, 64MiB, c, *
65MiB, 8MiB, 83
73MiB, 16MiB, 83
EOT
dd if=p3.sqfs of="$IMG" bs=1M seek=73 conv=notrunc status=none
rm -f p3.sqfs
cmp -i 512 -n $((73*1048576-512)) sd-stage2.img "$IMG" && echo "p1/p2 не изменились (MBR переписан sfdisk — ожидаемо)"
chmod 600 "$IMG"
sha256sum "$IMG" | tee "$IMG.sha256"
sfdisk -l "$IMG"
echo "Запись (владелец, X = буква карты из lsblk): sudo dd if=$PWD/$IMG of=/dev/sdX bs=4M conv=fsync status=progress && sudo cmp -n $(stat -c %s "$IMG") $PWD/$IMG /dev/sdX && echo CARD_OK"
