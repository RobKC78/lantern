"""Fixed Windows repair adapters. No executable names, commands or URLs from logs."""
import json
import re
import subprocess
import time

ACTIONS = {'windows_components', 'gameinput'}


def ps(script, timeout=60):
    from .repairs import native, invoke
    return json.loads(invoke([native('powershell'), '-NoProfile', '-NonInteractive', '-Command',
        "$ErrorActionPreference='Stop'; " + script], timeout=timeout) or 'null')


def gameinput():
    # Registry inventory does not trigger the repair side effects of Win32_Product.
    return ps(r"""
$rows=@(Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*' -ErrorAction SilentlyContinue |
 Where-Object {$_.DisplayName -eq 'Microsoft GameInput' -and $_.Publisher -eq 'Microsoft Corporation' -and $_.WindowsInstaller -eq 1} |
 Select-Object PSChildName,DisplayName,DisplayVersion -Unique)
if($rows.Count -ne 1){throw 'Exactly one registered Microsoft GameInput MSI is required; ambiguous or missing installations need source recovery.'}
$code=$rows[0].PSChildName
if($code -notmatch '^\{[0-9A-Fa-f-]{36}\}$'){throw 'Invalid product registration'}
$wi=New-Object -ComObject WindowsInstaller.Installer
$cache=$wi.ProductInfo($code,'LocalPackage')
if(-not $cache -or -not (Test-Path -LiteralPath $cache -PathType Leaf)){throw 'The original installer is missing or inaccessible. Restore the official matching installer source before repairing; no registry entries were deleted.'}
$sig=Get-AuthenticodeSignature -LiteralPath $cache
if($sig.Status -ne 'Valid' -or $sig.SignerCertificate.Subject -notmatch '(^|,\s*)O=Microsoft Corporation(,|$)'){throw 'A valid Microsoft-signed installer is required'}
@{product=$code;version=$rows[0].DisplayVersion;cache=$cache;sha256=(Get-FileHash -LiteralPath $cache -Algorithm SHA256).Hash} | ConvertTo-Json -Compress
""")


def snapshot(action):
    from .repairs import platform_key
    if platform_key() != 'windows' or action not in ACTIONS:
        raise ValueError('Unsupported Windows repair')
    config = gameinput() if action == 'gameinput' else {'tool': 'Windows DISM and System File Checker'}
    return {'state': 'available', 'start_type': 'repair_adapter', 'configuration': config, 'name': action}


def describe(action):
    shared = {'action': action,
        'backup': 'Create and verify a NEW Windows System Restore point plus a local repair record before any repair starts. This is a system recovery checkpoint, not a backup of personal files. If Windows cannot create it, this batch stops.',
        'undo': 'Use Windows System Restore to return system settings to the recorded checkpoint if needed. Recovery is not guaranteed and may affect other installed apps; Lantern does not automatically roll back.'}
    if action == 'windows_components':
        return {**shared, 'label': 'Check and repair Windows components',
            'change': 'Check the Windows component store and protected system files. Repair only when the checks identify corruption. Healthy or unrecognized results do not trigger a repair.',
            'impact': 'May take 15–60 minutes or longer. Repair can contact Windows Update, replace protected system files and require a later restart. Save your work. No restart is forced. This may help component crashes, but does not prove their cause.'}
    return {**shared, 'label': 'Repair Microsoft GameInput',
        'change': 'Recheck the registered Microsoft GameInput package and its Microsoft-signed installer, then ask Windows Installer to repair missing or older files and machine registration.',
        'impact': 'Close games first. GameInput services may restart and controller input may be interrupted. The installer may need its original source; if unavailable, repair stops. No uninstall, registry deletion, driver replacement or forced restart is requested.'}


def checkpoint():
    label = 'Lantern repair ' + str(time.time_ns())
    # Never weaken System Restore throttling or enable protection behind the user's back.
    return ps("$label='" + label + "'; Checkpoint-Computer -Description $label -RestorePointType MODIFY_SETTINGS; "
              "$p=@(Get-ComputerRestorePoint | Where-Object {$_.Description -eq $label}); "
              "if($p.Count -ne 1){throw 'A new recovery checkpoint could not be verified. Enable System Protection or wait until Windows permits another restore point.'}; "
              "$p[0] | Select-Object SequenceNumber,Description,CreationTime | ConvertTo-Json -Compress", 180)


def command(tool, args, folder, name):
    from .repairs import native, write_verified
    # Wait for completion instead of killing a servicing operation on an arbitrary timeout.
    result = subprocess.run([native(tool), *args], capture_output=True, creationflags=0x08000000)
    raw = result.stdout + result.stderr
    output = raw.decode('utf-16', errors='replace') if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else raw.decode('utf-16-le' if b'\x00' in raw[:100] else 'utf-8', errors='replace')
    write_verified(folder / (name + '.json'), {'exit_code': result.returncode, 'output': output[-60000:]})
    if result.returncode not in (0, 3010):
        raise RuntimeError(f'{tool} stopped with code {result.returncode}. See the saved diagnostic output. No further repair steps ran.')
    return output, result.returncode


def sfc_state(output):
    text = output.lower()
    if 'did not find any integrity violations' in text:
        return 'healthy'
    if 'found integrity violations' in text or 'found corrupt files' in text:
        return 'corrupt'
    return 'unknown'


def execute(action, folder, notify):
    from .repairs import write_verified
    if action == 'gameinput':
        product = gameinput()
        if not re.fullmatch(r'\{[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}\}', product['product']):
            raise ValueError('Invalid product code')
        _, code = command('msiexec', ['/fom', product['product'], '/qn', '/norestart', '/L*v', str(folder / 'gameinput-msi.log')], folder, 'gameinput-repair')
        after = gameinput()
        return {'status': 'Restart needed' if code == 3010 else 'Repair completed — test your games',
                'detail': 'Windows Installer completed the repair. This does not establish that the earlier upgrade failure is resolved; retry the original update after testing.', 'after': after}
    notify({'stage': 'verifying', 'message': 'Checking Windows components first. This can take several minutes; keep Lantern open.'})
    scan, _ = command('dism', ['/Online', '/Cleanup-Image', '/ScanHealth', '/English', '/NoRestart'], folder, 'component-check')
    lower = scan.lower()
    if 'component store is repairable' in lower:
        notify({'stage': 'repairing', 'message': 'Windows confirmed component-store damage. Repairing from Windows sources; this may use the internet.'})
        command('dism', ['/Online', '/Cleanup-Image', '/RestoreHealth', '/English', '/NoRestart'], folder, 'component-repair')
    elif 'no component store corruption detected' not in lower:
        return {'status': 'Needs review', 'detail': 'Windows did not report a recognized healthy or repairable component store. No repair was attempted. Review the saved check output.'}
    verify, _ = command('sfc', ['/verifyonly'], folder, 'protected-file-check')
    state = sfc_state(verify)
    if state == 'corrupt':
        notify({'stage': 'repairing', 'message': 'Windows confirmed protected-file damage. Repairing system files.'})
        command('sfc', ['/scannow'], folder, 'protected-file-repair')
    elif state == 'unknown':
        return {'status': 'Needs review', 'detail': 'The file-check result could not be interpreted (including unsupported output languages). No SFC repair was started. Review the saved output.'}
    final, _ = command('dism', ['/Online', '/Cleanup-Image', '/ScanHealth', '/English', '/NoRestart'], folder, 'component-verification')
    final_sfc, _ = command('sfc', ['/verifyonly'], folder, 'protected-file-verification')
    healthy = 'no component store corruption detected' in final.lower() and sfc_state(final_sfc) == 'healthy'
    return {'status': 'System files verified healthy' if healthy else 'Still needs attention',
            'detail': 'Follow-up component and protected-file checks completed. Try the affected feature again; this does not prove a crash or driver problem is fixed. A restart may still be required.'}
