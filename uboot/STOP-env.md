# STOP-запрос v3: третья запись env U-Boot в NOR (29.09.2026 00:45)

**История.** v1 (с `mmc rescan`, crc32 `b8213e13`) записан 28.09 23:26; v2 (без rescan, с `mmc dev 0`, crc32 `2aa0dde8`) записан
29.09 00:31 (все гейты, `cmp.b` совпал). **Обе версии в автозагрузке падали в сток** (`** No partition table - mmc 0 **` →
`Wrong Image Format` → `norboot`); цепочка отката работает, кирпича нет, камера на стоке.

**Настоящая причина** (логи `uart/stage-nor-env-write-20260928-232454.log`, `…-20260929-003030.log`, сравнение с перехваченными загрузками):
1. Стоковый U-Boot **до bootcmd** сам инициализирует карту (проверка обновления `tf_update.img`: `mmc_core_init` с `RealClk=0 [LS]` → HS 32 МГц,
   MBR и каталог FAT прочитаны, файл не найден — «read file tf_update.img error»).
2. Любая **повторная** инициализация сразу за ней (`mmc dev 0` и `mmc rescan` — обе force-init) в 3 автозагрузках из 5 возвращает мусор
   в блоке 0 → «No partition table». v1: `dev 0` ОК, `rescan` отказ (2/2); v2: `dev 0` отказ (1/1).
3. При перехвате Enter'ом автозагрузка обрывается **до** проверки tf_update → карта в приглашении не инициализирована → все репетиции
   v1/v2 шли от чистой карты и автозагрузку не моделировали (ошибка STOP v2: «`mmc dev 0` читал MBR во всех 4 случаях»).
4. `fatload` на уже инициализированной карте повторную init не делает (U-Boot 2015.01 `mmc_init`: `has_init` → выход; в наших логах
   после `mmc rescan` третьего `mmc_core_init` перед `fatload` нет).

**v3 = `sdboot` без единой mmc-init-команды: сразу `fatload`** — используется инициализация, которую сток уже сделал для tf_update.img.

## Что пишем
| | |
|---|---|
| Смещение | `0x4F000` |
| Размер | `0x1000` (4096 Б, один 4K-сектор EN25QH128A) |
| Что это | блок переменных U-Boot (env): CRC32 + `k=v\0…\0\0`, хвост нули |
| Сейчас в NOR (v2) | sha256 `2e48731d81f4ad7c7affe51ae02a26c03d99a6accd77f969b41ec1b1460c9316`, crc32(4096) `2aa0dde8` |
| Новый блок (v3) | `uboot/mkenv.py` (SDBOOT из uart/stage.py, MMA_SZ=0x1800000): sha256 `eda6b62e6c5875506dcf52a8ef8e6e7ee4472db2ba8b21194751cf51254c7744`, crc32(4096) `18901e20`, занято 1059 Б. Файл `env-new-v3.bin` кладу на p1 как `env-new.bin` после загрузки OpenIPC (tools/p1-put.sh) |
| Разница v3 − v2 | ТОЛЬКО `sdboot`: `mw.l 0x22000000 0 4; fatload mmc 0:1 0x22000000 uImage.ssc325; setenv bootargs ${sdargs}; bootm 0x22000000` (убрано `mmc dev 0; `). `bootcmd`, `norboot`, `sdargs`, `norargs` и 19 стоковых переменных — байт в байт как в v1/v2 |
| Стоковый блок (откат) | sha256 `8e912e76f338410689e514bf91c8bdcc97bd8c3b1bc574ab40adb68226056e27`, crc32 `6c1674b6` — `env-old.bin` на p1 |

## Репетиция перед записью (RAM, NOR не трогает) — на этот раз состояние карты как в автозагрузке
1. Этап `2a-p4-env3` (камера на стоке, файла v3 на p1 ещё нет): `fatload mmc 0:1 0x22200000 tf_update.img` = ровно стоковая проверка
   (init #1 + поиск в FAT → «Unable to read file»), затем команды SDBOOT построчно из той же константы: `mw.l` → `fatload uImage.ssc325`
   (ожидаю `bytes read`, иначе ABORT — остаюсь в U-Boot, добираю через FIFO) → `setenv bootargs ${sdargs}` (из env v2 в NOR) → `bootm`.
   **Критерий v3:** в логе между двумя `fatload` НЕТ `mmc_core_init` (всего один за перехват). Есть → v3 не годится, не пишем.
2. Этап `2a-p4-env` после `tools/p1-put.sh env-new-v3.bin` (по `#stage` + `reboot -f`): `fatload env-new.bin` (первая mmc-команда = init #1)
   → `crc32 = 18901e20` → `env import -c` → `printenv sdboot` = `mw.l …` → `run sdboot` → ядро → SSH → CAM_UP. Тот же критерий по логу.
Оговорка: набор построчно медленнее автозагрузки (секунды вместо мс), но повторной init нет вообще, тайминг ни на что не влияет.
Настоящая приёмка — холодный старт после записи.

## Что может сломаться и почему не кирпич
Без изменений против v1/v2 (тот же сектор, те же команды, тот же 4K-путь `sf erase` — research/uboot-env-notes.md 21:23):
- Пишется только сектор `0x4F000`; хвост U-Boot в том же 64K-блоке не трогается. IPL/U-Boot/kernel/rootfs не пишутся ни одной командой этапа.
- Худшее — битый env → default env (`bootdelay=0`, `baudrate=115200`, без bootcmd) → приглашение U-Boot по UART, лечится `sf write` блока через stage.py.
- Промежуточный отказ (после `sf erase`, до `sf write`): сектор FF → default env → приглашение; дописываю `sf write` через `uart/console.in`, потом `#passive`, `reset`.
- Программатора нет; этап туда, где он нужен, не пишет. Три идентичных дампа `spi/original-0{1,2,3}.bin` есть.
- Если v3 тоже не загрузит карту: `norboot` → сток (проверено трижды). Дальше остаются либо загрузка с помощью stage.py на Pi
  (не «без Pi»), либо разбор стокового U-Boot глубже (дизассемблер: где именно ставится `has_init`).

## Команды (U-Boot по UART через stage.py, после «да»)
Этап `nor-env-write` в `uart/stage.py`: те же команды, что 23:26 и 00:31, после КАЖДОЙ проверяется ответ; нет ожидаемого → `ABORT`.
Гейты v3 (дефолты в stage.py: `ENV_OLD_CRC=2aa0dde8`, `ENV_NEW_CRC=18901e20`):
`SF: Detected` → `Read: OK` → `==> 2aa0dde8` (в NOR v2; иначе ABORT) → `4096 bytes read` → `==> 18901e20` (файл с p1 = этот STOP) →
`Erased: OK` → `Written: OK` → `Read: OK` → `==> 18901e20` → `were the same` → `reset` → stage.py пассивен (приёмка автозагрузки).
Запуск — только владелец, через `!`, после «да»:
```
cd ~/mjsxj05cm-research; for p in $(pgrep -f "stage.py"); do [ "$p" != "$$" ] && kill $p; done; NOR_WRITE=yes STAGE_WAIT=86400 nohup python3 uart/stage.py nor-env-write > /dev/null 2>&1 &
```
затем я: `python3 uart/camssh.py 'reboot -f'` → stage.py ловит U-Boot → этап → `reset` → U-Boot грузит карту сам.
```
sf probe 0
sf read 0x22200000 0x4F000 0x1000
crc32 0x22200000 0x1000            # ожидаем 2aa0dde8 (v2)
mmc dev 0; mmc rescan              # построчно, карта после перехвата чистая — работает (3/3)
fatload mmc 0:1 0x22100000 env-new.bin
crc32 0x22100000 0x1000            # ожидаем 18901e20
sf erase 0x4F000 0x1000
sf write 0x22100000 0x4F000 0x1000
sf read 0x22300000 0x4F000 0x1000
crc32 0x22300000 0x1000            # 18901e20
cmp.b 0x22100000 0x22300000 0x1000 # Total of 4096 bytes were the same
```

## Откат
- Мягкий: вынуть карту → `norboot` → сток (без карты/с нечитаемой картой камера = сток, проверено трижды).
- Полный: `fatload mmc 0:1 0x22100000 env-old.bin` (на p1, sha256 8e912e76…) → те же `sf erase`/`sf write` → crc32 `6c1674b6`,
  вручную через `uart/console.in` (или stage.py с `ENV_OLD_CRC=18901e20 ENV_NEW_CRC=6c1674b6` и файлом env-old.bin как env-new.bin).

## Приёмка «грузится без Pi»
1. После `reset` stage.py пассивен: в логе ожидаю `bytes read in` → `Starting kernel` → `INIT4_START` → `SSH_READY_ip` → `CAM_UP_done`.
2. Холодный старт: владелец дёргает питание → то же самое. Это и есть приёмка.
3. Карту вынуть, питание → сток поднимается (`norboot`), карту вернуть. Владелец останавливает stage.py.
