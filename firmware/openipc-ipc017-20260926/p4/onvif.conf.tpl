# Шаблон /tmp/onvif/onvif_simple_server.conf; __PW__ подставляет autorun.sh из /tmp/p1/onvif-password.txt (та же учётка admin,
# что у majestic ONVIF :80 и RTSP Basic). %s = IP камеры (сервер берёт по адресу клиента). Порядок ключей важен (парсер построчный).
model=MJSXJ05CM
manufacturer=Xiaomi
firmware_ver=OpenIPC
hardware_id=LSAM041D1-1
serial_num=MJSXJ05CM
port=8080
scope=onvif://www.onvif.org/Profile/Streaming
scope=onvif://www.onvif.org/hardware/MJSXJ05CM
scope=onvif://www.onvif.org/name/MJSXJ05CM
user=admin
password=__PW__
adv_enable_media2=0
adv_fault_if_unknown=0
adv_fault_if_set=0
adv_synology_nvr=0
#Profile 0 — majestic video0 (1080p 20 fps, aac)
name=Profile_0
width=1920
height=1080
url=rtsp://%s/stream=0
snapurl=http://%s/image.jpg
type=H264
bitrate=4096
framerate=20
audio_encoder=AAC
audio_decoder=NONE
#Profile 1 — video1 704x576 15 fps
name=Profile_1
width=704
height=576
url=rtsp://%s/stream=1
snapurl=http://%s/image.jpg
type=H264
bitrate=0
framerate=15
audio_encoder=AAC
audio_decoder=NONE
#PTZ → onvif-ptz.sh → /tmp/ptz (пан ≈360°, тилт ≈96°, зума нет)
ptz=1
min_step_x=0
max_step_x=360
min_step_y=0
max_step_y=96
min_step_z=0
max_step_z=0
get_position=/tmp/onvif-ptz.sh pos
is_moving=/tmp/onvif-ptz.sh moving
move_left=/tmp/onvif-ptz.sh left %f
move_right=/tmp/onvif-ptz.sh right %f
move_up=/tmp/onvif-ptz.sh up %f
move_down=/tmp/onvif-ptz.sh down %f
move_stop=/tmp/onvif-ptz.sh stop %s
goto_home_position=/tmp/onvif-ptz.sh home
jump_to_rel=/tmp/onvif-ptz.sh rel %f %f %f
