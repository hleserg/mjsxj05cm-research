#!/bin/bash
# rootfs для NOR (раздел rootfs @0x250000, 0x760000 = 7 733 248 Б): тот же состав, что p3 карты в make-sd8.sh
# (rootfs OpenIPC + init4.sh + /wpa.conf + /shadow4), плюс /opt/p1/ — копия скриптов, которые на карте лежат на p1
# (autorun/cam-up/ptz/demo.sh + onvif-password.txt), чтобы камера поднималась и БЕЗ карты. Родной /init OpenIPC не используется
# (init=/init4.sh в norargs env v5), поэтому ничего из userland в NOR не пишет — как и с карты. 09.10.2026.
# Выход: rootfs-nor.squashfs и rootfs-nor.pad.bin (дополнен 0xFF до 0x760000) — СЕКРЕТНЫЕ (SSID/PSK, хеш root, пароль ONVIF),
# в репо не входят (.gitignore *.bin, *.squashfs*). CRC.txt обновляется строкой rootfs-nor.pad.bin (crc32 = то, что печатает U-Boot).
set -euo pipefail
cd "$(dirname "$0")"
SZ=$((0x760000))
grep -q 'AR=/opt/p1/autorun.sh' p4/init4.sh || { echo "init4.sh без ветки /opt/p1 (нужен v8)"; exit 1; }
chmod 755 p4/init4.sh
rm -rf nor.root rootfs-nor.squashfs rootfs-nor.pad.bin
unsquashfs -q -n -d nor.root rootfs.squashfs.ssc325 2>&1 | grep -v -i xattr || true
cp p4/init4.sh nor.root/init4.sh
cp p4/secret/wpa.conf nor.root/wpa.conf
cp p4/secret/shadow4 nor.root/shadow4
mkdir -p nor.root/opt/p1
cp p4/autorun.sh p4/cam-up.sh p4/ptz.sh p4/demo.sh p4/dance.sh p4/ptz p4/ptz-cgi.sh p4/onvif-ptz.sh p4/onvif-serve.sh p4/tcpserve p4/onvif.conf.tpl p4/onvif.tgz p4/secret/onvif-password.txt nor.root/opt/p1/   # 10.10: полный набор p1 (PTZ-бинарник, кнопки HA, ONVIF PTZ, танец)
chmod 755 nor.root/opt/p1/*.sh nor.root/opt/p1/ptz nor.root/opt/p1/tcpserve; chmod 600 nor.root/opt/p1/onvif-password.txt
chmod 4755 nor.root/bin/busybox   # unsquashfs без root теряет setuid
mksquashfs nor.root rootfs-nor.squashfs -comp xz -all-root -noappend -no-progress -quiet
rm -rf nor.root
n=$(stat -c %s rootfs-nor.squashfs)
[ "$n" -le "$SZ" ] || { echo "squashfs $n Б > раздел $SZ Б"; exit 1; }
cp rootfs-nor.squashfs rootfs-nor.pad.bin
python3 -c "import sys; open('rootfs-nor.pad.bin','ab').write(b'\xff'*($SZ-$n))"
chmod 600 rootfs-nor.squashfs rootfs-nor.pad.bin
unsquashfs -l rootfs-nor.squashfs | grep -E '^squashfs-root/(init4.sh|wpa.conf|shadow4|opt/p1/.*|etc/wireless/usb|usr/sbin/dropbear|lib/modules/4.9.84/extra/mt7601sta.ko)$'
python3 - <<'PY'
import hashlib, re, zlib
from pathlib import Path
rows = {}
for f, note in (("rootfs-nor.squashfs", ""), ("rootfs-nor.pad.bin", " (0x250000, 0xFF до 0x760000)")):
    d = Path(f).read_bytes()
    rows[f] = f"{f}{note} | {len(d)} (0x{len(d):X}) | {zlib.crc32(d) & 0xffffffff:08x} | {hashlib.sha256(d).hexdigest()}"
crc = Path("CRC.txt").read_text().splitlines()
crc = [l for l in crc if not any(l.startswith(k) for k in rows)] + list(rows.values())
Path("CRC.txt").write_text("\n".join(crc) + "\n")
print("\n".join(rows.values()))
PY
echo "squashfs $n Б из $SZ ($((100*n/SZ))%). Дальше: tools/p1-put.sh rootfs-nor.pad.bin → stage nor-openipc-write (только владелец, uboot/STOP-nor.md)"
