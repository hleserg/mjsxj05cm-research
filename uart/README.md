# UART: passive physical inspection and boot capture

Status (2026-09-27): фото платы есть, кандидаты пронумерованы 1–18 на [карте](../docs/img/board-pads-numbered.jpg), GND отмечен владельцем. TX ещё не найден, boot log нет. Приёмник (актуально с 28.09): `/dev/ttyAMA2` Pi 5 (overlay `uart2-pi5`): площадка 13 (TX камеры) → pin 29 (GPIO5), площадка 14 (RX камеры) ← 1 кОм ← pin 7 (GPIO4), GND — pin 6. Pin 8 не подключать. Захват: `./capture.sh` пишет `boot-YYYYMMDD-HHMMSS.log` и строку в `captures.txt`.

## Before any connection

1. With stock USB power disconnected, photograph both sides of the main PCB, all printed board revisions, SoC and 8-pin flash markings, and each group of unpopulated test pads. Include one wide view showing orientation and close, sharply focused macro views. Do not remove or write the SPI chip.
2. Mark candidate pads on those photos. Confirm GND by continuity to the board ground plane or USB power ground while unpowered. With the camera on **stock USB power**, measure each candidate pad relative to confirmed GND using a high-impedance meter; identify likely TX from idle level and boot-time activity, preferably with an oscilloscope or logic analyzer. A steady voltage alone does not confirm TX or RX.
3. Connect only camera GND → USB-UART GND and camera TX → USB-UART RX after voltage is known. Use a 3.3 V logic adapter with its **TX and VCC disconnected**. If the pad level is incompatible with the receiver, stop and select a compatible high-impedance receiver. Never power the camera from the adapter.

## First capture, once TX and GND are confirmed

- Start the host capture before applying stock USB power to the camera. Set `115200 8N1`, no hardware or software flow control. Save unedited output as `uart/boot-115200.log`, including the first bytes and any garbled bytes.
- On this host the read-only capture can use `stty -F <USB_UART_PORT> 115200 cs8 -parenb -cstopb -ixon -ixoff -crtscts raw -echo` followed by `timeout 180s cat <USB_UART_PORT> | tee /home/hleserg/mjsxj05cm-research/uart/boot-115200.log`. These are **prepared commands, not executed**; the serial device path must first be identified on the host.
- If the signal is active but illegible, repeat a complete stock-power boot capture at `57600`, `38400`, then `921600`, each in its own log. Do not infer a baud rate from noise alone.

No adapter TX connection, autoboot interruption, U-Boot command, SPI probe, flash write, SD recovery, factory reset, or cloud change is authorized by this stage. A boot log may reveal U-Boot version, flash model, MXPT/MTD partitions, kernel command line, rootfs, and console state; these remain **unknown on our camera** until captured.
