#!/bin/sh
# cam-health.sh — автономная проверка камеры MJSXJ05CM из cron, без сессии агента.
# Каждый проход: одна строка в ~/.local/state/cam-health/health.log.
# Уведомление в Telegram (если есть ~/.config/cam-health/env с TG_BOT_TOKEN и TG_CHAT_ID)
# только при СМЕНЕ состояния: не отвечает / снова отвечает / перезагрузилась / новое предупреждение.
# Установка и снятие: tools/health/README.md.
set -u
REPO=/home/hleserg/mjsxj05cm-research
CAM=${CAM_HOST:-192.168.1.53}
ST=${CAM_HEALTH_STATE:-$HOME/.local/state/cam-health}; mkdir -p "$ST"
PY=/home/hleserg/.espressif/python_env/idf5.5_py3.13_env/bin/python3   # единственный python3 с paramiko (для uart/camssh.py)
[ -r "$HOME/.config/cam-health/env" ] && . "$HOME/.config/cam-health/env"
[ -e "$ST/pause" ] && exit 0   # 09.10: touch $ST/pause — тишина на время прошивки/репетиций, rm — снова следим
exec 9>"$ST/lock"; flock -n 9 || exit 0
now=$(date '+%d.%m %H:%M')
prev_up=0; prev_state=unknown; prev_warn=
[ -r "$ST/last.env" ] && . "$ST/last.env"

notify() {
  [ -n "${TG_BOT_TOKEN:-}" ] && [ -n "${TG_CHAT_ID:-}" ] || return 0
  curl -s -m 15 -o /dev/null "https://api.telegram.org/bot$TG_BOT_TOKEN/sendMessage" \
    --data-urlencode "chat_id=$TG_CHAT_ID" --data-urlencode "text=Камера $now: $1"
}
fmt_up() { echo "$(( $1 / 86400 ))д$(( $1 % 86400 / 3600 ))ч$(( $1 % 3600 / 60 ))м"; }

out=$(ping -c 1 -W 2 "$CAM" >/dev/null 2>&1 && cd "$REPO" && timeout 40 "$PY" uart/camssh.py \
  "cut -d. -f1 /proc/uptime; pidof majestic >/dev/null && echo 1 || echo 0; cat /sys/class/watchdog/watchdog0/state; dmesg | grep -c 'mma fail'; df /tmp/p4 | awk 'END{print \$5}'" 2>/dev/null)
up=$(echo "$out" | sed -n 1p); maj=$(echo "$out" | sed -n 2p); wd=$(echo "$out" | sed -n 3p)
mma=$(echo "$out" | sed -n 4p); p4=$(echo "$out" | sed -n 5p)
if [ "$up" -ge 0 ] 2>/dev/null; then state=ok; else state=down; up=0; fi

fps=$(ssh -o BatchMode=yes -o ConnectTimeout=8 bigpc "wsl -d Ubuntu -e bash -c \"docker exec frigate curl -s -m 10 http://127.0.0.1:5000/api/stats\"" 2>/dev/null \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["cameras"]["mjsxj05cm"]["camera_fps"])' 2>/dev/null || echo '?')

event=
if [ "$state" = down ]; then
  [ "$prev_state" = ok ] && event="НЕ ОТВЕЧАЕТ (ping/ssh), было uptime $(fmt_up "$prev_up")"
else
  [ "$prev_state" = down ] && event="снова отвечает, uptime $(fmt_up "$up")"
  [ "$prev_state" = ok ] && [ "$up" -lt "$prev_up" ] && event="ПЕРЕЗАГРУЗИЛАСЬ: uptime $(fmt_up "$up"), было $(fmt_up "$prev_up")"
fi
warn=
[ "$state" = ok ] && {
  [ "$maj" = 1 ] || warn="$warn majestic-нет"
  [ "$wd" = active ] || warn="$warn watchdog=$wd"
  [ "$mma" = 0 ] || warn="$warn mma-fail=$mma"
  [ "${p4%\%}" -lt 95 ] 2>/dev/null || warn="$warn p4=$p4"
  [ -n "$warn" ] && [ "$warn" != "$prev_warn" ] && event="${event:+$event; }предупреждение:$warn"
}

line="$now $state up=$(fmt_up "$up") maj=${maj:-?} wd=${wd:-?} mma=${mma:-?} p4=${p4:-?} fps=$fps${event:+ | $event}"
echo "$line" >> "$ST/health.log"
[ -n "$event" ] && notify "$event (up=$(fmt_up "$up") maj=${maj:-?} wd=${wd:-?} mma=${mma:-?} p4=${p4:-?} fps=$fps)"
printf 'prev_up=%s\nprev_state=%s\nprev_warn="%s"\n' "$up" "$state" "$warn" > "$ST/last.env"
