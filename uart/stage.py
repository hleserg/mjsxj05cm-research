#!/usr/bin/env python3
"""Этапы 1–2 плана (DECISIONS.md, 27.09): U-Boot из RAM, во flash ничего не пишется.

  ./stage.py --dry-run 1        показать команды этапа
  ./stage.py 1                  остановить U-Boot зажатым Enter, послать команды этапа,
                                дальше держать порт: лог uart/stage-<этап>-<время>.log,
                                команды в Linux — через FIFO uart/console.in:
                                    echo 'cat /proc/mtd' > uart/console.in
  Этапы: 1 (сток, init=/bin/sh), 2pre (только проверки SD/U-Boot, остаётся в U-Boot),
         2a-nor (ядро OpenIPC с SD + стоковый rootfs, init=/bin/sh),
         2a-p3 (OpenIPC + сток с SD p3, init=/recon.sh), 2a-p4 (OpenIPC с SD p3, init=/init4.sh: Wi-Fi+SSH),
         2a (OpenIPC с SD, init=/bin/sh — раскладка NOR), 2b (OpenIPC с SD полностью).
  Самопроверка: ./stage.py --selftest
"""
import os, re, sys, time
from pathlib import Path

HERE = Path(__file__).parent
FIFO = HERE / "console.in"
# 28.09 20:40: размер MMA-кучи из окружения (MMA_SZ=0x1800000 — эксперимент против "vpe0-out0-1 mma fail"; сток = 0x1400000).
# 28.09 21:50: heap-тест пройден (mma fail 0, idle 83%) → дефолт 0x1800000; MMA_SZ=0x1400000 = откат на сток.
MEM = f"LX_MEM=0x3fc6000 mma_heap=mma_heap_name0,miu=0,sz={os.environ.get('MMA_SZ', '0x1800000')}"
# mtdparts OpenIPC c ro у всех разделов — страховка от записи в NOR из userland.
# Если ядро дописывает свою cmdline (CMDLINE_EXTEND), победит его строка — проверить /proc/mtd.
RO = ("mtdparts=NOR_FLASH:320k(boot)ro,2048k(kernel)ro,7552k(rootfs)ro,"
      "6272k(rootfs_data)ro,64k(env)ro,64k(config)ro,64k(factory)ro")
SD_PRE = [
    "help mmc", "help fatload", "mmc dev 0", "mmc rescan", "mmc info", "fatls mmc 0:1",
    "fatload mmc 0:1 0x22000000 uImage.ssc325",
    "crc32 0x22000000 0x1E2CE8",          # ожидается b2bd4848 (CRC.txt)
]
STAGES = {
    "1": [
        "sf probe 0",
        "sf read 0x22000000 0x50000 0x200000",
        "crc32 0x22000000 0x200000",      # ожидается a5447ccc (mtd-kernel.bin)
        f"setenv bootargs console=ttyS0,115200 root=/dev/mtdblock2 rootfstype=squashfs ro init=/bin/sh {MEM}",
        "bootm 0x22000000",
    ],
    "2pre": SD_PRE,
    # Ядро OpenIPC с SD + стоковый rootfs из NOR: стоковый userland под ядром, у которого работает приём на консоли
    # (стоковое ядро на ввод по UART не отвечает — этап 1, 28.09).
    "2a-nor": SD_PRE + [
        f"setenv bootargs console=ttyS0,115200 root=/dev/mtdblock2 rootfstype=squashfs ro init=/bin/sh {MEM}",
        "bootm 0x22000000",
    ],
    # Приём по UART мёртв под ОБОИМИ ядрами (28.09), поэтому команды не шлём: init=/recon.sh на p3 карты
    # (стоковый rootfs + скрипт, sd-stage3.img) сам печатает разведку в TX и в конце exec /bin/sh.
    "2a-p3": SD_PRE + [
        f"setenv bootargs console=ttyS0,115200 root=/dev/mmcblk0p3 rootwait rootfstype=squashfs init=/recon.sh {MEM}",
        "bootm 0x22000000",
    ],
    # sd-stage4.img: p3 = rootfs OpenIPC + /init4.sh (Wi-Fi + dropbear с карты, потом окна RX-эксперимента,
    # строки по маркерам шлёт uart/win4.sh). NOR не трогаем.
    "2a-p4": SD_PRE + [
        f"setenv bootargs console=ttyS0,115200 root=/dev/mmcblk0p3 rootwait rootfstype=squashfs init=/init4.sh {MEM}",
        "bootm 0x22000000",
    ],
    # Бисект ENOENT для init=/init4.sh (28.09 02:4x): тот же p3, но init=/bin/sh — грузится ли вообще busybox OpenIPC (musl).
    "2a-p4-sh": SD_PRE + [
        f"setenv bootargs console=ttyS0,115200 root=/dev/mmcblk0p3 rootwait rootfstype=squashfs init=/bin/sh {MEM}",
        "bootm 0x22000000",
    ],
    # Ядро 4.9 не находит /init4.sh (файл дописан mksquashfs-append; init=/bin/sh с того же p3 работает).
    # Обход: интерактивный ash выполняет файл из $ENV; неизвестные VAR=x из cmdline ядро отдаёт init как окружение.
    "2a-p4-env": SD_PRE + [
        f"setenv bootargs console=ttyS0,115200 root=/dev/mmcblk0p3 rootwait rootfstype=squashfs init=/bin/sh ENV=/init4.sh {MEM}",
        "bootm 0x22000000",
    ],
    # То же, но скрипт аргументом: слова cmdline без '=' после init= ядро отдаёт init как argv → sh /init4.sh.
    # Если lookup файла сломан и из userland, ash напечатает "can't open '/init4.sh'" (диагностика), затем panic → сток.
    "2a-p4-argv": SD_PRE + [
        f"setenv bootargs console=ttyS0,115200 root=/dev/mmcblk0p3 rootwait rootfstype=squashfs init=/bin/sh /init4.sh {MEM}",
        "bootm 0x22000000",
    ],
    # 28.09 21:30: репетиция будущего env (uboot/mkenv.py) в RAM — те же переменные, что пойдут в NOR, но через setenv без saveenv.
    # Проверяет парсер стокового U-Boot (без hush: `run`, ${}, mw.l). Гонять ОТДЕЛЬНЫМ ребутом после heap-теста.
    # (этап "2a-p4-env" добавляется ниже, после SD_ARGS/SDBOOT)
    "2a": SD_PRE + [
        f"setenv bootargs console=ttyS0,115200 root=/dev/mmcblk0p2 rootwait rootfstype=squashfs init=/bin/sh {MEM}",
        "bootm 0x22000000",
    ],
    "2b": SD_PRE + [
        f"setenv bootargs console=ttyS0,115200 root=/dev/mmcblk0p2 rootwait rootfstype=squashfs init=/linuxrc {MEM} {RO}",
        "bootm 0x22000000",
    ],
}
SD_ARGS = STAGES["2a-p4"][-2].split(" ", 2)[2]   # bootargs карты — единый источник для mkenv.py и этапа 2a-p4-env
# 29.09 00:40: v3 — БЕЗ `mmc dev 0` (и без rescan). v1 (rescan) и v2 (dev 0) записаны в NOR (23:26, 00:31) и оба в автозагрузке
# падали в сток. Причина (логи 232454/003030): стоковый U-Boot ДО bootcmd сам инициализирует карту (проверка tf_update.img:
# mmc_core_init с RealClk=0 [LS] → HS 32 МГц → FAT прочитан), а любая ПОВТОРНАЯ инициализация в bootcmd сразу за ней
# (`mmc dev 0`/`mmc rescan` = force init) в 3 случаях из 5 возвращает мусор в блоке 0 → «No partition table» → norboot.
# При перехвате Enter'ом автозагрузка обрывается ДО проверки tf_update → карта в приглашении НЕ инициализирована →
# все репетиции v1/v2 шли от чистой карты и автозагрузку не моделировали. fatload на уже инициализированной карте
# повторную init не делает (has_init; в логах после rescan третьего mmc_core_init нет) → v3 = только fatload.
# 29.09 03:03 (v4): `dcache off` первым. Дизасм (DECISIONS 02:52): сток перед run_command_list(bootcmd) включает MMU+D-кэш
# (0x23e01038) и выключает после (0x23e010a4); Enter-перехват этот блок пропускает → все репетиции v1..v3 шли с кэшем OFF
# (13/13 fatload OK), а автозагрузка — с ON (K0: mmc read под кэшем невидим CPU; K1: fatload → мусорная FAT-цепочка).
# `dcache off` = тот же flush+bic, что делает сам сток после bootcmd; RAM-only, не персистентно.
SDBOOT = "dcache off; mw.l 0x22000000 0 4; fatload mmc 0:1 0x22000000 uImage.ssc325; setenv bootargs ${sdargs}; bootm 0x22000000"
NORBOOT = "sf probe 0; sf read 0x22000000 ${sf_kernel_start} ${sf_kernel_size}; setenv bootargs ${norargs}; bootm 0x22000000"
# 09.10: bootargs для OpenIPC из NOR (env v5, uboot/mkenv.py --nor=openipc): те же, что у карты, только корень = mtd2 (rootfs @0x250000).
# init=/init4.sh тот же файл (v8 сам понимает, карта он или NOR, по root= в /proc/cmdline). DATA (mtd3) не трогаем.
NOR_ARGS = SD_ARGS.replace("root=/dev/mmcblk0p3", "root=/dev/mtdblock2")
assert NOR_ARGS != SD_ARGS
CRC_TXT = HERE.parent / "firmware/openipc-ipc017-20260926/CRC.txt"   # file | bytes | crc32 | sha256 — единый источник гейтов


def crc_txt(name, default="????????"):
    for l in CRC_TXT.read_text().splitlines() if CRC_TXT.exists() else []:
        f = [x.strip() for x in l.split("|")]
        if len(f) >= 3 and f[0].split(" ")[0] == name:
            return f[2]
    return default
# Репетиция env в RAM (advisor 21:30): грузим с p1 ТОТ ЖЕ 4K-блок, что пойдёт в NOR (uboot/mkenv.py → env-new.bin на p1),
# U-Boot сам проверяет CRC (`env import -c`). NOR не трогаем (env import — RAM).
# MAXARGS стокового U-Boot = 32 (cli_simple_parse_line @0x23e09438) — без запаса для setenv длинных строк не обойтись, поэтому файл.
# 29.09 00:40 (v3): `fatload env-new.bin` — ПЕРВАЯ mmc-команда (= init #1, как проверка tf_update в автозагрузке), затем
# `run sdboot` (НЕ bootcmd: при неудаче остаёмся в U-Boot, добираю через FIFO). Между двумя fatload в логе НЕ должно быть
# mmc_core_init — это и есть проверка v3 (grep по логу после загрузки). Приёмка всё равно = холодный старт после записи.
# CRC32(4096) блоков env для гейтов: OLD = что сейчас в NOR (v2 записан 00:31 → 2aa0dde8; v1 b8213e13; сток 6c1674b6),
# NEW = env-new.bin v3 с p1 (uboot/mkenv.py). Обе можно переопределить переменными окружения.
ENV_OLD_CRC, ENV_NEW_CRC = os.environ.get("ENV_OLD_CRC", "25f375ed"), os.environ.get("ENV_NEW_CRC", crc_txt("env-v5.bin"))   # 09.10: v4 в NOR с 29.09 15:51; NEW = v5
STAGES["2a-p4-env"] = [
    ("fatload mmc 0:1 0x22100000 env-new.bin", r"4096 bytes read"),   # init #1 (карта чистая после перехвата)
    ("crc32 0x22100000 0x1000", "==> " + ENV_NEW_CRC),
    "env import -c 0x22100000 0x1000", "printenv bootcmd", "printenv norboot",
    ("printenv sdboot", r"sdboot=dcache off; mw\.l 0x22000000"),     # v4: dcache off первым, ни dev 0, ни rescan
    "run sdboot",                                                     # fatload без повторной init → bootm
]
# 29.09 03:07 (advisor): репетиция v4 = состояние автозагрузки, т.е. `dcache on` ПЕРЕД `run sdboot` (сам sdboot его гасит).
# Из приглашения без `dcache on` v4 ничего не доказывает (там кэш и так OFF). Ожидаю `bytes read` → Starting kernel → INIT4.
STAGES["2a-p4-env4"] = STAGES["2a-p4-env"][:-1] + ["dcache on", "run sdboot"]
# 09.10: репетиция содержимого NOR-корня без записи NOR: rootfs-nor.squashfs положен dd на p2 карты (8 МиБ, старый stage-2),
# грузим ядро с p1 и корень с p2 — тот же init4.sh v8, /opt/p1 и т.д. Hostname будет mjsxj05cm-sd (root= не mtdblock) — это ожидаемо.
STAGES["2a-p2"] = SD_PRE + ["setenv bootargs " + SD_ARGS.replace("root=/dev/mmcblk0p3", "root=/dev/mmcblk0p2"), "bootm 0x22000000"]
# 29.09 00:40: репетиция v3 БЕЗ файла на p1 (камера на стоке, env-new-v3.bin ещё не залит): сначала fatload несуществующего
# tf_update.img = ровно то, что делает сток до bootcmd (init #1 + поиск в FAT, «Unable to read file»), затем команды SDBOOT
# построчно (из той же константы). ${sdargs} берётся из env v2 в NOR. После загрузки: grep mmc_core_init в логе — должен быть ОДИН.
STAGES["2a-p4-env3"] = [("fatload mmc 0:1 0x22200000 tf_update.img", r"Unable to read file")] + [
    (c, r"bytes read" if c.startswith("fatload") else None) for c in SDBOOT.split("; ")]
# 29.09 02:31: env v3 ЗАПИСАН (лог stage-nor-env-write-20260929-022832.log), автозагрузка снова в сток, но ПО-НОВОМУ:
# повторной mmc_core_init нет, а первое чтение блока 0 сразу (мс) после «read file tf_update.img error.» вернуло нули
# («bad MBR sector signature 0x0000» → «Invalid partition 1» → Wrong Image Format → norboot). В репетициях между теми же
# двумя fatload проходили секунды — MBR читался. Эксперимент в RAM (NOR не трогает, только чтение карты): одна строка =
# тайминг автозагрузки; варианты «что между» — ничего / холостое чтение блока 0 / задержка crc32 (~32 МБ) / задержка md
# (вывод в UART ~1 с). Результат считаю по логу: «bytes read» = ОК, «bad MBR|Invalid partition|Unable» = отказ. В конце
# грузим OpenIPC (SDBOOT построчно), чтобы камера была доступна по SSH.
_TF, _UI = "fatload mmc 0:1 0x22200000 tf_update.img", "fatload mmc 0:1 0x22000000 uImage.ssc325"
# Advisor 02:40: против «тайминга» — в v2 полная re-init (такты 300k→32M, десятки мс) всё равно дала нули; нули (не мусор) +
# ОК при наборе руками → похоже на состояние U-Boot после стоковой проверки tf_update (её мой fatload не воспроизводит), самый
# дешёвый кандидат — включённый dcache при DMA без invalidate. Пробы с dcache — ПОСЛЕДНИМИ (не портить ранние), `dcache on/off`
# = только кэш CPU, RAM, ничего постоянного (решение записано в DECISIONS 02:4x). Только A0 = «init → tf fail → uImage», A1..A3 —
# карта уже инициализирована; читать A0 отдельно. Все A прошли → мой fatload не воспроизводит стоковый триггер, B/C/D о v4 не говорят.
STAGES["2a-p4-sdtest"] = (   # `echo` в help стока нет — пробы различаю по тексту команды в логе (порядок: A×4, D×3, B×3, C×3, S, K…)
    ["dcache"] +                                                                  # состояние кэша в приглашении (только запрос)
    [f"{_TF}; {_UI}"] * 4 +                                                       # A: как в автозагрузке (мс между fatload)
    [f"{_TF}; mmc read 0x22400000 0 1; md.b 0x224001fe 2; {_UI}"] * 3 +           # D: холостое чтение блока 0 (+ видно 55aa/0000)
    [f"{_TF}; crc32 0x20000000 0x2000000; {_UI}"] * 3 +                           # B: задержка ~0.3 с без UART
    [f"{_TF}; md.l 0x22200000 0x400; {_UI}"] * 3 +                                # C: задержка ~1 с (вывод в UART)
    [f"{_TF}; sleep 1; {_UI}"] +                                                  # S: help в логе неполон (printenv есть) — вдруг sleep есть
    ["dcache on; mw.b 0x22400000 0 0x200; mmc read 0x22400000 0 1; md.b 0x224001fe 2; dcache off; md.b 0x224001fe 2"] +  # K0: когерентность
    [f"dcache on; {_TF}; {_UI}"] * 2 +                                            # K1: с кэшем, как (возможно) в автозагрузке
    [f"dcache on; {_TF}; dcache off; {_UI}"] * 2 +                                # K2: кандидат v4 = `dcache off` перед fatload
    ["dcache off"] +
    [(c, r"bytes read" if c.startswith("fatload") else None) for c in SDBOOT.split("; ")])
# 28.09 22:25: ЕДИНСТВЕННАЯ запись в NOR (uboot/STOP-env.md): 4K env @0x4F000. Запускается ТОЛЬКО владельцем после «да» на STOP:
#   NOR_WRITE=yes STAGE_WAIT=86400 nohup python3 uart/stage.py nor-env-write > /dev/null 2>&1 &
# Без NOR_WRITE=yes этап отклоняется (FORBIDDEN). Каждый шаг (cmd, ожидаемый ответ): нет ответа → ABORT, дальше ничего
# не шлём, камера остаётся в U-Boot (консоль через FIFO). До `sf erase` два гейта: блок в NOR crc32 ENV_OLD_CRC
# и новый файл с p1 crc32 ENV_NEW_CRC (uboot/mkenv.py; 29.09 v3 — см. SDBOOT). После записи: sf read → crc32 → cmp.b, затем `reset` — U-Boot
# перечитывает env из NOR и грузит карту сам; stage.py дальше ПАССИВЕН (Enter не шлёт, только лог + FIFO) = приёмка без Pi.
# U-Boot 2015.01: `sf erase`/`sf write` печатают "Erased: OK"/"Written: OK", `cmp.b` — "were the same" (строки есть в стоковом
# бинарнике, проверено 22:35; Read: OK / CRC32 / bytes read — в логах). После ABORT: доделать через FIFO, потом `echo '#passive' > FIFO`, `echo reset > FIFO`.
WRITE_STAGE = "nor-env-write"
STAGES[WRITE_STAGE] = [
    ("sf probe 0", r"SF: Detected"),
    ("sf read 0x22200000 0x4F000 0x1000", r"Read: OK"),
    ("crc32 0x22200000 0x1000", "==> " + ENV_OLD_CRC),               # в NOR ещё старый блок (иначе уже записано/чужое → ABORT)
    ("mmc dev 0", None), ("mmc rescan", None),
    ("fatload mmc 0:1 0x22100000 env-new.bin", r"4096 bytes read"),
    ("crc32 0x22100000 0x1000", "==> " + ENV_NEW_CRC),               # файл с p1 = тот, что в STOP-запросе
    ("sf erase 0x4F000 0x1000", r"Erased: OK"),
    ("sf write 0x22100000 0x4F000 0x1000", r"Written: OK"),
    ("sf read 0x22300000 0x4F000 0x1000", r"Read: OK"),
    ("crc32 0x22300000 0x1000", "==> " + ENV_NEW_CRC),               # верификация из NOR
    ("cmp.b 0x22100000 0x22300000 0x1000", r"were the same"),
    ("reset", None),
]
RESET = re.compile(rb"(^|\n)IPL[ _]")   # баннер IPL в начале строки = камера сбросилась (после загрузки ядра)
FORBIDDEN = re.compile(r"\b(saveenv|sf\s+(erase|write|update)|erase|update|upgrade|flashcp|nand)\b")

# 09.10: OpenIPC в NOR (uboot/STOP-nor.md). Три области, каждая: файл на p1 → RAM → гейты → erase → write → read → crc32 → cmp.b.
# Порядок rootfs → kernel → env: env (bootcmd=run sdboot; run norboot) переписывается ПОСЛЕДНИМ, так что при ABORT на любом
# шаге камера по-прежнему грузит карту (sdboot), а nor-stock-restore тем же билдером возвращает сток из mtd-*.bin на p1.
# Гейты «старого» состояния принимают сток | стёрто (0xFF) | уже новое — чтобы повторный запуск после ABORT не упёрся в гейт.
# RAM: файл rootfs 0x22000000..0x22760000, его readback 0x22800000; kernel 0x23000000 / 0x23200000; env 0x23400000 / 0x23500000;
# всё ниже U-Boot (0x23E00000). Таймауты 600 с: fatload/sf write 7 МиБ по SPI идут минутами. Никогда: 0x0 (U-Boot), 0x9B0000 (DATA),
# 0xFE0000 (config), 0xFF0000 (factory).
BIG = 600
ERASED = {0x1000: "f154670a", 0x200000: "9a4109e5", 0x760000: "024d6fec"}   # crc32 области из 0xFF (посчитано 09.10)
ROOTFS_NOR_CRC = os.environ.get("ROOTFS_NOR_CRC", crc_txt("rootfs-nor.pad.bin"))
KERNEL_PAD_CRC = crc_txt("kernel.pad.bin")          # 6b5590f4 = uImage.ssc325 + 0xFF до 0x200000
STOCK_ROOTFS_CRC, STOCK_KERNEL_CRC, STOCK_ENV_CRC = crc_txt("mtd-rootfs.bin"), crc_txt("mtd-kernel.bin"), "6c1674b6"
# (имя файла на p1, crc32 файла, смещение NOR, размер, адрес файла в RAM, адрес readback, допустимые crc области до записи)
OPENIPC_REGIONS = [
    ("rootfs-nor.pad.bin", ROOTFS_NOR_CRC, 0x250000, 0x760000, 0x22000000, 0x22800000, (STOCK_ROOTFS_CRC, ERASED[0x760000], ROOTFS_NOR_CRC)),
    ("kernel.pad.bin",     KERNEL_PAD_CRC, 0x50000,  0x200000, 0x23000000, 0x23200000, (STOCK_KERNEL_CRC, ERASED[0x200000], KERNEL_PAD_CRC)),
    ("env-new.bin",        ENV_NEW_CRC,    0x4F000,  0x1000,   0x23400000, 0x23500000, (ENV_OLD_CRC, ERASED[0x1000], ENV_NEW_CRC)),
]
STOCK_REGIONS = [
    ("mtd-rootfs.bin", STOCK_ROOTFS_CRC, 0x250000, 0x760000, 0x22000000, 0x22800000, (ROOTFS_NOR_CRC, ERASED[0x760000], STOCK_ROOTFS_CRC)),
    ("mtd-kernel.bin", STOCK_KERNEL_CRC, 0x50000,  0x200000, 0x23000000, 0x23200000, (KERNEL_PAD_CRC, ERASED[0x200000], STOCK_KERNEL_CRC)),
    ("env-old.bin",    STOCK_ENV_CRC,    0x4F000,  0x1000,   0x23400000, 0x23500000, (ENV_NEW_CRC, ENV_OLD_CRC, ERASED[0x1000], STOCK_ENV_CRC)),
]


def nor_write(regions, write=True):
    cmds = [("sf probe 0", r"SF: Detected")]
    for f, crc, off, size, la, rb, old in regions:                     # гейт 1: NOR в ожидаемом состоянии
        cmds += [(f"sf read 0x{rb:X} 0x{off:X} 0x{size:X}", r"Read: OK", BIG), (f"crc32 0x{rb:X} 0x{size:X}", "==> (" + "|".join(old) + ")")]
    cmds += [("mmc dev 0", None), ("mmc rescan", None)]
    for f, crc, off, size, la, rb, old in regions:                     # гейт 2: файлы с p1 = те, что в STOP (CRC.txt)
        cmds += [(f"fatload mmc 0:1 0x{la:X} {f}", f"{size} bytes read", BIG), (f"crc32 0x{la:X} 0x{size:X}", "==> " + crc)]
    for f, crc, off, size, la, rb, old in (regions if write else []):
        cmds += [(f"sf erase 0x{off:X} 0x{size:X}", r"Erased: OK", BIG), (f"sf write 0x{la:X} 0x{off:X} 0x{size:X}", r"Written: OK", BIG),
                 (f"sf read 0x{rb:X} 0x{off:X} 0x{size:X}", r"Read: OK", BIG), (f"crc32 0x{rb:X} 0x{size:X}", "==> " + crc),
                 (f"cmp.b 0x{la:X} 0x{rb:X} 0x{size:X}", r"were the same", BIG)]
    return cmds + ([("reset", None)] if write else [])


STAGES["nor-openipc-check"] = nor_write(OPENIPC_REGIONS, write=False)   # RAM-only репетиция: гейты + файлы с p1 + crc, без записи
STAGES["nor-openipc-write"] = nor_write(OPENIPC_REGIONS)                # NOR_WRITE=yes, только владелец (STOP-nor.md)
STAGES["nor-stock-restore"] = nor_write(STOCK_REGIONS)                  # возврат стока из mtd-*.bin + env-old.bin с p1
WRITE_STAGES = {WRITE_STAGE, "nor-openipc-write", "nor-stock-restore"}
PROMPT = re.compile(rb"\n([^\r\n#]{1,24})# ")


def prompt_of(buf):
    seen = {}
    for m in PROMPT.finditer(buf):
        seen[m.group(1)] = seen.get(m.group(1), 0) + 1
        if seen[m.group(1)] >= 3:
            return m.group(1) + b"# "
    return None


def norm(c):
    c = c if isinstance(c, tuple) else (c, None)
    return c if len(c) == 3 else (c[0], c[1], 30)   # 09.10: третий элемент — таймаут ожидания приглашения, с (sf/fatload 7 МиБ > 30 с)


def write_allowed(stage, env):
    return stage in WRITE_STAGES and env.get("NOR_WRITE") == "yes"


def selftest():
    assert prompt_of(b"\r\nSigmaStar # \r\nSigmaStar # \r\nSigmaStar # ") == b"SigmaStar # "
    assert prompt_of(b"\r\nSigmaStar # \r\nSigmaStar # ") is None
    for name, cmds in STAGES.items():
        hits = [c for c, _, _ in map(norm, cmds) if FORBIDDEN.search(c)]
        assert bool(hits) == (name in WRITE_STAGES), (name, hits)   # запись только в WRITE_STAGES, и там она есть
    assert not write_allowed(WRITE_STAGE, {}) and not write_allowed("2a-p4", {"NOR_WRITE": "yes"})
    assert all(write_allowed(w, {"NOR_WRITE": "yes"}) for w in WRITE_STAGES)
    for w in ("nor-openipc-write", "nor-stock-restore"):   # порядок записи: rootfs → kernel → env; env последним, чтобы при любом ABORT sdboot остался
        offs = [c.split()[2] for c, _, _ in map(norm, STAGES[w]) if c.startswith("sf erase")]
        assert offs == ["0x250000", "0x50000", "0x4F000"], (w, offs)
        assert not any(c.startswith("sf erase 0x0 ") or "0xFE0000" in c or "0xFF0000" in c or "0x9B0000" in c for c, _, _ in map(norm, STAGES[w]))
    assert [c for c, _, _ in map(norm, STAGES["nor-openipc-check"]) if c.startswith("sf ")] == ["sf probe 0"] + [c for c, _, _ in map(norm, STAGES["nor-openipc-check"]) if c.startswith("sf read")]
    assert "root=/dev/mtdblock2" in NOR_ARGS and "init=/init4.sh" in NOR_ARGS
    assert FORBIDDEN.search("sf update 0x22000000 0x50000 0x200000")
    assert FORBIDDEN.search("saveenv")
    assert not FORBIDDEN.search("sf read 0x22000000 0x50000 0x200000")
    print("selftest ok")


def main(stage):
    import serial
    cmds = [norm(c) for c in STAGES[stage]]
    if not write_allowed(stage, os.environ):
        assert not any(FORBIDDEN.search(c) for c, _, _ in cmds), f"запись в NOR только этапами {sorted(WRITE_STAGES)} с NOR_WRITE=yes"
    port = serial.Serial(os.environ.get("UART_PORT", "/dev/ttyAMA2"), 115200, timeout=0.02)
    out = HERE / time.strftime(f"stage-{stage}-%Y%m%d-%H%M%S.log")
    log, buf = open(out, "wb"), b""
    def say(m):   # 29.09: служебные строки и в stdout, и в лог (владелец запускает с > /dev/null)
        print(m, flush=True); log.write(m.encode() + b"\n"); log.flush()

    def rx():
        nonlocal buf
        d = port.read(4096)
        if d:
            log.write(d); log.flush(); buf += d
            if len(buf) > 1 << 20:   # 28.09: UART-флуд MI ERR ~2 КБ/с — без потолка поиск по buf становится O(n²)
                buf = buf[-65536:]
            sys.stdout.write(d.decode("latin-1")); sys.stdout.flush()

    wait = int(os.environ.get("STAGE_WAIT", "300"))
    if not FIFO.exists():
        os.mkfifo(FIFO)
    fd = os.open(FIFO, os.O_RDONLY | os.O_NONBLOCK)
    passive = False   # после nor-env-write: U-Boot грузит карту сам по env из NOR — Enter не шлём, только лог + FIFO
    while True:   # 28.09: цикл на сброс камеры — после «IPL» в консоли снова ловим U-Boot, иначе сброс = загрузка стока из NOR
        if passive:
            say("\n--- пассивно: env в NOR записан, автозагрузка без Enter; только лог + FIFO")
        else:
            print(f"пишу {out}\nшлю Enter — ВКЛЮЧАЙ КАМЕРУ (жду {wait} с)", flush=True)
            end, prompt = time.time() + wait, None
            while time.time() < end and not prompt:
                port.write(b"\r"); rx()
                prompt = prompt_of(buf[-8192:])
            if not prompt:
                sys.exit("\nU-Boot не остановился")
            time.sleep(0.3); rx()
            for c, expect, tmo in cmds:
                mark = len(buf)
                port.write(c.encode() + b"\r")
                t = time.time() + tmo
                while time.time() < t and buf.rfind(prompt) <= mark + len(c):
                    rx()
                    if c.startswith(("bootm", "run ", "reset")) and (b"Starting kernel" in buf[mark:] or RESET.search(buf[mark:])):
                        break
                if expect and not re.search(expect, buf[mark:].decode("latin-1")):
                    say(f"\n--- ABORT: после `{c}` нет ответа /{expect}/ — дальше ничего не шлю, камера в U-Boot")
                    break
            else:
                passive = stage in WRITE_STAGES
            say(f"\n--- команды этапа {stage} посланы; консоль: echo CMD > {FIFO} ; лог {out}")
        buf = b""
        hooked = False   # постбут-хук: init4.sh напечатал SSH_READY_ip → uart/postboot.sh (autorun.sh с p1 карты по SSH), один раз
        while True:
            rx()
            if not hooked and b"SSH_READY_ip" in buf:
                hooked = True
                import subprocess
                subprocess.Popen([str(HERE / "postboot.sh")], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                say("\n--- SSH_READY_ip: запущен postboot.sh (лог uart/postboot.log)")
            if RESET.search(buf[-8192:]):
                say("\n--- IPL после загрузки: камера сбросилась, снова ловлю U-Boot")
                break
            try:
                line = os.read(fd, 4096)
            except BlockingIOError:
                line = b""
            if line.startswith(b"#passive"):   # управление, в порт не идёт: после ручного дописывания/отката через FIFO
                passive = True                   # (ABORT, затем `reset` руками) не ловить U-Boot заново — дать автозагрузку
                say("\n--- #passive: Enter больше не шлю")
            elif line.startswith(b"#stage "):   # 29.09: `#stage 2a-p4-env` — какой этап слать при СЛЕДУЮЩЕМ перехвате U-Boot
                name = line.split()[1].decode(errors="replace")   # (после reboot -f), без перевзвода процесса владельцем.
                if name in STAGES and name not in WRITE_STAGES:   # только RAM-этапы: запись в NOR — отдельный запуск с NOR_WRITE=yes
                    stage, cmds, passive = name, [norm(c) for c in STAGES[name]], False   # 00:40: и после пассивного этапа
                    say(f"\n--- #stage: следующий перехват U-Boot = этап {stage}")
                else:
                    say(f"\n--- #stage {name}: отказ (нет такого или это запись: {sorted(WRITE_STAGES)})")
            elif line:
                port.write(line.rstrip(b"\n") + b"\n")
            else:
                time.sleep(0.02)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a == ["--selftest"]:
        selftest()
    elif a[:1] == ["--dry-run"] and a[1:2] and a[1] in STAGES:
        print("\n".join(f"{c}\t\t# ожидаю /{e}/" + (f", до {t} с" if t != 30 else "") if e else c for c, e, t in map(norm, STAGES[a[1]])))
    elif len(a) == 1 and a[0] in STAGES:
        main(a[0])
    else:
        sys.exit(__doc__)
