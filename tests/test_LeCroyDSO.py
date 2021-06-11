import unittest
from lecroydso.lecroydso import LeCroyDSO
from lecroydso.activedso import ActiveDSO
from lecroydso.lecroyvisa import LeCroyVISA
from lecroydso.errors import DSOConnectionError, DSOIOError, ParametersError

import os
use_activedso = True

if os.name != 'nt':
    use_activedso = False

connection_string = 'TCPIP0::127.0.0.1::inst0::INSTR'
if use_activedso:
    connection_string = 'VXI11:127.0.0.1'


class TestLeCroyDSO(unittest.TestCase):
    def setUp(self):
        try:
            transport = ActiveDSO(connection_string) if use_activedso else LeCroyVISA(connection_string)
            self.assertTrue(transport.connected, "Unable to make connection")
            self.my_conn = LeCroyDSO(transport)

        except DSOConnectionError as err:
            self.fail(err.message)

    def tearDown(self):
        self.my_conn.disconnect()

    def test_properties(self):
        dso = self.my_conn
        self.assertGreater(dso.num_channels, 2)
        self.assertGreater(dso.num_functions, 2)
        self.assertGreater(dso.num_memories, 2)
        self.assertGreater(dso.num_zooms, 2)
        self.assertGreater(dso.num_parameters, 2)
        self.assertIsNotNone(dso.firmware_version)
        self.assertIsNotNone(dso.model)
        self.assertIsNotNone(dso.manufacturer)
        dso.hor_scale = 50e-9
        self.assertEqual(50e-9, dso.hor_scale)
        dso.hor_offset = 100e-9
        self.assertEqual(dso.hor_offset, 100e-9)

    def test_acquisition(self):
        dso = self.my_conn
        dso.set_hor_scale(50e-9)
        dso.set_hor_offset()
        dso.set_trigger_source('C1')
        dso.set_trigger_level('C1', 0.1)
        for mode in ['AUTO', 'NORMAL']:
            dso.set_trigger_mode(mode)
            trigger_mode = dso.query('TRMD?')
            if trigger_mode == 'NORM':
                trigger_mode = 'NORMAL'
            self.assertEqual(trigger_mode, mode)

    def test_get_waveform(self):
        model = self.my_conn.get_instrument_model()     # noqa
        wf = self.my_conn.get_waveform('C1')        # noqa

    def test_dialog_functions(self):
        pages = self.my_conn.get_docked_dialog_page_names()
        sel_page = self.my_conn.get_docked_dialog_selected_page()
        print(sel_page)
        print(pages)

    def test_invalid_parameters(self):
        try:
            dso = self.my_conn
            dso.set_trigger_source('B1')
        except ParametersError:
            assert(True)
        except DSOIOError:
            assert(True)


if __name__ == '__main__':
    unittest.main()
