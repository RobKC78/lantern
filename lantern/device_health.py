"""Read-only device evidence. No driver-age guessing or online scans on startup."""
import json
import os
from pathlib import Path
import re
import subprocess

from .repairs import native, invoke


def ps_json(script, timeout=20):
    return json.loads(invoke([native('powershell'), '-NoProfile', '-NonInteractive', '-Command',
                             "$ErrorActionPreference='Stop'; " + script], timeout=timeout) or '[]')


def as_list(data):
    return data if isinstance(data, list) else [data] if data else []


def collect_device_health():
    result = {'problem_devices': [], 'driver_updates': {'status': 'unknown', 'items': []}, 'coverage': []}
    def query(name, fn):
        try:
            result[name] = fn()
            result['coverage'].append({'check': name, 'status': 'ok'})
        except Exception as exc:
            result['coverage'].append({'check': name, 'status': 'unavailable', 'detail': str(exc)[:300]})
    if os.name == 'nt':
        query('problem_devices', lambda: as_list(ps_json("@(Get-CimInstance Win32_PnPEntity -Filter 'ConfigManagerErrorCode != 0' | Select-Object -First 100 @{n='name';e={$_.Name}}, @{n='class';e={$_.PNPClass}}, @{n='code';e={$_.ConfigManagerErrorCode}}) | ConvertTo-Json -Depth 3 -Compress")))
        query('installed_drivers', lambda: as_list(ps_json("@(Get-CimInstance Win32_PnPSignedDriver | Where-Object {$_.DeviceClass -in 'MEDIA','DISPLAY','NET','BLUETOOTH','USB'} | Select-Object -First 200 DeviceName,DeviceClass,DriverProviderName,DriverVersion,DriverDate,InfName,IsSigned) | ConvertTo-Json -Depth 3 -Compress")))
        def cached_updates():
            script = "$s=New-Object -ComObject Microsoft.Update.Session; $q=$s.CreateUpdateSearcher(); $q.Online=$false; $q.CanAutomaticallyUpgradeService=$false; $r=$q.Search(\"IsInstalled=0 and Type='Driver' and IsHidden=0\"); @($r.Updates | Select-Object -First 50 Title,DriverClass,DriverManufacturer,DriverModel) | ConvertTo-Json -Depth 3 -Compress"
            return {'status': 'cached_only', 'items': as_list(ps_json(script, timeout=25)),
                    'note': 'Saved Windows Update results only; empty does not mean up to date. No online search was requested.'}
        query('driver_updates', cached_updates)
        query('reboot_pending', lambda: bool(ps_json("[bool]((Test-Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Component Based Servicing\\RebootPending') -or (Test-Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\WindowsUpdate\\Auto Update\\RebootRequired')) | ConvertTo-Json")))
    else:
        query('installed_drivers', lambda: invoke([native('lspci'), '-nnk'])[:30000])
        def audio():
            volume = invoke([native('wpctl'), 'get-volume', '@DEFAULT_AUDIO_SINK@'])
            match = re.search(r'Volume:\s+([0-9.]+)', volume)
            return {'muted': '[MUTED]' in volume, 'volume': float(match.group(1)) if match else None,
                    'note': 'Current user PipeWire output only. No changes made.'}
        query('audio', audio)
        query('audio_services', lambda: invoke([native('systemctl'), '--user', 'show', 'pipewire.service', 'wireplumber.service', 'pipewire-pulse.service', '--property=Id,LoadState,ActiveState,UnitFileState', '--no-pager'])[:10000])
        query('dkms', lambda: invoke([native('dkms'), 'status'])[:10000])
        result['reboot_pending'] = Path('/var/run/reboot-required').exists()
        result['driver_updates']['note'] = 'Linux drivers are often shipped with kernel/firmware packages. No current vendor comparison has been performed. Use your distribution’s updater.'
    return result
