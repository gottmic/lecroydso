from lecroydso.dsoconnection import DSOConnection
import os
import unittest

class TestConnection():
    def __init__(self):
        self.my_conn: DSOConnection
 
    def test_basic_commands(self):
        self.my_conn.send_command('CHDR OFF')
        print(self.my_conn.errorString)
        self.assertFalse(self.my_conn.errorFlag)

        idn = self.my_conn.send_query('*IDN?')
        self.assertFalse(self.my_conn.errorFlag)
        self.assertTrue(len(idn) > 0)

        self.my_conn.send_vbs_command('app.Acquisition.C1.VerScale=0.01')
        response = self.my_conn.send_query('C1:VDIV?')
        self.assertTrue('10E-3' in response)

        id = self.my_conn.send_vbs_query('app.InstrumentID')
        self.assertTrue(len(id.split(',')) == 4)

        cur_timeout = self.my_conn.timeout
        self.my_conn.timeout = 10.0
        self.assertEqual(self.my_conn.timeout, 10.0)
        self.my_conn.timeout = cur_timeout
        self.assertEqual(self.my_conn.timeout, cur_timeout)

        # test write_binary and read_binary functions


    def test_panel_functions(self):
        setup = self.my_conn.get_panel()
        self.assertTrue(setup.startswith("\' XStreamDSO ConfigurationVBScript"))

        self.assertTrue(self.my_conn.set_panel(setup))

    def test_file_transfer(self):
        random_bytes = os.urandom(100000)
        source_file = 'conn_test.bin'
        dest_file = r'C:\Temp\conn_test.bin'
        with open(source_file, 'wb+') as fp:
            fp.write(random_bytes)
        success = self.my_conn.transfer_file_to_dso('HDD', dest_file, source_file)
        self.assertTrue(success)
        # check if the file exists, since we are executing on the same machine(localhost)
        # we can confirm that the file exists and check contents
        self.assertTrue(os.path.isfile(dest_file))
        with open(dest_file, 'rb') as fp:
            transferred_bytes = fp.read()
            self.assertEqual(random_bytes, transferred_bytes)   # check if the source and destination bytes are the same

        remote_file = dest_file
        dest_file = source_file
        if os.path.isfile(dest_file):
            os.remove(dest_file)
        success = self.my_conn.transfer_file_to_pc('HDD', remote_file, dest_file)
        self.assertTrue(os.path.isfile(dest_file))
        with open(dest_file, 'rb') as fp:
            transferred_bytes = fp.read()
            self.assertEqual(random_bytes, transferred_bytes)   # check if the source and destination bytes are the same
