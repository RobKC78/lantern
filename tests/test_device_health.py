import unittest
from unittest.mock import patch

from lantern.analysis import analyze
from lantern.guides import guides
from lantern.repairs import CATALOG, description
from lantern.device_health import as_list


class CommonProblemTests(unittest.TestCase):
    def report(self, health):
        return {'collectors': {'device_health': {'data': health}}}

    def test_old_driver_date_is_not_an_update_finding(self):
        findings = analyze(self.report({'installed_drivers': [{'DriverDate': '2006-06-21', 'DriverVersion': '1.0'}]}))
        self.assertFalse(any('update' in f['title'].lower() for f in findings))

    def test_cached_update_is_not_presented_as_current(self):
        findings = analyze(self.report({'driver_updates': {'status': 'cached_only', 'items': [{'Title': 'Example driver'}]}}))
        self.assertIn('saved', findings[0]['title'])
        self.assertIsNone(findings[0]['repair'])

    def test_disabled_device_is_not_automatically_reinstalled(self):
        findings = analyze(self.report({'problem_devices': [{'name': 'Example GPU', 'code': 22}]}))
        self.assertEqual(findings[0]['severity'], 'info')
        self.assertIn('intentional', findings[0]['plain_explanation'])
        self.assertIsNone(findings[0]['repair'])

    def test_problem_device_requires_targeted_guidance(self):
        findings = analyze(self.report({'problem_devices': [{'name': 'Example audio device', 'code': 28}]}))
        self.assertEqual(findings[0]['severity'], 'warning')
        self.assertIn('not a confirmed', findings[0]['plain_explanation'])

    def test_linux_muted_output_and_reboot(self):
        titles = [f['title'] for f in analyze(self.report({'audio': {'muted': True}, 'reboot_pending': True}))]
        self.assertIn('Sound output is muted', titles)
        self.assertIn('A restart is pending', titles)

    def test_audio_and_bluetooth_do_not_get_clock_explanations(self):
        for action in ('audio', 'audio_devices', 'bluetooth'):
            findings = analyze({'collectors': {'repair_services': {'data': [{'action': action, 'status': 'ok', 'state': 'stopped', 'start_type': 'manual'}]}}})
            self.assertEqual(findings[0]['repair'], action)
            self.assertNotIn('Clock', findings[0]['title'])
            with patch('lantern.repairs.platform_key', return_value='windows'):
                self.assertNotIn('time server', description(action)['impact'])

    def test_ten_guides_on_both_platforms_with_platform_steps(self):
        win, linux = guides('windows'), guides('linux')
        self.assertEqual(len(win), 10)
        self.assertEqual({x['id'] for x in win}, {x['id'] for x in linux})
        self.assertNotEqual(win[0]['steps'], linux[0]['steps'])
        self.assertTrue(all(g['verify'] and g['steps'] for g in linux))

    def test_empty_single_and_multiple_query_results(self):
        self.assertEqual(as_list(None), [])
        self.assertEqual(as_list({'name': 'device'}), [{'name': 'device'}])
        self.assertEqual(as_list([1, 2]), [1, 2])


if __name__ == '__main__':
    unittest.main()
