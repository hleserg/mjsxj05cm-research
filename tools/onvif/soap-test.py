#!/usr/bin/env python3
# tools/onvif/soap-test.py — сырые SOAP-запросы к onvif_simple_server на камере (WS-UsernameToken PasswordDigest, без зависимостей).
# Использование: python3 tools/onvif/soap-test.py GetCapabilities GetProfiles GetStreamUri GetStatus MoveLeft Stop GotoHome
import sys, os, base64, hashlib, datetime, http.client, re, time
HOST = "192.168.30.53"
PORT = int(os.environ.get("ONVIF_PORT", 8080))
BASE = os.environ.get("ONVIF_BASE", "/cgi-bin/onvif/")
PW = open(os.path.join(os.path.dirname(__file__), "../../firmware/openipc-ipc017-20260926/p4/secret/onvif-password.txt")).readline().strip()
def hdr():
    nonce = os.urandom(16); created = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    dig = base64.b64encode(hashlib.sha1(nonce + created.encode() + PW.encode()).digest()).decode()
    return f'''<s:Header><Security xmlns="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd"><UsernameToken><Username>admin</Username><Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordDigest">{dig}</Password><Nonce EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary">{base64.b64encode(nonce).decode()}</Nonce><Created xmlns="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">{created}</Created></UsernameToken></Security></s:Header>'''
OPS = {
 "GetSystemDateAndTime": ("device_service", '<tds:GetSystemDateAndTime xmlns:tds="http://www.onvif.org/ver10/device/wsdl"/>', False),
 "GetDeviceInformation": ("device_service", '<tds:GetDeviceInformation xmlns:tds="http://www.onvif.org/ver10/device/wsdl"/>', True),
 "GetCapabilities": ("device_service", '<tds:GetCapabilities xmlns:tds="http://www.onvif.org/ver10/device/wsdl"><tds:Category>All</tds:Category></tds:GetCapabilities>', True),
 "GetServices": ("device_service", '<tds:GetServices xmlns:tds="http://www.onvif.org/ver10/device/wsdl"><tds:IncludeCapability>false</tds:IncludeCapability></tds:GetServices>', True),
 "GetProfiles": ("media_service", '<trt:GetProfiles xmlns:trt="http://www.onvif.org/ver10/media/wsdl"/>', True),
 "GetStreamUri": ("media_service", '<trt:GetStreamUri xmlns:trt="http://www.onvif.org/ver10/media/wsdl"><trt:StreamSetup><tt:Stream xmlns:tt="http://www.onvif.org/ver10/schema">RTP-Unicast</tt:Stream><tt:Transport xmlns:tt="http://www.onvif.org/ver10/schema"><tt:Protocol>RTSP</tt:Protocol></tt:Transport></trt:StreamSetup><trt:ProfileToken>Profile_0</trt:ProfileToken></trt:GetStreamUri>', True),
 "GetSnapshotUri": ("media_service", '<trt:GetSnapshotUri xmlns:trt="http://www.onvif.org/ver10/media/wsdl"><trt:ProfileToken>Profile_0</trt:ProfileToken></trt:GetSnapshotUri>', True),
 "GetNodes": ("ptz_service", '<tptz:GetNodes xmlns:tptz="http://www.onvif.org/ver20/ptz/wsdl"/>', True),
 "GetStatus": ("ptz_service", '<tptz:GetStatus xmlns:tptz="http://www.onvif.org/ver20/ptz/wsdl"><tptz:ProfileToken>Profile_0</tptz:ProfileToken></tptz:GetStatus>', True),
 "MoveLeft": ("ptz_service", '<tptz:ContinuousMove xmlns:tptz="http://www.onvif.org/ver20/ptz/wsdl"><tptz:ProfileToken>Profile_0</tptz:ProfileToken><tptz:Velocity><tt:PanTilt xmlns:tt="http://www.onvif.org/ver10/schema" x="-0.5" y="0"/></tptz:Velocity></tptz:ContinuousMove>', True),
 "MoveUp": ("ptz_service", '<tptz:ContinuousMove xmlns:tptz="http://www.onvif.org/ver20/ptz/wsdl"><tptz:ProfileToken>Profile_0</tptz:ProfileToken><tptz:Velocity><tt:PanTilt xmlns:tt="http://www.onvif.org/ver10/schema" x="0" y="0.5"/></tptz:Velocity></tptz:ContinuousMove>', True),
 "Stop": ("ptz_service", '<tptz:Stop xmlns:tptz="http://www.onvif.org/ver20/ptz/wsdl"><tptz:ProfileToken>Profile_0</tptz:ProfileToken><tptz:PanTilt>true</tptz:PanTilt><tptz:Zoom>true</tptz:Zoom></tptz:Stop>', True),
 "GetNode": ("ptz_service", '<tptz:GetNode xmlns:tptz="http://www.onvif.org/ver20/ptz/wsdl"><tptz:NodeToken>PTZNodeToken</tptz:NodeToken></tptz:GetNode>', True),
 "GetConfigurations": ("ptz_service", '<tptz:GetConfigurations xmlns:tptz="http://www.onvif.org/ver20/ptz/wsdl"/>', True),
 "GetConfigurationOptions": ("ptz_service", '<tptz:GetConfigurationOptions xmlns:tptz="http://www.onvif.org/ver20/ptz/wsdl"><tptz:ConfigurationToken>PTZCfgToken</tptz:ConfigurationToken></tptz:GetConfigurationOptions>', True),
 "RelativeLeft": ("ptz_service", '<tptz:RelativeMove xmlns:tptz="http://www.onvif.org/ver20/ptz/wsdl"><tptz:ProfileToken>Profile_0</tptz:ProfileToken><tptz:Translation><tt:PanTilt xmlns:tt="http://www.onvif.org/ver10/schema" x="-0.1" y="0"/></tptz:Translation></tptz:RelativeMove>', True),
 "GotoHome": ("ptz_service", '<tptz:GotoHomePosition xmlns:tptz="http://www.onvif.org/ver20/ptz/wsdl"><tptz:ProfileToken>Profile_0</tptz:ProfileToken></tptz:GotoHomePosition>', True),
}
for op in sys.argv[1:]:
    svc, body, auth = OPS[op]
    env = f'<?xml version="1.0" encoding="UTF-8"?><s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">{hdr() if auth else ""}<s:Body>{body}</s:Body></s:Envelope>'
    t = time.time(); c = http.client.HTTPConnection(HOST, PORT, timeout=15)
    c.request("POST", BASE + svc, env, {"Content-Type": "application/soap+xml; charset=utf-8"})
    r = c.getresponse(); d = r.read().decode(errors="replace"); dt = time.time() - t
    short = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", d)).strip()
    xaddr = re.findall(r"(?:XAddr|Uri)>([^<]+)<", d)
    print(f"{op}: {r.status} {len(d)}B {dt:.2f}s | {' '.join(xaddr[:4]) if xaddr else short[:160]}")
    if "Fault" in d and r.status != 200: print("   ", short[:300])
    if os.environ.get("RAW"): print(d)
