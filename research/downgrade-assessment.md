# Оценка khmyznikov/mjsxj05cm-firmware-downgrade

Проверено 2026-09-22 по `main` (HEAD `ab75b433082e`); локальные копии README и трёх Python-скриптов лежат рядом. GitHub API: создан 2026-03-12, последний push 2026-03-18, шесть commits, одна ветка, ноль forks, одна open issue `#1 Original maintainers`. Issue не содержит независимого отчёта о загрузке hybrid. Проект относится к авторской MJSXJ05CM; работы на нашей `4.3.9_0445` никто не проверял.

`unpacker_spi.py` читает MXPT с `0x20000`, шаг записи `0x88`. `unpacker_recovery.py` вырезает старые kernel/SquashFS/JFFS2 с жёсткими размерами образа `3.5.1_0052`. Его SHA-256 `c787…034a` полностью совпал с официальным Xiaomi recovery.

| SPI offset | Размер | Источник hybrid |
|---:|---:|---|
| `0x000000` | 192 KiB | свой boot: IPL/MXPT |
| `0x030000` | 128 KiB | свой U-Boot/environment |
| `0x050000` | 2 MiB | recovery 0052 kernel |
| `0x250000` | 7.375 MiB | recovery 0052 SquashFS |
| `0x9B0000` | 6.1875 MiB | recovery 0052 JFFS2 data |
| `0xFE0000` | 64 KiB | свой config |
| `0xFF0000` | 64 KiB | свой factory/MAC/calibration |

Идея технически состоятельна **при совпадении фактической MXPT-карты и аппаратного маркера**: родные загрузочные и уникальные разделы сохраняются, Linux-разделы заменяются старым I6/LX409 образом. Старый Linux может загрузиться с новым U-Boot, но это нельзя доказать только offsets и CRC. У нас нет собственного SPI dump и boot log, поэтому hybrid для нашей камеры **не собирался**.

Ограничения кода: `packer.py` жёстко задаёт offsets, допускает отсутствующие разделы (FF + предупреждение, но в конце пишет «ready to flash»), не сверяет три независимых dump и не проверяет полную MXPT/calibration. CRC и magic не заменяют boot test. Публичный `downgraded_firmware.bin` содержит чужие config/factory; записывать его нельзя.

Rollback возможен только после трёх совпадающих собственных read-only SPI dump (`READ1.bin`, `READ2.bin`, `READ3.bin`) с SHA-256 и сохранёнными boot/U-Boot/config/factory/MAC/calibration. Чип, напряжение и способ ISP/выпайки определяются по плате. До явного разрешения ни SD recovery, ни SPI write не выполняются.

Источник: [репозиторий и скрипты](https://github.com/khmyznikov/mjsxj05cm-firmware-downgrade). [Отчёты 4PDA](https://4pda.to/forum/index.php?showtopic=1016850&st=2760) об SD recovery противоречивы и не подтверждают гарантированный downgrade `0445→0426→0052`.
