import pytest
from lecroydso import LeCroyDSO
from lecroydso import ActiveDSO
from lecroydso import LeCroyVISA
from lecroydso import DSOConnectionError, DSOIOError, ParametersError   # noqa

import os
use_activedso = True

if os.name != 'nt':
    use_activedso = False

connection_string = 'TCPIP0::127.0.0.1::inst0::INSTR'
if use_activedso:
    connection_string = 'VXI11:127.0.0.1'


@pytest.fixture(scope='module', params=['ActiveDSO', 'LeCroyVISA'])
def dso(request) -> LeCroyDSO:
    try:
        # setup
        if request.param == 'ActiveDSO':
            connection_string = 'VXI11:127.0.0.1'
            transport = ActiveDSO(connection_string)
            assert not transport.error_flag
        if request.param == 'LeCroyVISA':
            connection_string = 'TCPIP0::127.0.0.1::inst0::INSTR'
            transport = LeCroyVISA(connection_string)
        assert transport.connected, 'Unable to make connection'
        conn = LeCroyDSO(transport)
        yield conn
        # teardown
        conn.disconnect()
    except DSOConnectionError as err:
        assert False, err.message


def test_properties(dso: LeCroyDSO):
    assert dso.num_channels > 2
    assert dso.num_functions > 2
    assert dso.num_memories > 2
    assert dso.num_zooms > 2
    assert dso.num_parameters > 2
    assert dso.firmware_version is not None
    assert dso.model is not None
    assert dso.manufacturer is not None
    dso.hor_scale = 50e-9
    assert 50e-9 == dso.hor_scale
    dso.hor_offset = 100e-9
    assert dso.hor_offset == 100e-9


def test_acquisition(dso: LeCroyDSO):
    dso.set_hor_scale(50e-9)
    dso.set_hor_offset()
    dso.set_trigger_source('C1')
    dso.set_trigger_level('C1', 0.1)
    for mode in ['AUTO', 'NORMAL']:
        dso.set_trigger_mode(mode)
        trigger_mode = dso.query('TRMD?')
        if trigger_mode == 'NORM':
            trigger_mode = 'NORMAL'
        assert trigger_mode == mode


def test_get_waveform(dso: LeCroyDSO):
    model = dso.get_instrument_model()     # noqa
    wf = dso.get_waveform('C1')        # noqa


def test_dialog_functions(dso: LeCroyDSO):
    pages = dso.get_docked_dialog_page_names()
    sel_page = dso.get_docked_dialog_selected_page()
    print(sel_page)
    print(pages)


def test_invalid_parameters(dso: LeCroyDSO):
    try:
        dso.set_trigger_source('B1')
    except ParametersError:
        assert(True)
    except DSOIOError:
        assert(True)
