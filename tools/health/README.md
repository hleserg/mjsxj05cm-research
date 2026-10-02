# Автономный надзор за камерой (не зависит от сессии агента)

## cam-health.sh — проверка каждые 10 минут из cron

Что делает: ping → ssh (`uart/camssh.py`) → uptime, majestic, watchdog, `mma fail`, заполнение p4 → fps в Frigate (bigpc).
Одна строка на проход в `~/.local/state/cam-health/health.log`. Сообщение в Telegram только при смене
состояния: не отвечает / снова отвечает / перезагрузилась (uptime упал) / новое предупреждение
(majestic нет, watchdog не active, mma fail > 0, p4 ≥ 95%).

Установка (уже сделано 03.10): строка в `crontab -e`
```
*/10 * * * * /home/hleserg/mjsxj05cm-research/tools/health/cam-health.sh # cam-health
```
Telegram: создать `~/.config/cam-health/env` (chmod 600):
```
TG_BOT_TOKEN=123456:ABC...
TG_CHAT_ID=123456789
```
Без этого файла скрипт только пишет лог. Посмотреть: `tail ~/.local/state/cam-health/health.log`.
Снять: удалить строку `# cam-health` из `crontab -e`.

## uart-logger.service — UART-консоль камеры в файл, переживает ребут Pi

Пишет `/dev/ttyAMA2` в `uart/boot-console.log` (gitignored), перезапускается сам.
Установка (уже сделано 03.10):
```
ln -sf ~/mjsxj05cm-research/tools/health/uart-logger.service ~/.config/systemd/user/
systemctl --user daemon-reload && systemctl --user enable --now uart-logger
```
**`/dev/ttyAMA2` появляется только после `sudo dtoverlay uart2-pi5`** — после каждого ребута Pi. Чтобы навсегда:
```
echo 'dtoverlay=uart2-pi5' | sudo tee -a /boot/firmware/config.txt
```
**Один читатель UART:** перед `uart/stage.py` или `uart/dump.py` — `systemctl --user stop uart-logger`, после — `start`.
