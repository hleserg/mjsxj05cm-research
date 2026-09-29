# HANDOFF — камера MJSXJ05CM, состояние на 29.09.2026 03:00 (стоп: владелец перебирает малинку)

## Где мы
- **Камера на СТОКЕ** (4.3.9_0445, 192.168.1.53, SSH нет), карта в камере. В NOR лежит **env v3** (crc32 `18901e20`,
  bootcmd=`run sdboot; run norboot`). Каждое включение: sdboot пробует карту → падает → norboot → сток. Кирпича нет,
  откат = вынуть карту (norboot) или `env-old.bin` с p1 (crc32 `6c1674b6`). Питание камере дёргать можно свободно.
- **Причина трёх падений автозагрузки НАЙДЕНА** (DECISIONS 02:31 + 02:52, дизасм стокового U-Boot): перед `run_command_list(bootcmd)`
  сток включает MMU + D-кэш (0x23e01038) и I-кэш (0x23e00ff8), после — выключает; перехват Enter'ом этот блок пропускает.
  В приглашении кэш выключен → репетиции по UART проходят; в автозагрузке включён → DMA-чтение карты без инвалидации → блок 0 = нули
  («bad MBR 0x0000» / «No partition table») → `Wrong Image Format` → norboot.
- **Лечение (кандидат v4):** `sdboot=dcache off; mw.l 0x22000000 0 4; fatload mmc 0:1 0x22000000 uImage.ssc325; setenv bootargs ${sdargs}; bootm 0x22000000`.
  Одно слово `dcache off;` в начале. Пишется ТОЛЬКО после эксперимента ниже, нового STOP (uboot/STOP-env.md → v4) и явного «да».

## 03:03 ЭКСПЕРИМЕНТ ВЫПОЛНЕН (DECISIONS 03:03): 13/13 проб без кэша ОК; K0 — с D-кэшем DMA-данные CPU не видит (00 00); K1 (`dcache on` + fatload = автозагрузка) — мусорная FAT-цепочка, U-Boot завис на чтении карты. Механизм доказан → v4 = `dcache off;` в начале sdboot. K2 не выполнилась (нет приглашения). Камера в U-Boot гоняет карту: питание → сток. Раздел ниже — история, что было запланировано:

## (выполнено) эксперимент `2a-p4-sdtest`
Этап готов в `uart/stage.py` (коммиты a01f2a5, 1c49b30), критерии заранее в DECISIONS 02:42/02:52. Не запускался (владелец остановился 02:57).
1. На малинке после перезагрузки (владелец, через `!`):
   `cd ~/mjsxj05cm-research; for p in $(pgrep -f "stage.py"); do [ "$p" != "$$" ] && kill $p; done; STAGE_WAIT=86400 nohup python3 uart/stage.py 2a-p4-sdtest > /dev/null 2>&1 &`
2. Монитор на свежий `uart/stage-2a-p4-sdtest-*.log` (фильтр в HANDOFF-строке 02:41: `grep -aE` по `IPL|bytes read in|bad MBR|Invalid partition|224001fe|dcache|Unknown command|ABORT|INIT4_START|SSH_READY_ip|CAM_UP_done`, маска MAC/ssid/psk).
3. Владелец дёргает питание камеры → stage.py ловит U-Boot → ~25 проб (~3 мин) → в конце SDBOOT построчно → OpenIPC (INIT4_START → SSH_READY → CAM_UP_done).
4. Чтение лога (`rtk proxy grep -an`): по каждой пробе `bytes read` = OK, `bad MBR|Invalid partition|Unable` = отказ.
   - **K1** (`dcache on; fatload tf; fatload uImage`) = точная автозагрузка → жду ОТКАЗ. **K2** (`… dcache off; fatload uImage`) → жду `bytes read`.
   - **K0** `md.b 0x224001fe 2`: `00 00` при dcache on, потом `55 aa` после off → некогерентность доказана.
   - Все A-пробы (без dcache) должны проходить. `sleep` — скорее «Unknown command» (в help его нет).
5. Если K1 падает, K2 проходит: STOP v4 (`uboot/STOP-env.md`: гейты `ENV_OLD_CRC=18901e20` → новый crc; `uboot/mkenv.py` с `dcache off; ` в SDBOOT;
   `env-new-v4.bin` на p1 через `tools/p1-put.sh` когда OpenIPC поднят) → AskUserQuestion «да» → владелец через `!`:
   `NOR_WRITE=yes ENV_OLD_CRC=18901e20 ENV_NEW_CRC=<v4> STAGE_WAIT=86400 nohup python3 uart/stage.py nor-env-write …` → `reboot -f` → приёмка холодным стартом.
   Если K1 тоже проходит — механизм не воспроизведён, v4 не писать; глубже в дизасм (что ещё меняет автозагрузка) или загрузка с помощью Pi.

## Следующая сессия (порядок)
1. Владелец через `!`: перевзвод `STAGE_WAIT=86400 nohup python3 uart/stage.py 2a-p4-env3` (RAM-загрузка OpenIPC как 00:55) → `reboot` камеры → OpenIPC.
2. В `uart/stage.py` SDBOOT = `dcache off; mw.l …` (один префикс); `python3 uboot/mkenv.py` → `uboot/env-new-v4.bin` (gitignored) → crc32 → `tools/p1-put.sh uboot/env-new-v4.bin`.
3. Репетиция v4 в RAM: `#stage 2a-p4-env` через FIFO (`env import -c` блока с p1 → `run sdboot`), `reboot -f` → ожидаю bytes read → INIT4. Это заменяет K2.
4. STOP v4 в uboot/STOP-env.md (гейты `ENV_OLD_CRC=18901e20`, `ENV_NEW_CRC=<v4>`), AskUserQuestion → «да» → владелец `NOR_WRITE=yes ENV_OLD_CRC=18901e20 ENV_NEW_CRC=<v4> … stage.py nor-env-write`.
5. Приёмка холодным стартом (ниже).

## После рабочего env (приёмка)
Холодный старт → INIT4/SSH/CAM_UP без Pi; карта вынута → сток; карта обратно. stage.py остановить. Потом: отмашка владельцу (HA-поток,
Onvifer автообнаружение, Frigate Face Library — «посмотри в камеру»), раздел p4 (данные) на карте (владелец «конечно да», план сначала),
STATUS.md, FULL-CONTROL-ACCEPTANCE.md.

## Что теряется при перезагрузке малинки
- stage.py, монитор UART, кроны сессии — умирают; камера при этом безопасна (сток).
- Scratchpad `/tmp/claude-1000/-home-hleserg-xiaomi360/cbe78943-…/scratchpad/` (ub.dis, uboot.bin, disasm.py, env-new-v*.bin, data-own/) — в /tmp,
  скопировать мне классификатор запретил. Всё воспроизводимо: uboot.bin = `spi/original-01.bin` со смещения U-Boot (research/uboot-env-notes.md),
  дизасм — `arm-none-eabi-objdump -D -b binary -m arm --adjust-vma=0x23E00000`, env-блоки — `uboot/mkenv.py`. Если хочется сохранить —
  владелец сам: `cp -a /tmp/claude-1000/-home-hleserg-xiaomi360/*/scratchpad ~/mjsxj05cm-research/research/disasm/scratchpad-20260929` (папка в .gitignore).

## Правила, которые нельзя забыть
Секреты (SSID/PSK/MAC/root/ONVIF-пароль) не печатать; любая запись в NOR — только владелец через `!` после STOP + «да»; stage.py запускает/убивает
только владелец через `!`; один UART — не запускать два stage.py; `tf_update.img` на карте не создавать; majestic не рестартовать (MMA).
Полный список — в верхней части этого репо: DECISIONS.md, STATUS.md, uboot/STOP-env.md.
