from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from lantern.insights import BaselineStore, baseline, compare, enrich, grouped_logs, research_packet, support_summary
from lantern.media import parse_advertisement, TARGETS


class InsightTests(unittest.TestCase):
    def report(self):
        return {'collected_at': '2026-01-01', 'findings': [], 'collectors': {
            'system': {'status': 'ok', 'data': {'hostname': 'private-machine', 'os': 'Linux', 'disks': [{'mount': '/', 'percent': 40}]}},
            'logs': {'status': 'ok', 'data': {'entries': [{'source': 'app', 'message': 'error 42 token=secret123', 'time': 'one'}, {'source': 'app', 'message': 'error 43 token=secret123', 'time': 'two'}]}},
            'device_health': {'status': 'ok', 'data': {'installed_drivers': [{'DeviceClass': 'DISPLAY', 'DeviceName': 'Example', 'DriverVersion': '1'}]}}}}

    def test_baseline_omits_logs_and_host(self):
        data = baseline(self.report())
        self.assertNotIn('secret123', str(data))
        self.assertNotIn('private-machine', str(data))

    def test_version_change_not_claimed_cause(self):
        before = baseline(self.report())
        after = deepcopy(before)
        after['drivers']['DISPLAY:Example'] = '2'
        changes = compare(before, after)
        self.assertEqual(changes[0]['category'], 'drivers')
        self.assertIn('does not establish', changes[0]['meaning'])

    def test_message_grouping_and_unknown_research(self):
        report = self.report()
        self.assertEqual(grouped_logs(report)['groups'][0]['count'], 2)
        enrich(report)
        self.assertEqual(report['findings'][0]['id'], 'unclassified-logs')
        packet = research_packet(report, 'unclassified-logs')
        self.assertNotIn('secret123', packet)
        self.assertNotIn('private-machine', packet)
        detailed = research_packet(report, 'unclassified-logs', True)
        self.assertNotIn('secret123', detailed)
        self.assertIn('UNTRUSTED', detailed)

    def test_support_summary_omits_evidence(self):
        report = self.report()
        enrich(report)
        text = support_summary(report, [])
        self.assertNotIn('secret123', text)
        self.assertNotIn('private-machine', text)

    def test_baseline_save_load_forget(self):
        with tempfile.TemporaryDirectory() as temp:
            store = BaselineStore(Path(temp) / 'app')
            self.assertIsNone(store.read())
            data = baseline(self.report())
            store.save(data)
            self.assertEqual(store.read(), data)
            store.forget()
            self.assertIsNone(store.read())

    def test_unknown_research_id_fails(self):
        with self.assertRaises(ValueError):
            research_packet(self.report(), 'unknown')


class MediaTests(unittest.TestCase):
    def packet(self, kind=TARGETS[0]):
        return ('HTTP/1.1 200 OK\r\nST: ' + kind + '\r\nSERVER: Example TV\r\nLOCATION: http://169.254.169.254/secrets\r\n\r\n').encode()

    def test_advertisement_not_casting_confirmation(self):
        result = parse_advertisement(self.packet(), '192.168.1.10', ['192.168.1.0/24'])
        self.assertIn('Not tested', result['casting'])
        self.assertNotIn('LOCATION', str(result))
        self.assertNotIn('169.254', str(result))

    def test_off_network_oversized_and_unknown_replies_ignored(self):
        self.assertIsNone(parse_advertisement(self.packet(), '8.8.8.8', ['192.168.1.0/24']))
        self.assertIsNone(parse_advertisement(b'x'*9000, '192.168.1.10', ['192.168.1.0/24']))
        self.assertIsNone(parse_advertisement(self.packet('unsupported'), '192.168.1.10', ['192.168.1.0/24']))


if __name__ == '__main__':
    unittest.main()
