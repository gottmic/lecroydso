import unittest
from lecroydso import LeCroyVISA
from lecroydso import DSOConnectionError
from tests.testConnection import TestConnection

# requires a scope application running on the local host with Remote as LXI
connection_string = 'TCPIP0::127.0.0.1::inst0::INSTR'


class TestLeCroyVISA(unittest.TestCase, TestConnection):

    def setUp(self):
        try:
            self.my_conn = LeCroyVISA(connection_string)     # replace with IP address of the scope
        except DSOConnectionError as err:
            self.fail(err.message)

        if not self.my_conn.connected:
            self.fail('ActiveDSO unable to make a connection to {0}'.format(connection_string))

    def tearDown(self):
        self.my_conn.disconnect()

    def test_connection(self):
        # connect to some unlikely IP address
        try:
            my_conn = LeCroyVISA('TCPIP0::123.123.45.6::inst0::INSTR')
            if my_conn is not None:
                my_conn.disconnect()
        except DSOConnectionError as err:
            self.assertEqual(err.message, "Unable to connect to resource")     # this should most likely fail


if __name__ == '__main__':
    unittest.main()
