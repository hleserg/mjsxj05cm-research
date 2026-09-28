# MJSXJ05CM PTZ и аудио: GPIO и устройства

## Источники

**Основной репозиторий:** grablya95/Xiaomi-360-MJSXJ05CM  
**URL:** https://github.com/grablya95/Xiaomi-360-MJSXJ05CM  
**Версия:** stable (v1.2.2)  
**Дата публикации:** 2026-07-06T18:20:18Z  
**Тип исходных кодов:** прошивка SigmaStar SSC323 (IPC019) 3.5.1_0052  
**Ссылка на релиз:** https://github.com/grablya95/Xiaomi-360-MJSXJ05CM/releases/tag/stable  
**Актив релиза:** MJSXJ05CM-v1.2.2-stable-full.zip (13162186 байт)  

**Альтернативный источник:** 7damian7 — fork репозитория, pushed_at: не используется (основной репо актуальнее)

## Архитектура и бинарники

| Файл | Размер | Архитектура | NEEDED | Примечание |
|------|--------|------------|--------|-----------|
| `hacks/motor-control/bin/motord` | 29140 | ARM EABI5 32-bit | libc.so.0, libgcc_s.so.1, ld-uClibc.so.1 | **фактичес**: Не найдены GPIO в strings; использует libdevice_kit.so (SigmaStar) |
| `hacks/motor-control/bin/motord-no-startup-move` | 29140 | ARM EABI5 32-bit | » | Копия motord без инициализации |
| `hacks/motor-control/bin/motord.with-startup-calibration` | 13084 | ARM EABI5 32-bit | » | Полная калибровка при старте |
| `hacks/audio-bridge/bin/audio-bridge-v028` | 16684 | ARM EABI5 32-bit | libmi_ao.so, libmi_sys.so, libboardav.so.1 | **фактическое**: SigmaStar MI audio; debug refs к speaker_gpio |
| `hacks/bin/onvif-audio-proxy-v009` | 20348 | ARM EABI5 32-bit | libc.so.0, ld-uClibc.so.1 | Минимальный прокси без аудио libs |
| `hacks/framegrabber/bin/framegrabber-audio` | 7680 | ARM EABI5 32-bit (stripped) | libshbf.so.0.2, libshbfev.so.0.2, libev.so.4 | SigmaStar SHBF frame/audio |

## GPIO и LED

### LED индикаторы (подтверждено в `hacks/bin/led-indicator.sh`)

- **GPIO 76**: синий светодиод, active-high (обычный режим = вкл)
- **GPIO 77**: жёлтый светодиод, active-high  
- **Интерфейс**: `/sys/class/gpio/` (sysfs userspace GPIO)
- **Метод включения**: `echo 76 > /sys/class/gpio/export`, затем `echo out > /sys/class/gpio/gpio76/direction`, `echo 1 > /sys/class/gpio/gpio76/value`
- **Источник**: `hacks/bin/led-indicator.sh`, строка комментария: `# MJSXJ05CM status LEDs: GPIO76 = blue, GPIO77 = yellow.`

## PTZ и управление моторами

### Управление по программе (motord)

**Статус**: не найдены GPIO номера в бинарниках motord; управление **опосредованно**.

| Аспект | Значение | Источник |
|--------|----------|---------|
| **Функции двигателя** | motor_init, motor_h_move, motor_v_move, motor_h_dir_set, motor_v_dir_set, motor_calibrate, motor_goto | strings(motord) |
| **Позиция** | motor_h_position_get, motor_v_position_get, сохр. в `/mnt/data/config/position` | debug strings в motord, `hacks/installer/etc/perp/motor-controller/rc.main` |
| **Библиотека управления** | **libdevice_kit.so** (SigmaStar) | NEEDED в strings(motord); не найдена в поставке |
| **Стартовый режим** | Используется `motord.with-startup-calibration` (13084 байт) при PTZ_ENABLE=on | `hacks/installer/etc/perp/motor-controller/rc.main` |
| **Отключение** | Если PTZ_ENABLE=off, motord не запускается, камера не делает проверку мотора | `hacks/installer/config.sh`, README.md |
| **Ограничения** | Минимум (0,0), максимум не явно указан в strings; предположительно ≤360° / ≤180° | debug strings "MIN H", "MIN V", "MAX H", "MAX V" |

**Вывод**: моторы управляются через **закрытую SigmaStar библиотеку** (libdevice_kit.so). GPIO номера для управления двигателями не выставлены в userspace, управление идёт через ядро/устройства SigmaStar. **Предположение**: UTC2803M (step-motor driver) питается и управляется через регистры `/dev/mem` или модуль ядра, не через GPIO sysfs.

## Аудио и микрофон

### Входящее аудио (микрофон)

| Параметр | Значение | Источник |
|----------|----------|---------|
| **Бинарник захвата** | `hacks/framegrabber/bin/framegrabber-audio` | audio-capture rc.main |
| **Интерфейс** | ALSA/shbf (SigmaStar board audio framework) | NEEDED: libshbf.so.0.2, libshbfev.so.0.2 |
| **Pipe вывода** | `/var/run/rtsp_audio` (именованный FIFO) | `hacks/installer/etc/perp/audio-capture/rc.main` |
| **Запуск** | `/mnt/sdcard/hacks/framegrabber/bin/framegrabber-audio -a /var/run/rtsp_audio` | audio-capture rc.main |
| **Задержка старта** | AUDIO_START_DELAY=120 (сек, настраивается в config.sh) | config.sh, README |

### Выходящее аудио и speaker enable

| Параметр | Значение | Источник |
|----------|----------|---------|
| **Бинарник** | `hacks/audio-bridge/bin/audio-bridge-v028` (16684 б) | audio-bridge rc.main |
| **Библиотеки** | libmi_ao.so (SigmaStar MI Audio Output), libmi_sys.so, libboardav.so.1 | readelf -d audio-bridge-v028 |
| **Speaker enable GPIO** | **Неизвестен точно** (есть в debug strings); debug: `audio-bridge: speaker_gpio=0x%x` | strings audio-bridge-v028 @offset 0xXXX |
| **Speaker init** | функция `speaker_gpio_init`, `Mstar_enable_speaker` | strings audio-bridge-v028 |
| **Backchannel pipe** | `/var/run/audio_backchannel_v023` (FIFO) | audio-bridge rc.main |
| **Задержка старта** | BACKCHANNEL_START_DELAY=20, BACKCHANNEL_RESTART_DELAY=10 | config.sh |

**Вывод**: Speaker enable GPIO есть, но **номер не выставлен в userspace**. Управление спикером идёт через:
1. SigmaStar закрытый API (libmi_ao.so)
2. Функции Mstar_enable_speaker (вероятно, ядро-модуль или прямой `/dev/mem` доступ)
3. GPIO (номер в коде audio-bridge-v028, недоступен без декомпиляции ARM EABI5)

## IR-cut фильтр и IR-LED

**Статус**: не найдены явные GPIO номера в репозитории.

| Источник поиска | Результат |
|-----------------|-----------|
| `hacks/bin/led-indicator.sh` | только GPIO 76/77 (визуальные LED) |
| strings(motord), strings(audio-bridge*), strings(framegrabber-audio) | нет "ir-cut", "ir-led", "night" в контексте GPIO |
| README.md | упоминается NIGHT_VISION=auto, WDR, но не GPIO номера |
| config.sh | FULL_COLOR, NIGHT_VISION, WDR — настройки ISP, не GPIO |

**Вывод**: управление ночным видением **вероятно** идёт через ISP регистры (SigmaStar `_ISP_` адреса, `/dev/mem`), не через GPIO. **Предположение**: IR-cut может быть автоматизирован в прошивке SSC323 и не требует управления из userspace.

## Неизвестные и требующие дополнительного анализа

| Вопрос | Источник недостатка | Способ решения |
|--------|------------------|-----------------|
| Точный GPIO speaker enable | ARM EABI5 бинарник без исходников | ARM дизассемблер (`objdump -d -M intel audio-bridge-v028`) или debugger на камере |
| GPIO управления двигателями (если прямое) | libdevice_kit.so (закрытая SigmaStar) не поставляется | Трассировка `/dev/mem` при запуске motord (`strace -e openat,mmap`) |
| IR-cut / IR-LED GPIO | не упомянуто в скриптах | Поиск в образе прошивки 3.5.1_0052 (tf_recovery.bin) или трассировка ISP драйвера |
| ONVIF PTZ профиль детали | onvif-audio-proxy-v009 не содержит реализации PTZ | Снять PCAP при запросе PTZ команды в Onvifer |
| Точные пределы PTZ (макс. шаг, ускорение) | debug strings говорят "MIN", "MAX", но значения не указаны | Перехватить IPC с motord или запустить с ASAN/UBSAN |

## Итоги (факт vs предположение)

### Факты
- **GPIO 76/77** управляют LED через `/sys/class/gpio` sysfs ✓
- **motord** статически линкован с функциями SigmaStar, использует libdevice_kit.so ✓
- **audio-bridge-v028** использует libmi_ao.so для speaker ✓
- Версия v1.2.2, прошивка 3.5.1_0052 (SigmaStar SSC323 IPC019) ✓

### Предположения
- Моторы управляются через libdevice_kit.so → закрытый API или `/dev/mem` доступ (не GPIO sysfs)
- Speaker enable через GPIO, но номер закодирован в бинарнике audio-bridge-v028
- IR-cut / IR-LED управляются ISP драйвером, не GPIO
- UTC2803M steppers получают сигналы через регистры SSC323, не через userspace GPIO

---

**Сборка:** v1.2.2  
**Дата анализа:** 2026-09-27  
**Источник исходных кодов:** GitHub API (репозиторий grablya95)  
**Способ анализа:** readelf, strings, disasm docs, исходники скриптов  

## Поправка 28.09 (дизассемблирование стока, см. stock-gpio-map.md)
Предположение выше «моторы через регистры /dev/mem, не через GPIO» — неверно. libdevice_kit крутит их через ядровый sysfs‑драйвер `/sys/devices/virtual/mstar/motor/group_*` (PWM‑группа 4..7 → GPIO 44–47) и выбирает ось GPIO 80/16 через `/sys/class/gpio`. Speaker enable = GPIO 15 (libboardav `speaker_gpio_init`), усилитель `amp-gpio` 62 в DTB. Оба ядра (сток, OpenIPC) содержат драйвер; в DTB OpenIPC PWM4..7 не выведены на пады.
