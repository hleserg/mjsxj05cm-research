#!/bin/sh
# tools/onvif/build.sh — статический onvif_simple_server (roleoroleo, 95c17f7) под ARM musl через zig cc (как tools/ptz/build.sh).
# Выход: firmware/openipc-ipc017-20260926/p4/onvif.tgz = бинарник + шаблоны 4 сервисов как .xml.gz (USE_ZLIB, ~1.7 МБ → tmpfs экономим).
# Патчи исходников: пути сервисов /onvif/ → /cgi-bin/onvif/ (busybox httpd запускает CGI только из /cgi-bin/),
#                   конфиг по умолчанию /etc/… → /tmp/onvif/onvif_simple_server.conf (CGI не получает -c).
# Запуск на камере: autorun.sh распаковывает в /tmp/www/cgi-bin/onvif, симлинки device/media/ptz_service → бинарник.
set -e
R=$(cd "$(dirname "$0")/../.." && pwd); W=${W:-$R/../onvif-build}; mkdir -p "$W"; cd "$W"
PY=$HOME/.local/zigenv/bin/python   # pip install ziglang
printf '#!/bin/sh\nexec %s -m ziglang cc -target arm-linux-musleabihf -mcpu=cortex_a7 "$@"\n' "$PY" > zigcc
printf '#!/bin/sh\nexec %s -m ziglang ar "$@"\n' "$PY" > zigar; chmod 755 zigcc zigar; Z=$W/zigcc; A=$W/zigar
[ -d onvif_simple_server ] || { git clone -q https://github.com/roleoroleo/onvif_simple_server; git -C onvif_simple_server checkout -q 95c17f7; }
cd onvif_simple_server
grep -q cgi-bin/onvif device_service.c || sed -i 's#/onvif/#/cgi-bin/onvif/#g' device_service.c fault.c events_service.c events_service_files/GetEventProperties_1.xml events_service_files/GetEventProperties_3.xml
sed -i 's#"/etc/onvif_simple_server.conf"#"/tmp/onvif/onvif_simple_server.conf"#' onvif_simple_server.c
[ -f extras/mbedtls/library/libmbedcrypto.a ] || { [ -d extras/mbedtls ] || git clone -q -b v2.28.8 --depth 1 https://github.com/Mbed-TLS/mbedtls.git extras/mbedtls
  make -s -C extras/mbedtls/library CC=$Z AR=$A CFLAGS="-Os -fPIC" libmbedcrypto.a; }
[ -f extras/zlib/libz.a ] || { [ -d extras/zlib ] || git clone -q -b v1.3.1 --depth 1 https://github.com/madler/zlib.git extras/zlib
  (cd extras/zlib && CC=$Z AR=$A ./configure --static >/dev/null && make -s libz.a); }
[ -f extras/json-c/build/libjson-c.a ] || { [ -d extras/json-c ] || git clone -q -b json-c-0.17-20230812 --depth 1 https://github.com/json-c/json-c.git extras/json-c
  cmake -S extras/json-c -B extras/json-c/build -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=arm -DCMAKE_C_COMPILER=$Z -DCMAKE_AR=$A \
    -DBUILD_SHARED_LIBS=OFF -DBUILD_STATIC_LIBS=ON -DDISABLE_EXTRA_LIBS=ON -DBUILD_TESTING=OFF -DCMAKE_INSTALL_PREFIX=$PWD/extras/json-c/build/_install >/dev/null
  make -s -C extras/json-c/build install >/dev/null; }
rm -f onvif_simple_server *.o
make -s -f Makefile.static onvif_simple_server CC=$Z HAVE_MBEDTLS=1 USE_ZLIB=1 STRIP=echo \
  LIBS_O="-Wl,--gc-sections -static extras/mbedtls/library/libmbedcrypto.a extras/zlib/libz.a extras/json-c/build/libjson-c.a -lpthread -lrt"
P=$W/pack; rm -rf "$P"; mkdir "$P"; cp onvif_simple_server "$P"/
for d in generic_files device_service_files media_service_files ptz_service_files; do
  mkdir "$P/$d"; for f in "$d"/*.xml; do gzip -9c "$f" > "$P/$d/$(basename "$f").gz"; done; done
tar czf "$R/firmware/openipc-ipc017-20260926/p4/onvif.tgz" -C "$P" .
file onvif_simple_server; ls -la "$R/firmware/openipc-ipc017-20260926/p4/onvif.tgz"
