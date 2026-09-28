# UART0 на infinity6: что нашёл сабагент (28.09.2026), для итерации после 2a-p3

Приём по UART мёртв под обоими ядрами (сток и OpenIPC), в U-Boot работает — см. DECISIONS.md 28.09.

Найдено (OpenIPC/linux, ветка sigmastar-infinity6b0, drivers/sstar/):
- `include/infinity6/irqs.h`: `INT_IRQ_UART_0 = GIC_SPI_MS_IRQ_START + 34 = 66 (0x42)` — совпадает с
  `interrupts = <0 0x42 4>` в обоих DTB → номер IRQ в DTS верный, не в нём дело.
- `gpio/infinity6/mhal_pinmux.c`: `PINMUX_FOR_UART0_MODE_1..4 = 0x22..0x25`; `REG_UART0_MODE = 0x03`
  в `CHIPTOP_BANK`, маска `BIT6|BIT5|BIT4`. У uart1 в DTB есть `pad=<0x2b>`, у uart0 — нет
  (в обоих DTB). Гипотеза: драйвер ms_uart без `pad` не трогает падмукс, а U-Boot ставит режим
  UART0 сам → в U-Boot RX есть; ядро (или gpioi2c на GPIO 8/9?) перебивает.
- CHIPTOP bank infinity6 = 0x101E → RIU 0x1F000000 + 0x101E*0x200 = **0x1F203C00**; регистр 0x03 →
  **0x1F203C0C** (16-бит в 32-битном слове). Не проверено живьём.
- Пады FUART (QFN88 pin 43–46), GPIO 8/9 = I2C на Chuangmi (cmsxj19e SERIAL_CONSOLE.md).
- Не найдено: полная таблица PAD_* для SSC323, probe ms_uart.c, «Disable uart rx via PAD_DDCA».

Следующий шаг (после лога 2a-p3): в recon.sh добавить дамп CHIPTOP 0x1F203C00–0x1F203DFF и
PM_SLEEP/PM_TOP (0x1F001C00, 0x1F001E00) через devmem — только чтение; сравнить с тем, что видно
в U-Boot (`md.w 0x1F203C0C 1` — разрешено, print-only). Если UART0_MODE в Linux ≠ U-Boot →
патч DTB (`pad`) в uImage в RAM.
