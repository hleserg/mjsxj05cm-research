// ptz — быстрый полушаг PTZ MJSXJ05CM на OpenIPC через sysfs GPIO (замена шелл-цикла в ptz.sh).
//   ptz h|v +|- N [us]   — N полушагов, us = пауза на состояние (мкс), по умолчанию $PTZ_US или 8000.
// Та же таблица 8 состояний и тот же смысл N, что в ptz.sh (калибровка 4100/700 остаётся). GPIO должны быть
// уже экспортированы и out (ptz.sh init). Любой выход — обмотки обесточены (SIGTERM/SIGINT/ошибка тоже).
// Сборка: tools/ptz/build.sh (zig cc, static musl armhf). Проверка на Pi: PTZ_GPIO=<каталог-заглушка> ./ptz h + 8 0
// ponytail: без разгона/торможения — добавить рампу, если при малом us мотор срывается только на старте.
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

static int fd[4], sel = -1;
static const char seq[8][4] = {{1,0,0,1},{1,0,0,0},{1,1,0,0},{0,1,0,0},{0,1,1,0},{0,0,1,0},{0,0,1,1},{0,0,0,1}};

static void w(int f, int v) { if (write(f, v ? "1" : "0", 1) != 1) { perror("write gpio"); } }
static void off(void) { for (int i = 0; i < 4; i++) if (fd[i] >= 0) w(fd[i], 0); if (sel >= 0) w(sel, 0); }
static void bye(int s) { off(); _exit(128 + s); }

static int opn(const char *base, int g) {
    char p[256]; snprintf(p, sizeof p, "%s/gpio%d/value", base, g);
    int f = open(p, O_WRONLY);
    if (f < 0) { fprintf(stderr, "ptz: %s: %s (нужен ptz.sh init)\n", p, strerror(errno)); exit(1); }
    return f;
}

int main(int argc, char **argv) {
    if (argc < 4 || (argv[1][0] != 'h' && argv[1][0] != 'v') || (argv[2][0] != '+' && argv[2][0] != '-')) {
        fprintf(stderr, "ptz h|v +|- полушаги [мкс]\n"); return 2;
    }
    long n = atol(argv[3]);
    long us = argc > 4 ? atol(argv[4]) : (getenv("PTZ_US") ? atol(getenv("PTZ_US")) : 8000);
    const char *base = getenv("PTZ_GPIO") ? getenv("PTZ_GPIO") : "/sys/class/gpio";
    for (int i = 0; i < 4; i++) fd[i] = opn(base, 44 + i);
    sel = opn(base, argv[1][0] == 'h' ? 80 : 16);
    int other = opn(base, argv[1][0] == 'h' ? 16 : 80);
    signal(SIGTERM, bye); signal(SIGINT, bye); signal(SIGHUP, bye);
    off(); w(other, 0); w(sel, 1);
    struct timespec t0, t1, d = { us / 1000000, (us % 1000000) * 1000 };
    clock_gettime(CLOCK_MONOTONIC, &t0);
    int dir = argv[2][0] == '+' ? 1 : -1, s = dir > 0 ? 0 : 7;
    for (long k = 0; k < n; k++, s = (s + dir) & 7) {
        for (int i = 0; i < 4; i++) w(fd[i], seq[s][i]);
        if (us > 0) nanosleep(&d, NULL);
    }
    off();
    clock_gettime(CLOCK_MONOTONIC, &t1);
    double el = (t1.tv_sec - t0.tv_sec) + (t1.tv_nsec - t0.tv_nsec) / 1e9;
    printf("ptz %s%s %ld ок, %.2f с, %.0f полушагов/с\n", argv[1], argv[2], n, el, el > 0 ? n / el : 0);
    return 0;
}
