// ptz — быстрый полушаг PTZ MJSXJ05CM на OpenIPC через sysfs GPIO (замена шелл-цикла в ptz.sh).
//   ptz h|v +|- N [us]   — N полушагов, us = пауза на состояние (мкс), по умолчанию $PTZ_US или 2000 (10.10: 1000 — подёргивается, 2000 — чисто, запас ×2).
//   ptz hv +|- N +|- M [us] — диагональ: шаговые линии 44–47 общие, селекты 80/16; оси едут по очереди пачками по $PTZ_CHUNK
//   полушагов (по умолчанию 8), каждая вдвое медленнее, чем одна. Нужно Onvifer: диагональные стрелки = ContinuousMove по обеим осям.
//   Почему пачками, а не по одному полушагу (10.10, измерено снимками): при чередовании 1:1 с разными знаками (вниз-влево,
//   вверх-вправо) обе оси теряли шаги, с одинаковыми — нет. Порядок записи селектов, мёртвое время до 3 мс и пауза до 20 мс
//   не помогали → «отпущенный» мотор всё равно чувствует чужую картинку на общих линиях (при одинаковых знаках она его же
//   и держит). Пачки = как одноосные ходы, где второй мотор спокойно стоит. PTZ_CHUNK=1 возвращает чередование 1:1.
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

static int fd[4], sel[2] = { -1, -1 }; /* sel[0] = h (gpio80), sel[1] = v (gpio16), как в ptz.sh */
static const char seq[8][4] = {{1,0,0,1},{1,0,0,0},{1,1,0,0},{0,1,0,0},{0,1,1,0},{0,0,1,0},{0,0,1,1},{0,0,0,1}};

static void w(int f, int v) { if (write(f, v ? "1" : "0", 1) != 1) { perror("write gpio"); } }
static void off(void) { for (int i = 0; i < 4; i++) if (fd[i] >= 0) w(fd[i], 0); for (int i = 0; i < 2; i++) if (sel[i] >= 0) w(sel[i], 0); }   // как ptz.sh stop
static void bye(int s) { off(); _exit(128 + s); }

static int opn(const char *base, int g) {
    char p[256]; snprintf(p, sizeof p, "%s/gpio%d/value", base, g);
    int f = open(p, O_WRONLY);
    if (f < 0) { fprintf(stderr, "ptz: %s: %s (нужен ptz.sh init)\n", p, strerror(errno)); exit(1); }
    return f;
}

int main(int argc, char **argv) {
    int two = argc > 1 && !strcmp(argv[1], "hv"), na = two ? 2 : 1, use[2] = { 0, 0 }, dir[2], st[2];
    long n[2] = { 0, 0 }, k[2] = { 0, 0 };
    const char *usage = "ptz h|v +|- полушаги [мкс]  |  ptz hv +|- N +|- M [мкс]\n";
    if (argc < (two ? 6 : 4) || (!two && argv[1][0] != 'h' && argv[1][0] != 'v')) { fputs(usage, stderr); return 2; }
    for (int a = 0; a < na; a++) {
        int ax = two ? a : (argv[1][0] == 'h' ? 0 : 1); const char *sg = argv[2 + 2 * a];
        if (sg[0] != '+' && sg[0] != '-') { fputs(usage, stderr); return 2; }
        use[ax] = 1; dir[ax] = sg[0] == '+' ? 1 : -1; n[ax] = atol(argv[3 + 2 * a]); st[ax] = dir[ax] > 0 ? 0 : 7;
    }
    int ua = 2 + 2 * na;
    long us = argc > ua ? atol(argv[ua]) : (getenv("PTZ_US") ? atol(getenv("PTZ_US")) : 2000);
    long chunk = getenv("PTZ_CHUNK") ? atol(getenv("PTZ_CHUNK")) : 8;   /* калибровка: полушагов на ось за один захват линий в hv */
    if (chunk < 1) chunk = 1;
    const char *base = getenv("PTZ_GPIO") ? getenv("PTZ_GPIO") : "/sys/class/gpio";
    for (int i = 0; i < 4; i++) fd[i] = opn(base, 44 + i);
    sel[0] = opn(base, 80); sel[1] = opn(base, 16);
    signal(SIGTERM, bye); signal(SIGINT, bye); signal(SIGHUP, bye);
    off();
    struct timespec t0, t1, d = { us / 1000000, (us % 1000000) * 1000 };
    clock_gettime(CLOCK_MONOTONIC, &t0);
    for (int any = 1; any;) {
        any = 0;
        for (int a = 0; a < 2; a++) {
            if (!use[a] || k[a] >= n[a]) continue;
            any = 1;
            w(sel[1 - a], 0);                                      // чужую ось отпустить, пока на линиях ещё её картинка
            for (long j = 0; j < chunk && k[a] < n[a]; j++) {
                for (int i = 0; i < 4; i++) w(fd[i], seq[st[a]][i]);
                if (j == 0) w(sel[a], 1);                          // свой селект — после своей первой картинки, не раньше
                if (us > 0) nanosleep(&d, NULL);
                k[a]++; st[a] = (st[a] + dir[a]) & 7;
            }
        }
    }
    off();
    clock_gettime(CLOCK_MONOTONIC, &t1);
    double el = (t1.tv_sec - t0.tv_sec) + (t1.tv_nsec - t0.tv_nsec) / 1e9;
    printf("ptz h%ld v%ld ок, %.2f с, %.0f полушагов/с\n", k[0], k[1], el, el > 0 ? (k[0] + k[1]) / el : 0);
    return 0;
}
