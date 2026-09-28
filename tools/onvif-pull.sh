#!/bin/bash
# Проверка событий движения majestic через ONVIF PullPoint (только curl, без python-onvif).
#   tools/onvif-pull.sh [секунд опроса, дефолт 60]
# Пароль root берётся из p4/secret/root-password.txt и маскируется в выводе. Камера: 192.168.1.53.
set -u
cd "$(dirname "$0")/.."
PW=$(cat firmware/openipc-ipc017-20260926/p4/secret/root-password.txt)
CAM=${CAM:-192.168.1.53}; SECS=${1:-60}
EV=http://$CAM/onvif/event_service
soap() { curl -s -m 10 -u "root:$PW" -H 'Content-Type: application/soap+xml' -d "$1" "$2" | sed "s/$PW/***/g"; }
env() { echo "<s:Envelope xmlns:s=\"http://www.w3.org/2003/05/soap-envelope\" xmlns:a=\"http://www.w3.org/2005/08/addressing\"><s:Header>${2:-}</s:Header><s:Body>$1</s:Body></s:Envelope>"; }

sub=$(soap "$(env '<tev:CreatePullPointSubscription xmlns:tev="http://www.onvif.org/ver10/events/wsdl"><tev:InitialTerminationTime>PT10M</tev:InitialTerminationTime></tev:CreatePullPointSubscription>')" "$EV")
ADDR=$(grep -o "<[a-z]*:Address>[^<]*" <<<"$sub" | head -1 | sed "s/<[a-z]*:Address>//")
[ -z "$ADDR" ] && { echo "нет адреса подписки:"; echo "$sub" | head -c 800; exit 1; }
echo "подписка: ${ADDR#http://$CAM}"
end=$((SECS + $(date +%s)))
while [ "$(date +%s)" -lt "$end" ]; do
  r=$(soap "$(env '<tev:PullMessages xmlns:tev="http://www.onvif.org/ver10/events/wsdl"><tev:Timeout>PT5S</tev:Timeout><tev:MessageLimit>10</tev:MessageLimit></tev:PullMessages>' "<a:To>$ADDR</a:To>")" "$ADDR")
  # одна строка на сообщение: время, топик, состояние
  grep -o '<wsnt:Topic[^>]*>[^<]*\|UtcTime="[^"]*"\|<tt:SimpleItem Name="[^"]*" Value="[^"]*"' <<<"$r" \
    | sed -E 's/<wsnt:Topic[^>]*>//; s/<tt:SimpleItem Name="([^"]*)" Value="([^"]*)"/\1=\2/' | paste -sd' ' | grep . | sed "s/^/$(date +%H:%M:%S) /"
done
