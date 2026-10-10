/* tcpserve: `tcpserve PORT PROG` — на каждое TCP-соединение fork + exec PROG со stdin/stdout на сокете (как tcpsvd/inetd).
 * Зачем: в busybox камеры нет inetd/tcpsvd, а `nc -ll -e` делает vfork и зависает (родитель в D в _do_fork, ребёнок в futex)
 * после десятка соединений Onvifer. Статика musl через zig, см. build.sh. ponytail: без лимита детей и таймаутов. */
#include <netinet/in.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>
int main(int argc, char **argv) {
    if (argc < 3) { fprintf(stderr, "usage: tcpserve PORT PROG [ARGS]\n"); return 2; }
    signal(SIGCHLD, SIG_IGN); /* детей не ждём — ядро само хоронит */
    signal(SIGPIPE, SIG_IGN);
    int s = socket(AF_INET, SOCK_STREAM, 0), one = 1;
    setsockopt(s, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);
    struct sockaddr_in a = { .sin_family = AF_INET, .sin_port = htons(atoi(argv[1])), .sin_addr.s_addr = INADDR_ANY };
    if (bind(s, (struct sockaddr *)&a, sizeof a) || listen(s, 16)) { perror("bind/listen"); return 1; }
    for (;;) {
        int c = accept(s, NULL, NULL);
        if (c < 0) continue;
        if (fork() == 0) {
            dup2(c, 0); dup2(c, 1); close(c); close(s);
            execv(argv[2], argv + 2);
            _exit(127);
        }
        close(c);
    }
}
