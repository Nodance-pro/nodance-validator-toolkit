import unittest
from unittest.mock import patch
from collections import namedtuple
import nodance_check as n

class CheckerTests(unittest.TestCase):
    def test_cpu_inventory(self):
        with patch('nodance_check.os.cpu_count', return_value=8):
            self.assertEqual(n.cpu_check(None)['status'], 'INFO')
            self.assertEqual(n.cpu_check(8)['status'], 'PASS')
            self.assertEqual(n.cpu_check(16)['status'], 'WARN')
    def test_disk_threshold(self):
        usage = namedtuple('Usage', 'total used free')(100*n.GIB, 90*n.GIB, 10*n.GIB)
        with patch('nodance_check.shutil.disk_usage', return_value=usage):
            self.assertEqual(n.disk_check('/', None, 15)['status'], 'WARN')
            self.assertEqual(n.disk_check('/', None, 5)['status'], 'PASS')
            self.assertEqual(n.disk_check('/', 20, 5)['status'], 'WARN')
    def test_disk_unavailable(self):
        with patch('nodance_check.shutil.disk_usage', side_effect=OSError):
            self.assertEqual(n.disk_check('/', None, 15)['status'], 'UNKNOWN')
    def test_time(self):
        for rc, value, expected in [(0,'yes','PASS'),(0,'no','WARN'),(1,'','UNKNOWN')]:
            with patch('nodance_check.command', return_value=(rc,value)):
                self.assertEqual(n.time_check()['status'], expected)
    def test_service(self):
        self.assertEqual(n.service_check(None)['status'], 'SKIP')
        with patch('nodance_check.command', return_value=(0,'LoadState=loaded\nActiveState=active')):
            self.assertEqual(n.service_check('example.service')['status'], 'PASS')
        with patch('nodance_check.command', return_value=(0,'LoadState=not-found\nActiveState=inactive')):
            self.assertEqual(n.service_check('example.service')['status'], 'UNKNOWN')
    def test_overall(self):
        self.assertEqual(n.overall([{'status':'PASS'},{'status':'INFO'}]), 'NO_WARNINGS')
        self.assertEqual(n.overall([{'status':'UNKNOWN'}]), 'INCOMPLETE')
        self.assertEqual(n.overall([{'status':'UNKNOWN'},{'status':'WARN'}]), 'WARN')

if __name__ == '__main__':
    unittest.main()
