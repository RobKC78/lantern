"""Small fixed repair catalog. No commands or paths are accepted from the UI."""
import base64
import ctypes
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

CATALOG = {
    'windows': {'printing': ('Spooler', 'printing'), 'clock': ('W32Time', 'clock syncing'),
                'audio': ('Audiosrv', 'sound'), 'audio_devices': ('AudioEndpointBuilder', 'sound-device detection'),
                'bluetooth': ('bthserv', 'Bluetooth support')},
    'linux': {'printing': ('cups.service', 'printing'), 'clock': ('systemd-timesyncd.service', 'clock syncing'),
              'bluetooth': ('bluetooth.service', 'Bluetooth support')},
}

SERVICE_EXPLANATIONS = {
    'printing': ('Printing helper is inactive', 'The printing helper is not running. This may be normal if nothing needs printing.', 'If you are having trouble printing, you can start this helper.'),
    'clock': ('Clock-sync helper is inactive', 'The clock-sync helper is not running. Another service may already be keeping time.', 'Only start this if you want this time service and are not already using another one.'),
    'audio': ('Sound helper is inactive', 'Windows cannot play normal audio through this helper while it is stopped.', 'If you want sound, start the sound helper, then try a familiar recording.'),
    'audio_devices': ('Sound-device helper is inactive', 'The helper that makes speakers and microphones available is not running.', 'Start the helper, then check that your intended speaker or headset is selected.'),
    'bluetooth': ('Bluetooth helper is inactive', 'The helper for Bluetooth devices is not running. This can be normal if you do not use Bluetooth.', 'If a Bluetooth device will not connect, start the helper, then reconnect it in Settings.'),
}


def platform_key():
    return 'windows' if os.name == 'nt' else 'linux'


def native(name):
    if os.name == 'nt':
        buffer = ctypes.create_unicode_buffer(32768)
        if not ctypes.windll.kernel32.GetSystemDirectoryW(buffer, len(buffer)):
            raise RuntimeError('Cannot locate Windows system tools')
        root = Path(buffer.value)
        return str(root / ('WindowsPowerShell/v1.0/powershell.exe' if name == 'powershell' else name + '.exe'))
    path = Path('/usr/bin') / name
    if not path.exists():
        path = Path('/bin') / name
    if not path.exists():
        raise RuntimeError(f'{name} is not installed; this repair is unavailable')
    return str(path)


def invoke(args, timeout=40):
    result = subprocess.run(args, capture_output=True, text=True, errors='replace', timeout=timeout,
                            creationflags=0x08000000 if os.name == 'nt' else 0)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or 'System tool failed')[:600])
    return result.stdout


def service_state(action, platform=None):
    platform = platform or platform_key()
    name, _ = CATALOG[platform][action]
    if platform == 'windows':
        import psutil
        info = psutil.win_service_get(name).as_dict()
        return {'name': name, 'state': info['status'], 'start_type': info['start_type'],
                'configuration': {k: info.get(k) for k in ('name', 'display_name', 'start_type', 'binpath', 'username')}}
    raw = invoke([native('systemctl'), 'show', name, '--no-pager',
                  '--property=LoadState,ActiveState,SubState,UnitFileState,Result,FragmentPath'])
    values = dict(line.split('=', 1) for line in raw.splitlines() if '=' in line)
    if values.get('LoadState') != 'loaded':
        raise RuntimeError('This service is not installed or cannot be loaded')
    if action == 'clock':
        competing = invoke([native('systemctl'), 'list-units', 'chronyd.service', 'chrony.service', 'ntp.service', 'ntpd.service', 'openntpd.service', '--state=active,activating', '--no-legend', '--no-pager'])
        if competing.strip():
            raise RuntimeError('Another time service is active. Leave that service in charge.')
    return {'name': name, 'state': values.get('ActiveState'), 'start_type': values.get('UnitFileState'), 'configuration': values}


def eligible(state):
    # Never enable disabled services or bypass masking. Inactive/on-demand is not a diagnosis.
    return state['state'] in ('stopped', 'inactive', 'failed') and state['start_type'] in ('automatic', 'manual', 'enabled', 'enabled-runtime')


def inspect_services():
    rows = []
    for action in CATALOG[platform_key()]:
        try:
            rows.append({'action': action, 'status': 'ok', **service_state(action)})
        except Exception as exc:
            rows.append({'action': action, 'status': 'unavailable', 'detail': str(exc)[:300]})
    return rows


def description(action):
    name, label = CATALOG[platform_key()][action]
    impact = {'printing': 'Queued print jobs may resume, and printing may open configured network listeners.',
              'clock': 'The clock may change and the service may contact its configured time server.',
              'audio': 'Sound may resume at your existing volume. Turn down speakers first. Service dependencies may start.',
              'audio_devices': 'Speakers and microphones may become available to apps with existing permission. Dependencies may start.',
              'bluetooth': 'Previously paired devices may reconnect. Your existing pairing and radio settings are retained.'}[action]
    return {'action': action, 'service': name, 'label': 'Start ' + label,
            'change': f'Start {name} if it is still inactive. Its startup settings will not change.',
            'impact': impact, 'backup': 'Save and verify the current service state and settings before starting any selected service. This is not a personal-file or full-system backup.',
            'undo': f'The saved snapshot records the previous state. Stopping {name} can restore its inactive state, but cannot undo printed jobs, clock adjustments or dependency side effects. No automatic undo is offered.'}


def prepare_plan(report, ids):
    if not isinstance(ids, list) or not ids or len(ids) > 20 or any(not isinstance(x, str) for x in ids):
        raise ValueError('Choose at least one supported finding')
    available = {f['id']: f for f in report['findings'] if f.get('repair')}
    if any(i not in available for i in ids):
        raise ValueError('A selected item is no longer repairable. Refresh the checks.')
    actions = sorted({available[i]['repair'] for i in ids})
    return {'id': secrets.token_hex(16), 'expires_at': time.time() + 300,
            'items': [description(a) for a in actions], 'actions': actions,
            'warning': 'Only the listed service starts are included. Review the effects, then approve the operating-system permission prompt. If any backup fails, no selected repairs start.'}


def start_service(action):
    name, _ = CATALOG[platform_key()][action]
    if os.name == 'nt':
        invoke([native('powershell'), '-NoProfile', '-NonInteractive', '-Command',
                f"$ErrorActionPreference='Stop'; Start-Service -Name '{name}'"])
    else:
        invoke([native('systemctl'), 'start', name])


def backup_directory():
    # Exclusive creation; no user-supplied destination and no re-use of existing paths.
    if os.name == 'nt':
        root = Path(native('cmd')).anchor
        folder = Path(tempfile.mkdtemp(prefix='Lantern-backup-', dir=root + 'ProgramData'))
        invoke([native('icacls'), str(folder), '/inheritance:r', '/grant:r',
                '*S-1-5-18:(OI)(CI)F', '*S-1-5-32-544:(OI)(CI)F'])
    else:
        folder = Path(tempfile.mkdtemp(prefix='lantern-backup-', dir='/var/lib'))
        folder.chmod(0o700)
    return folder


def write_verified(path, data):
    payload = json.dumps(data, sort_keys=True, indent=2).encode('utf-8')
    with path.open('xb') as f:
        f.write(payload)
        f.flush()
        os.fsync(f.fileno())
    if path.read_bytes() != payload:
        raise RuntimeError('Backup verification failed')
    return hashlib.sha256(payload).hexdigest()


def execute_batch(actions, notify, snapshot=service_state, start=start_service, directory=backup_directory):
    if not isinstance(actions, list) or not actions or len(actions) > len(CATALOG[platform_key()]) or len(set(actions)) != len(actions):
        raise ValueError('Invalid action list')
    if any(a not in CATALOG[platform_key()] for a in actions):
        raise ValueError('Unknown repair')
    before = {}
    for action in actions:
        state = snapshot(action)
        if not eligible(state):
            raise ValueError('Service state changed or repair is unsupported. Refresh before trying again.')
        before[action] = state
    notify({'stage': 'backing_up', 'message': 'Saving service states and settings. No repairs have started.'})
    folder = directory()
    digest = write_verified(folder / 'before.json', {'version': 1, 'platform': platform_key(), 'services': before})
    # All backup writes and verification must complete before the first mutation.
    write_verified(folder / 'manifest.json', {'before_sha256': digest, 'created_at': time.time()})
    notify({'stage': 'repairing', 'backup': str(folder), 'message': 'Service-state backup verified. Starting the approved services.'})
    results = []
    for action in actions:
        result = {'action': action, 'label': description(action)['label'], 'status': 'Couldn’t complete'}
        try:
            current = snapshot(action)
            if current != before[action]:
                raise ValueError('The service changed after backup. Skipped; refresh and review it again.')
            # A durable per-action intent record precedes the operating-system command.
            write_verified(folder / (action + '-intent.json'), {'action': action, 'started_at': time.time()})
            start(action)
            notify({'stage': 'verifying', 'message': 'Checking ' + result['label'].lower() + '…', 'backup': str(folder)})
            after = snapshot(action)
            result.update(status='Fixed' if after['state'] in ('running', 'active') else 'Still needs attention',
                          detail='Service state after the request: ' + after['state'] + '. Please also try the feature; service state alone does not prove it works.', after=after)
        except Exception as exc:
            result['detail'] = str(exc)[:600] + ' The request may have partly completed; check the service before retrying.'
        results.append(result)
        try:
            write_verified(folder / (action + '-result.json'), result)
        except Exception as exc:
            result['detail'] += ' Result could not be saved: ' + str(exc)[:200]
            notify({'stage': 'complete', 'backup': str(folder), 'results': results, 'message': 'Stopped because the repair record could not be saved. Remaining actions were not run.'})
            return
        notify({'stage': 'repairing', 'backup': str(folder), 'results': list(results), 'message': result['label'] + ': ' + result['status']})
    notify({'stage': 'complete', 'backup': str(folder), 'results': results, 'message': 'Finished checking the selected repairs. Review each result below.'})


def helper_main(encoded):
    from .server import elevated
    if not elevated():
        raise RuntimeError('Administrator permission was not granted')
    payload = json.loads(base64.urlsafe_b64decode(encoded).decode())
    port, secret = payload['port'], payload['secret']
    if type(port) is not int or not 1 <= port <= 65535 or not isinstance(secret, str) or len(secret) != 64:
        raise ValueError('Invalid local repair session')
    def notify(event):
        request = urllib.request.Request(f'http://127.0.0.1:{port}/api/repair-event',
                    data=json.dumps(event).encode(), headers={'X-Repair-Token': secret, 'Content-Type': 'application/json'})
        # Never honor proxy environment variables for local helper communication.
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request, timeout=10) as response:
            response.read()
    try:
        execute_batch(payload['actions'], notify)
    except Exception as exc:
        notify({'stage': 'failed', 'message': 'Repair stopped: ' + str(exc)[:600]})


def launch_helper(actions, port, secret):
    payload = base64.urlsafe_b64encode(json.dumps({'actions': actions, 'port': port, 'secret': secret}).encode()).decode()
    executable = str(Path(sys.executable).resolve())
    arguments = ([] if getattr(sys, 'frozen', False) else [str(Path(__file__).resolve().parents[1] / 'run.py')]) + ['--repair-helper', payload]
    if os.name == 'nt':
        # Correct Windows argv quoting, then PowerShell literal quoting; never shell-built user commands.
        quote = lambda s: "'" + s.replace("'", "''") + "'"
        script = "$ErrorActionPreference='Stop'; $p=Start-Process -FilePath " + quote(executable) + ' -ArgumentList ' + quote(subprocess.list2cmdline(arguments)) + ' -Verb RunAs -WindowStyle Hidden -Wait -PassThru; exit $p.ExitCode'
        result = subprocess.run([native('powershell'), '-NoProfile', '-NonInteractive', '-Command', script],
                                capture_output=True, text=True, creationflags=0x08000000)
    else:
        pkexec = native('pkexec')
        result = subprocess.run([pkexec, '--disable-internal-agent', executable, *arguments], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError('Permission was declined, an authentication agent is unavailable, or the repair helper failed. No further actions were requested. Refresh to check current state.')
