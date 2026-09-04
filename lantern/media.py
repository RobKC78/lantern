"""Bounded SSDP discovery only; never fetch device-provided URLs or launch playback."""
import socket
import time
import ipaddress
from .collectors import interfaces, allowed_target

TARGETS = ('urn:dial-multiscreen-org:service:dial:1', 'urn:schemas-upnp-org:device:MediaRenderer:1')


def parse_advertisement(payload, address, networks):
    if len(payload) > 8192 or not allowed_target(address, networks):
        return None
    lines = payload.decode('utf-8', errors='replace').splitlines()
    if not lines or not lines[0].startswith('HTTP/1.1 200'):
        return None
    headers = {}
    for line in lines[1:]:
        if ':' in line:
            key, value = line.split(':', 1)
            headers[key.strip().lower()] = value.strip()[:300]
    kind = headers.get('st')
    if kind not in TARGETS:
        return None
    return {'ip': address, 'kind': 'DIAL app receiver' if kind == TARGETS[0] else 'DLNA media renderer',
            'advertised_software': headers.get('server', 'Not provided'),
            'confidence': 'Self-advertised capability; not independently verified',
            'casting': 'Not tested. This advertisement does not prove Google Cast, AirPlay or screen-mirroring support.',
            'steps': ['Confirm which physical device this address belongs to in your TV or router settings.',
                      'For a Google Cast-capable TV, open Chrome’s Cast menu and explicitly select the device and content. The TV must appear there before treating it as ready.',
                      'For DLNA, use a compatible media player and select its renderer. DIAL indicates app-launch discovery, not arbitrary screen casting.',
                      'If discovery fails, check the same Wi-Fi network, guest-network isolation, VPN and TV standby settings. Do not disable the firewall wholesale.'],
            'help_url': 'https://support.google.com/googlecast/answer/3228332?hl=en'}


def discover_media():
    candidates = []
    for iface in interfaces():
        if not iface['up']:
            continue
        for item in iface['addresses']:
            try:
                network = ipaddress.ip_network(f"{item['address']}/{item['netmask']}", strict=False)
                if network.version == 4 and allowed_target(item['address'], [str(network)]):
                    candidates.append((item['address'], str(network)))
            except ValueError:
                continue
    devices, coverage = {}, []
    for address, network in candidates[:8]:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.bind((address, 0))
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(address))
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
                sock.settimeout(.25)
                for target in TARGETS:
                    query = f'M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\nMAN: "ssdp:discover"\r\nMX: 1\r\nST: {target}\r\n\r\n'
                    sock.sendto(query.encode('ascii'), ('239.255.255.250', 1900))
                deadline, count = time.monotonic() + 2, 0
                while time.monotonic() < deadline and count < 128:
                    try:
                        payload, peer = sock.recvfrom(8193)
                    except socket.timeout:
                        continue
                    count += 1
                    device = parse_advertisement(payload, peer[0], [network])
                    if device:
                        devices[(device['ip'], device['kind'])] = device
                coverage.append({'interface_address': address, 'status': 'queried'})
        except OSError as exc:
            coverage.append({'interface_address': address, 'status': 'unavailable', 'detail': str(exc)[:200]})
    return {'devices': list(devices.values()), 'coverage': coverage, 'checked_at': time.time(),
            'note': 'Local SSDP discovery only, up to 8 private IPv4 interfaces. Sleeping, isolated, mDNS-only or incompatible devices may be missed. No playback or device-control commands were sent.'}
