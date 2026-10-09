#!/bin/sh
# init=/init4.sh на p3 карты (sd-stage8.img, v7 = v6 + хук autorun.sh с p1): rootfs OpenIPC + этот скрипт + /wpa.conf + /shadow4. 28.09.2026.
# Цель: Wi-Fi (MT7601U) + SSH (dropbear, пароль root) прямо с карты, БЕЗ записи в NOR.
# v6 (после sd-stage5): wpa.conf как у стока (key_mgmt/proto/scan_ssid), `iwconfig mode Managed` перед wpa_supplicant,
# лог wpa_supplicant в /tmp/wpa.log и печать состояния каждые 5 с; udhcpc со своим скриптом (без fallback-IP 192.168.1.10
# из default.script OpenIPC — адрес занят в LAN); консоль в конце — `cat | sh`, а не интерактивный ash: на stage5 приём UART
# работал во всех окнах read из скрипта и умирал сразу после запуска интерактивного /bin/sh (tcsetattr → ms_uart set_termios).
# Скрипт НЕ завершается (panic=20: выход init = паника = ребут в сток). Ничего не пишем в /dev/mtd*.
S() { echo; echo "==== $*"; }
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev 2>/dev/null
mkdir -p /dev/pts /dev/shm
mount -t devpts devpts /dev/pts
mount -t tmpfs tmpfs /tmp; mount -t tmpfs tmpfs /var; mount -t tmpfs tmpfs /run
mkdir -p /var/run /var/log /run/lock /var/lock
S INIT4_START; uname -a; cat /proc/cmdline | sed 's/mtdparts=[^ ]*/mtdparts=.../'
mkdir /tmp/etc && cp -a /etc/. /tmp/etc/ && mount --bind /tmp/etc /etc
cp /shadow4 /etc/shadow && chmod 600 /etc/shadow
sed -i 's#^root:.*#root:x:0:0:root:/root:/bin/sh#' /etc/passwd
mkdir -p /etc/dropbear; hostname mjsxj05cm-sd
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
S mtd; cat /proc/mtd
S WIFI; /etc/wireless/usb mt7601u-ssc325-chuangmi-ipc017; echo "usb rc=$?"   # gpio 14 -> 1, modprobe mt7601sta
n=0; while [ $n -lt 40 ] && [ ! -d /sys/class/net/wlan0 ]; do sleep 1; n=$((n+1)); done; echo "wlan0 появился через ${n}s"
ip link set wlan0 up; sleep 1
iwconfig wlan0 mode Managed; echo "iwconfig rc=$?"                          # как сток (wifi_start.sh)
mkdir -p /var/run/wpa_supplicant
wpa_supplicant -B -i wlan0 -D nl80211 -c /wpa.conf -f /tmp/wpa.log -d; echo "wpa rc=$?"   # сток: -Dnl80211
cat > /tmp/dhcp.sh <<'EOF'
#!/bin/sh
case "$1" in
  deconfig) ip addr flush dev "$interface" ;;
  bound|renew) ip addr flush dev "$interface"; ip addr add "$ip/${mask:-24}" dev "$interface"
     ip route replace default via "$router" dev "$interface"; echo "nameserver $dns" > /tmp/resolv.conf ;;
esac
EOF
chmod +x /tmp/dhcp.sh
udhcpc -i wlan0 -b -t 40 -T 3 -s /tmp/dhcp.sh -x hostname:mjsxj05cm-sd; echo "udhcpc rc=$?"
n=0; while [ $n -lt 90 ] && ! ip -4 addr show wlan0 | grep -q inet; do
  sleep 5; n=$((n+5)); echo "t=${n}s $(wpa_cli -i wlan0 status 2>&1 | grep -E '^(wpa_state|key_mgmt|pairwise)' | tr '\n' ' ')"
done
S WIFI_RESULT; ip -4 addr show wlan0; ip route; wpa_cli -i wlan0 status 2>&1 | grep -E 'ssid|state|ip_address|bssid|freq'
S WPA_LOG; grep -iE 'CTRL-EVENT|Trying to associate|Associat|Authenticat|WPA:|EAPOL|SME|Scan|Failed|nl80211: (Could|Fail|Driver)|Could not|error' /tmp/wpa.log | tail -60
S SSH; dropbear -R -p 22 -K 300; echo "dropbear rc=$?"; sleep 2; pidof dropbear
S SSH_READY_ip; ip -4 addr show wlan0 | sed -n 's/.*inet \([0-9.]*\).*/\1/p'
# v7 (sd-stage8): хук автозапуска с FAT p1 карты — autorun.sh (NTP со шлюза, cam-up.sh, ptz init) без пересборки squashfs.
# Фоном: сломанный autorun не должен стоить SSH и консоли. Лог /tmp/autorun.log. p1 монтируется ro (/mnt на squashfs read-only).
S AUTORUN_p1
mkdir -p /tmp/p1; mount -o ro -t vfat /dev/mmcblk0p1 /tmp/p1 && [ -f /tmp/p1/autorun.sh ] && sh /tmp/p1/autorun.sh > /tmp/autorun.log 2>&1 &
# ---------- консоль: неинтерактивный sh из cat (см. шапку). Не слать '11111'/'22222' (магия ms_uart) ----------
S INIT4_SHELL_forever
while :; do cat | /bin/sh; sleep 2; done
