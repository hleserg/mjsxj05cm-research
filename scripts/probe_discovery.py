#!/usr/bin/env python3
"""Send bounded SSDP and WS-Discovery probes; never authenticate or write."""

import argparse
import socket
import time
import uuid


def probe(host, port, payload, multicast):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(0.5)
        sock.bind(("", 0))
        if multicast:
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
        sock.sendto(payload, (host, port))
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            try:
                data, peer = sock.recvfrom(8192)
            except socket.timeout:
                continue
            print(f"response from {peer[0]}:{peer[1]} ({len(data)} bytes)")
            print(data.decode("utf-8", errors="replace"))


parser = argparse.ArgumentParser()
parser.add_argument("host", help="camera IPv4 address")
args = parser.parse_args()

ssdp = (
    "M-SEARCH * HTTP/1.1\r\n"
    "HOST: 239.255.255.250:1900\r\n"
    'MAN: "ssdp:discover"\r\n'
    "MX: 1\r\n"
    "ST: ssdp:all\r\n\r\n"
).encode()
wsd = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope" '
    'xmlns:a="http://schemas.xmlsoap.org/ws/2004/08/addressing" '
    'xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery">'
    "<s:Header>"
    '<a:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</a:Action>'
    f"<a:MessageID>urn:uuid:{uuid.uuid4()}</a:MessageID>"
    "<a:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</a:To>"
    "</s:Header><s:Body><d:Probe/></s:Body></s:Envelope>"
).encode()

for name, port, payload, group in (
    ("SSDP unicast", 1900, ssdp, args.host),
    ("SSDP multicast", 1900, ssdp, "239.255.255.250"),
    ("WS-Discovery unicast", 3702, wsd, args.host),
    ("WS-Discovery multicast", 3702, wsd, "239.255.255.250"),
):
    print(f"\n{name} to {group}:{port}", flush=True)
    probe(group, port, payload, group != args.host)
