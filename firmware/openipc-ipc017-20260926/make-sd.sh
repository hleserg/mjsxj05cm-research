#!/bin/bash
# Образ SD для этапа 2 (DECISIONS.md, 27.09): p1 FAT32 64 MiB — файлы для U-Boot (fatload),
# p2 8 MiB — rootfs.squashfs OpenIPC (root=/dev/mmcblk0p2). Без root: mkfs.vfat + pyfatfs + sfdisk.
# На карте НЕ должно быть tf_update.img, tf_recovery.img, tf_all*.img, auto_update.txt, manu_test/.
set -euo pipefail
cd "$(dirname "$0")"
OWN=../own-4.3.9_0445
IMG=sd-stage2.img
[ -d .venv ] || { python3 -m venv .venv && .venv/bin/pip -q install pyfatfs; }

rm -f fat.img "$IMG"
truncate -s 64M fat.img
mkfs.vfat -F 32 -n OPENIPC fat.img >/dev/null
.venv/bin/python - <<'EOF'
from pyfatfs.PyFatFS import PyFatFS
fs = PyFatFS("fat.img")
for f in ["uImage.ssc325", "kernel.pad.bin", "rootfs.pad.bin", "rootfs.squashfs.ssc325", "CRC.txt",
          "../own-4.3.9_0445/mtd-kernel.bin", "../own-4.3.9_0445/mtd-rootfs.bin", "../own-4.3.9_0445/mtd-data.bin"]:
    name = f.rsplit("/", 1)[-1]
    with open(f, "rb") as src, fs.openbin("/" + name, "w") as dst:
        dst.write(src.read())
print("FAT:", sorted(fs.listdir("/")))
fs.close()
EOF

truncate -s 8M sq.img
dd if=rootfs.squashfs.ssc325 of=sq.img conv=notrunc status=none

truncate -s 73M "$IMG"
sfdisk -q "$IMG" <<'EOF'
label: dos
unit: sectors
1MiB, 64MiB, c, *
65MiB, 8MiB, 83
EOF
dd if=fat.img of="$IMG" bs=1M seek=1  conv=notrunc status=none
dd if=sq.img  of="$IMG" bs=1M seek=65 conv=notrunc status=none
rm -f fat.img sq.img
sha256sum "$IMG" | tee "$IMG.sha256"
sfdisk -l "$IMG"
echo "Запись на карту (владелец, X = буква карты из lsblk): sudo dd if=$PWD/$IMG of=/dev/sdX bs=4M conv=fsync status=progress"
