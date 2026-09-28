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
SDBOOT = "mmc dev 0; mmc rescan; mw.l 0x22000000 0 4; fatload mmc 0:1 0x22000000 uImage.ssc325; setenv bootargs ${sdargs}; bootm 0x22000000"
NORBOOT = "sf probe 0; sf read 0x22000000 ${sf_kernel_start} ${sf_kernel_size}; setenv bootargs ${norargs}; bootm 0x22000000"
# Репетиция env в RAM (advisor 21:30): грузим с p1 ТОТ ЖЕ 4K-блок, что пойдёт в NOR (uboot/mkenv.py → env-new.bin на p1),
# U-Boot сам проверяет CRC (`env import -c`), затем полная цепочка bootcmd (sdboot → norboot). NOR не трогаем (env import — RAM).
# MAXARGS стокового U-Boot = 32 (cli_simple_parse_line @0x23e09438) — без запаса для setenv длинных строк не обойтись, поэтому файл.
STAGES["2a-p4-env"] = [
    "mmc dev 0", "mmc rescan", "fatload mmc 0:1 0x22100000 env-new.bin",
    "crc32 0x22100000 0x1000",             # сверить с crc32(4096) из mkenv.py
    "env import -c 0x22100000 0x1000", "printenv bootcmd", "printenv sdboot", "printenv norboot",
    "run bootcmd",
]
RESET = re.compile(rb"(^|\n)IPL[ _]")   # баннер IPL в начале строки = камера сбросилась (после загрузки ядра)
FORBIDDEN = re.compile(r"\b(saveenv|sf\s+(erase|write|update)|erase|update|upgrade|flashcp|nand)\b")
PROMPT = re.compile(rb"\n([^\r\n#]{1,24})# ")


def prompt_of(buf):
    seen = {}
    for m in PROMPT.finditer(buf):
        seen[m.group(1)] = seen.get(m.group(1), 0) + 1
        if seen[m.group(1)] >= 3:
            return m.group(1) + b"# "
    return None


def selftest():
    assert prompt_of(b"\r\nSigmaStar # \r\nSigmaStar # \r\nSigmaStar # ") == b"SigmaStar # "
    assert prompt_of(b"\r\nSigmaStar # \r\nSigmaStar # ") is None
    for cmds in STAGES.values():
        assert not any(FORBIDDEN.search(c) for c in cmds), cmds
    assert FORBIDDEN.search("sf update 0x22000000 0x50000 0x200000")
    assert FORBIDDEN.search("saveenv")
    assert not FORBIDDEN.search("sf read 0x22000000 0x50000 0x200000")
    print("selftest ok")


def main(stage):
    import serial
    cmds = STAGES[stage]
    assert not any(FORBIDDEN.search(c) for c in cmds)
    port = serial.Serial("/dev/ttyAMA0", 115200, timeout=0.02)
    out = HERE / time.strftime(f"stage-{stage}-%Y%m%d-%H%M%S.log")
    log, buf = open(out, "wb"), b""

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
    while True:   # 28.09: цикл на сброс камеры — после «IPL» в консоли снова ловим U-Boot, иначе сброс = загрузка стока из NOR
        print(f"пишу {out}\nшлю Enter — ВКЛЮЧАЙ КАМЕРУ (жду {wait} с)", flush=True)
        end, prompt = time.time() + wait, None
        while time.time() < end and not prompt:
            port.write(b"\r"); rx()
            prompt = prompt_of(buf[-8192:])
        if not prompt:
            sys.exit("\nU-Boot не остановился")
        time.sleep(0.3); rx()
        for c in cmds:
            mark = len(buf)
            port.write(c.encode() + b"\r")
            t = time.time() + 30
            while time.time() < t and buf.rfind(prompt) <= mark + len(c):
                rx()
                if c.startswith(("bootm", "run ")) and b"Starting kernel" in buf[mark:]:
                    break
        print(f"\n--- команды этапа {stage} посланы; консоль: echo CMD > {FIFO} ; лог {out}", flush=True)
        buf = b""
        hooked = False   # постбут-хук: init4.sh напечатал SSH_READY_ip → uart/postboot.sh (autorun.sh с p1 карты по SSH), один раз
        while True:
            rx()
            if not hooked and b"SSH_READY_ip" in buf:
                hooked = True
                import subprocess
                subprocess.Popen([str(HERE / "postboot.sh")], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print("\n--- SSH_READY_ip: запущен postboot.sh (лог uart/postboot.log)", flush=True)
            if RESET.search(buf[-8192:]):
                print("\n--- IPL после загрузки: камера сбросилась, снова ловлю U-Boot", flush=True)
                break
            try:
                line = os.read(fd, 4096)
            except BlockingIOError:
                line = b""
            if line:
                port.write(line.rstrip(b"\n") + b"\n")
            else:
                time.sleep(0.02)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a == ["--selftest"]:
        selftest()
    elif a[:1] == ["--dry-run"] and a[1:2] and a[1] in STAGES:
        print("\n".join(STAGES[a[1]]))
    elif len(a) == 1 and a[0] in STAGES:
        main(a[0])
    else:
        sys.exit(__doc__)
