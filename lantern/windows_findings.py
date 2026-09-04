"""Turn Windows event families into named, bounded repair candidates."""
import re
from datetime import datetime


def refine(findings, collectors):
    entries = collectors.get('logs', {}).get('data', {}).get('entries', [])
    readiness = collectors.get('windows_repair_readiness', {}).get('data', {})
    crashes = [e for e in entries if e.get('ProviderName') == 'Application Error' and e.get('Id') == 1000]
    if crashes:
        findings = [f for f in findings if not (f['title'] == 'Application crash' and isinstance(f['evidence'], dict)
                    and f['evidence'].get('sample', {}).get('ProviderName') == 'Application Error')]
        groups = {}
        for event in crashes:
            match = re.search(r'Faulting application name:\s*([^,\r\n]+)', event.get('message', ''), re.I)
            name = match.group(1).strip()[:100] if match else 'Unidentified application'
            groups.setdefault(name, []).append(event)
        for name, events in groups.items():
            system_component = any(re.search(r'Faulting application path:\s*[A-Z]:\\Windows\\System32\\[^\r\n]+', e.get('message', ''), re.I) for e in events)
            finding = {'severity': 'warning', 'title': name + ' crashed',
                       'evidence': {'count': len(events), 'sample': events[0]},
                       'likely_cause': f'{name} stopped unexpectedly {len(events)} time(s) in the collected period. The event does not establish why.',
                       'suggestion': 'Check the affected feature and its supported update or repair options. A faulting DLL name alone does not establish that Windows files are corrupt.',
                       'confidence': 'Recorded crash; root cause unconfirmed'}
            if system_component and readiness.get('windows_components', {}).get('available'):
                finding.update(repair='windows_components', repair_label='Check & repair Windows files',
                               repair_mode='conditional', suggestion='The Windows-file workflow checks for corruption and repairs only recognized damage. If files are healthy, it reports that and leaves the crash unresolved.')
            findings.append(finding)
    installers = [e for e in entries if e.get('ProviderName') == 'MsiInstaller' and
                  re.search(r'Microsoft GameInput', e.get('message', ''), re.I) and
                  re.search(r'\b(1714|1612)\b', e.get('message', ''))]
    if installers:
        ready = readiness.get('gameinput', {})
        findings.append({'severity': 'warning', 'title': 'Microsoft GameInput installation needs repair',
            'evidence': {'count': len(installers), 'sample': installers[0]},
            'likely_cause': 'An update could not remove an older GameInput installation. Its original installer source may be missing or inaccessible.',
            'suggestion': 'Repair is available only with one unambiguous registered package and a valid Microsoft-signed installer source. No installer registrations will be deleted.',
            'confidence': 'Installer failure recorded; current package checked separately',
            'repair': 'gameinput' if ready.get('available') else None,
            'repair_label': 'Repair GameInput',
            'repair_blocked_reason': None if ready.get('available') else ready.get('reason', 'Installer readiness has not been collected.')})
    # Pair supporting shutdown records only when logged within the same boot window.
    powers = [e for e in entries if e.get('ProviderName') == 'Microsoft-Windows-Kernel-Power' and e.get('Id') == 41]
    older = [e for e in entries if e.get('ProviderName') == 'EventLog' and e.get('Id') == 6008]
    def close(a, b):
        try:
            return abs((datetime.fromisoformat(a['time']) - datetime.fromisoformat(b['time'])).total_seconds()) <= 120
        except (KeyError, ValueError, TypeError):
            return False
    if older and all(any(close(a, b) for b in powers) for a in older):
        findings = [f for f in findings if f['title'] != 'Previous shutdown was unexpected']
        for f in findings:
            if f['title'] == 'Unexpected shutdown':
                f['evidence']['supporting_shutdown_records'] = len(older)
    for f in findings:
        if f['title'] == 'Services listening on all interfaces':
            f['suggestion'] = 'This is network information, not proof of a fault. Review intended services and firewall settings only if you have a related concern.'
            f['informational'] = True
        if f['title'] == 'Driver updates listed in saved update information':
            f['informational'] = True
    return findings
