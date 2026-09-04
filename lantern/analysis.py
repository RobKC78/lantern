"""Evidence-based hypotheses with separately allowlisted repair choices."""
import re


def analyze(report):
    findings = []
    def add(severity, title, evidence, explanation, action):
        findings.append(dict(severity=severity, title=title, evidence=evidence, likely_cause=explanation,
                             suggestion=action, confidence='heuristic; verify before changing settings'))
    data = report['collectors']
    for disk in data.get('system', {}).get('data', {}).get('disks', []):
        if disk['percent'] >= 90:
            add('warning', 'Low disk space', f"{disk['mount']}: {disk['percent']}% used", 'Storage pressure can interrupt updates and logging.',
                'Review large files and OS storage cleanup. Back up important files before deleting anything.')
    patterns = [
        (r'machine check|hardware error|EDAC.*(error|fail)', 'Hardware error reported', 'Linux recorded a possible hardware error.', 'Review repeated errors and the named component. Save important files before further hardware testing.'),
        (r'kernel panic|segfault|watchdog.*(lockup|timeout)', 'Application crash', 'Linux recorded a crash or lockup signal.', 'Compare the event time with the problem you noticed and check the named application or driver.'),
        (r'no space left|disk full', 'Storage exhaustion', 'A volume may be full.', 'Check free space on the volume named in the event.'),
        (r'name resolution|dns.*(fail|timeout)', 'Possible DNS failure', 'Resolver reachability or configuration may be incorrect.', 'Compare interface DNS settings with your network configuration and test resolution.'),
        (r'permission denied|access is denied', 'Access failure', 'The application account may lack access.', 'Check the named resource and intended account permissions; avoid broad permission grants.'),
        (r'out of memory|oom-kill', 'Memory pressure', 'A workload may have exhausted available memory.', 'Review memory use and the affected application workload.'),
        (r'timed? out|timeout', 'Operation timeout', 'A service, dependency, or network path may be unavailable.', 'Check the event time, destination, and related service status before restarting anything.')]
    entries = data.get('logs', {}).get('data', {}).get('entries', [])
    event_rules = [
        ('Microsoft-Windows-WHEA-Logger', None, 'Hardware error reported', 'Windows recorded a hardware error; the failing component needs investigation.', 'Review the complete event and recent firmware or hardware changes. Repeated errors deserve hardware diagnostics.'),
        ('Microsoft-Windows-Kernel-Power', 41, 'Unexpected shutdown', 'Windows detected an unclean shutdown. This alone does not identify power supply failure.', 'Compare the time with intentional resets, power loss and crash records.'),
        ('EventLog', 6008, 'Previous shutdown was unexpected', 'A prior shutdown did not complete normally.', 'Correlate this with Kernel-Power and bugcheck events; do not count both as separate incidents.'),
        ('Application Error', 1000, 'Application crash', 'An application fault was recorded.', 'Review the application and faulting module in the event, then check its supported update or repair options.'),
        ('Microsoft-Windows-WER-SystemErrorReporting', 1001, 'Bugcheck recorded', 'Windows recorded a system crash.', 'Review the bugcheck code and associated dump with a debugger before selecting a repair.')]
    for provider, event_id, title, cause, action in event_rules:
        matches = [e for e in entries if e.get('ProviderName') == provider and (event_id is None or e.get('Id') == event_id)]
        if matches:
            add('warning', title, {'count': len(matches), 'sample': matches[0]}, cause, action)
    storage = [e for e in entries if str(e.get('ProviderName', '')).lower() in ('disk', 'ntfs', 'storahci', 'stornvme', 'volmgr')]
    if storage:
        add('warning', 'Storage subsystem event', {'count': len(storage), 'sample': storage[0]}, 'A storage provider reported a warning or error; free space alone cannot establish drive health.', 'Back up important data and review the event details and vendor drive diagnostics.')
    for pattern, title, cause, action in patterns:
        matches = [e for e in entries if re.search(pattern, e['message'], re.I)]
        if matches:
            add('warning', title, {'count': len(matches), 'sample': matches[0]}, cause, action)
    listeners = [c for c in data.get('connections', {}).get('data', {}).get('items', [])
                 if c['status'] == 'LISTEN' and c['local'] and c['local']['ip'] in ('0.0.0.0', '::')]
    if listeners:
        add('info', 'Services listening on all interfaces', listeners, 'These services accept traffic on multiple interfaces; firewall rules determine reachability.',
            'Confirm each service is intended and review its binding and firewall rules.')
    from .repairs import eligible, SERVICE_EXPLANATIONS
    for row in data.get('repair_services', {}).get('data', []):
        if row.get('status') != 'ok' or not eligible(row):
            continue
        if row['action'] not in SERVICE_EXPLANATIONS:
            continue
        title, explanation, suggestion = SERVICE_EXPLANATIONS[row['action']]
        add('info', title, row, explanation, suggestion)
        findings[-1]['repair'] = row['action']
    health = data.get('device_health', {}).get('data', {})
    for device in health.get('problem_devices', []):
        code = device.get('code')
        add('info' if code == 22 else 'warning', 'Device needs attention', device,
            f"{device.get('name', 'A device')} is disabled. That may be intentional." if code == 22 else
            f"{device.get('name', 'A device')} reports a problem. A driver is one possible cause, not a confirmed diagnosis.",
            'Open the Drivers help below. Check the exact device and error code before updating, rolling back or reinstalling its driver.')
    cached = health.get('driver_updates', {})
    if cached.get('items'):
        add('info', 'Driver updates listed in saved update information', cached,
            'Windows previously recorded possible driver updates. The saved list may have changed.',
            'Use Drivers help to check Windows Update now. Confirm the device and offered version there before installing.')
    audio = health.get('audio', {})
    if audio.get('muted'):
        add('info', 'Sound output is muted', audio, 'The selected Linux sound output is muted.',
            'Open Sound settings, choose the intended speakers or headset, lower the volume, then unmute. Use the Sound help below.')
    if health.get('reboot_pending') is True:
        add('info', 'A restart is pending', {'reboot_pending': True}, 'The operating system has recorded work that needs a restart.',
            'Save your work and restart from the normal system menu when convenient. This app will not restart the computer for you.')
    from .windows_findings import refine
    findings = refine(findings, data)
    from .explanations import explain
    return explain(findings)
