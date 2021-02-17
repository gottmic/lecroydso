import unittest
from lecroydso.activedso import ActiveDSO
from tests.testConnection import TestConnection
import os

# requires a scope application running on the local host set to LXI
connection_string = 'VXI11:127.0.0.1'

class TestActiveDSO(unittest.TestCase, TestConnection):
    
    def setUp(self):
        self.my_conn = ActiveDSO(connection_string)     # replace with IP address of the scope
        if self.my_conn is None:
            self.fail('ActiveDSO is not installed or registered')

        if not self.my_conn.connected:
            self.fail('ActiveDSO unable to make a connection to {0}'.format(connection_string))
        self.assertFalse(self.my_conn.errorFlag)
        self.my_conn.send_command('CHDR OFF')
        chdr = self.my_conn.send_query('CHDR?')
        if 'WARNING' in chdr:
            self.fail("Connection on the instrument set to TCPIP, please set to LXI")

    def tearDown(self):
        self.my_conn.disconnect()

    def test_connection(self):
        # connect to some unlikely IP address
        my_conn = ActiveDSO('IP:123.123.45.6')
        self.assertFalse(my_conn.connected)     # this should most likely fail
        if my_conn is not None:
            my_conn.disconnect()


if __name__ == '__main__':
    if os.name == 'nt':
        unittest.main()