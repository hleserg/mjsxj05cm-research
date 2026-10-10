#!/bin/sh
# onvif-serve.sh: Onvifer принимает только host+port и стучится в /onvif/device_service, а busybox httpd
# пускает CGI только под /cgi-bin/ и не умеет прокси. Поэтому отдельный порт: nc -ll -e → этот скрипт
# на каждый коннект: разбираем HTTP сами и зовём onvif_simple_server как CGI. Через `httpd -i` нельзя:
# stdin там пайп, REMOTE_ADDR не ставится, а без него onvif_simple_server молча выходит (conf.c).
# ponytail: REMOTE_ADDR фиксирован — всё из дома приходит через NAT роутера 192.168.30.1, OSS по нему лишь выбирает свой адрес.
O=/tmp/www/cgi-bin/onvif; P=${ONVIF_PORT:-8082}; CR=$(printf '\r')
read -r M U _; U=${U%%\?*}; L=0
while read -r H; do H=${H%$CR}; [ -z "$H" ] && break
  case "$H" in [Cc]ontent-[Ll]ength:*) L=${H#*:}; L=${L# } ;; esac; done
S=${U##*/}
case "$S" in device_service|media_service|ptz_service) ;; *) printf 'HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n'; exit 0 ;; esac
echo "$(date +%T) :$P $M $U len=$L" >> /tmp/onvif/req.log
printf 'HTTP/1.1 200 OK\r\n'
cd $O && head -c "$L" | env -i PATH=/bin:/usr/bin GATEWAY_INTERFACE=CGI/1.1 SERVER_PROTOCOL=HTTP/1.1 REQUEST_METHOD="$M" \
  CONTENT_LENGTH="$L" CONTENT_TYPE=application/soap+xml REMOTE_ADDR=192.168.30.1 SERVER_NAME=192.168.30.53 SERVER_PORT=$P \
  SCRIPT_NAME="$U" REQUEST_URI="$U" QUERY_STRING= ./$S
