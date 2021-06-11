# -----------------------------------------------------------------------------
# Summary:		Implementation of LeCroyDSO class
# Authors:		Ashok Bruno
# Started:		2/9/2021
# Copyright 2021-2024 Teledyne LeCroy Corporation. All Rights Reserved.
# -----------------------------------------------------------------------------

from lecroydso.errors import ParametersError
from lecroydso import DSOConnection
import time
import re
import logging
from datetime import datetime

verbose = 2     # set 1 (or 2)


# ------------------------------------------------------------------------------------
# Class: LeCroyDSO
class LeCroyDSO:
    """Communication interface to a LeCroy Oscilloscope

    Args:
        myConnection (DSOConnection): A connection interface to the oscilloscope like ActiveDSO, LeCroyVISA
        log (bool, optional): creates a log output. Defaults to False.
    """

    def __init__(self, connection: DSOConnection, log: bool = False):

        self._conn = connection
        self.connected = True
        self.verbose = verbose
        self.logger = None
        if self.connected is True:
            if log:
                self.__createLogger(self._conn.connection_string)

            self._insert_wait_opc = False
            self.init_vbs()

            # determine what model this scope is
            (self.manufacturer, self.model, self.serial_number, self.firmware_version) = self.query('*IDN?').split(',')

            self.available_channels = []
            self.available_digital_channels = []
            self.available_functions = []
            self.available_parameters = []
            self.available_memories = []
            self.available_zooms = []

            try:
                self.execsAll = self.query_vbs('app.ExecsNameAll').split(',')
                # parse this to get numChannels, numFunctions, numMemories, numParameters
                for exec in self.execsAll:
                    if exec.startswith('C'):
                        self.available_channels.append(exec)
                    elif exec.startswith('D'):
                        self.available_digital_channels.append(exec)
                    elif exec.startswith('F'):
                        self.available_functions.append(exec)
                    elif exec.startswith('P'):
                        self.available_parameters.append(exec)
                    elif exec.startswith('M'):
                        self.available_memories.append(exec)
                    elif exec.startswith('Z'):
                        self.available_zooms.append(exec)
            except ValueError:
                # some default values if unable to read the cvar
                self.available_channels = ['C1', 'C2', 'C3', 'C4']
                self.available_digital_channels = ['D1', 'D2', 'D3', 'D4']
                self.available_functions = ['F1', 'F2', 'F3', 'F4']
                self.available_parameters = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6']
                self.available_memories = ['M1', 'M2', 'M3', 'M4']
                self.available_zooms = ['Z1', 'Z2', 'Z3', 'Z4']

            iNumChannels = len(self.available_channels)
            self.is_attenuator_used = True
            if (iNumChannels == 2):
                self.is_attenuator_used = False
            self.get_instrument_max_bandwidth()

    def __del__(self):
        if self.connected:
            self.disconnect_from_dso()
            self.disconnect()

    def __createLogger(self, suffix: str):
        self.logger = logging.getLogger('LeCroyDSO_' + suffix)
        self.logger.setLevel(logging.INFO)

        # create file handler which logs debug messages
        fh = logging.FileHandler('LeCroyDSO_' + suffix + '_' + datetime.now().strftime('%Y_%m_%d') + '.log')
        fh.setLevel(logging.DEBUG)

        # create console handler with a higher log level
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        # create formatter and add it to the handlers
        formatter = logging.Formatter('%(asctime)s [%(levelname)s]: %(message)s', datefmt='%m/%d/%Y %H:%M:%S')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        # add the handlers to the logger
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)

    def init_vbs(self):
        """Define some 'standard' variables in scope's VBS context, so commands
        are simpler and more efficient.
        After this function is called you can
        """
        self.write_vbs('set acq = app.Acquisition')
        self.write_vbs('set acqHorz = acq.Horizontal')
        self.write_vbs('set chans = acq.channels')
        self.write_vbs('set meas = app.Measure')
        self.write_vbs('set math = app.Math')
        self.write_vbs('set zoom = app.Zoom')
        self.write_vbs('set memory = app.Memory')
        self.write_vbs('set syscon = app.SystemControl')

    def validate_source(self, source: str) -> bool:
        """Validate the source against Analog and Digital channels

        Args:
            source (str): source to validate

        Raises:
            ParametersError: on Invalid source

        Returns:
            bool: True, when source is valid
        """

        if source.upper() in self.available_channels or source.upper() in self.available_digital_channels:
            return True
        raise ParametersError('source not found')

    def validate_channel_source(self, source: str) -> bool:
        """Validate the source against Analog channels

        Args:
            source (str): source to validate

        Raises:
            ParametersError: on Invalid source

        Returns:
            bool: True, when source is valid
        """
        if source.upper() in self.available_channels:
            return True
        raise ParametersError('Channel source not found')

    def validate_digital_source(self, source: str) -> bool:
        """Validate the source against Digital channels

        Args:
            source (str): source to validate

        Raises:
            ParametersError: on Invalid source

        Returns:
            bool: True, when source is valid
        """
        if source.upper() in self.available_digital_channels:
            return True
        raise ParametersError('Digital source not found')

    def validate_parameters_source(self, parameter: str):
        """Validate the source against paramter sources

        Args:
            parameter (str): source to validate

        Raises:
            ParametersError: on Invalid source

        Returns:
            bool: True, when source is valid
        """
        if parameter.upper() in self.available_parameters:
            return True
        raise ParametersError('Parameter source not found')

    def validate_zoom_source(self, zoom: str):
        """Validate the source against zoom sources

        Args:
            zoom (str): source to validate

        Raises:
            ParametersError: on Invalid source

        Returns:
            bool: True, when source is valid
        """
        if zoom.upper() in self.available_zooms:
            return True
        raise ParametersError('Zoom source not found')

    def disconnect(self):
        if self.connected:
            self.connected = False

    def disconnect_from_dso(self):
        self._conn.disconnect()

    def get_float_value(self, query_cmd: str) -> float:
        """Gets value of the VBS command

        Args:
            query_cmd (str): VBS command

        Returns:
            float: value
        """
        val = float(self.query_vbs(query_cmd))
        return val

    def get_string_value(self, query_cmd: str) -> float:
        """Gets value of the VBS command

        Args:
            query_cmd (str): VBS command

        Returns:
            str: string value
        """
        val = self.query_vbs(query_cmd)
        return val.upper()

    @property
    def num_channels(self) -> int:
        """readonly Property for number of channels
        """
        return len(self.available_channels)

    @property
    def num_digital_channels(self) -> int:
        """readonly Property for number of Digital Channels
        """
        return len(self.available_digital_channels)

    @property
    def num_functions(self) -> int:
        """readonly Property for number of Functions F1 to Fn
        """
        return len(self.available_functions)

    @property
    def num_memories(self) -> int:
        """readonly Property for number of Memories M1 to Mn
        """
        return len(self.available_memories)

    @property
    def num_parameters(self) -> int:
        """readonly Property for number of Parameters P1 to Pn
        """
        return len(self.available_parameters)

    @property
    def num_zooms(self) -> int:
        """readonly Property for number of Zoom Z1 to Zn
        """
        return len(self.available_zooms)

    @property
    def query_response_max_length(self) -> int:
        """read max length of response string
        """
        return self._conn.query_response_max_length

    @query_response_max_length.setter
    def query_response_max_length(self, val: int):
        """set the maximum length of the response string from the instrument
        """
        self._conn.query_response_max_length = val

    @property
    def insert_wait_opc(self):
        self._insert_wait_opc = self._conn.insert_wait_opc
        return self._insert_wait_opc

    @insert_wait_opc.setter
    def insert_wait_opc(self, val: bool):
        """Inserts a OPC command for reads and writes.
        This ensures that the command will execute sequentially.
        The default value for a connection is false.
        NOTE: There is a performance impact by setting this flag

        Args:
            val (bool): True to insert wait_opc, False otherwise.
        """
        self._insert_wait_opc = val
        self._conn.insert_wait_opc = val

    @property
    def hor_scale(self) -> float:
        """Reads the horizontal scale from the dso
        """
        return self.get_hor_scale()

    @hor_scale.setter
    def hor_scale(self, val: float):
        """Sets the horizontal scale of the dso
        """
        self.set_hor_scale(val)

    @property
    def hor_offset(self) -> float:
        """Reads the horizontal offset from the dso
        """
        return self.get_hor_offset()

    @hor_offset.setter
    def hor_offset(self, val: float):
        """Sets the horizontal offset of the dso
        """
        self.set_hor_offset(val)

    @property
    def sample_mode(self) -> str:
        """Reads the sample mode of the dso
        """
        return self.query_vbs('acqHorz.samplemode')

    @sample_mode.setter
    def sample_mode(self, val: str):
        """Sets the sample mode of the dso
        """
        self.set_sample_mode(val)

    @property
    def trigger_mode(self) -> str:
        """Reads the trigger mode of the dso
        """
        return self.get_string_value('acq.TriggerMode')

    @trigger_mode.setter
    def trigger_mode(self, val: str):
        """Sets the trigger mode of the dso
        """
        self.set_trigger_mode(val)

    @property
    def triggerType(self) -> str:
        """Reads the trigger type of the dso
        """
        self.get_string_value('acq.Trigger.Type')

    @triggerType.setter
    def triggerType(self, val: str):
        """Sets the trigger type of the dso
        """
        self.set_trigger_type(val)

    @property
    def trigger_source(self) -> str:
        """Reads the trigger source of the dso
        """
        return self.get_string_value('acq.Trigger.Source')

    @trigger_source.setter
    def trigger_source(self, val: str):
        """Sets the trigger source of the dso
        """
        self.set_trigger_source(val)

    @property
    def trigger_coupling(self) -> str:
        """Reads the trigger coupling of the dso
        """
        self.get_string_value('acq.Trigger.Coupling')

    @trigger_coupling.setter
    def trigger_coupling(self, val: str):
        """Sets the trigger coupling of the dso
        """
        self.set_trigger_coupling(val)

    def write(self, strCmd: str):
        """Sends the command

        Args:
            message (str): command string
        """
        self._conn.write(strCmd)

    def write_vbs(self, strCmd: str):
        """Sends the command as a VBS formatted comamnd

        Args:
            message (str): command string
        """
        self._conn.write_vbs(strCmd)

    def query(self, message: str, query_delay: float = None) -> str:
        """Send the query and returns the response

        Args:
            message (string): command to send
            query_delay (float, optional): delay between the command and response. Defaults to None.

        Returns:
            string: Response from the instrument
        """
        return self._conn.query(message, query_delay)

    def query_vbs(self, message: str, query_delay: float = None) -> str:
        """Send the query as a VBS formatted string and returns the response

        Args:
            message (string): command to send
            query_delay (float, optional): delay between the command and response. Defaults to None.

        Returns:
            string: Response from the instrument
        """
        return self._conn.query_vbs(message, query_delay)

    def vbs(self, vbs_command: str, is_query: bool = False, max_length: int = None) -> str:
        """vbs command wrapper for read or write

        Args:
            vbs_command (str): vbs command to send
            is_query (bool, optional): Set to Tue if expecting a return value. Defaults to False.
            max_length (int, optional): maximum length of the expected transfer. Defaults to None.
        Returns:
            str: return value of the response
        """
        if not is_query:
            self.write_vbs(vbs_command)
            response = 0
        else:
            if max_length is not None:
                self.query_response_max_length = max_length
            response = self.query_vbs(vbs_command)
        return response

    def set_default_state(self):
        """Sets the default state of the DSO
        """
        self.write_vbs('app.SystemControl.EnableMessageBox = ' + str(0))
        self.write('CHDR OFF')
        self.query('ALST?')
        self.wait_opc()
        self.write('*RST')
        self.write('CHDR OFF')
        self.write_vbs('app.SaveRecall.Setup.DoRecallDefaultPanelWithTriggerModeAuto')
        self.wait_opc()
        self.wait_opc()

    def restart_app(self):
        """Restarts the scope application
        """
        self.disconnect()
        self.write_vbs('app.Restart')
        # wait and reconnect
        for _ in range(20):
            time.sleep(5)
            self._conn.reconnect()
            if self._conn.connected:
                break
        self.__init__(self._conn, self.logger)

    def acquire(self, timeout: float = 0.1, force: bool = True) -> bool:
        """Acquire a waveform

        Args:
            timeout (float, optional): timeout in seconds for the acquisition to wait. Defaults to 0.1.
            force (bool, optional): Forces an acquisition to complete. Defaults to True.

        Returns:
            bool: True for Triggered, False if not Triggered or unknown state
        """
        if force:
            self.write_vbs('acq.acquire ' + str(timeout) + ',' + str(force))
            self.wait_opc()
            return True
        else:
            triggered = self.query_vbs('acq.acquire(' + str(timeout) + ')')
            if triggered == '0':
                return False
            elif triggered == '1':
                return True
            else:
                return False

    def get_scope_setup(self, filename: str = None) -> str:
        """Reads the instrument control state into a string

        Returns:
            str: panel file returned as a string, trailing terminator removed
        """
        setup = self._conn.get_panel()

        if filename is not None:
            setup = setup[0:-8]
            with open(filename, 'w') as f:
                f.write(setup)
        return setup

    def set_scope_setup(self, setup: str, filename: str = None):
        """Set the instrument control state using a panel string, typically from the method get_panel

        Args:
            panel (str): description

        Returns:
            bool: True on success, False on failure
        """
        if filename is None:
            theSetup = setup
        else:
            with open(filename, 'r') as f:
                theSetup = f.read() + 'ffffffff'

        return self._conn.set_panel(theSetup)

    def get_waveform(self, source: str) -> bytes:
        """Get a waveform from the source specified

        Args:
            source (str): Source string 'C1'

        Returns:
            bytes: return the waveform as bytes, may need to processed further to make sense of it
        """
        self.validate_source(source)
        self._conn.write('{}:WF?'.format(source))
        time.sleep(0.1)

        # read the first 11 bytes, this gives us the length of the transfer
        header = self._conn.read_raw(15)
        if 'WARNING' in str(header):
            return ''

        tmp = header[6:15]
        # get number of bytes in the response
        bytes = int(tmp.tobytes().decode('utf-8'))

        # read the amount of data
        wf = self._conn.read_raw(bytes)
        return wf

    def transfer_file_to_dso(self, remoteDevice: str, remoteFileName: str, localFileName: str) -> bool:
        """Transfers a file from the PC to the DSO

        Args:
            remoteDevice (str): The device name on the instrument end, typically CARD, HDD
            remoteFileName (str): The name and path of the destination file on the instrument
            localFileName (str): The name and path of the source file on the PC

        Returns:
            bool: True on success, False on failure
        """
        response = self._conn.transfer_file_to_dso(remoteDevice, remoteFileName, localFileName)
        return response >= 0.0

    def transfer_file_to_pc(self, remoteDevice: str, remoteFileName: str, localFileName: str) -> bool:
        """Transfers a file from the DSO to the PC

        Args:
            remoteDevice (str): The device name on the instrument end, typically CARD, HDD
            remoteFileName (str): The name and path of the destination file on the instrument
            localFileName (str): The name and path of the source file on the PC

        Returns:
            bool: True on success, False on failure
        """
        response = self._conn.transfer_file_to_pc(remoteDevice, remoteFileName, localFileName)
        return response >= 0.0

    def pava(self, channel: str, measurement: str) -> tuple:
        """Sends a PAVA query to the DSO

        Args:
            channel (str): channel index as a str ('C1')
            measurement (str): specifies the PAVA measurement

        Returns:
            tuple: returns (value, status)
        """
        result = self.query(channel + ':PAVA? ' + measurement).split(',')
        status = result[2]

        if status.upper() == 'OK':
            value = float(result[1])
        else:
            value = 0.0

        return value, status

    def set_trigger_source(self, source: str):
        """Sets the Trigger Source of the DSO

        Args:
            source (str): C1 to Cn, D1 to Dn, EXT, LINE are possible choices

        Raises:
            ParametersError: if the source is not valid
        """
        if (source.upper() in ['EXT', 'LINE'] or self.validate_source(source)):
            self.write_vbs('acq.Trigger.source = "' + source.upper() + '"')
        else:
            raise ParametersError('source not found')

    def set_trigger_mode(self, mode: str):
        """Set Trigger Mode of the DSO

        Args:
            mode (str): Set Trigger Mode to ['AUTO', 'NORMAL', 'SINGLE', 'STOPPED'].

        Raises:
            ParametersError: invalid values
        """
        if mode.upper() in ['AUTO', 'NORMAL', 'SINGLE', 'STOPPED']:
            self.write_vbs('acq.triggermode = "' + mode.upper() + '"')
            self.wait_opc()
        else:
            raise ParametersError('TriggerMode not valid')

    def get_trigger_mode(self) -> str:
        """Get the Trigger Mode of the DSO

        Returns:
            str: returns the Trigger Mode
        """
        mode = self.query_vbs('acq.TriggerMode')
        return mode.upper()

    def get_trigger_type(self) -> str:
        """Gets the trigger type of the DSO

        Returns:
            str: Trigger type value
        """
        type = self.query_vbs('acq.Trigger.Type')
        return type.upper()

    def set_trigger_coupling(self, channel: str, coupling: str):
        """Set the Trigger Coupling of the DSO

        Args:
            channel (str): Channel Source
            coupling (str): Sets the coupling.

        Raises:
            ParametersError: Invalid channel or coupling
        """
        if ((channel.upper() in self.available_channels) and (coupling.upper() in ('DC', 'AC', 'LFREJ', 'HFREJ'))):
            self.write_vbs('acq.Trigger.' + channel.upper() + 'Coupling = "' + coupling.upper() + '"')
        else:
            raise ParametersError('Trigger Coupling not valid')

    def set_holdoff_type(self, type: str):
        """Sets the Trigger Holdoff type

        Args:
            type (str): possible values ['OFF', 'TIME', 'EVENTS']
        """
        if type.upper() in ['OFF', 'TIME', 'EVENTS']:
            self.write_vbs('acq.Trigger.HoldoffType = "' + type.upper() + '"')

    def set_holdoff_events(self, numEvents: int = 1):
        """Set Trigger Holdoff events

        Args:
            numEvents (int, optional): Sets the number of holdoff events. Defaults to 1.
        """
        if 1 <= numEvents <= 1000000000:
            self.write_vbs('acq.Trigger.HoldoffEvents = ' + str(numEvents))

    def set_average_sweeps(self, channel: str, sweeps: int = 1):
        """Set the Average number of sweeps for a channel

        Args:
            channel (str): Channel source
            sweeps (int, optional): Number of sweeps. Defaults to 1.

        Raises:
            ParametersError: on invalid channel or number of sweeps
        """
        if (self.validate_channel_source(channel) and 1 <= sweeps <= 1000000):
            self.write_vbs('app.acquisition.' + channel.upper() + '.AverageSweeps = ' + str(sweeps))
        else:
            raise ParametersError('Sweeps invalid')

    def clear_sweeps(self):
        """Clear Sweeps
        """
        self.write_vbs('app.ClearSweeps.ActNow()')

    def set_trigger_level(self, source: str, level: float = 0.0):
        """Set the Trigger Level of the DSO

        Args:
            source (str): Channel source
            level (float, optional): Trigger Level of the trigger source. Defaults to 0.0.

        Raises:
            ParametersError: on invalid Channel source
        """
        if (source.upper() in ('EXT') or source.upper() in self.available_channels):
            self.write_vbs('acq.Trigger.' + source.upper() + 'Level = ' + str(level))
        elif (source.upper() in self.available_digital_channels):
            group = int(source.upper().replace('D', '')) / 9
            self.write_vbs('app.LogicAnalyzer.MSxxLogicFamily' + str(group) + ' = "UserDefined"')
            self.write_vbs('app.LogicAnalyzer.MSxxThreshold' + str(group) + ' = ' + str(level))
        else:
            raise ParametersError('source not found')

    def set_digital_hysteresis_level(self, source: str, level: float = 0.1):
        """Set Digital Hysteresis Level

        Args:
            source (str): Digital Channel source
            level (float, optional): Hysteresis. Defaults to 0.1.

        Raises:
            ParametersError: on invalid Digital Channel Source and invalid level
        """
        if (self.validate_digital_source(source) and level >= .1 and level <= 1.4):
            group = int(source.upper().replace('D', '')) / 9
            self.write_vbs('app.LogicAnalyzer.MSxxLogicFamily' + str(group) + ' = "UserDefined"')
            self.write_vbs('app.LogicAnalyzer.MSxxHysteresis' + str(group) + ' = ' + str(level), True)
        else:
            raise ParametersError('source not found')

    def set_trigger_type(self, type: str = 'EDGE'):
        """Set Trigger Type

        Args:
            type (str, optional): Type of Triger specified as a string. Defaults to 'EDGE'.

        Raises:
            ParametersError: on invalid Trigger Type
        """
        if type.upper() in ['EDGE', 'WIDTH', 'QUALIFIED', 'WINDOW', 'INTERNAL', 'TV', 'PATTERN']:
            self.write_vbs('acq.Trigger.type = ' + type.upper())
        else:
            raise ParametersError('source not found')

    def set_trigger_slope(self, channel: str, slope: str = 'POSITIVE'):
        """Sets the trigger slope of the DSO

        Args:
            channel (str): Channel source
            slope (str, optional): Typically 'POSITIVE', 'NEGATIVE', 'EITHER'. Defaults to 'POSITIVE'.

        Raises:
            ParametersError: on invalid source or slope
        """
        if (slope.upper() in ['POSITIVE', 'NEGATIVE', 'EITHER']):
            if (channel.upper() in self.available_channels):
                self.write_vbs('acq.Trigger.' + channel.upper() + '.slope = "' + slope.upper() + '"')
            elif channel.uppper in ['EXT', 'LINE']:
                self.write_vbs('acq.Trigger.' + channel.upper() + '.slope = "' + slope.upper() + '"')
            else:
                raise ParametersError('source not found')
        else:
            raise ParametersError('slope not found')

    def set_coupling(self, source: str, coupling: str = 'DC50'):
        """Set the channel coupling of the source specified

        Args:
            source (str): Channel source
            coupling (str, optional): Coupling is typically 'DC50', 'DC1M', 'AC1M', 'GND','DC100k'. Defaults to 'DC50'.

        Raises:
            ParametersError: on invalid Coupling
        """
        if coupling.upper() not in ['DC50', 'DC1M', 'AC1M', 'GND', 'DC100k']:
            raise ParametersError('Invalid Coupling')
        if source.upper() in self.available_channels:
            self.write_vbs('app.acquisition.' + source.upper() + '.Coupling = "' + coupling.upper() + '"')
        else:
            if source.upper() == 'EXT':
                source = 'AUXIN'
            if source.upper() == 'AUXIN':
                self.write_vbs('app.acquisition.' + source.upper() + '.Coupling = "' + coupling.upper() + '"')

    def set_ver_offset(self, source: str, offset: float = 0.0):
        """Sets the vertical offset of the channel

        Args:
            source (str): Channel source
            offset (float, optional): Vertical offset. Defaults to 0.0.

        Raises:
            ParametersError: on invalid channel source
        """
        if source.upper() in self.available_channels:
            self.write_vbs('app.acquisition.' + source.upper() + '.VerOffset = ' + str(offset))
        else:
            raise ParametersError('source not found')

    def set_view(self, channel: str, view: bool = True, digitalGroup: str = 'Digital1'):
        """Set view on or off

        Args:
            channel (str): Analog or Digital source
            view (bool, optional): True sets view ON. Defaults to True.
            digitalGroup (str, optional): This is ignored if source is analog. If it is a digital source, specifies the group it belongs to. Defaults to 'Digital1'.

        Raises:
            ParametersError: on invalid source or group
        """
        if (channel.upper() in self.available_channels):
            self.write_vbs('app.acquisition.' + channel.upper() + '.view = ' + str(view))
        elif (channel.upper() in self.available_digital_channels and digitalGroup.upper() in ('DIGITAL1', 'DIGITAL2', 'DIGITAL3', 'DIGITAL4')):
            self.write_vbs('app.LogicAnalyzer.' + digitalGroup.upper() + '.Digital' + channel.upper()[1:] + ' = ' + str(view))
        else:
            raise ParametersError('source not found')

    def set_bandwidth_limit(self, channel: str, bandwidth: str = 'FULL'):
        """Set bandwidth limit for the channel

        Args:
            channel (str): Channel source
            bandwidth (str, optional): possible values are 'FULL', '350MHZ', '200MHZ', '100MHZ', '20MHZ', 'RAW'. Defaults to 'FULL'.

        Raises:
            ParametersError: on invalid channel source or bandwidth limit
        """
        if (self.validate_channel_source(channel) and (bandwidth.upper() in ['FULL', '350MHZ', '200MHZ', '100MHZ', '20MHZ', 'RAW'])):
            self.write_vbs('app.acquisition.' + channel.upper() + '.BandwidthLimit = "' + bandwidth.upper() + '"')
        else:
            raise ParametersError('Invalid bandwidth limit')

    def set_ver_scale(self, channel: str, ver_scale: float = 0.001):
        """Set vertical scale for the channel

        Args:
            channel (str): Channel source
            ver_scale (float, optional): vertical scale. Defaults to 0.001.
        """
        self.validate_channel_source(channel)
        self.write_vbs('acq.' + channel.upper() + '.VerScale = ' + str(ver_scale))

    def set_ver_scale_variable(self, channel: str, variable: bool = False):
        """Set vertical scale variable flag

        Args:
            channel (str): Channel source
            variable (bool, optional): True sets the variable flag to ON and the step of the vertical scale is variable. Defaults to False.
        """
        self.validate_channel_source(channel)
        self.write_vbs('acq.' + channel.upper() + '.VerScaleVariable = ' + '1' if variable else '0')

    def set_sample_mode(self, sample_mode: str = 'REALTIME', segments: int = 10):
        """Sets the sample mode of the DSO

        Args:
            sample_mode (str, optional): Typical values for sample mode are REALTIME|RIS|ROLL|SEQUENCE. Defaults to 'REALTIME'.
            segments (int, optional): This is used for Sequence mode to set the number of segments. Defaults to 10.
        """
        if sample_mode.upper() in ['REALTIME', 'RIS', 'ROLL', 'SEQUENCE']:
            self.write_vbs('acqHorz.samplemode = "' + sample_mode.upper() + '"')
            if sample_mode.upper() == 'SEQUENCE' and segments >= 2:
                self.write_vbs('acqHorz.numsegments = ' + str(segments))
        else:
            ParametersError('Invalid Sample mode')

    def set_reference_clock(self, reference: str = 'INTERNAL'):
        """Set the reference clock of the DSO

        Args:
            source (str, optional): Possible values are INTERNAL|EXTERNAL. Defaults to 'INTERNAL'.

        Raises:
            ParametersError: on invalid reference
        """
        if reference.upper() in ('INTERNAL', 'EXTERNAL'):
            self.write_vbs('acqHorz.referenceclock = "' + reference.upper() + '"')
        else:
            raise ParametersError('Invalid Reference clock')

    def set_hor_scale(self, hor_scale: float):
        """Sets the horizontal scale of the DSO

        Args:
            hor_scale (float): Horizontal scale value
        """
        self.write_vbs('acqHorz.horscale = ' + str(hor_scale))

    def set_hor_offset(self, hor_offset: float = 0.0):
        """Set the Horizontal offset of the scope

        Args:
            hor_offset (float, optional): Horizontal offset value. Defaults to 0.0.
        """
        self.write_vbs('acqHorz.horoffset = ' + str(hor_offset))

    def set_num_points(self, num_points: int):
        """Set Number of the points for the acquisition

        Args:
            num_points (int): number of points

        """
        self.write_vbs('acqHorz.numpoints = ' + str(num_points))

    def set_max_samples(self, max_samples: int):
        """Sets the Max Samples possible in the acquisition

        Args:
            max_samples (int): maximum samples value
        """
        self.write_vbs('acqHorz.MaxSamples = ' + str(max_samples))

    def set_sample_rate(self, sample_rate: float):
        """Set the sample rate to a specific value. This sets the DSO to FixedSampleRate
        memory mode.

        Args:
            sample_rate (float): sample rate value

        Raises:
            ParametersError: on invalid Sample rate
        """
        self.set_memory_mode('FIXEDSAMPLERATE')
        self.write_vbs('acqHorz.samplerate = ' + str(sample_rate))
        if self.get_sample_rate() != float(sample_rate):
            raise ParametersError('Invalid Sample Rate')

    def set_memory_mode(self, maximize: str = 'SetMaximumMemory'):
        """Set Memory mode of the DSO

        Args:
            maximize (str, optional): Possible values are SETMAXIMUMMEMORY|FIXEDSAMPLERATE. Defaults to 'SetMaximumMemory'.

        Raises:
            ParametersError: on invalid Memory mode
        """
        if maximize.upper() in ['SETMAXIMUMMEMORY', 'FIXEDSAMPLERATE']:
            self.write_vbs('acqHorz.maximize = "' + maximize.upper() + '"')
        else:
            raise ParametersError('Invalid Memory mode')

    def set_hardcopy(self, filename: str = 'wav000.jpg', destination: str = 'EMAIL',
                     area: str = 'DSOWINDOW', orientation: str = 'LANDSCAPE', color: str = 'BW'):
        """Set the hardcopy variables

        Args:
            filename (str, optional): filename on the DSO. Defaults to 'wav000.jpg'.
            destination (str, optional): possible destination are CLIPBOARD|EMAIL|FILE|PRINTER|REMOTE. Defaults to 'EMAIL'.
            area (str, optional): possible area are DSOWINDOW|FULLSCREEN|GRIDAREAONLY. Defaults to 'DSOWINDOW'.
            orientation (str, optional): possible orientation are PORTRAIT|LANDSCAPE. Defaults to 'LANDSCAPE'.
            color (str, optional): possible colors are BW|PRINT|STD. Defaults to 'BW'.
        """
        if filename is not None:
            self.write_vbs('app.Hardcopy.PreferredFilename = "' + filename + '"')
        if destination.upper() in ['CLIPBOARD', 'EMAIL', 'FILE', 'PRINTER', 'REMOTE']:
            self.write_vbs('app.Hardcopy.Destination = "' + destination.upper() + '"')
        if area.upper() in ['DSOWINDOW', 'FULLSCREEN', 'GRIDAREAONLY']:
            self.write_vbs('app.Hardcopy.HardCopyArea = "' + area.upper() + '"')
        if orientation.upper() in ['PORTRAIT', 'LANDSCAPE']:
            self.write_vbs('app.Hardcopy.Orientation = "' + orientation.upper() + '"')
        if color.upper() in ['BW', 'PRINT', 'STD']:
            self.write_vbs('app.Hardcopy.UseColor = "' + color.upper() + '"')

    def hardcopy_print(self):
        """Generates a hardcopy
        """
        self.write_vbs('app.Hardopy.Print')

    def get_hor_scale(self) -> float:
        """Gets the Horizontal scale

        Returns:
            [float]: horizontal scale value
        """
        hor_scale = float(self.query_vbs('acqHorz.horscale'))
        return hor_scale

    def get_hor_offset(self) -> float:
        """Gets the Horizontal offset

        Returns:
            [float]: horizontal offset value
        """
        hor_offset = float(self.query_vbs('acqHorz.horoffset'))
        return hor_offset

    def get_num_points(self) -> float:
        """Gets the number of points

        Returns:
            float: Number of points value
        """
        num_points = float(self.query_vbs('acqHorz.numpoints'))
        return num_points

    def get_sample_rate(self) -> float:
        """Gets the sample rate of the DSO

        Returns:
            float: Sample rate value
        """
        sample_rate = float(self.query_vbs('acqHorz.samplerate'))
        return sample_rate

    def get_num_sweeps(self, channel: str) -> int:
        """Gets the number of sweeps of the channel specified

        Args:
            channel (str): Channel source

        Returns:
            int: number of values acquired so far
        """
        self.validate_source(channel)
        res = self.query_vbs('app.acquisition.' + channel.upper() + '.Out.Result.Sweeps')
        try:
            numSweeps = int(res)
        except ValueError:
            numSweeps = -100
        return numSweeps

    def get_time_per_point(self) -> float:
        """Gets the time per point value of the DSO

        Returns:
            float: Time per point value
        """
        time_per_point = float(self.query_vbs('acqHorz.timeperpoint'))
        return time_per_point

    def get_ver_scale(self, channel: str) -> float:
        """Get Vertical scale of the DSO

        Args:
            channel (str): Channel source

        Returns:
            float: Vertical scale value
        """
        self.validate_channel_source(channel)
        verScale = float(self.query_vbs('app.acquisition.' + channel.upper() + '.VerScale'))
        return verScale

    def get_ver_offset(self, channel: str) -> float:
        """Gets the vertical offset of the channel

        Args:
            channel (str): Channel source

        Returns:
            float: Vertical offset value
        """
        self.validate_channel_source(channel)
        verScale = float(self.query_vbs('app.acquisition.' + channel.upper() + '.VerOffset'))
        return verScale

    def recall_default_panel(self):
        """Recall the default setup of the DSO
        """
        self.write_vbs('app.SaveRecall.Setup.DoRecallDefaultPanel')
        self.wait_opc()

    def get_serial_number(self) -> str:
        """Get the serial number of the DSO

        Returns:
            str: Serial number as a string
        """
        self.scopeSerial = self.query_vbs('app.SerialNumber')
        return self.scopeSerial

    def get_instrument_max_bandwidth(self) -> str:
        """Gets the maximum bandwidth of the DSO

        Returns:
            str: Maximum bandwidth value
        """
        self.maxBandwidth = self.query_vbs('app.InstrumentMaxBandwidth')
        return self.maxBandwidth

    def get_instrument_model(self) -> str:
        """Gets the instrument model of the DSO

        Returns:
            str: Instrument model as a string
        """
        self.instrumentModel = self.query_vbs('app.InstrumentModel')
        return self.instrumentModel

    def get_firmware_version(self) -> str:
        """Gets the firmware version of the DSO

        Returns:
            str: Firmware version as string
        """
        self.firmware_version = self.query_vbs('app.FirmwareVersion')
        return self.firmware_version

    def set_measure_statistics(self, on: bool):
        """Set the measure statistics on or off

        Args:
            on (bool): True turns on measurement statistics
        """
        self.write_vbs('meas.StatsOn = ' + '1' if on else '0')

    def set_measure(self, parameter: str, source1: str, source2: str = 'None', param_engine: str = 'TimeAtLevel', view: bool = True):
        """Setup a parameter measurement

        Args:
            parameter (str): Parameter source P1 to Pn
            source1 (str): possible measurement sources
            source2 (str, optional): possible measurement sources. Defaults to 'None'.
            param_engine (str, optional): measurement engine to use. Defaults to 'TimeAtLevel'.
            view (bool, optional): True turns on measurement view. Defaults to True.

        Raises:
            ParametersError: on invalid paramter source
        """
        self.validate_parameters_source(parameter)
        self.write_vbs('meas.' + parameter.upper() + '.ParamEngine = "' + param_engine.upper() + '"')
        self.write_vbs('meas.' + parameter.upper() + '.Source1 = "' + source1.upper() + '"')
        self.write_vbs('meas.' + parameter.upper() + '.Source2 = "' + source2.upper() + '"')
        self.write_vbs('meas.View' + parameter.upper() + ' = 1' if view else ' = 0')

    def get_measure_stats(self, parameter: str) -> tuple:
        """Reads the measurement statistics values for a parameter

        Args:
            parameter (str): Parameter name P1 to Pn

        Returns:
            tuple: Returns the values (last, max, mean, min, num, sdev, status)

        Raises:
            ParametersError: on invalid paramter source
        """
        self.validate_parameters_source(parameter)
        last = self.query_vbs('meas.' + parameter + '.last.Result.Value')
        max = self.query_vbs('meas.' + parameter + '.max.Result.Value')
        mean = self.query_vbs('meas.' + parameter + '.mean.Result.Value')
        min = self.query_vbs('meas.' + parameter + '.min.Result.Value')
        num = self.query_vbs('meas.' + parameter + '.num.Result.Value')
        sdev = self.query_vbs('meas.' + parameter + '.sdev.Result.Value')
        status = self.query_vbs('meas.' + parameter + '.Out.Result.Status')
        self.wait_opc()

        return (last, max, mean, min, num, sdev, status)

    def get_measure_value(self, parameter: str) -> float:
        """Gets the last measurement value of a parameter

        Args:
            parameter (str): Parameter source P1 to Pn

        Returns:
            [float]: Last measurement value of the parameter, -999999.99 on error

        Raises:
            ParametersError: on invalid parameter source
        """
        self.validate_parameters_source(parameter)
        last = self.query_vbs('meas.' + parameter + '.last.Result.Value')
        try:
            fLast = float(last)
        except ValueError:
            fLast = -999999.99
        return fLast

    def get_measure_mean(self, parameter: str) -> float:
        """Gets the mean value of the parameter

        Args:
            parameter (str): Parameter source P1 to Pn

        Returns:
            [float]: Mean value of the parameter, -999999.99 on error

        Raises:
            ParametersError: on invalid parameter source
        """
        self.validate_parameters_source(parameter)
        mean = self.query_vbs('meas.' + parameter + '.mean.Result.Value')
        try:
            fMean = float(mean)
        except TypeError:
            fMean = -999999.99
        return fMean

    def set_zoom(self, zoom: str, source: str):
        """Sets the zoom function for a channel source

        Args:
            zoom (str): Zoom Channel Source Z1 to Zn
            source (str): Channel source

        Raises:
            ParametersError: on invalid zoom source
        """
        self.validate_source(source)
        self.validate_zoom_source(zoom)
        self.write_vbs('zoom.' + zoom.upper() + '.Source = "' + source.upper() + '"')
        self.write_vbs('zoom.' + zoom.upper() + '.View = ' + str(-1))

    def show_zoom(self, zoom: str, show: bool = True):
        """Set the zoom trace view on or off

        Args:
            zoom (str): Zoom Channel Source Z1 to Zn
            show (bool, optional): True to view the zoom trace. Defaults to True.

        Raises:
            ParametersError: on invalid zoom source
        """
        self.validate_zoom_source(zoom)
        self.write_vbs('zoom.' + zoom.upper() + '.View = ' + str(-1) if show else str(0))

    def set_zoom_segment(self, zoom: str, startSeg: int = 1, numToShow: int = 1):
        """Set the Zoom segment for sequence mode waveforms

        Args:
            zoom (str): Zoom Channel Source Z1 to Zn
            startSeg (int, optional): Start segment index. Defaults to 1.
            numToShow (int, optional): Number of segments to display. Defaults to 1.

        Raises:
            ParametersError: on invalid zoom source
        """
        self.validate_zoom_source(zoom)
        self.write_vbs('zoom.' + zoom.upper() + '.Zoom.SelectedSegment = "' + str(startSeg) + '"')
        self.write_vbs('zoom.' + zoom.upper() + '.Zoom.NumSelectedSegments = "' + str(numToShow) + '"')

    def set_aux_mode(self, mode: str):
        """Set the Auxilary mode

        Args:
            mode (str): Auxilary mode value, Possible values are: TRIGGERENABLED|TRIGGEROUT|PASSFAIL|FASTEDGE|OFF

        Raises:
            ParametersError: on invalid Auxilary mode values
        """
        if mode.upper() in ['TRIGGERENABLED', 'TRIGGEROUT', 'PASSFAIL', 'FASTEDGE', 'OFF']:
            self.write_vbs('app.Acquisition.AuxOutput.AuxMode = "' + mode.upper() + '"')
        else:
            raise ParametersError('Invalid Auxilary Mode value')

    def set_show_measure(self, show: bool = True):
        """Opens the measure dialog

        Args:
            show (bool, optional): True to open and False to close. Defaults to True.
        """
        self.write_vbs('meas.ShowMeasure = 1' if show else 'meas.ShowMeasure = 0')

    def set_auxin_attenuation(self, attenuation: str = 'X1'):
        if attenuation.upper() in ['X1', 'DIV10']:
            self.write_vbs('app.acquisition.AuxIn.Attenuation = "' + attenuation + '"')

    def wait_opc(self):
        """Wait for the previous operation to complete
        """
        self._conn.wait_opc()

    def sleep(self, tm: float):
        """Sends a sleep command to the instrument

        Args:
            tm ([float]): time to sleep in
        """
        self.write_vbs('app.Sleep {0}'.format(tm))

    def force_trigger(self):
        """Forces a trigger on the instrument
        """
        self.write('FRTR')

    def is_popup_dialog_open(self) -> bool:
        """Checks if a popup dialog is open

        Returns:
            [bool]: True if a popup dialog is open, False otherwise
        """
        response = self.query_vbs('not syscon.dialogontop.widgetpageontop.value is Nothing')
        return re.match('0', response) is None

    def close_popup_dialog(self):
        """Closes any popup dialogs that are open
        """
        self.write_vbs('syscon.DialogOnTop.ClosePopup')

    def click_popup_dialog(self, popup_action: str):
        """Key Action on Popup Dialog

        Args:
            popup_action (str): Popup action string
        """
        self.write_vbs('syscon.DialogOnTop.{0}'.format(popup_action))

    def get_docked_dialog_page_names(self, rhs: bool = False) -> list:
        """Gets a list of the docked dialog pages

        Args:
            rhs (bool, optional): True to return the right hand side dialogs. Defaults to False.

        Returns:
            list: of page names, None if no docked dialogs are open
        """
        response = self.query_vbs('syscon{0}.DialogPageNames'.format('.Right' if rhs else ''))
        return None if 'none' in response.lower() else response.split(',')

    def get_docked_dialog_selected_page(self, rhs: bool = False) -> str:
        """Gets docked selected page

        Args:
            rhs (bool, optional): True to return the right hand side selected page. Defaults to False.

        Returns:
            str: returns the page name of the selected page, None if no docked dialogs are open
        """
        response = self.query_vbs('syscon{0}' + '.Right' if rhs else '' + 'DialogPage')
        return None if response == '' else response

    def is_docked_dialog_open(self, rhs: bool) -> bool:
        """Checks if a docked dialog is open

        Args:
            rhs ([bool]): True to check if right hand side dialog is open

        Returns:
            bool: Returns True if a docked dialog is open else False
        """
        strPage = self.get_docked_dialog_selected_page(rhs)
        return strPage.len > 0

    def close_docked_dialog(self):
        """Closes the docked dialog page
        """
        self.write_vbs('syscon.CloseDialog')

    def is_option_enabled(self, option: str) -> bool:
        """Checks if the option specified is enabled

        Args:
            option (str): Option string

        Returns:
            bool: True if option present else False
        """
        response = self.query('$$OP_PRE? {0}'.format(option))
        return response != '0'

    def get_automation_items(self, collection_name: str, filter_spec: list = [('name', None)], match_all: bool = True) -> list:
        """Gets a list of automation collection items matching the specified criteria.

        Args:
            collection_name (str): must be a valid automation collection name within the scope app's VBS context.
            filter_spec (list, optional): list of 2-tuples, where the first tuple item specifies the name of an
                automation property and the second specifies a matching regex, may be None which matches all. Defaults to [('name', None)].
                filter_spec, by default, causes the returned list to contain the names of all items in the collection.
            match_all (bool, optional): [description]. Defaults to True.

        Returns:
            [list]: list of automation collection items
        """

        # build a vbs function in the scope context that will generate the comma-sep properties string for each item in the collection.
        # we'll apply the matching specs in python after parsing the responses, since it's much better at that and developing/maintaining/debugging
        # these scope vbs functions is horrible.
        prop_names = [prop_item[0] for prop_item in filter_spec]
        get_props_script = ['function getProps(o)']
        get_props_script.append('on error resume next')
        get_props_script.append('strProps = \'\'')
        for prop_name in prop_names:
            get_props_script.append('strProps = strProps & \',\'')  # default to comma-sep if property doesn't exist
            get_props_script.append('strProps = strProps & o.{0}'.format(prop_name))
        get_props_script.append('getProps = strProps')
        get_props_script.append('end function')
        script_to_exec = ':'.join(get_props_script)
        self.write_vbs(script_to_exec)

        # build the vbs query that iterates the collection calling the vbs function for each item, semi-colon sep each item's properties.
        if False:
            # at least for now, for-each (IEnumVARIANT) is not correctly supported on CE... seems to be missing marshalling
            response = self.query("vbs? 'strProps = \"\": for each obj in {0}: strProps = strProps & \";\" & getProps(obj): next: return = strProps'".format(collection_name))
        else:
            # work-around for bad for-each behavior on CE.
            # painful: need to figure out if collection is 0-based index or not and set the startIndex and stopIndex variables used in query.
            vbs_statements = ['on error resume next']
            vbs_statements.append('set o1 = nothing')
            vbs_statements.append('set o1 = {0}.item(0)'.format(collection_name))
            vbs_statements.append('stopIndex = {0}.count'.format(collection_name))
            vbs_statements.append('startIndex = 1')
            vbs_statements.append('if not o1 is nothing then: startIndex = 0: stopIndex = stopIndex - 1: end if')
            vbs_statements.append('on error goto 0')
            vbs_to_exec = ':'.join(vbs_statements)
            self.write_vbs(vbs_to_exec)
            response = self.query("vbs? 'strProps = \"\": for i = startIndex to stopIndex: set obj = {0}(i): strProps = strProps & \";\" & getProps(obj): next: return = strProps'".format(collection_name))

        # parse the response, stripping and splitting on the item and property separators.
        # strip leading semi-colon and split to get list of comma-sep property strings for each object
        props_response = response.lstrip(';').split(';')
        output_items = []
        for props in props_response:

            # strip leading command and split to get list of properties
            list_props = props.lstrip(',').split(',')
            output_props = []
            props_matched = 0
            for idx in range(0, len(list_props)):

                if idx < len(filter_spec):
                    str_prop = list_props[idx]
                    str_output = ''
                    if (filter_spec[idx][1] is None or filter_spec[idx][1].search(str_prop)):
                        props_matched += 1
                        str_output = str_prop

                    # add to output list of properties
                    output_props.append(str_output)

            if (match_all and props_matched == len(filter_spec)) or (not match_all and props_matched > 0):
                # add to output list of objects
                output_items.append(output_props)

        if self.verbose == 3:
            # print to pyconsole if verbose mode 3
            message = 'get_automation_items({0}, {1}):response={2} => {3}'.format(collection_name, filter_spec, response, output_items)
            self.logger.debug(message)

        return output_items

    def get_object_names(self, coll_name: str, matching: str = None) -> list:
        """return a list of all matching object names (in specified coll_name collection).

        Args:
            coll_name (str): Collection name
            matching (str, optional): If no match is specified then all are returned. Defaults to None.

        Returns:
            list: matching object names
        """
        objects_into = self.get_automation_items(coll_name, [('name', matching)])
        object_names = [obj_info[0] for obj_info in objects_into]
        return object_names

    def does_object_exist(self, coll_name: str, object_name: str) -> bool:
        """Tests if the object exists in the collection

        Args:
            coll_name (str): Collection name
            object_name (str): object name

        Returns:
            bool: True if specified coll_name has the specified object, False if it does not.
        """
        cvars_info = self.get_automation_items(coll_name, [('name', re.compile('^{0}$'.format(object_name), re.IGNORECASE))])
        return len(cvars_info) > 0

    def does_cvar_exist(self, object_name: str, cvar_name: str) -> bool:
        """Tests if the cvar exists in an automation object

        Args:
            object_name (str): Object name
            cvar_name (str): Cvar name

        Returns:
            bool: True if specified object_name has the specified cvar, False if it does not.
        """
        cvars_info = self.get_automation_items(object_name, [('name', re.compile('^{0}$'.format(cvar_name), re.IGNORECASE))])
        return len(cvars_info) > 0

    def is_cvar_enum_value_in_range(self, cvar_enum_name: str, enum_value: str, range_property: str = 'RangeStringAutomation') -> bool:
        """Tests if Cvar enum value is in range

        Args:
            cvar_enum_name (str): Cvar enum name
            enum_value (str): Value of the enum
            range_property (str, optional): Range property. Defaults to 'RangeStringAutomation'.

        Returns:
            [bool]: True if cvar is in range else False
        """
        response = self.query_vbs('{0}.{1}'.format(cvar_enum_name, range_property))
        return re.search(r'(^|,){0}(,|$)'.format(enum_value), response, re.IGNORECASE)

    def get_cvars_info(self, automation_path: str) -> zip:
        """Get Cvar Info for the automation path specified

        Args:
            automation_path (str): Automation path

        Returns:
            zip: zip object containing list of cvar names, types and flags (3-tuple) for the specified automation object.
        """
        self.write_vbs('s1 = \'\'')     # for some reason, doing this in the query_vbs isn't sufficient... ugh
        response = self.query_vbs('s1 = \'\': for i=0 to {0}.count - 1: set ocv={0}.Item(i): a1 = Array(s1, ocv.name, ocv.type, ocv.flags): s1 = Join(a1, \',\'): next: return = s1'.format(automation_path))
        # convert to list and remove 0th element due to extra comma (this is easier than in the VBS code above)
        lTokens = response.upper().split(',')[1:]
        iterTokens = iter(lTokens)
        return zip(iterTokens, iterTokens, iterTokens)

    def get_panel_cvar_names(self, automation_path: str) -> list:
        """Return list of cvar names for cvars that are eligible for save in panel

        Args:
            automation_path ([str]): Automation start path

        Returns:
            [list]: Returns the Cvar names
        """
        # CvarsValuesRemote property returns comma-sep list of cvar,name pairs for all cvars
        # that are eligible for the panel
        response = self.query_vbs('{0}.CvarsValuesRemote'.format(automation_path))
        lTokens = response.upper().split(',')
        # slice-spec to create a list containing every other element
        return lTokens[::2]

    def get_automation_cvar_names(self, automation_path: str) -> list:
        """Return list of cvar names for cvars that are available to the user

        Args:
            automation_path (str): Automation start path

        Returns:
            [list]: Returns the Cvar names
        """
        # these are the panel cvars and any that have cvarflags 16384 (ForcePublic)
        lPanelCvars = self.get_panel_cvar_names(automation_path)
        lCvarsInfo = self.get_cvars_info(automation_path)
        lForcePublic = [cvName for (cvName, cvType, cvFlags) in lCvarsInfo if int(cvFlags) & 16384 == 16384]
        lPanelCvars.extend(lForcePublic)
        return lPanelCvars
