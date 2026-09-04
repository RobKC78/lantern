import json
import threading
import time
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

from lantern.collectors import allowed_target, discover, redact
from lantern.analysis import analyze
from lantern.server import make_server


class SafetyTests(unittest.TestCase):
    def test_local_scope(self):
        nets = ['192.168.1.0/24']
        for ip in ['8.8.8.8', '127.0.0.1', '169.254.169.254', '192.168.2.1', '::1', 'garbage']:
            self.assertFalse(allowed_target(ip, nets))
        self.assertTrue(allowed_target('192.168.1.5', nets))

    @patch('lantern.collectors.interfaces', return_value=[])
    @patch('lantern.collectors.socket.create_connection')
    def test_discovery_rejects_before_connect(self, connect, _):
        for cidr in ['8.8.8.0/24', '192.168.0.0/16', '127.0.0.0/24', '::/0']:
            with self.assertRaises(ValueError):
                discover(cidr)
        connect.assert_not_called()

    def test_redaction(self):
        self.assertNotIn('hunter2', redact('password=hunter2'))
        self.assertNotIn('abc123', redact('Bearer abc123'))

    def test_evidence_rules(self):
        report = {'collectors': {'logs': {'data': {'entries': [{'message': 'unexpected restart', 'ProviderName': 'Microsoft-Windows-Kernel-Power', 'Id': 41}]}},
                                 'system': {'data': {'disks': [{'mount': '/', 'percent': 95}]}}}}
        titles = [f['title'] for f in analyze(report)]
        self.assertIn('Low disk space', titles)
        self.assertIn('Unexpected shutdown', titles)

    @patch('lantern.server.collect', return_value={'collectors': {}})
    @patch('lantern.server.interfaces', return_value=[])
    def test_api_access(self, *_):
        server, token = make_server()
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f'http://127.0.0.1:{server.server_port}'
        try:
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(url + '/api/state')
            self.assertEqual(error.exception.code, 403)
            request = urllib.request.Request(url + '/api/state', headers={'X-Lantern-Token': token})
            with urllib.request.urlopen(request) as response:
                self.assertIn('status', json.load(response))
            request = urllib.request.Request(url + '/api/state', headers={'X-Lantern-Token': token, 'Origin': 'https://evil.invalid'})
            with self.assertRaises(urllib.error.HTTPError):
                urllib.request.urlopen(request)
            request = urllib.request.Request(url + '/api/discover', data=b'{"cidr":"192.168.1.0/24"}', headers={'X-Lantern-Token': token})
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(request)
            self.assertEqual(error.exception.code, 400)
        finally:
            server.shutdown()
            server.server_close()

    @patch('lantern.server.launch_helper')
    @patch('lantern.server.interfaces', return_value=[])
    @patch('lantern.server.collect', return_value={'collectors': {'repair_services': {'data': [{'status': 'ok', 'action': 'printing', 'state': 'stopped', 'start_type': 'automatic'}]}}})
    def test_repair_requires_plan_and_consent(self, collect_mock, interfaces_mock, launch):
        server, token = make_server()
        threading.Thread(target=server.serve_forever, daemon=True).start()
        url = f'http://127.0.0.1:{server.server_port}/api/'
        def request(path, body=None):
            req = urllib.request.Request(url + path, data=json.dumps(body).encode() if body is not None else None, headers={'X-Lantern-Token': token})
            with urllib.request.urlopen(req) as response:
                return json.load(response)
        try:
            for _ in range(100):
                state = request('state')
                if state['status'] == 'ready':
                    break
                time.sleep(.01)
            with self.assertRaises(urllib.error.HTTPError) as error:
                request('repair-approve', {'consent': True, 'plan_id': 'invented'})
            self.assertEqual(error.exception.code, 409)
            plan = request('repair-plan', {'ids': [state['report']['findings'][0]['id']]})
            with self.assertRaises(urllib.error.HTTPError) as error:
                request('repair-approve', {'plan_id': plan['id']})
            self.assertEqual(error.exception.code, 400)
            launch.assert_not_called()
            request('repair-approve', {'plan_id': plan['id'], 'consent': True})
            for _ in range(100):
                if launch.called:
                    break
                time.sleep(.01)
            launch.assert_called_once()
            self.assertEqual(launch.call_args.args[0], ['printing'])
            with self.assertRaises(urllib.error.HTTPError):
                request('repair-approve', {'plan_id': plan['id'], 'consent': True})
            launch.assert_called_once()
        finally:
            server.shutdown()
            server.server_close()


if __name__ == '__main__':
    unittest.main()
