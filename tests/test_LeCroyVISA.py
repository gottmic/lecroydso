import unittest
from lecroydso.lecroyvisa import LeCroyVISA
from tests.testConnection import TestConnection

# requires a scope application running on the local host with Remote as LXI
connection_string = 'TCPIP0::127.0.0.1::inst0::INSTR'

class TestLeCroyVISA(unittest.TestCase, TestConnection):
    
    def setUp(self):
        self.my_conn = LeCroyVISA(connection_string)     # replace with IP address of the scope
        if self.my_conn is None:
            self.fail('VISA is not installed or registered')

        if not self.my_conn.connected:
            self.fail('ActiveDSO unable to make a connection to {0}'.format(connection_string))

    def tearDown(self):
        self.my_conn.disconnect()

    def test_connection(self):
        # connect to some unlikely IP address
        my_conn = LeCroyVISA('TCPIP0::123.123.45.6::inst0::INSTR')
        self.assertFalse(my_conn.connected)     # this should most likely fail
        if my_conn is not None:
            my_conn.disconnect()
        
if __name__ == '__main__':
    unittest.main()