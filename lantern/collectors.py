"""Explicit, trusted collector registry. No runtime downloaded plugins."""
import concurrent.futures
import datetime as dt
import ipaddress
import json
import os
import platform
import re
import socket
import subprocess
from pathlib import Path

import psutil

REGISTRY = {}
PRIVATE = tuple(ipaddress.ip_network(n) for n in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'))
SERVICES = {22: 'SSH', 80: 'HTTP', 443: 'HTTPS', 445: 'SMB', 3389: 'RDP'}


def collector(name):
    def register(fn):
        REGISTRY[name] = fn
        return fn
    return register


@collector('windows_repair_readiness')
def windows_repair_readiness():
    if os.name != 'nt':
        return {}
    from .windows_repairs import snapshot
    rows = {}
    for action in ('windows_components', 'gameinput'):
        try:
            rows[action] = {'available': True, **snapshot(action)}
        except Exception as exc:
            rows[action] = {'available': False, 'reason': str(exc)[:500]}
    return rows


@collector('device_health')
def device_health():
    from .device_health import collect_device_health
    return collect_device_health()


@collector('repair_services')
def repair_services():
    from .repairs import inspect_services
    return inspect_services()


def command(args, timeout=12):
    result = subprocess.run(args, capture_output=True, text=True, errors='replace',
                            timeout=timeout, creationflags=0x08000000 if os.name == 'nt' else 0)
    if result.returncode:
        raise RuntimeError((result.stderr or 'Command unavailable or access denied')[:300])
    return result.stdout


def redact(text):
    text = re.sub(r'(?i)\b(password|passwd|token|secret|api[_-]?key|authorization)\s*[:=]\s*\S+', r'\1=[REDACTED]', str(text))
    text = re.sub(r'(?i)\bBearer\s+\S+', 'Bearer [REDACTED]', text)
    return text[:2000]


@collector('system')
def system():
    disks = []
    for part in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(part.mountpoint)
            disks.append({'mount': part.mountpoint, 'total': usage.total, 'free': usage.free, 'percent': usage.percent})
        except (OSError, PermissionError):
            pass
    return {'hostname': socket.gethostname(), 'os': platform.platform(), 'architecture': platform.machine(),
            'processor': platform.processor(), 'logical_cpus': psutil.cpu_count(), 'cpu_percent': psutil.cpu_percent(interval=0.3),
            'memory': psutil.virtual_memory()._asdict(), 'boot_time': psutil.boot_time(), 'disks': disks}


@collector('interfaces')
def interfaces():
    stats = psutil.net_if_stats()
    return [{'name': name, 'up': stats[name].isup if name in stats else False,
             'addresses': [{'family': str(a.family), 'address': a.address, 'netmask': a.netmask}
                           for a in addresses]}
            for name, addresses in psutil.net_if_addrs().items()]


@collector('processes')
def processes():
    rows = []
    for process in psutil.process_iter(['pid', 'name', 'memory_percent']):
        try:
            rows.append(process.info)
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass
    return sorted(rows, key=lambda p: p.get('memory_percent') or 0, reverse=True)[:25]


@collector('services')
def services():
    if os.name == 'nt':
        rows = []
        for service in psutil.win_service_iter():
            try:
                info = service.as_dict()
                rows.append({k: info[k] for k in ('name', 'display_name', 'status', 'start_type')})
            except psutil.AccessDenied:
                pass
        return rows
    return command(['systemctl', '--no-pager', '--plain', 'list-units', '--type=service', '--all'])[:50000]


def local_networks(items):
    result = set()
    for iface in items:
        if not iface['up']:
            continue
        for a in iface['addresses']:
            try:
                network = ipaddress.ip_network(f"{a['address']}/{a['netmask']}", strict=False)
                if network.version == 4 and any(network.subnet_of(p) for p in PRIVATE):
                    result.add(str(network))
            except ValueError:
                pass
    return sorted(result)


def allowed_target(address, networks):
    try:
        ip = ipaddress.ip_address(address)
        return ip.version == 4 and any(ip in p for p in PRIVATE) and any(ip in ipaddress.ip_network(n) for n in networks)
    except ValueError:
        return False


@collector('connections')
def connections():
    def endpoint(a):
        return {'ip': a.ip, 'port': a.port} if a else None
    return {'coverage': 'Best effort. OS permissions can omit connections and process IDs.',
            'items': [{'local': endpoint(c.laddr), 'remote': endpoint(c.raddr), 'status': c.status,
                       'pid': c.pid, 'transport': 'TCP' if c.type == socket.SOCK_STREAM else 'UDP'}
                      for c in psutil.net_connections(kind='inet')][:4000]}


@collector('neighbors')
def neighbors():
    networks = local_networks(interfaces())
    raw = command(['arp', '-a'] if os.name == 'nt' else ['ip', '-4', 'neigh', 'show'])
    found = {}
    for line in raw.splitlines():
        ips = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', line)
        for ip in ips:
            if allowed_target(ip, networks):
                mac = re.search(r'\b(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}\b', line)
                found[ip] = {'ip': ip, 'mac': mac.group() if mac else None,
                             'evidence': 'Neighbor cache; presence does not prove current reachability', 'services': []}
    return list(found.values())


@collector('logs')
def logs():
    entries, coverage = [], []
    if os.name == 'nt':
        for source in ('System', 'Application'):
            try:
                script = "$ErrorActionPreference='Stop'; @(Get-WinEvent -FilterHashtable @{LogName='" + source + "'; StartTime=(Get-Date).AddHours(-24); Level=1,2,3} -MaxEvents 150 | Select-Object @{n='time';e={$_.TimeCreated.ToString('o')}}, @{n='level';e={$_.LevelDisplayName}}, @{n='message';e={$_.Message}}, Id, ProviderName) | ConvertTo-Json -Compress"
                data = json.loads(command(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script]) or '[]')
                for row in data if isinstance(data, list) else [data]:
                    entries.append({'source': source, **row, 'message': redact(row.get('message', ''))})
                coverage.append({'source': source, 'status': 'ok', 'limit': '150 warning/error events, last 24h'})
            except Exception as exc:
                coverage.append({'source': source, 'status': 'unavailable', 'detail': redact(exc)})
    else:
        try:
            raw = command(['journalctl', '--since', '24 hours ago', '-p', 'warning', '-n', '300', '-o', 'json', '--no-pager'])
            for line in raw.splitlines():
                row = json.loads(line)
                entries.append({'source': row.get('_SYSTEMD_UNIT', 'journal'), 'time': row.get('__REALTIME_TIMESTAMP'),
                                'level': 'error' if int(row.get('PRIORITY', 4)) <= 3 else 'warning',
                                'message': redact(row.get('MESSAGE', ''))})
            coverage.append({'source': 'journal', 'status': 'ok', 'limit': '300 events, last 24h; only user-accessible journal entries'})
        except Exception as exc:
            coverage.append({'source': 'journal', 'status': 'unavailable', 'detail': redact(exc)})
        for filename in ('/var/log/syslog', '/var/log/messages'):
            try:
                with open(filename, 'rb') as f:
                    f.seek(0, 2)
                    f.seek(max(0, f.tell() - 65536))
                    lines = f.read().decode('utf-8', errors='replace').splitlines()[-300:]
                for line in lines:
                    if re.search(r'error|warn|fail|critical', line, re.I):
                        entries.append({'source': filename, 'time': None, 'level': 'warning', 'message': redact(line)})
                coverage.append({'source': filename, 'status': 'ok', 'limit': 'last 64KiB / 300 lines; timestamps not filtered'})
            except OSError:
                coverage.append({'source': filename, 'status': 'unavailable', 'detail': 'Absent or not readable'})
    return {'entries': entries, 'coverage': coverage,
            'privacy': 'Best-effort secret redaction only. Logs may contain personal or sensitive data. Review before sharing.'}


def discover(cidr):
    # Re-evaluate interfaces for every run; never trust a client supplied subnet.
    networks = local_networks(interfaces())
    network = ipaddress.ip_network(cidr, strict=True)
    if network.version != 4 or network.num_addresses > 256 or not any(network.subnet_of(ipaddress.ip_network(n)) for n in networks):
        raise ValueError('Choose a directly connected private IPv4 subnet with at most 256 addresses (/24 or smaller).')
    def probe(ip):
        opened = []
        for port, label in SERVICES.items():
            try:
                with socket.create_connection((str(ip), port), timeout=0.18):
                    opened.append({'port': port, 'label': label, 'confidence': 'Port-based guess; not verified'})
            except OSError:
                pass
        return {'ip': str(ip), 'mac': None, 'services': opened, 'evidence': 'TCP connection accepted'} if opened else None
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        return [x for x in pool.map(probe, network.hosts()) if x]


def collect():
    results = {}
    for name, fn in REGISTRY.items():
        try:
            results[name] = {'status': 'ok', 'data': fn()}
        except Exception as exc:
            results[name] = {'status': 'unavailable', 'error': redact(exc)}
    return {'schema_version': 1, 'collected_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'collectors': results}
