# Карта GPIO/PWM стока MJSXJ05CM 4.3.9_0445 (из бинарников DATA, 28.09.2026)

Источник: дизассемблирование (capstone) `lib/libdevice_kit.so.0.0.1`, `lib/libboardav.so.1.0.0`, `bin/miio_algo`
из собственного дампа DATA (jffs2) + DTB, встроенный в стоковое ядро (0x307870 в vmlinux) и в ядро OpenIPC IPC017 (0x3a7af0).
Скрипт: `firmware/openipc-ipc017-20260926/.venv` + `disasm.py` (в scratchpad сессии; при необходимости восстановить — capstone+pyelftools).
**Всё ниже — из кода, не с живой платы. Проверено на этапе 1 (28.09) и живой работой PTZ/ИК/звука — см. `firmware/openipc-ipc017-20260926/p4/ptz.sh`, DECISIONS.md.**

| Узел | Интерфейс | Номера | Откуда |
|---|---|---|---|
| Моторы pan/tilt | `/sys/devices/virtual/mstar/motor/group_{mode,period,begin,end,polarity,round,enable,stop,hold}` — PWM‑группа каналов **4,5,6,7** | пады PWM4..7 = GPIO **44,45,46,47** (`pad-ctrl` в DTB стока) | libdevice_kit 0x3f74/0x3fd0 (последовательность 4→7 / 7→4), DTB `pwm { pad-ctrl }` |
| Выбор мотора | `/sys/class/gpio` out | GPIO **80** и **16**: одна ось = 80:1,16:0, другая = 80:0,16:1 | libdevice_kit 0x402c (switch по команде), init 0x4380 |
| Параметры фаз | группа: pwm(polarity, begin, end) | 4:(0,0,0x177) 5:(0,0xfa,0x271) 6:(0,0x1f4,0x36b) 7:(1,0x7d,0x2ee); `group_enable` ← "1 %d", `group_stop` ← "1" | libdevice_kit 0x3dc4, 0x3cb4, 0x3d2c |
| ИК‑подсветка | `/sys/class/pwm/pwmchip0/pwm0` (period/duty_cycle/enable) | PWM0 = pad GPIO **52** (в DTB стока **и** OpenIPC) | miio_algo `_mstar_pwm_duty`, строки `pwm0` |
| ИК‑фильтр (UTC6208) | `/sys/class/gpio` out, импульс 500 мс | GPIO **78** и **79** | miio_algo `ircut_config_init` (строки "78","79"), `_mstar_ircut_drv_sw` (usleep 0x7a120) |
| Динамик | GPIO out, init 0 | GPIO **15** (libboardav `speaker_gpio_init`); плюс `amp-gpio = <62 1>` в узле `sound` DTB стока | libboardav 0x5140; DTB diff |
| Светодиоды | `/sys/class/gpio` | синий **76**, жёлтый **77** | libdevice_kit `led_init`, совпадает с grablya95 |
| Кнопка | `/sys/class/gpio` in | GPIO **66** | libdevice_kit `key_init` |
| Wi‑Fi MT7601U | питание | GPIO **14** | boot log / ранее |

## Разница DTB сток ↔ OpenIPC IPC017 (единственные два отличия из 40300 байт)
1. `sound { amp-gpio }`: сток `<0x3e 0x01>` (GPIO 62, active 1), OpenIPC `<0xffff 0x01>` (нет) → под OpenIPC усилитель включать самим (`gpio set 62 1`) или патчить DTB.
2. `pwm { pad-ctrl }`: сток PWM4..7 → пады 44..47, OpenIPC → 0xffff (PWM4..7 не выведены) → под OpenIPC моторная PWM‑группа без патча DTB/падмукса крутить не будет; варианты: (а) патч DTS в сборке OpenIPC, (б) `riu_w`/devmem падмукса как `DrvPWMPadSet`, (в) bit‑bang 4 фаз как обычных GPIO 44–47 + выбор 80/16 из userspace.
Строки драйвера (`group_*`, `DrvPWMPadSet`, `motor`) есть в обоих ядрах → сам драйвер в OpenIPC собран.
