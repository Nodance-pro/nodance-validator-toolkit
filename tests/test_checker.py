
import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch, mock_open
from collections import namedtuple

import nodance_check as n


class CheckerTests(unittest.TestCase):

    def test_cpu_inventory(self):
        with patch('nodance_check.os.cpu_count', return_value=8):
            self.assertEqual(n.cpu_check(None)['status'], 'INFO')
            self.assertEqual(n.cpu_check(8)['status'], 'PASS')
            self.assertEqual(n.cpu_check(16)['status'], 'WARN')

    def test_disk_threshold(self):
        usage = namedtuple('Usage', 'total used free')(
            100*n.GIB, 90*n.GIB, 10*n.GIB)

        with patch('nodance_check.shutil.disk_usage', return_value=usage):
            self.assertEqual(n.disk_check('/', None, 15)['status'], 'WARN')
            self.assertEqual(n.disk_check('/', None, 5)['status'], 'PASS')
            self.assertEqual(n.disk_check('/', 20, 5)['status'], 'WARN')

    def test_disk_unavailable(self):
        with patch('nodance_check.shutil.disk_usage', side_effect=OSError):
            self.assertEqual(
                n.disk_check('/', None, 15)['status'], 'UNKNOWN')

    def test_time(self):
        for rc, value, expected in [
            (0, 'yes', 'PASS'),
            (0, 'no', 'WARN'),
            (1, '', 'UNKNOWN')
        ]:
            with patch('nodance_check.command', return_value=(rc, value)):
                self.assertEqual(n.time_check()['status'], expected)

    def test_service(self):
        self.assertEqual(n.service_check(None)['status'], 'SKIP')

        with patch('nodance_check.command', return_value=(
            0, 'LoadState=loaded\nActiveState=active'
        )):
            self.assertEqual(
                n.service_check('example.service')['status'], 'PASS')

        with patch('nodance_check.command', return_value=(
            0, 'LoadState=not-found\nActiveState=inactive'
        )):
            self.assertEqual(
                n.service_check('example.service')['status'], 'UNKNOWN')

    def test_overall(self):
        self.assertEqual(
            n.overall([{'status': 'PASS'}, {'status': 'INFO'}]),
            'NO_WARNINGS')

        self.assertEqual(
            n.overall([{'status': 'UNKNOWN'}]),
            'INCOMPLETE')

        self.assertEqual(
            n.overall([{'status': 'UNKNOWN'}, {'status': 'WARN'}]),
            'WARN')

    def test_cpu_metrics(self):
        with patch('nodance_check.os.cpu_count', return_value=8):
            r = n.cpu_check(4)
            self.assertEqual(r['metrics']['logical_cpus'], 8)
            self.assertEqual(r['thresholds']['min_logical_cpus'], 4)

    def test_cpu_unknown_metrics(self):
        with patch('nodance_check.os.cpu_count', return_value=None):
            r = n.cpu_check(4)
            self.assertEqual(r['status'], 'UNKNOWN')
            self.assertIsNone(r['metrics']['logical_cpus'])
            self.assertEqual(r['thresholds']['min_logical_cpus'], 4)

    def test_memory_metrics(self):
        data = (
            'MemTotal: 16777216 kB\n'
            'MemAvailable: 8388608 kB\n'
        )

        with patch('builtins.open', mock_open(read_data=data)):
            r = n.memory_check(16)
            self.assertEqual(r['status'], 'PASS')
            self.assertEqual(r['metrics']['total_gib'], 16)
            self.assertEqual(r['metrics']['available_gib'], 8)
            self.assertEqual(r['thresholds']['min_total_gib'], 16)

    def test_memory_unavailable(self):
        with patch('builtins.open', side_effect=OSError):
            r = n.memory_check(16)
            self.assertEqual(r['status'], 'UNKNOWN')
            self.assertIsNone(r['metrics']['total_gib'])
            self.assertIsNone(r['metrics']['available_gib'])

    def test_disk_metrics(self):
        usage = namedtuple('Usage', 'total used free')(
            100*n.GIB, 60*n.GIB, 40*n.GIB)

        with patch('nodance_check.shutil.disk_usage', return_value=usage):
            r = n.disk_check('/', 20, 15)
            self.assertEqual(r['status'], 'PASS')
            self.assertEqual(r['metrics']['total_gib'], 100)
            self.assertEqual(r['metrics']['free_gib'], 40)
            self.assertEqual(r['metrics']['free_percent'], 40)
            self.assertEqual(r['thresholds']['min_free_gib'], 20)
            self.assertEqual(r['thresholds']['min_free_percent'], 15)

    def test_disk_unknown_metrics(self):
        with patch('nodance_check.shutil.disk_usage', side_effect=OSError):
            r = n.disk_check('/', None, 15)
            self.assertEqual(r['status'], 'UNKNOWN')
            self.assertIsNone(r['metrics']['total_gib'])
            self.assertIsNone(r['metrics']['free_gib'])
            self.assertIsNone(r['metrics']['free_percent'])

    def test_ntp_metrics(self):
        for rc, value, expected in [
            (0, 'yes', True),
            (0, 'no', False),
            (1, '', None)
        ]:
            with patch('nodance_check.command', return_value=(rc, value)):
                r = n.time_check()
                self.assertIs(
                    r['metrics']['ntp_synchronized'], expected)

    def test_service_metrics(self):
        r = n.service_check(None)
        self.assertFalse(r['metrics']['configured'])
        self.assertIsNone(r['metrics']['active_state'])

        with patch('nodance_check.command', return_value=(
            0, 'LoadState=loaded\nActiveState=active'
        )):
            r = n.service_check('example.service')
            self.assertTrue(r['metrics']['configured'])
            self.assertEqual(r['metrics']['load_state'], 'loaded')
            self.assertEqual(r['metrics']['active_state'], 'active')

    def test_json_schema(self):
        output = io.StringIO()

        with patch('nodance_check.platform.system', return_value='Linux'):
            with redirect_stdout(output):
                n.main([
                    '--json',
                    '--chain', 'solana',
                    '--role', 'backup'
                ])

        report = json.loads(output.getvalue())

        self.assertEqual(report['schema_version'], 2)
        self.assertEqual(report['version'], n.VERSION)
        self.assertEqual(report['chain_label'], 'solana')
        self.assertEqual(report['role'], 'backup')
        self.assertIn('timestamp_utc', report)
        self.assertEqual(len(report['checks']), 5)

        for check in report['checks']:
            self.assertIn('check', check)
            self.assertIn('status', check)
            self.assertIn('detail', check)
            self.assertIsInstance(check['metrics'], dict)
            self.assertIsInstance(check['thresholds'], dict)

    def test_exit_codes(self):
        for status, expected in [
            ('NO_WARNINGS', 0),
            ('WARN', 1),
            ('INCOMPLETE', 2)
        ]:
            with patch('nodance_check.platform.system', return_value='Linux'):
                with patch('nodance_check.overall', return_value=status):
                    with redirect_stdout(io.StringIO()):
                        self.assertEqual(n.main(['--json']), expected)


if __name__ == '__main__':
    unittest.main()
