# STOP-запрос v4: четвёртая запись env U-Boot в NOR (29.09.2026, черновик 13:2x — подаётся ТОЛЬКО после репетиции 2a-p4-env4)

**История.** v1 (`mmc rescan`, crc32 `b8213e13`) 28.09 23:26; v2 (`mmc dev 0`, `2aa0dde8`) 29.09 00:31; v3 (только `fatload`, `18901e20`)
29.09 02:31 — все гейты, `cmp.b` совпал. **Все три в автозагрузке падали в сток** (`norboot`); цепочка отката работает, кирпича нет.
Сейчас в NOR v3: каждое включение = попытка sdboot → отказ карты → norboot → сток.

**Настоящая причина (доказана 29.09 02:52–03:03, DECISIONS):**
1. Дизасм стокового U-Boot (`uboot.bin` из `spi/original-01.bin`, база 0x23E00000): перед `run_command_list(bootcmd)` вызывается
   `dcache_enable` (0x23e01038: таблица страниц, MMU + D-кэш) и `icache_enable`, после — `dcache_disable` (0x23e010a4) и `icache_disable`.
   Перехват Enter'ом обрывает автозагрузку **до** этого блока → в приглашении кэш ВЫКЛЮЧЕН (`dcache` → «Data (writethrough) Cache is OFF»).
2. Эксперимент `2a-p4-sdtest` (лог `uart/stage-2a-p4-sdtest-20260929-025652.log`): с кэшем OFF `fatload uImage.ssc325` 13/13 ОК
   (все варианты тайминга); K0: `dcache on; mmc read блок 0` → «OK», но CPU видит нули вместо `55 aa`; K1: `dcache on; fatload tf_update.img;
   fatload uImage` = состояние автозагрузки → мусорная FAT-цепочка, U-Boot зациклился на чтении карты (ABORT, ничего персистентного).
   Вывод: DMA-чтения mmc при включённом D-кэше невидимы CPU (нет invalidate) — v1/v2/v3 падали именно поэтому, а не из-за тайминга.

**v4 = `sdboot` начинается с `dcache off`** — та же операция (flush + сброс MMU/D-бита), которую сток сам делает после bootcmd,
только раньше; RAM-only, ничего персистентного. После неё U-Boot в том состоянии, в котором fatload прошёл 13/13.
`norboot` после неё тоже идёт с выключенным кэшем — `sf read` ядра из NOR будет медленнее (секунды), на приёмке без карты засечь время.

## Что пишем
| | |
|---|---|
| Смещение | `0x4F000` |
| Размер | `0x1000` (4096 Б, один сектор; `sf erase` = 4K-путь, хвост U-Boot в 64K-блоке не трогается — research/uboot-env-notes.md) |
| Что это | блок переменных U-Boot (env): CRC32 + `k=v\0…\0\0`, хвост нули |
| Сейчас в NOR (v3) | sha256 `eda6b62e6c5875506dcf52a8ef8e6e7ee4472db2ba8b21194751cf51254c7744`, crc32(4096) `18901e20` |
| Новый блок (v4) | `uboot/mkenv.py` → `uboot/env-new-v4.bin`: sha256 `76f919731d6cc0634e725488dd4494e702bb0da829fc2ad4da2acbc021c2a1d9`, crc32(4096) `25f375ed`, занято 1071 Б. На p1 как `env-new.bin` (tools/p1-put.sh) |
| Разница v4 − v3 | ТОЛЬКО `sdboot`: `dcache off; mw.l 0x22000000 0 4; fatload mmc 0:1 0x22000000 uImage.ssc325; setenv bootargs ${sdargs}; bootm 0x22000000` (добавлено `dcache off; `). `bootcmd`, `norboot`, `sdargs`, `norargs` и стоковые переменные — байт в байт как в v3 |
| Стоковый блок (откат) | sha256 `8e912e76f338410689e514bf91c8bdcc97bd8c3b1bc574ab40adb68226056e27`, crc32 `6c1674b6` — `env-old.bin` на p1 |

## Репетиция перед записью (RAM, NOR не трогает) — на этот раз состояние КЭША как в автозагрузке
Этап `2a-p4-env4` (stage.py, владелец перевзводит через `!`, затем `reboot -f` камеры):
`fatload env-new.bin` (init #1) → `crc32 = 25f375ed` → `env import -c` → `printenv sdboot` = `dcache off; mw.l …` → **`dcache on`** →
`run sdboot`. Ожидаю `bytes read` → `Starting kernel` → `INIT4_START` → `SSH_READY` → `CAM_UP`.
Без `dcache on` репетиция ничего не доказывает (в приглашении кэш и так OFF — так «проходили» v1..v3).
Отказ = нет `bytes read` (ABORT, остаюсь в U-Boot, `dcache off` через FIFO) → v4 не пишем, дальше дизасм fatload/mmc.

**Итог репетиции: ВЫПОЛНЕНА 29.09 14:48, УСПЕХ.** Лог `uart/stage-2a-p4-env4-20260929-144726.log` (UART теперь uart2-pi5 → `/dev/ttyAMA2`, pin 29/7): `4096 bytes read` → `CRC32 … ==> 25f375ed` → `env import` → `printenv sdboot` = `dcache off; mw.l …` → `SigmaStar # dcache on` → `SigmaStar # run sdboot` → `1977576 bytes read in 283 ms` → `Starting kernel` → `INIT4_START` → `SSH_READY_ip` (14:49). Т.е. с включённым D-кэшем (как в автобуте) `sdboot` v4 читает uImage и грузит OpenIPC. Сравнение: v3 в той же ситуации давало сток (три автобута). Единственная непроверенная разница с реальным автобутом — v4 запускался из промпта, а не из bootcmd; bootcmd = `run sdboot; run norboot` уже в NOR (v3) и отрабатывает (доказано тремя падениями в norboot). Контрольный опыт с кэшем ON без `dcache off` есть: `uart/stage-2a-p4-sdtest-20260929-025652.log`, строка 11878 после `tr '\r' '\n'`: `dcache on; fatload … uImage.ssc325` → `reading tf_update.img` → бесконечный цикл CMD_18 (14906 чтений, `bytes read` так и не пришло, ABORT). Тот же механизм, что валил автобут v1–v3; v4 его обходит.

## Что может сломаться и почему не кирпич
Без изменений против v1..v3 (тот же сектор, те же команды, тот же 4K-путь `sf erase`):
- Пишется только сектор `0x4F000`; IPL/U-Boot/kernel/rootfs не пишутся ни одной командой этапа.
- Худшее — битый env → default env (`bootdelay=0`, `baudrate=115200`, без bootcmd) → приглашение U-Boot по UART, лечится `sf write` блока через stage.py.
- Промежуточный отказ (после `sf erase`, до `sf write`): сектор FF → default env → приглашение; дописываю `sf write` через `uart/console.in`, потом `#passive`, `reset`.
- Если запись прервалась ПОСЛЕ `sf erase` (обрыв UART/Pi/питания): в NOR сектор 0xFF, crc32 стёртого сектора = **f154670a**; U-Boot грузит default env (bootdelay/baudrate) и даёт приглашение — кирпича нет. Повтор: `sudo dtoverlay uart2-pi5` (если Pi перезагружался), затем тот же запуск с `ENV_OLD_CRC=f154670a` (гейт «до erase» тогда ждёт crc стёртого сектора). Восстановление ≤10 мин.
- Если прервалось ПОСЛЕ `sf write` до `reset`: env v4 уже в NOR, проверка `sf read`+`crc32` покажет 25f375ed; просто передёрнуть питание камеры — это и есть приёмка автобута.
- `dcache off` в bootcmd: если бы команда отсутствовала — `Unknown command` → sdboot всё равно идёт дальше (run не прерывается), fatload как в v3 → norboot → сток. Команда есть (список `help`, K0/K1 её выполняли).
- Программатора нет; этап туда, где он нужен, не пишет. Три идентичных дампа `spi/original-0{1,2,3}.bin` есть.
- Если v4 тоже не загрузит карту: `norboot` → сток (проверено трижды, теперь с кэшем OFF — медленнее, но тот же путь).

## Команды (U-Boot по UART через stage.py, после «да»)
Этап `nor-env-write` в `uart/stage.py`: те же команды, что 23:26, 00:31 и 02:31, после КАЖДОЙ проверяется ответ; нет ожидаемого → `ABORT`.
Гейты v4 (дефолты в stage.py: `ENV_OLD_CRC=18901e20`, `ENV_NEW_CRC=25f375ed`):
`SF: Detected` → `Read: OK` → `==> 18901e20` (в NOR v3; иначе ABORT) → `4096 bytes read` → `==> 25f375ed` (файл с p1 = этот STOP) →
`Erased: OK` → `Written: OK` → `Read: OK` → `==> 25f375ed` → `were the same` → `reset` → stage.py пассивен (приёмка автозагрузки).
Запуск — только владелец, через `!`, после «да»:
```
cd ~/mjsxj05cm-research; pkill -f "^python3 uart/stage.py"; sleep 1; NOR_WRITE=yes ENV_OLD_CRC=18901e20 ENV_NEW_CRC=25f375ed STAGE_WAIT=86400 nohup python3 uart/stage.py nor-env-write > /dev/null 2>&1 & sleep 2; pgrep -a python3; ls -l /proc/$(pgrep -f "^python3 uart/stage.py")/fd | grep tty
```
затем я: `python3 uart/camssh.py 'reboot -f'` → stage.py ловит U-Boot → этап → `reset` → U-Boot грузит карту сам.
```
sf probe 0
sf read 0x22200000 0x4F000 0x1000
crc32 0x22200000 0x1000            # ожидаем 18901e20 (v3)
mmc dev 0; mmc rescan              # построчно, карта после перехвата чистая — работает (4/4)
fatload mmc 0:1 0x22100000 env-new.bin
crc32 0x22100000 0x1000            # ожидаем 25f375ed
sf erase 0x4F000 0x1000
sf write 0x22100000 0x4F000 0x1000
sf read 0x22300000 0x4F000 0x1000
crc32 0x22300000 0x1000            # 25f375ed
cmp.b 0x22100000 0x22300000 0x1000 # Total of 4096 bytes were the same
```

## Откат
- Мягкий: вынуть карту → `norboot` → сток (без карты/с нечитаемой картой камера = сток, проверено трижды).
- Полный: `fatload mmc 0:1 0x22100000 env-old.bin` (на p1, sha256 8e912e76…) → те же `sf erase`/`sf write` → crc32 `6c1674b6`,
  вручную через `uart/console.in` (или stage.py с `ENV_OLD_CRC=25f375ed ENV_NEW_CRC=6c1674b6` и файлом env-old.bin как env-new.bin).

## Приёмка «грузится без Pi»
1. После `reset` stage.py пассивен: в логе ожидаю `bytes read in` → `Starting kernel` → `INIT4_START` → `SSH_READY_ip` → `CAM_UP_done`.
2. Холодный старт: владелец дёргает питание → то же самое. Это и есть приёмка.
3. Карту вынуть, питание → сток поднимается (`norboot`, засечь время `sf read`), карту вернуть. Владелец останавливает stage.py.
