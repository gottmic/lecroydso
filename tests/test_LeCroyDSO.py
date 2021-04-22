import unittest
from lecroydso.lecroydso import LeCroyDSO
from lecroydso.activedso import ActiveDSO
from lecroydso.lecroyvisa import LeCroyVISA
from lecroydso.errors import DSOConnectionError, DSOIOError, ParametersError

import os

connection_string = 'VXI11:127.0.0.1'

class TestLeCroyDSO(unittest.TestCase):
    def setUp(self):
        try:
            transport = LeCroyVISA(connection_string)     # replace with IP address of the scope
            self.my_conn = LeCroyDSO(transport)

        except DSOConnectionError as err:
            self.fail(err.message)

    def tearDown(self):
        self.my_conn.disconnect()

    def test_connection(self):

        # Make and test a VICP connection through ActiveDSO 
        # this will work on windows but not on linux
        if os.name == 'nt':
            aDSO_conn = ActiveDSO('VXI11:127.0.0.1')
            self.assertTrue(aDSO_conn.connected, "Unable to make connection to ActiveDSO")

            if not aDSO_conn.connected:
                return
            aDSO_conn.timeout = 0.5     # set the timeout property of the test_connection

            dso = LeCroyDSO(aDSO_conn)
            self.assertTrue(dso.connected, "No DSO connected at VXI11:127.0.0.1")

            dso.disconnect()

        # Make and test a VISA connection
        visa_conn = LeCroyVISA('TCPIP0::127.0.0.1::inst0::INSTR')
        self.assertTrue(visa_conn.connected, "Unable to make connection to LeCroyVISA")

        if not visa_conn.connected:
            return
        dso = LeCroyDSO(visa_conn)
        self.assertTrue(dso.connected, "No DSO connected at TCPIP0::127.0.0.1::inst0::INSTR")

        dso.disconnect()

    def test_get_waveform(self):
        wf = self.my_conn.get_waveform('C1')

if __name__ == '__main__':
    unittest.main()