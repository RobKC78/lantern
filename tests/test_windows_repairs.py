import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from lantern.analysis import analyze
from lantern.repairs import execute_batch, prepare_plan
from lantern import windows_repairs as wr


class WindowsRepairTests(unittest.TestCase):
    def report(self, events, available=True):
        return {'collectors': {'logs': {'data': {'entries': events}},
            'windows_repair_readiness': {'data': {'windows_components': {'available': True},
                                                  'gameinput': {'available': available, 'reason': 'Installer source missing'}}}}}

    def test_system_crash_gets_conditional_repair_not_arbitrary_executable(self):
        event = {'ProviderName': 'Application Error', 'Id': 1000,
                 'message': 'Faulting application name: Example.exe, version: 1\nFaulting application path: C:\\Windows\\System32\\Example.exe'}
        f = analyze(self.report([event]))[0]
        self.assertEqual(f['repair'], 'windows_components')
        self.assertEqual(f['repair_mode'], 'conditional')
        self.assertEqual(f['title'], 'Example.exe crashed')
        event['message'] = 'Faulting application name: Example.exe, version: 1\nFaulting application path: C:\\Users\\test\\Example.exe'
        self.assertIsNone(analyze(self.report([event]))[0]['repair'])

    def test_missing_installer_is_explicit_and_not_repairable(self):
        event = {'ProviderName': 'MsiInstaller', 'Id': 11714, 'message': 'Microsoft GameInput Error 1714 System Error 1612'}
        f = analyze(self.report([event], False))[0]
        self.assertIsNone(f['repair'])
        self.assertEqual(f['repair_blocked_reason'], 'Installer source missing')
        self.assertEqual(analyze(self.report([event]))[0]['repair'], 'gameinput')

    def test_shutdown_only_merged_with_matching_timestamps(self):
        events = [{'ProviderName': 'Microsoft-Windows-Kernel-Power', 'Id': 41, 'time': '2026-01-01T12:00:00+00:00', 'message': 'shutdown'},
                  {'ProviderName': 'EventLog', 'Id': 6008, 'time': '2026-01-01T12:00:10+00:00', 'message': 'shutdown'}]
        self.assertEqual(len(analyze(self.report(events))), 1)
        events[1]['time'] = '2026-01-01T13:00:00+00:00'
        self.assertEqual(len(analyze(self.report(events))), 2)

    @patch('lantern.repairs.platform_key', return_value='windows')
    @patch('lantern.windows_repairs.execute')
    @patch('lantern.windows_repairs.checkpoint', side_effect=RuntimeError('Protection unavailable'))
    def test_checkpoint_failure_blocks_every_mutation_in_mixed_batch(self, checkpoint, execute, platform):
        service_start = Mock()
        def snapshot(action):
            return {'state': 'available', 'start_type': 'repair_adapter'} if action == 'windows_components' else {'state': 'stopped', 'start_type': 'manual'}
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(RuntimeError):
                execute_batch(['printing', 'windows_components'], Mock(), snapshot=snapshot, start=service_start, directory=lambda: Path(temp))
        service_start.assert_not_called()
        execute.assert_not_called()

    @patch('lantern.repairs.platform_key', return_value='windows')
    @patch('lantern.windows_repairs.checkpoint', return_value={'SequenceNumber': 123})
    def test_new_adapter_cannot_run_before_verified_checkpoint(self, checkpoint, platform):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            def execute(action, directory, notify):
                self.assertEqual(json.loads((folder / 'restore-point.json').read_text())['SequenceNumber'], 123)
                self.assertTrue((folder / 'manifest.json').exists())
                self.assertTrue((folder / 'windows_components-intent.json').exists())
                return {'status': 'System files verified healthy', 'detail': 'Crash still needs testing'}
            with patch('lantern.windows_repairs.execute', side_effect=execute):
                events = []
                execute_batch(['windows_components'], events.append, snapshot=lambda a: {'state': 'available', 'start_type': 'repair_adapter'}, directory=lambda: folder)
            self.assertNotEqual(events[-1]['results'][0]['status'], 'Fixed')

    @patch('lantern.windows_repairs.command')
    def test_healthy_windows_never_invokes_repair_commands(self, command):
        command.side_effect = [('No component store corruption detected.', 0), ('Windows Resource Protection did not find any integrity violations.', 0)] * 2
        result = wr.execute('windows_components', Path('.'), Mock())
        self.assertEqual(result['status'], 'System files verified healthy')
        self.assertFalse(any('/RestoreHealth' in call.args[1] or '/scannow' in call.args[1] for call in command.call_args_list))

    @patch('lantern.windows_repairs.command', return_value=('Unrecognized/localized output', 0))
    def test_unknown_result_never_repairs(self, command):
        self.assertEqual(wr.execute('windows_components', Path('.'), Mock())['status'], 'Needs review')
        self.assertEqual(command.call_count, 1)

    @patch('lantern.windows_repairs.command')
    def test_confirmed_damage_repairs_then_verifies(self, command):
        command.side_effect = [('The component store is repairable.', 0), ('Done', 0),
                              ('Windows Resource Protection found integrity violations.', 0), ('Repaired', 0),
                              ('No component store corruption detected.', 0), ('Windows Resource Protection did not find any integrity violations.', 0)]
        self.assertEqual(wr.execute('windows_components', Path('.'), Mock())['status'], 'System files verified healthy')
        self.assertIn('/RestoreHealth', command.call_args_list[1].args[1])
        self.assertIn('/scannow', command.call_args_list[3].args[1])

    def test_shared_workflow_deduplicates(self):
        with patch('lantern.repairs.platform_key', return_value='windows'):
            plan = prepare_plan({'findings': [{'id': 'one', 'repair': 'windows_components'}, {'id': 'two', 'repair': 'windows_components'}]}, ['one', 'two'])
        self.assertEqual(plan['actions'], ['windows_components'])
