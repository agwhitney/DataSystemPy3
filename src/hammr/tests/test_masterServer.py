from masterServer import ServerFactory

from twisted.test import proto_helpers
from twisted.trial import unittest

import json


class ServerTestCase(unittest.TestCase):
    def setUp(self):
        factory = ServerFactory(r'C:\Users\agwhi\Desktop\DataSystemPy3\config\system.cfg')
        self.proto = factory.buildProtocol('127.0.0.1')
        self.tr = proto_helpers.StringTransport()
        self.proto.makeConnection(self.tr)


    def _test(self, operation, expected):
        self.proto.dataReceived(f"{operation}\r\n".encode())
        self.assertEqual(self.tr.value(), f"{expected}\r\n".encode())


    def test_stop(self):
        return self._test('STOP', 'stopped')
    def test_info(self):
        return self._test('INFO', 'infoed')
    def test_syst(self):
        data = json.dumps(self.proto.factory.system_config)
        return self._test('SYST', data)
    def test_mstart(self):
        return self._test('MSTART', 'motor started')
    def test_mstop(self):
        return self._test('MSTOP', 'motor stopped')
    