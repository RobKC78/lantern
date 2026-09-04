import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from lantern.analysis import analyze
from lantern.repairs import eligible, execute_batch, prepare_plan, service_state


class RepairTests(unittest.TestCase):
    def state(self, name='cups.service', state='inactive'):
        return {'name': name, 'state': state, 'start_type': 'enabled', 'configuration': {'unit': name}}

    def test_same_buttons_on_both_platforms(self):
        for state, mode in [('stopped', 'automatic'), ('inactive', 'enabled')]:
            report = {'collectors': {'repair_services': {'data': [{'action': 'printing', 'status': 'ok', 'state': state, 'start_type': mode}]}}}
            findings = analyze(report)
            self.assertEqual(findings[0]['repair'], 'printing')
            self.assertIn('normal', findings[0]['plain_explanation'])
            self.assertTrue(findings[0]['id'])

    def test_disabled_and_masked_never_repairable(self):
        for mode in ('disabled', 'masked', 'static', None):
            self.assertFalse(eligible({**self.state(), 'start_type': mode}))

    def test_plan_rejects_unknown_and_guidance_only(self):
        report = {'findings': [{'id': 'disk', 'repair': None}, {'id': 'print', 'repair': 'printing'}]}
        for ids in [[], ['disk'], ['unknown'], 'print']:
            with self.assertRaises(ValueError):
                prepare_plan(report, ids)
        plan = prepare_plan(report, ['print', 'print'])
        self.assertEqual(plan['actions'], ['printing'])
        self.assertIn('not a personal-file', plan['items'][0]['backup'])

    def test_backup_failure_prevents_every_start(self):
        start = Mock()
        with patch('lantern.repairs.platform_key', return_value='linux'), tempfile.TemporaryDirectory() as temp:
            with patch('lantern.repairs.write_verified', side_effect=OSError('disk full')):
                with self.assertRaises(OSError):
                    execute_batch(['printing', 'clock'], Mock(), snapshot=lambda a: self.state(), start=start, directory=lambda: Path(temp))
        start.assert_not_called()

    def test_verified_backup_precedes_start_and_records_result(self):
        events = []
        with patch('lantern.repairs.platform_key', return_value='linux'), tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            calls = [self.state(), self.state(), self.state(state='active')]
            def start(action):
                self.assertTrue((folder / 'manifest.json').exists())
                self.assertIn(action, json.loads((folder / 'before.json').read_text())['services'])
                self.assertTrue((folder / (action + '-intent.json')).exists())
            execute_batch(['printing'], events.append, snapshot=Mock(side_effect=calls), start=start, directory=lambda: folder)
            self.assertEqual(events[-1]['results'][0]['status'], 'Fixed')
            self.assertTrue((folder / 'printing-result.json').exists())

    def test_state_changed_after_backup_is_skipped(self):
        start = Mock()
        with patch('lantern.repairs.platform_key', return_value='linux'), tempfile.TemporaryDirectory() as temp:
            events = []
            execute_batch(['printing'], events.append, snapshot=Mock(side_effect=[self.state(), self.state(state='active')]), start=start, directory=lambda: Path(temp))
        start.assert_not_called()
        self.assertEqual(events[-1]['results'][0]['status'], 'Couldn’t complete')

    def test_unknown_action_rejected_before_any_collection(self):
        snapshot = Mock()
        with self.assertRaises(ValueError):
            execute_batch(['arbitrary-command'], Mock(), snapshot=snapshot)
        snapshot.assert_not_called()

    def test_linux_competing_time_service_is_blocked(self):
        with patch('lantern.repairs.native', return_value='/usr/bin/systemctl'), patch('lantern.repairs.invoke', side_effect=['LoadState=loaded\nActiveState=inactive\nUnitFileState=enabled', 'ActiveState=active']):
            with self.assertRaisesRegex(RuntimeError, 'Another time service'):
                service_state('clock', platform='linux')


if __name__ == '__main__':
    unittest.main()
