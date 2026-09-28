#!/bin/bash
# Frigate на Pi (192.168.1.139) по go2rtc-рестримам камеры. Секретов нет (cam_sub/cam_main без auth).
#   tools/frigate/run.sh            # (пере)создать контейнер frigate; UI http://192.168.1.139:5000
# Bridge-сеть (не host: встроенный go2rtc Frigate занял бы 8554/1984 внешнего go2rtc). Медиа: ~/frigate/media.
set -eu
cd "$(dirname "$0")"
mkdir -p ~/frigate/config ~/frigate/media
cp config.yml ~/frigate/config/config.yml
docker rm -f frigate 2>/dev/null || true
docker run -d --name frigate --restart unless-stopped --shm-size=128m \
  -v ~/frigate/config:/config -v ~/frigate/media:/media/frigate -v /etc/localtime:/etc/localtime:ro \
  -e FRIGATE_RTSP_PASSWORD=unused -p 5000:5000 -p 8971:8971 \
  ghcr.io/blakeblackshear/frigate:stable
sleep 20; docker logs --tail 15 frigate 2>&1 | grep -viE "password|rtsp://" ; curl -s -m 5 http://127.0.0.1:5000/api/stats | head -c 400
