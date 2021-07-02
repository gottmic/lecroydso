import pytest
import os
import tempfile
from lecroydso import ActiveDSO, LeCroyVISA, LeCroyVICP, DSOConnection
from lecroydso.errors import DSOConnectionError


@pytest.fixture(scope='module', params=['ActiveDSO', 'LeCroyVISA', 'LeCroyVICP'])
def conn(request) -> DSOConnection:
    try:
        # setup
        if request.param == 'ActiveDSO':
            connection_string = 'VXI11:127.0.0.1'
            conn = ActiveDSO(connection_string)
            assert conn.error_flag is False
        if request.param == 'LeCroyVISA':
            connection_string = 'TCPIP0::127.0.0.1::inst0::INSTR'
            conn = LeCroyVISA(connection_string)
        if request.param == 'LeCroyVICP':
            connection_string = 'TCPIP0::127.0.0.1::inst0::INSTR'
            conn = LeCroyVISA(connection_string)
            conn.write_vbs('app.Utility.Remote.Interface="TCPIP"')
            conn.disconnect()
            connection_string = '127.0.0.1'
            conn = LeCroyVICP(connection_string)
        conn.write('CHDR OFF')
        chdr = conn.query('CHDR?')
        assert 'WARNING' not in chdr, 'Connection on the instrument set to TCPIP, please set to LXI'
        yield conn
        # teardown
        conn.write_vbs('app.Utility.Remote.Interface="LXI"')
        conn.disconnect()
    except DSOConnectionError as err:
        assert False, err.message


def test_connection(conn: DSOConnection):
    ver = conn.query('*idn?')
    print(ver)


@pytest.mark.parametrize('conn_type', [ActiveDSO, LeCroyVISA, LeCroyVICP])
def test_bad_connection(conn_type):
    # connect to some unlikely IP address
    try:
        my_conn = conn_type('IP:123.123.45.6')
        if my_conn is not None:
            my_conn.disconnect()
    except DSOConnectionError as err:
        assert 'connection failed' in err.message


def test_basic_commands(conn: DSOConnection):
    conn.write('CHDR OFF')
    print(conn.error_string)
    assert conn.error_flag is False

    idn = conn.query('*IDN?')
    assert conn.error_flag is False
    assert len(idn) > 0

    conn.write_vbs('app.Acquisition.C1.VerScale=0.01')
    response = conn.query('C1:VDIV?')
    assert '10E-3' in response

    id = conn.query_vbs('app.InstrumentID')
    assert len(id.split(',')) == 4

    cur_timeout = conn.timeout
    conn.timeout = 10.0
    assert conn.timeout == 10.0
    conn.timeout = cur_timeout
    assert conn.timeout == cur_timeout

    # test write_binary and read_binary functions


def panel_functions(conn: DSOConnection):
    setup = conn.get_panel()
    assert setup.startswith("\' XStreamDSO ConfigurationVBScript")

    assert conn.set_panel(setup)


def file_transfer(conn: DSOConnection):
    random_bytes = os.urandom(100000)
    source_file = os.path.join(tempfile.gettempdir(), 'conn_test.bin')
    dest_file = r'C:\Temp\conn_test.bin'
    with open(source_file, 'wb+') as fp:
        fp.write(random_bytes)
    success = conn.transfer_file_to_dso('HDD', dest_file, source_file)
    assert success
    # check if the file exists, since we are executing on the same machine(localhost)
    # we can confirm that the file exists and check contents
    assert os.path.isfile(dest_file)
    with open(dest_file, 'rb') as fp:
        transferred_bytes = fp.read()
        assert random_bytes == transferred_bytes   # check if the source and destination bytes are the same

    remote_file = dest_file
    dest_file = source_file
    if os.path.isfile(dest_file):
        os.remove(dest_file)
    success = conn.transfer_file_to_pc('HDD', remote_file, dest_file)
    assert os.path.isfile(dest_file)
    with open(dest_file, 'rb') as fp:
        transferred_bytes = fp.read()
        assert random_bytes == transferred_bytes   # check if the source and destination bytes are the same


def test_utilities(conn: DSOConnection):
    file_transfer(conn)
    panel_functions(conn)
