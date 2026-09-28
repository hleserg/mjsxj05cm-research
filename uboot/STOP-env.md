# STOP-запрос v2: повторная запись env U-Boot в NOR (29.09.2026 00:20)

**История.** v1 этого блока записан 28.09 23:26 (единственная запись во flash за проект, crc32 `b8213e13`, верифицирована `cmp.b`).
Результат: и тёплый `reset` (23:3x), и холодный старт (владелец «дернул» ~00:00) **ушли в сток** — цепочка `sdboot → norboot`
отработала (кирпича нет, сток грузится), но карту U-Boot при автозагрузке не прочитал. Причина найдена в логе
`uart/stage-nor-env-write-20260928-232454.log` (boot 2 и 3, одинаково): в `sdboot` v1 `mmc rescan` идёт сразу за `mmc dev 0`
(одна строка, без паузы) → драйвер шлёт CMD_6-проверку (0x00FFFFF1), но **не шлёт переключение в HS** (0x80FFFFF1) → карта
остаётся `20000000 [DS]` → CMD_17 блока 0 → `** No partition table - mmc 0 **` → `Wrong Image Format` → `norboot`.
С паузой между командами (stage.py набирает построчно, лог 214152) тот же `mmc rescan` держит HS. `mmc dev 0` сам
инициализирует карту (HS 32 МГц) и читает MBR в обеих неудачных загрузках; сток так и грузит `tf_update.img`: init → fatload.
`sleep`/`test`/`if` в стоковом U-Boot нет — задержку вставить нечем, значит `mmc rescan` просто убираем.

## Что пишем
| | |
|---|---|
| Смещение | `0x4F000` |
| Размер | `0x1000` (4096 Б, один 4K-сектор EN25QH128A) |
| Что это | блок переменных U-Boot (env): CRC32 + `k=v\0…\0\0`, хвост нули |
| Сейчас в NOR (v1) | sha256 `41aba33b2f72bcaa433a05459b703809e3a9b500e81b5f4051731410aeb9d440`, crc32(4096) `b8213e13` |
| Новый блок (v2) | `uboot/mkenv.py` (SDBOOT из uart/stage.py, MMA_SZ=0x1800000): sha256 `2e48731d81f4ad7c7affe51ae02a26c03d99a6accd77f969b41ec1b1460c9316`, crc32(4096) `2aa0dde8`, занято 1070 Б. Файл `env-new.bin` кладу на p1 карты после загрузки OpenIPC (перезаписывает v1) |
| Разница v2 − v1 | ТОЛЬКО `sdboot`: `mmc dev 0; mw.l 0x22000000 0 4; fatload mmc 0:1 0x22000000 uImage.ssc325; setenv bootargs ${sdargs}; bootm 0x22000000` (убран `mmc rescan; `). `bootcmd`, `norboot`, `sdargs`, `norargs` и 19 стоковых переменных (MAC, стоковый `bootargs`) — байт в байт как в v1 |
| Стоковый блок (откат) | sha256 `8e912e76f338410689e514bf91c8bdcc97bd8c3b1bc574ab40adb68226056e27`, crc32 `6c1674b6` — `env-old.bin` на p1 |

## Репетиция перед записью (RAM, NOR не трогает) — этап `2a-p4-env`
Одной строкой, как в автозагрузке: `mmc dev 0; mmc rescan; fatls mmc 0:1` (ожидаю тот же отказ карты — подтверждение механизма),
затем `mmc dev 0; fatls mmc 0:1` (ожидаю листинг, иначе ABORT — гипотеза неверна, запись не предлагаю). Потом `fatload env-new.bin` →
`crc32` = `2aa0dde8` → `env import -c` → `printenv sdboot` (без rescan) → `run sdboot` (не `bootcmd`: при неудаче остаюсь в U-Boot,
добираю через `uart/console.in`, а не уезжаю в сток без SSH). Оговорка: это прокси — 4-я инициализация карты за сессию, а не 2-я, как в
автозагрузке; настоящая приёмка — холодный старт после записи.

## Что может сломаться и почему не кирпич
Без изменений против v1 (тот же сектор, те же команды, тот же путь `sf erase` 4K — research/uboot-env-notes.md 21:23):
- Пишется только сектор `0x4F000`; хвост U-Boot в том же 64K-блоке не трогается. IPL/U-Boot/kernel/rootfs не пишутся ни одной командой этапа.
- Худшее — битый env → default env (`bootdelay=0`, `baudrate=115200`, без bootcmd) → приглашение U-Boot по UART, лечится `sf write` старого/нового блока через stage.py.
- Промежуточный отказ (после `sf erase`, до `sf write`): сектор FF → default env → приглашение U-Boot; дописываю `sf write` через `uart/console.in`, потом `#passive` и `reset`.
- Программатора нет; этот этап туда, где он нужен, не пишет. Три идентичных дампа `spi/original-0{1,2,3}.bin` есть.
- Если v2 тоже не загрузит карту: цепочка снова уйдёт в `norboot` = сток (проверено дважды), камера не теряется.

## Команды (U-Boot по UART через stage.py, после «да»)
Этап `nor-env-write` в `uart/stage.py`: шлёт ровно эти команды и после КАЖДОЙ проверяет ответ; нет ожидаемого → `ABORT`, дальше ничего
не шлётся, камера остаётся в U-Boot. Гейты v2 (дефолты `ENV_OLD_CRC=b8213e13`, `ENV_NEW_CRC=2aa0dde8` в stage.py):
`SF: Detected` → `Read: OK` → `==> b8213e13` (в NOR v1; иначе ABORT) → `4096 bytes read` → `==> 2aa0dde8` (файл с p1 = этот STOP) →
`Erased: OK` → `Written: OK` → `Read: OK` → `==> 2aa0dde8` → `were the same` → `reset` → stage.py пассивен (Enter не шлёт = приёмка автозагрузки).
Запуск — только владелец, через `!`, после «да»:
```
cd ~/mjsxj05cm-research; for p in $(pgrep -f "stage.py"); do [ "$p" != "$$" ] && kill $p; done; NOR_WRITE=yes STAGE_WAIT=86400 nohup python3 uart/stage.py nor-env-write > /dev/null 2>&1 &
```
затем я: `python3 uart/camssh.py 'reboot -f'` → stage.py ловит U-Boot → этап → `reset` → U-Boot грузит карту сам.
```
sf probe 0
sf read 0x22200000 0x4F000 0x1000
crc32 0x22200000 0x1000            # ожидаем b8213e13 (v1)
mmc dev 0; mmc rescan              # построчно, с паузой — так rescan работает
fatload mmc 0:1 0x22100000 env-new.bin
crc32 0x22100000 0x1000            # ожидаем 2aa0dde8
sf erase 0x4F000 0x1000
sf write 0x22100000 0x4F000 0x1000
sf read 0x22300000 0x4F000 0x1000
crc32 0x22300000 0x1000            # 2aa0dde8
cmp.b 0x22100000 0x22300000 0x1000 # Total of 4096 bytes were the same
```

## Откат
- Мягкий: вынуть карту → `norboot` → сток (и так работает: без карты/с нечитаемой картой камера = сток).
- Полный: `fatload mmc 0:1 0x22100000 env-old.bin` (на p1, sha256 8e912e76…) → те же `sf erase`/`sf write` → crc32 `6c1674b6`,
  вручную через `uart/console.in` (`ENV_NEW_CRC=6c1674b6` для гейтов, если через stage.py).

## Приёмка «грузится без Pi»
1. После `reset` stage.py пассивен: в логе ожидаю `bytes read in` → `Starting kernel` → `INIT4_START` → `SSH_READY_ip` → `CAM_UP_done`.
2. Холодный старт: владелец дёргает питание → то же самое. Это и есть приёмка (тёплый reset после записи — только предварительно).
3. Карту вынуть, питание → сток поднимается (`norboot`), карту вернуть. Владелец останавливает stage.py.

## Итог репетиции (00:29, RAM, NOR не тронут)
Все гейты пройдены: `4096 bytes read` → `==> 2aa0dde8` → `env import -c` → `printenv sdboot` без rescan → `run sdboot` → ядро с карты → OpenIPC (SSH, ONVIF admin).
Оговорка: шаг A (одной строкой с `mmc rescan`) на этот раз НЕ отказал (HS-переключение прошло) — отказ rescan воспроизводится только в автозагрузке (2/2), при наборе — 0/2.
Это гонка, а не детерминизм; v2 убирает rescan целиком, так что автозагрузка = `mmc dev 0` (читал MBR во всех 4 случаях) + fatload, как у стока с tf_update.img.
Если v2 всё же не загрузит карту — `norboot` → сток (проверено дважды), откат env-old.bin по UART.
