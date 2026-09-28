#!/bin/bash
# sd-stage3.img = sd-stage2.img (p1 FAT, p2 OpenIPC rootfs, байт в байт) + p3 16 MiB squashfs:
# стоковый rootfs 4.3.9_0445 + /recon.sh (init=/recon.sh, этап 2a-p3 в uart/stage.py). 28.09.2026.
set -euo pipefail
cd "$(dirname "$0")"
ROOT=../own-4.3.9_0445/rootfs
IMG=sd-stage3.img
chmod 755 p3/recon.sh
rm -f p3.sqfs "$IMG"
mksquashfs "$ROOT" p3.sqfs -comp xz -all-root -noappend -no-progress -quiet
mksquashfs p3/recon.sh p3.sqfs -comp xz -all-root -no-progress -quiet   # дописать в корень
truncate -s 16M p3.sqfs
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
cmp -n $((65*1048576+8*1048576)) sd-stage2.img "$IMG" && echo "p1/p2 не изменились"
sha256sum "$IMG" | tee "$IMG.sha256"
sfdisk -l "$IMG"
echo "Запись (владелец, X = буква карты из lsblk): sudo dd if=$PWD/$IMG of=/dev/sdX bs=4M conv=fsync status=progress && sudo cmp -n $(stat -c %s "$IMG") $PWD/$IMG /dev/sdX && echo CARD_OK"
