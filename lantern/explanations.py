"""Original light observational humor, with factual guidance kept separate."""
import hashlib
import json

VOICE = {
    'Sound helper is inactive': ('The helper Windows uses to play sound is stopped.', 'The band showed up. Someone forgot to open the venue.'),
    'Sound-device helper is inactive': ('Windows has stopped the helper that makes speakers and microphones available.', 'The sound crew hasn’t clocked in yet.'),
    'Bluetooth helper is inactive': ('The helper for Bluetooth connections is stopped. That may be intentional.', 'Your headphones are waiting for someone to answer the door.'),
    'Sound output is muted': ('The selected sound output is muted.', 'The speakers have taken a vow of silence. This one might be a short meeting.'),
    'A restart is pending': ('Some system changes need a restart to finish.', 'The computer has unfinished paperwork. Save your work before sending it on a break.'),
    'Printing helper is inactive': ('The background helper for printing is not running. That can be normal when nothing is printing.', 'The printer’s assistant is off duty. Only call them back if you need something printed.'),
    'Clock-sync helper is inactive': ('One clock-sync service is not running. Another service may already be keeping time.', 'Before we hire another timekeeper, let’s make sure someone else isn’t already wearing the watch.'),
    'Low disk space': ('Your storage is almost full.', 'That drive is packing for a month-long trip in an overnight bag.'),
    'Storage exhaustion': ('An app reported that it ran out of storage space.', 'The computer tried to put one more thing in the closet. The closet declined.'),
    'Possible DNS failure': ('Your device had trouble looking up an internet address.', 'It has the contact name, but the address book is having a moment.'),
    'Access failure': ('An app was not allowed to open something it needed.', 'Somebody showed up without a backstage pass.'),
    'Memory pressure': ('An app may have needed more working memory than was available.', 'Too many plates spinning. Somebody brought another plate.'),
    'Operation timeout': ('Something took longer to respond than the app was willing to wait.', 'The loading circle has apparently taken a lunch break.'),
    'Services listening on all interfaces': ('Some apps are ready to accept connections through more than one network connection.', 'A few apps have their reception desks open. Let’s check who needs one.'),
    'Hardware error reported': ('Your computer recorded a hardware-related error. We need more evidence to identify the part.', ''),
    'Unexpected shutdown': ('Your computer stopped without completing its normal shutdown.', ''),
    'Previous shutdown was unexpected': ('Your computer recorded an earlier unplanned shutdown.', ''),
    'Application crash': ('An app stopped unexpectedly.', 'That app left the meeting without saying goodbye.'),
    'Bugcheck recorded': ('Windows recorded a system crash.', ''),
    'Storage subsystem event': ('Your computer recorded a warning or error involving storage.', ''),
}


def explain(findings):
    for finding in findings:
        raw = json.dumps([finding['title'], finding['evidence']], sort_keys=True, default=str)
        finding['id'] = hashlib.sha256(raw.encode()).hexdigest()[:20]
        plain, joke = VOICE.get(finding['title'], (finding['likely_cause'], ''))
        finding['plain_explanation'] = plain
        finding['humor'] = joke
        finding.setdefault('repair', None)
        finding['importance'] = 'Worth checking' if finding['severity'] == 'warning' else 'Good to know'
    return findings
