from lecroydso.errors import DSOConnectionError
import unittest
from lecroydso.activedso import ActiveDSO
from tests.testConnection import TestConnection

# requires a scope application running on the local host set to LXI
connection_string = 'VXI11:127.0.0.1'


class TestActiveDSO(unittest.TestCase, TestConnection):

    def setUp(self):
        try:
            self.my_conn = ActiveDSO(connection_string)     # replace with IP address of the scope
        except DSOConnectionError as err:
            self.fail(err.message)
        self.assertFalse(self.my_conn.error_flag)
        self.my_conn.write('CHDR OFF')
        chdr = self.my_conn.query('CHDR?')
        if 'WARNING' in chdr:
            self.fail("Connection on the instrument set to TCPIP, please set to LXI")

    def tearDown(self):
        self.my_conn.disconnect()

    def test_connection(self):
        # connect to some unlikely IP address
        try:
            my_conn = ActiveDSO('IP:123.123.45.6')
            if my_conn is not None:
                my_conn.disconnect()
        except DSOConnectionError as err:
            self.assertTrue('ActiveDSO connection failed' in err.message)
