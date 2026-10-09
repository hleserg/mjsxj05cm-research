# STOP-запрос: OpenIPC в SPI-NOR (09.10.2026, черновик 15:42 — подаётся ТОЛЬКО после репетиций ниже)

Вторая серия записей во флеш после env v4 (STOP-env.md, 29.09 15:51). Пишутся три области: rootfs, kernel, env.
Запускает **только владелец** после явного «да». Я к stage.py не прикасаюсь.

## История
- 28–29.09: env v1..v4 в NOR; v4 (crc32 `25f375ed`) грузит карту с 29.09 15:51, приёмка 16:42. С тех пор NOR **не писался**.
- 03.10: аптайм-тест пройден, надзор автономный (cron cam-health + uart-logger).
- 09.10: «делай nor» + «оба способа прошивки в git, в README как сделать какой, автоматизировано». Готово всё, кроме самой записи.
- Факты для решения (советник 09.10): (1) ядро OpenIPC делит NOR на 7 разделов cmdlinepart из своей CMDLINE_EXTEND — `mtdparts` в bootargs
  и `saveenv` не нужны; (2) из Linux камеры NOR **писать нельзя**: `[FSP] Unknown flash type (0xFF,0xFF,0xFF)` — ядро не опознало EN25QH128A,
  чтение совпадает с дампом, запись не проверена → пишет только U-Boot (`SF: Detected nor0 … 16 MiB`); (3) kernel/rootfs в NOR до сих пор
  сток (crc32 `a5447ccc` / `c41c56d0` = mtd-kernel.bin / mtd-rootfs.bin из своих дампов) — гейты «до стирания» действительны.

## Что пишем (порядок: rootfs → kernel → env)
| область | смещение | размер | сейчас в NOR (сток), crc32 | новое, файл на p1 | crc32 нового | sha256 нового |
|---|---|---|---|---|---|---|
| rootfs (mtd2) | `0x250000` | `0x760000` | `c41c56d0` | `rootfs-nor.pad.bin` = rootfs-nor.squashfs (4 923 392 Б, 63 %) + 0xFF | `1b23dd8c` | `2ea3b9f53daa02a7f3fb908b06bec698d84a4c17d92235ca901d0692a83aceb7` |
| kernel (mtd1) | `0x50000` | `0x200000` | `a5447ccc` | `kernel.pad.bin` = uImage.ssc325 (тот же, что грузится с карты с 28.09) + 0xFF | `6b5590f4` | `2c340c0b678e336825e12ecb58dc8e9c9177f619de8ebecb761b4187ca996228` |
| env | `0x4F000` | `0x1000` | `25f375ed` (v4) | `env-new.bin` = `uboot/mkenv.py uboot/env-new-v5.bin --nor=openipc` (v5) | `818e914a` | `b4fbbb3949e9a545293dc526520786ec4e5a7305698d0ac769ba55cb080c3395` |

- **rootfs-nor.squashfs** (`make-rootfs-nor.sh`): rootfs OpenIPC ipc017 как на p3 карты (make-sd8.sh) + `init4.sh` v8 + `/wpa.conf` + `/shadow4`
  **+ `/opt/p1/`** (autorun/cam-up/ptz/demo.sh, onvif-password.txt) — чтобы камера поднималась **без карты**. Файл секретный (SSID/PSK, хеш root,
  пароль ONVIF) → в git нет, только crc/sha в `CRC.txt`. Цена: смена Wi-Fi/пароля = пересборка + новая запись rootfs по STOP.
- **env v5 − v4 = только `norargs`**: было стоковое `bootargs` (init=/linuxrc), стало `console=ttyS0,115200 root=/dev/mtdblock2 rootwait rootfstype=squashfs init=/init4.sh LX_MEM=0x3fc6000 mma_heap=mma_heap_name0,miu=0,sz=0x1800000`. `bootcmd`, `sdboot`, `norboot`, `sdargs`,
  стоковые переменные — байт в байт как в v4 (mkenv.py без `--nor` по-прежнему выдаёт v4, crc `25f375ed`, проверено 09.10).
- init4.sh v8 сам понимает, откуда загружен (`root=` в /proc/cmdline): hostname `mjsxj05cm-nor` / `mjsxj05cm-sd`, autorun с `/tmp/p1` если карта
  есть, иначе из `/opt/p1`. Одно и то же ядро и один init для обоих режимов.
- `root=/dev/mtdblock2` проверен на живой камере 09.10 под ядром OpenIPC (`/proc/mtd`: mtd0 boot 320k, mtd1 kernel 2048k, mtd2 rootfs 7552k,
  mtd3 rootfs_data) — разметка зашита в ядро (mtdparts в /proc/cmdline), от env не зависит.
- **DATA (mtd3, `0x9B0000`, стоковый jffs2) не трогаем**: OpenIPC из NOR работает RAM-only, как и с карты (записи — только на p4 карты).

## Навсегда запрещено (ни одной командой этапов)
`0x0–0x4F000` (IPL/U-Boot), `0x9B0000` DATA, `0xFE0000` config, `0xFF0000` factory (MAC, калибровки, ключи); `saveenv`, `sysupgrade`, `fw_setenv`,
любая запись из Linux камеры. selftest stage.py проверяет: `sf erase` только по `0x250000`, `0x50000`, `0x4F000` и ровно в этом порядке.

## Что меняется в «откате»
**Вынутая карта больше не = сток.** После записи без карты грузится OpenIPC из NOR. Сток = этап `nor-stock-restore` (те же шаги, файлы
`mtd-rootfs.bin` / `mtd-kernel.bin` / `env-old.bin` с p1 = свои дампы, crc `c41c56d0` / `a5447ccc` / `6c1674b6`), тоже только владельцем.
Переключение режимов — без записи: `tools/boot-mode.sh sd|nor|status` (переименовывает uImage.ssc325 на p1).

## Репетиции перед записью (RAM, NOR не трогает) — обе через stage.py, перевзводит владелец
1. **`nor-openipc-check`** — все гейты и загрузка всех трёх файлов с p1 в RAM с crc32, без erase/write (`--dry-run` показывает ровно
   первые 15 команд этапа записи). Ожидаю: `SF: Detected`, три `Read: OK` + crc стока, три `bytes read` + crc из таблицы.
2. **`2a-p2`** — тот же rootfs-nor.squashfs, положенный `dd` на p2 карты (8 МиБ, старый stage-2, воспроизводим из sd-stage2.img), грузится
   ядром с p1 с `root=/dev/mmcblk0p2`. Ожидаю `INIT4_START` → `SSH_READY` → `CAM_UP`, autorun из /tmp/p1 (карта есть). Доказывает, что
   содержимое NOR-корня (init4 v8, /opt/p1, модули, dropbear) живое. Проверка без карты невозможна до записи — поэтому /opt/p1 проверяю
   руками: `ls -l /opt/p1`, `sh -n /opt/p1/*.sh`.
Запуск каждой: `systemctl --user stop uart-logger` → владелец: `STAGE_WAIT=86400 nohup python3 uart/stage.py <этап> > /dev/null 2>&1 &` →
я: `timeout 12 python3 uart/camssh.py "sync; reboot -f"` (с согласия) → лог `uart/stage-<этап>-*.log` → после: `systemctl --user start uart-logger`.

## Что может сломаться и почему не кирпич
**Карта остаётся вставленной всю запись и после неё.** Env v4 в NOR до самого последнего `sf write` (4 КиБ, доли секунды), поэтому любое
промежуточное состояние kernel/rootfs грузится с карты как сейчас — настоящий откат «на полпути» это `sdboot`, а не `nor-stock-restore`.
Таймауты erase/write 1800 с (стирание 0x760000 по 4К-секторам — до ~10 мин по даташиту); по таймауту stage.py шлёт ABORT и больше ничего,
U-Boot свою команду доделывает.
- Любой ABORT до последнего `sf write` env: в NOR env v4, `bootcmd=run sdboot; run norboot` → карта грузится как сейчас. Стёртые/битые
  kernel/rootfs в NOR не мешают: sdboot не читает NOR. Повтор этапа после ABORT проходит гейты (принимают сток | 0xFF | новое).
- ABORT после `sf erase 0x4F000` до `sf write`: default env, приглашение U-Boot по UART (bootdelay) — дописать `sf write` через
  `uart/console.in`, как в STOP-env.md; crc стёртого сектора `f154670a`.
- Обрыв питания/UART посреди `sf write` rootfs (минуты): область частично записана, crc ≠ любому гейту, повтор упрётся в гейт 1. Порядок:
  камера грузится с карты (env v4 цел) → я читаю фактический crc из лога ABORT (строка `crc32 ... ==> xxxxxxxx`) → владелец перезапускает
  тот же этап с `EXTRA_OLD_CRC=xxxxxxxx` (через запятую, если областей несколько) — гейт примет его, erase/write пройдут заново целиком.
- Новый rootfs в NOR не поднимается без карты (Wi-Fi, модуль, pid): карта с uImage → режим SD, чиним, пересобираем, пишем rootfs заново.
- Пока идёт запись (≈10–15 мин с fatload 7 МиБ и cmp.b), cam-health пришлёт «НЕ ОТВЕЧАЕТ» — это ожидаемо.
- U-Boot (0x0–0x4F000) не пишется ни одной командой → приглашение по UART остаётся всегда; программатор не нужен.

## Команды (после «да»)
```bash
cd ~/mjsxj05cm-research && pkill -f "^python3 uart/stage.py"; systemctl --user stop uart-logger   # один читатель ttyAMA2
NOR_WRITE=yes STAGE_WAIT=86400 nohup python3 uart/stage.py nor-openipc-write > /dev/null 2>&1 &
# я, с согласия: timeout 12 python3 uart/camssh.py "sync; reboot -f"
tail -f uart/stage-nor-openipc-write-*.log       # ждём 3× "were the same" → reset → автозагрузка с карты (uImage на p1 есть)
```
Переменные-гейты по умолчанию берутся из `CRC.txt` (`ENV_OLD_CRC=25f375ed`, `ENV_NEW_CRC=818e914a`, `ROOTFS_NOR_CRC=1b23dd8c`);
`EXTRA_OLD_CRC=…` — только для повтора после обрыва (см. выше).

## Проверено перед «да» (09.10)
- Репетиция 1 `nor-openipc-check` (16:40): гейты NOR=сток, файлы p1=CRC.txt, fatload 7.4 MiB — ok. Репетиция 2 `2a-p2` (16:46): образ NOR загружен с p2 карты — ssh, majestic, dropbear, RTSP/ONVIF живы, init4.sh = репо.
- Цепочка `sdboot падает → norboot` реально отрабатывала 29.09 (v4: «Wrong Image Format» → `sf read 0x50000 0x200000` → kernel cmdline = norargs). v5 меняет только текст `norargs`.
- `kernel.pad.bin` = `uImage.ssc325` + паддинг (`cmp -n 1977576`). `stage.py selftest` проверяет смещения ровно `0x250000, 0x50000, 0x4F000`.
- **Без карты:** init4.sh v8 при неудаче `mount p1` печатает «карты нет» и берёт autorun.sh из `/opt/p1` внутри squashfs — ssh + majestic + autorun есть, данных p4 нет.
- **Время:** реально 5–15 мин; потолок ≈ 30 мин (три записи с таймаутом 1800 с каждая). Сигнал «готово» — три строки «were the same» в логе, затем `reset` и загрузка с карты.
- cam-health на паузе до конца записи: пока «да» не сказано, камера без мониторинга в Telegram.

## Откат
`NOR_WRITE=yes STAGE_WAIT=86400 nohup python3 uart/stage.py nor-stock-restore > /dev/null 2>&1 &` — rootfs → kernel → env стоковые из p1.
Или ничего не делать: с картой камера грузит OpenIPC с карты, что бы ни лежало в NOR.

## Приёмка
1. ✅ 20:34 После `reset`: автозагрузка с карты, `tools/boot-mode.sh status` → `mjsxj05cm-sd`, root=/dev/mmcblk0p3.
2. ✅ 21:33 `tools/boot-mode.sh nor` → владелец перезагрузил → `status`: `mjsxj05cm-nor`, root=/dev/mtdblock2 (mtdparts из ядра), /init4.sh md5 4fc97a6f = репо, p1 смонтирован (autorun с карты), p4 пишет, majestic/dropbear, RTSP/ONVIF 401 (= auth), postboot ок. Камера оставлена в NOR-режиме с картой как данными.
3. ⏳ Физически без карты (владелец вынимает) → камера в сети как `mjsxj05cm-nor`, autorun из /opt/p1, RTSP идёт.
4. ⏳ (по желанию) `tools/boot-mode.sh sd` → перезагрузка → снова `mjsxj05cm-sd`; механизм тот же, что в п.2, обратный. Оба режима задокументированы в README («Два режима»).

## ЗАПИСАНО
**09.10 ≈20:30–20:34 (MSK), лог `uart/stage-nor-openipc-write-20261009-165513.log`** (взведён 16:55, камеру перезагрузил владелец).
Гейты до стирания: rootfs `c41c56d0`, kernel `a5447ccc`, env `25f375ed` (сток/v4), RAM-образы `1b23dd8c`/`6b5590f4`/`818e914a` — всё как в CRC.txt.
Записано и прочитано назад (U-Boot `sf read` + `crc32` + cmp.b):

| область | смещение | размер | Erased/Written | crc readback | «were the same» |
|---|---|---|---|---|---|
| rootfs | 0x250000 | 7733248 | OK/OK | 1b23dd8c | 7733248 |
| kernel | 0x50000 | 2097152 | OK/OK | 6b5590f4 | 2097152 |
| env v5 | 0x4F000 | 4096 | OK/OK | 818e914a | 4096 |

После `reset` загрузчик по env v5 выбрал `sdboot` (uImage на p1): камера поднялась с карты p3 (`mjsxj05cm-sd`), ssh, majestic, dropbear, RTSP/ONVIF 401 (= auth), postboot ок 20:34. Откат через карту работает. Приёмка режима NOR — следующий шаг (`tools/boot-mode.sh nor` + reboot).
