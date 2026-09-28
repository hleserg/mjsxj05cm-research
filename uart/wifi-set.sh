#!/bin/bash
# Подставить в wpa_supplicant камеры (live, по UART, RAM) SSID и пароль из секретного файла — значения НЕ печатаются.
#   uart/wifi-set.sh firmware/openipc-ipc017-20260926/p4/secret/wifi-current.txt
# Файл: строка 1 — SSID, строка 2 — пароль (8..63 символов, без кавычек). chmod 600.
set -u
F=$1; FIFO=$(dirname "$0")/console.in
S=$(sed -n 1p "$F"); P=$(sed -n 2p "$F")
[ -n "$S" ] && [ ${#P} -ge 8 ] && [ ${#P} -le 63 ] || { echo "файл: нужны 2 строки (ssid, пароль 8..63)"; exit 1; }
H=$(printf '%s' "$S" | od -An -tx1 | tr -d ' \n')
case "$H$P" in *11111*|*22222*) echo "в hex(SSID)/пароле есть 11111 или 22222 — магия ms_uart, слать нельзя"; exit 1;; esac
case "$P" in *\"*|*\\*) echo "в пароле кавычка или backslash — не поддерживаю"; exit 1;; esac
{
  echo 'echo WIFI_SET_begin'
  echo "wpa_cli -i wlan0 set_network 0 ssid $H"
  echo "wpa_cli -i wlan0 set_network 0 psk '\"$P\"'"
  echo "wpa_cli -i wlan0 set_network 0 scan_ssid 1; wpa_cli -i wlan0 enable_network 0; wpa_cli -i wlan0 reassociate"
  echo 'for i in $(seq 1 12); do sleep 5; echo "t=$((i*5))s $(wpa_cli -i wlan0 status | grep -E "^(wpa_state|freq)" | tr "\n" " ")"; ip -4 addr show wlan0 | grep -q inet && break; done'
  echo 'echo WIFI_SET_result; ip -4 addr show wlan0 | grep inet; ip route | head -n 3'
  echo 'echo WIFI_SET_end'
} > "$FIFO"
echo "отправлено; ssid_len=${#S} psk_len=${#P}; смотреть лог по маркерам WIFI_SET_*"
