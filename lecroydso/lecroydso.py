#-----------------------------------------------------------------------------
# $Header: $
#-----------------------------------------------------------------------------
# Summary:		Implementation of LeCroyDSO class
# Authors:		Ashok Bruno
# Started:		2/9/2021
# Copyright 2021-2024 Teledyne LeCroy Corporation. All Rights Reserved.
#-----------------------------------------------------------------------------

from lecroydso.errors import ParametersError
from typing import Any
from lecroydso.dsoconnection import DSOConnection
import time
import re
import logging
from datetime import datetime

verbose = 2     #set 1 (or 2) 


#------------------------------------------------------------------------------------
# Class: LeCroyDSO
class LeCroyDSO:
    """Communication interface to a LeCroy Oscilloscope
        
    Args:
        myConnection (DSOConnection): A connection interface to the oscilloscope like ActiveDSO, LeCroyVISA
        log (bool, optional): creates a log output. Defaults to False.
    """

    def __init__(self, myConnection:DSOConnection, log:bool=False):
        self._conn = myConnection
        self.connected = True
        self.verbose = verbose
        self.logger = None
        if self.connected == True:
            if log:
                self.__createLogger(self._conn.connectionString)

            self.__init_vbs()
            
            #determine what model this scope is
            (self.manufacturer, self.model, self.serial_number, self.firmware_version) = self.send_query('*IDN?').split(',')
            
            self.available_channels = []
            self.available_digital_channels = []
            self.available_functions = []
            self.available_parameters = []
            self.available_memories = []
            self.available_zooms = []

            try:
                self.execsAll = self.send_vbs_query('app.ExecsNameAll').split(',')
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
                    elif exec.startswith('Z1'):
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

    def __createLogger(self, suffix:str):
        self.logger = logging.getLogger('LeCroyDSO_' + suffix)
        self.logger.setLevel(logging.INFO)

        # create file handler which logs even debug messages
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

    def __init_vbs(self):
        # define some 'standard' variables in scope's VBS context, so commands
        # are simpler and more efficient
        self.send_vbs_command('set acq = app.Acquisition')
        self.send_vbs_command('set acqHorz = acq.Horizontal')
        self.send_vbs_command('set acqTrig = acq.Trigger')
        self.send_vbs_command('set chans = acq.channels')
        self.send_vbs_command('set sysCtrl = app.SystemControl')
        self.send_vbs_command('set meas = app.Measure')
        self.send_vbs_command('set p1 = meas.p1')
        self.send_vbs_command('set math = app.Math')
        self.send_vbs_command('set zoom = app.Zoom')
        self.send_vbs_command('set memory = app.Memory')
        self.send_vbs_command('set syscon = app.SystemControl')

    def validate_source(self, source:str):
        """Checks if source is valid

        Args:
            source (str): source string

        Raises:
            ParametersError: Raises exception if source is not valid
        """
        if source.upper() in self.available_channels or source.upper() in self.available_digital_channels:
            return
        raise ParametersError('source not found')

    def validate_parameters_source(self, parameterNumber: str):
        if parameterNumber not in self.available_parameters:
            raise ParametersError('parameterNumber not found')

    def disconnect(self):
        if self.connected:
            self.connected = False

    def disconnect_from_dso(self):
        self._conn.disconnect()

    @property 
    def numChannels(self) -> int:
        """readonly Property for number of channels
        """
        return len(self.available_channels)

    @property 
    def numDigitalChannels(self) -> int:
        """readonly Property for number of Digital Channels
        """
        return len(self.available_digital_channels)

    @property
    def numFunctions(self) -> int:
        """readonly Property for number of Functions F1 to Fn
        """        
        return len(self.available_functions)

    @property 
    def numMemories(self) -> int:
        """readonly Property for number of Memories M1 to Mn
        """ 
        return len(self.available_memories)
    
    @property
    def numParameters(self) -> int:
        """readonly Property for number of Parameters P1 to Pn
        """
        return len(self.available_parameters)

    @property
    def numZooms(self) -> int:
        """readonly Property for number of Zoom Z1 to Zn
        """        
        return len(self.available_zooms)

    @property
    def queryResponseMaxLength(self) -> int:
        """read max length of response string
        """        
        return self._conn.queryResponseMaxLength

    @queryResponseMaxLength.setter
    def queryResponseMaxLen(self, val:int):
        """set the maximum length of the response string from the instrument
        """
        self._conn.queryResponseMaxLength = val

    def send_command(self, strCmd:str):
        """Sends the command 

        Args:
            message (str): command string
        """
        self._conn.send_command(strCmd)

    def send_vbs_command(self, strCmd:str):
        """Sends the command as a VBS formatted comamnd

        Args:
            message (str): command string
        """
        self._conn.send_vbs_command(strCmd)

    def send_query(self, message:str, query_delay:float=None) -> str:
        """Send the query and returns the response

        Args:
            message (string): command to send
            query_delay (float, optional): delay between the command and response. Defaults to None.

        Returns:
            string: Response from the instrument
        """
        return self._conn.send_query(message, query_delay)

    def send_vbs_query(self, message:str, query_delay:float=None) -> str:
        """Send the query as a VBS formatted string and returns the response

        Args:
            message (string): command to send
            query_delay (float, optional): delay between the command and response. Defaults to None.

        Returns:
            string: Response from the instrument
        """       
        return self._conn.send_vbs_query(message, query_delay)

    def set_default_state(self):
        """Sets the default state of the DSO
        """
        self.send_vbs_command('app.SystemControl.EnableMessageBox = ' + str(0))
        self.send_command('CHDR OFF')
        self.send_query('ALST?')
        self.wait_for_opc()
        self.send_command('*RST')
        self.send_command('CHDR OFF')
        self.send_vbs_command('app.SaveRecall.Setup.DoRecallDefaultPanelWithTriggerModeAuto')
        self.wait_for_opc()
        self.wait_for_opc()

    def restart_app(self):
        """Restarts the scope application
        """
        self.disconnect()
        self.send_vbs_command('app.Restart')
        # wait and reconnect
        for _ in range(20):
            time.sleep(5)
            self._conn.reconnect()
            if self._conn.connected:
                break
        self.__init__(self._conn, self.logger)

    def acquire(self, timeout:float=0.1, force:bool =True) -> bool:
        """summary

        Args:
            timeout (float, optional): timeout in seconds for the acquisition to wait. Defaults to 0.1.
            force (bool, optional): Forces an acquisition to complete. Defaults to True.

        Returns:
            bool: True for Triggered, False if not Triggered or unknown state
        """
        if force == True:
            self.send_vbs_command('acq.acquire ' + str(timeout) + ',' + str(force))
            self.wait_for_opc()
            return True
        else:
            triggered = self.send_vbs_query('acq.acquire(' + str(timeout) + ')')
            if triggered == '0':
                return False
            elif triggered == '1':
                return True
            else:
                return False

    def get_scope_setup(self, filename:str = None) -> str:
        """Reads the instrument control state into a string

        Returns:
            str: panel file returned as a string, trailing terminator removed
        """        
        setup = self._conn.get_panel()

        if filename != None:
            setup = setup[0:-8]
            with open(filename,'w') as f:
                f.write(setup)
        return setup

    def set_scope_setup(self, setup:str, filename:str = None):
        """Set the instrument control state using a panel string, typically from the method get_panel

        Args:
            panel (str): description

        Returns:
            bool: True on success, False on failure
        """
        if filename == None:
            theSetup = setup
        else:
            with open(filename, 'r') as f:
                theSetup = f.read() + 'ffffffff'

        return self._conn.set_panel(theSetup)

    def get_waveform(self, source:str) -> bytes:
        """Get a waveform from the source specified

        Args:
            source (str): Source string 'C1'

        Returns:
            bytes: return the waveform as bytes, may need to processed further to make sense of it
        """
        self.validate_source(source)
        self._conn.send_command('%s:WF?', source)
        time.sleep(0.1)

        # read the first 11 bytes, this gives us the length of the transfer
        header = self._conn.read_raw(11)
        if 'WARNING' in str(header):
            return ''

        # get number of bytes in the response
        bytes = int(header.decode('utf-8').replace('#9', ''))

        # read the amount of data
        wf = self._conn.read_raw(bytes)
        # convert from a bytes array to a string and remove the trailing ffffffff
        return (wf.strip(bytes('ffffffff')))

    def transfer_file_to_dso(self, remoteDevice:str, remoteFileName:str, localFileName:str) -> bool:
        """Transfers a file from the PC to the remote device

        Args:
            remoteDevice (str): The device name on the instrument end, typically CARD, HDD
            remoteFileName (str): The name and path of the destination file on the instrument
            localFileName (str): The name and path of the source file on the PC

        Returns:
            bool: True on success, False on failure
        """
        response = self._conn.transfer_file_to_dso(remoteDevice, remoteFileName, localFileName)
        return response >= 0.0

    def transfer_file_to_pc(self, remoteDevice:str, remoteFileName:str, localFileName:str) -> bool:
        """Transfers a file from the remote device to the PC

        Args:
            remoteDevice (str): The device name on the instrument end, typically CARD, HDD
            remoteFileName (str): The name and path of the destination file on the instrument
            localFileName (str): The name and path of the source file on the PC

        Returns:
            bool: True on success, False on failure
        """
        response = self._conn.transfer_file_to_pc(remoteDevice, remoteFileName, localFileName)
        return response >= 0.0


    def pava(self, channel:str, measurement:str) -> tuple:
        """Sends a PAVA query to the instrument

        Args:
            channel (str): channel index as a str ('C1')
            measurement (str): specifies the PAVA measurement 

        Returns:
            tuple: returns (value, status)
        """
        result = self.send_query(channel + ':PAVA? ' + measurement).split(',')
        status = result[2]

        if status.upper() == 'OK':
            value = float(result[1])
        else:
            value = 0.0

        return value, status

    def pava_one_parameter(self, source:str, param:str) -> str:
        if (source.upper() in self.available_channels or source.upper() in self.available_digital_channels):
            ret = self.send_query(source.upper() + ':PAVA? ' + param)
            if ret != '':
                return ret.split(',')[1]
            else:
                return '-1.0'
        else:
            return None

    #------------------------------------------------------------------------------------
    def set_trigger_source(self, source:str):
        if (source.upper() in ['EXT', 'LINE'] or source.upper() in self.available_channels or source.upper() in self.available_digital_channels):
            self.send_vbs_command('acqTrig.source = "' + source.upper() + '"')
        else:
            raise ParametersError('source not found')

    #------------------------------------------------------------------------------------
    def set_trigger_mode(self, mode:str = 'STOPPED'):
        if mode.upper() in ['AUTO', 'NORMAL', 'SINGLE', 'STOPPED']:
            self.send_vbs_command('acq.triggermode = "' + mode.upper() + '"')
            self.wait_for_opc()

    #------------------------------------------------------------------------------------
    def get_trigger_mode(self) -> str:
        mode = self.send_vbs_query('acq.TriggerMode')
        return mode.upper()

    #------------------------------------------------------------------------------------
    def set_trigger_coupling(self, channel:str, coupling:str = 'DC') -> bool:
        if ((channel.upper() in self.available_channels) and (coupling.upper() in ('DC', 'AC', 'LFREJ', 'HFREJ'))):
            self.send_vbs_command('acqTrig.' + channel.upper() + 'Coupling = "' + coupling.upper() + '"')
            return True
        else:
            return False

    #------------------------------------------------------------------------------------
    def set_holdoff_type(self, type:str = 'OFF'):
        if type.upper() in ['OFF', 'TIME', 'EVENTS']:
            self.send_vbs_command('acqTrig.HoldoffType = "' + type.upper() + '"')

    #------------------------------------------------------------------------------------
    def set_holdoff_events(self, numEvents:int = 1):
        if numEvents >= 1 and numEvents <= 1000000000:
            self.send_vbs_command('acqTrig.HoldoffEvents = ' + str(numEvents))

    #------------------------------------------------------------------------------------
    def set_average_sweeps(self, channel:str, sweeps:int = 1):
        if (channel.upper() in self.available_channels and sweeps >= 1 and sweeps <= 1000000):
            self.send_vbs_command('app.acquisition.' + channel.upper() + '.AverageSweeps = ' + str(sweeps))

    #------------------------------------------------------------------------------------
    def clear_sweeps(self):
        self.send_vbs_command('app.ClearSweeps.ActNow()')

    #------------------------------------------------------------------------------------
    def set_trigger_level(self, source:str, level:float=0.0):
        if (source.upper() in ('EXT') or source.upper() in self.available_channels):
            self.send_vbs_command('acqTrig.' + source.upper() + 'Level = ' + str(level))
        elif (source.upper() in self.available_digital_channels):
            group = int(source.upper().replace('D', '')) / 9
            self.send_vbs_command('app.LogicAnalyzer.MSxxLogicFamily' + str(group) + ' = "UserDefined"')
            self.send_vbs_command('app.LogicAnalyzer.MSxxThreshold' + str(group) + ' = ' + str(level))
        else:
            raise ParametersError('source not found')

    #------------------------------------------------------------------------------------
    def set_digital_hysteresis_level(self, source:str, level:float=0.1):
        if (source.upper() in self.available_digital_channels and level >= .1 and level <= 1.4):
            group = int(source.upper().replace('D', '')) / 9
            self.send_vbs_command('app.LogicAnalyzer.MSxxLogicFamily' + str(group) + ' = "UserDefined"')
            self.send_vbs_command('app.LogicAnalyzer.MSxxHysteresis' + str(group) + ' = ' + str(level),True)
        else:
            raise ParametersError('source not found')

    #------------------------------------------------------------------------------------
    def set_trigger_type(self, type:str = 'EDGE'):
        """Set Trigger Type 

        Args:
            type (str, optional): Type of Triger specified as a string. Defaults to 'EDGE'.

        Returns:
            [type]: [description]
        """
        if type.upper() in ['EDGE', 'WIDTH', 'QUALIFIED', 'WINDOW',
                            'INTERNAL', 'TV', 'PATTERN']:
            self.send_vbs_command('acqTrig.type = ' + type.upper())
        else:
            raise ParametersError('source not found')

    #------------------------------------------------------------------------------------
    def set_trigger_slope(self, channel:str, slope:str = 'POSITIVE') -> bool:
        if (slope.upper() in ['POSITIVE', 'NEGATIVE', 'EITHER']):
            if (channel.upper() in self.available_channels):
                self.send_vbs_command('acqTrig.' + channel.upper() + '.slope = "' + slope.upper() + '"')
            elif channel.uppper in ['EXT', 'LINE']:
                self.send_vbs_command('acqTrig.' + channel.upper() + '.slope = "' + slope.upper() + '"')
            else:
                raise ParametersError('source not found')
        else:
            raise ParametersError('slope not found')

    #------------------------------------------------------------------------------------
    def set_coupling(self, source:str, coupling:str ='DC50'):
        if coupling.upper() not in ['DC50', 'DC1M', 'AC1M', 'GND','DC100k']:
            raise ParametersError()
        if source.upper() in self.available_channels:
            self.send_vbs_command('app.acquisition.' + source.upper() + '.Coupling = "' + coupling.upper() + '"')
        else:
            if source.upper() == 'EXT':
                source = 'AUXIN'
            if source.upper() == 'AUXIN':
                self.send_vbs_command('app.acquisition.' + source.upper() + '.Coupling = "' + coupling.upper() + '"')


    #------------------------------------------------------------------------------------
    def set_ver_offset(self, source:str, verOffset:float = 0.0):
        if source.upper() in self.available_channels:
            self.send_vbs_command('app.acquisition.' + source.upper() + '.VerOffset = ' + str(verOffset))
        else:
            raise ParametersError('source not found')

    #------------------------------------------------------------------------------------
    def set_view(self, channel:str, view:bool=True, digitalGroup:str = 'Digital1'):
        if (channel.upper() in self.available_channels and (view in [True, False])):
            self.send_vbs_command('app.acquisition.' + channel.upper() + '.view = ' + str(view))
        elif (channel.upper() in self.available_digital_channels and view in (True, False) and digitalGroup.upper() in ('DIGITAL1', 'DIGITAL2', 'DIGITAL3', 'DIGITAL4')):
            self.send_vbs_command('app.LogicAnalyzer.' + digitalGroup.upper() + '.Digital' + channel.upper()[1:] + ' = ' + str(view))
        else:
            raise ParametersError('source not found')

    #------------------------------------------------------------------------------------
    def set_bandwidth_limit(self, channel:str, bandwidth:str='FULL'):
        if ((channel.upper() in self.available_channels) and (bandwidth.upper() in ['FULL', '350MHZ', '200MHZ', '100MHZ', '20MHZ', 'RAW'])):
            self.send_vbs_command('app.acquisition.' + channel.upper() + '.BandwidthLimit = "' + bandwidth.upper() + '"')

    #------------------------------------------------------------------------------------
    def set_ver_scale(self, source:str, verScale:float = 0.001):

        if source.upper() in self.available_channels:
            self.send_vbs_command('acq.' + source.upper() + '.VerScale = ' + str(verScale))

    #------------------------------------------------------------------------------------
    def set_ver_scale_variable(self, source:str, variable:bool = False):
        if variable and source.upper() in self.available_channels:
            self.send_vbs_command('acq.' + source.upper() + '.VerScaleVariable = 1')
        elif not variable and source.upper() in self.available_channels:
            self.send_vbs_command('acq.' + source.upper() + '.VerScaleVariable = 0')

    #------------------------------------------------------------------------------------
    def set_sample_mode(self, sampleMode:str = 'REALTIME', segments = 10):
        if sampleMode.upper() in ['REALTIME', 'RIS', 'ROLL', 'SEQUENCE']:
            self.send_vbs_command('acqHorz.samplemode = "' + sampleMode.upper() + '"')
        if sampleMode.upper() in ['SEQUENCE']:
            if segments >= 2:
                self.send_vbs_command('acqHorz.numsegments = ' + str(segments))

    #------------------------------------------------------------------------------------
    def set_reference_clock(self, source:str = 'INTERNAL'):
        if source.upper() in ('INTERNAL', 'EXTERNAL'):
            self.send_vbs_command('acqHorz.referenceclock = "' + source.upper() + '"')
            return True
        else:
            return False

    #------------------------------------------------------------------------------------
    def set_hor_scale(self, horScale:float = 2e-011):
        if horScale >= 2e-011 and horScale <= 3200:
            self.send_vbs_command('acqHorz.horscale = ' + str(horScale))

    #------------------------------------------------------------------------------------
    def set_hor_offset(self, horOffset:float = 0.0):
        if horOffset >= -5e-5 and horOffset <= 5e-8:
            self.send_vbs_command('acqHorz.horoffset = ' + str(horOffset))

    #------------------------------------------------------------------------------------
    def set_num_points(self, numPoints:int = 20000):
        if numPoints <= 1000000000 and numPoints >= 1:
            self.send_vbs_command('acqHorz.numpoints = ' + str(numPoints))

    #------------------------------------------------------------------------------------
    def set_max_samples(self, maxSamples:int = 50000):
        self.send_vbs_command('acqHorz.MaxSamples = ' + str(maxSamples))

    #------------------------------------------------------------------------------------
    def set_sample_rate(self, sampleRate:float = 2e09):
##        if sampleRate in [500, 1e3, 2.5e3, 5e3, 10e3, 25e3, 50e3, 100e3, #We
##        should go towards a more encompassing method of checking the things
##        we set.  However, we could still include helpful tidbits like this
##        sample rate information from magellan.
##                          250e3, 500e3, 1e6, 2.5e6, 5e6, 10e6, 25e6, 50e6,
##                          100e6, 250e6, 500e6, 1e9, 2e9]:
            self.setMaximize('FIXEDSAMPLERATE')
            self.send_vbs_command('acqHorz.samplerate = ' + str(sampleRate))
            if self.getSampleRate() == float(sampleRate):
                return True
            else:
                return False

    #------------------------------------------------------------------------------------
    def set_memory_mode(self, maximize:str = 'SetMaximumMemory'):
        if maximize.upper() in ['SETMAXIMUMMEMORY', 'FIXEDSAMPLERATE']:
            self.send_vbs_command('acqHorz.maximize = "' + maximize.upper() + '"')

    #------------------------------------------------------------------------------------
    def set_hardcopy_fileName(self, filename:str = 'wav000.jpg'):
        if filename != None:
            self.send_vbs_command('app.Hardcopy.PreferredFilename = "' + filename + '"')

    #------------------------------------------------------------------------------------
    def set_hardcopy_destination(self, destination:str = 'EMAIL'):
        if destination.upper() in ['CLIPBOARD', 'EMAIL', 'FILE', 'PRINTER', 'REMOTE']:
            self.send_vbs_command('app.Hardcopy.Destination = "' + destination.upper() + '"')

    #------------------------------------------------------------------------------------
    def set_hardcopy_area(self, area:str = 'DSOWINDOW'):
        if area.upper() in ['DSOWINDOW', 'FULLSCREEN', 'GRIDAREAONLY']:
            self.send_vbs_command('app.Hardcopy.HardCopyArea = "' + area.upper() + '"')

    #------------------------------------------------------------------------------------
    def set_hardopy_orientation(self, orientation:str ='LANDSCAPE'):
        if orientation.upper() in ['PORTRAIT', 'LANDSCAPE']:
            self.send_vbs_command('app.Hardcopy.Orientation = "' + orientation.upper() + '"')

    #------------------------------------------------------------------------------------
    def set_hardcopy_print(self):
        self.send_vbs_command('app.Hardopy.Print')

    #------------------------------------------------------------------------------------
    def set_hardcopy_color(self, color:str = 'BW'):
        if color.upper() in ['BW', 'PRINT', 'STD']:
            self.send_vbs_command('app.Hardcopy.UseColor = "' + color.upper() + '"')

    #------------------------------------------------------------------------------------
    def get_hor_scale(self):
        horScale = float(self.send_vbs_query('acqHorz.horscale'))
        return horScale

    #------------------------------------------------------------------------------------
    def get_num_points(self) -> float:
        horScale = float(self.send_vbs_query('acqHorz.numpoints'))
        return horScale

    #------------------------------------------------------------------------------------
    def getSampleRate(self) -> float:
        horScale = float(self.send_vbs_query('acqHorz.samplerate'))
        return horScale

    #------------------------------------------------------------------------------------
    def get_num_sweeps(self, source:str) -> int:
        if source.upper() in self.available_channels:
            res = self.send_vbs_query('app.acquisition.' + source.upper() + '.Out.Result.Sweeps')
            try:
                numSweeps = int(res)
            except ValueError:
                numSweeps = 0
            return numSweeps
        else:
            return -1

    #------------------------------------------------------------------------------------
    def get_time_per_point(self) -> float:
        timePerPoint = float(self.send_vbs_query('acqHorz.timeperpoint'))
        return timePerPoint

    #------------------------------------------------------------------------------------
    def get_ver_scale(self, source:str) -> float:

        if source.upper() in self.available_channels:
            verScale = float(self.send_vbs_query('app.acquisition.' + source.upper() + '.VerScale'))
            return verScale
        else:
            return 0.0

    #------------------------------------------------------------------------------------
    def get_ver_offset(self, source:str) -> float:

        if source.upper() in self.available_channels:
            verScale = float(self.send_vbs_query('app.acquisition.' + source.upper() + '.VerOffset'))
            return verScale
        else:
            return 0.0

    #------------------------------------------------------------------------------------
    def recall_default_panel(self):
        self.send_vbs_command('app.SaveRecall.Setup.DoRecallDefaultPanel')
        self.wait_for_opc()

    #------------------------------------------------------------------------------------
    def get_serial_number(self) -> str:
        self.scopeSerial = self.send_vbs_query('app.SerialNumber')
        return self.scopeSerial

    #------------------------------------------------------------------------------------
    def get_instrument_max_bandwidth(self) -> str:
        self.maxBandwidth = self.send_vbs_query('app.InstrumentMaxBandwidth')
        return self.maxBandwidth

    #------------------------------------------------------------------------------------
    def get_instrument_model(self) -> str:
        self.instrumentModel = self.send_vbs_query('app.InstrumentModel')
        return self.instrumentModel

    #------------------------------------------------------------------------------------
    def get_firmware_version(self) -> str:
        self.firmware_version = self.send_vbs_query('app.FirmwareVersion')
        return self.firmware_version

    #------------------------------------------------------------------------------------
    def set_measure_statistics(self, on:bool = True):
        self.MeasureStats = on
        if on:
            self.send_vbs_command('meas.StatsOn = 1')
        else:
            self.send_vbs_command('meas.StatsOn = 0')

    #------------------------------------------------------------------------------------
    def set_measure(self, parameterNumber:str, source1:str, source2:str = 'None', paramEngine:str = 'TimeAtLevel', view: bool = True):
        self.send_vbs_command('meas.' + parameterNumber.upper() + '.ParamEngine = "' + paramEngine.upper() + '"')
        self.send_vbs_command('meas.' + parameterNumber.upper() + '.Source1 = "' + source1.upper() + '"')
        self.send_vbs_command('meas.' + parameterNumber.upper() + '.Source2 = "' + source2.upper() + '"')
        if view:
            self.send_vbs_command('meas.View' + parameterNumber.upper() + ' = 1')
        else:
            self.send_vbs_command('meas.View' + parameterNumber.upper() + ' = 0')

    #------------------------------------------------------------------------------------
    def set_measure_channel(self, parameterNumber:str, source1:str, source2:str = 'None'):
        if (source1.upper() in self.available_channels and (source2.upper() in self.available_channels or source2.upper() == 'NONE')):

            self.send_vbs_command('meas.' + parameterNumber.upper() + '.Source1 = "' + source1.upper() + '"')
            self.send_vbs_command('meas.' + parameterNumber.upper() + '.Source2 = "' + source2.upper() + '"')
            return True
        else:
            return False

    #------------------------------------------------------------------------------------
    def get_measure_stats(self, parameterNumber:str) -> tuple:
        """Reads the measurement statistics values for a parameter

        Args:
            parameterNumber (str): Parameter name 'P1'

        Returns:
            tuple: Returns the values (last, max, mean, min, num, sdev, status)
        """
        if parameterNumber not in self.available_parameters:
            raise ParametersError('parameterNumber not found')

        last = self.send_vbs_query('meas.' + parameterNumber + '.last.Result.Value')
        max = self.send_vbs_query('meas.' + parameterNumber + '.max.Result.Value')
        mean = self.send_vbs_query('meas.' + parameterNumber + '.mean.Result.Value')
        min = self.send_vbs_query('meas.' + parameterNumber + '.min.Result.Value')
        num = self.send_vbs_query('meas.' + parameterNumber + '.num.Result.Value')
        sdev = self.send_vbs_query('meas.' + parameterNumber + '.sdev.Result.Value')
        status = self.send_vbs_query('meas.' + parameterNumber + '.Out.Result.Status')
        self.wait_for_opc()

        return (last, max, mean, min, num, sdev, status)

    #------------------------------------------------------------------------------------
    def get_measure_value(self, parameterNumber:str):
        if parameterNumber not in self.available_parameters:
            raise ParametersError('parameterNumber not found')
        last = self.send_vbs_query('meas.' + parameterNumber + '.last.Result.Value')
        self.wait_for_opc()
        try:
            fLast = float(last)
        except:
            fLast = -999999.99
        return fLast

    #------------------------------------------------------------------------------------
    def get_measure_mean(self, parameterNumber:str = 'P1'):
        if parameterNumber not in self.available_parameters:
            raise ParametersError('parameterNumber not found')
        mean = self.send_vbs_query('meas.' + parameterNumber + '.mean.Result.Value')
        self.wait_for_opc()
        try:
            fMean = float(mean)
        except:
            fMean = -999999.99
        return fMean

    #------------------------------------------------------------------------------------
    def set_zoom(self, zoomNum:str, source:str):
        self.validate_source(source)
        self.send_vbs_command('zoom.' + zoomNum.upper() + '.Source = "' + source.upper() + '"')
        self.show_zoom(zoomNum)

    #------------------------------------------------------------------------------------
    def show_zoom(self, zoomNum:str, show: bool = True):
        self.send_vbs_command('zoom.' + zoomNum.upper() + '.View = ' + str(-1) if show else str(0))

    #------------------------------------------------------------------------------------
    def set_zoom_segment(self, zoomNum:str, startSeg:int = 1,numToShow:int = 1):
        self.send_vbs_command('zoom.' + zoomNum.upper() + '.Zoom.SelectedSegment = "' + str(startSeg) + '"' )
        self.send_vbs_command('zoom.' + zoomNum.upper() + '.Zoom.NumSelectedSegments = "' + str(numToShow) + '"')

    #------------------------------------------------------------------------------------
    def set_aux_mode(self, mode:str = 'FASTEDGE'):
        if mode.upper() in ['TRIGGERENABLED', 'TRIGGEROUT', 'PASSFAIL', 'FASTEDGE', 'OFF']:
            self.send_vbs_command('app.Acquisition.AuxOutput.AuxMode = "' + mode.upper() + '"')

    def set_show_measure(self, show:bool =True):
        """Opens the measure dialog

        Args:
            show (bool, optional): True to open and False to close. Defaults to True.
        """
        self.send_vbs_command('meas.ShowMeasure = 1' if show else 'meas.ShowMeasure = 0')

    #------------------------------------------------------------------------------------
    def set_auxin_attenuation(self, attenuation:str = 'X1'):
        if attenuation.upper() in ['X1', 'DIV10']:
            self.send_vbs_command('app.acquisition.AuxIn.Attenuation = "' + attenuation + '"')

    def wait_for_opc(self):
        """Wait for the previous operation to complete
        """
        self._conn.wait_for_opc()

    def instrument_sleep(self, t):
        """Sends a sleep command to the instrument

        Args:
            t ([type]): time to sleep in 
        """
        self.send_vbs_command('app.Sleep {0}'.format(t))

    def force_trigger(self):
        """Forces a trigger on the instrument
        """
        self.send_command('FRTR')

    #------------------------------------------------------------------------------------
    def vbs(self, vbsCommand, expectingReturnValue: bool = False):
        if not expectingReturnValue:
            self.send_vbs_command(vbsCommand)
            response = 0
        else:
            response = self.send_vbs_query(vbsCommand)
        return response

    def is_popup_dialog_open(self) -> bool:
        """Checks if a popup dialog is open

        Returns:
            [bool]: True if a popup dialog is open, False otherwise
        """
        strResponse = self.send_vbs_query('not syscon.dialogontop.widgetpageontop.value is Nothing')
        return re.match('0', strResponse) is None

    def close_popup_dialog(self):
        """Closes any popup dialogs that are open
        """
        self.send_vbs_command('syscon.DialogOnTop.ClosePopup')

    def click_popup_dialog(self, strPopupAction:str):
        self.send_vbs_command('syscon.DialogOnTop.{0}'.format(strPopupAction))

    #------------------------------------------------------------------------------------
    def get_docked_dialog_page_names(self, bRight: bool) -> str:
        strResponse = self.send_vbs_query('syscon.{0}DialogPageNames'.format('Right' if bRight else ''))
        return strResponse

    #------------------------------------------------------------------------------------
    def get_docked_dialog_selected_page(self, bRight: bool) -> str:
        strResponse = self.send_vbs_query('syscon.{0}DialogPage'.format('Right' if bRight else ''))
        return strResponse

    #------------------------------------------------------------------------------------
    def is_docked_dialog_open(self, bRight:bool) -> bool:
        """Checks if a docked dialog is open

        Args:
            bRight ([bool]): Set to True to check if right hand side dialog is open

        Returns:
            bool: Returns True if a docked dialog is open else False
        """
        strPage = self.get_docked_dialog_selected_page(bRight)
        return strPage.len > 0

    def close_docked_dialog(self):
        """Closes the docked dialog page
        """
        self.send_vbs_command('syscon.CloseDialog')

    def is_option_enabled(self, strOpt:str) -> bool:
        """Checks if the option specified is enabled

        Args:
            strOpt (str): Option string

        Returns:
            bool: True if option present else False
        """
        strResp = self.send_query('$$OP_PRE? {0}'.format(strOpt))
        return strResp != '0'

    #------------------------------------------------------------------------------------
    # return a list of automation collection items matching the specified criteria.
    # vbsCollVarName must be a valid automation collection name within the scope app's VBS context.
    # propertyAndMatchSpec is a list of 2-tuples, where the first tuple item specifies the name of an automation property
    # and the second specifies a matching regex, may be None which matches all.
    # propertyAndMatchSpec, by default, causes the returned list to contain the names of all items in the collection.
    def get_automation_items(self, vbsCollVarName, propertyAndMatchSpec = [('name', None)], bMatchAll = True):

        # build a vbs function in the scope context that will generate the comma-sep properties string for each item in the collection.
        # we'll apply the matching specs in python after parsing the responses, since it's much better at that and developing/maintaining/debugging
        # these scope vbs functions is horrible.
        listPropNames = [propItem[0] for propItem in propertyAndMatchSpec]
        listVbsGetPropsStatements = ['function getProps(o)']
        listVbsGetPropsStatements.append('on error resume next')
        listVbsGetPropsStatements.append('strProps = \'\'')
        for propName in listPropNames:
            listVbsGetPropsStatements.append('strProps = strProps & \',\'') # default to comma-sep if property doesn't exist
            listVbsGetPropsStatements.append('strProps = strProps & o.{0}'.format(propName))
        listVbsGetPropsStatements.append('getProps = strProps')
        listVbsGetPropsStatements.append('end function')
        strVbsPropsFunc = ':'.join(listVbsGetPropsStatements)
        self.send_vbs_command(strVbsPropsFunc)

        # build the vbs query that iterates the collection calling the vbs function for each item, semi-colon sep each item's properties.
        if False:
            # at least for now, for-each (IEnumVARIANT) is not correctly supported on CE... seems to be missing marshalling
            strResp = self.send_query("vbs? 'strProps = \"\": for each obj in {0}:strProps = strProps & \";\" & getProps(obj): next: return = strProps'".format(vbsCollVarName))
        else:
            # work-around for bad for-each behavior on CE.
            # painful: need to figure out if collection is 0-based index or not and set the startIndex and stopIndex variables used in query.
            listVbsStatements = ['on error resume next']
            listVbsStatements.append('set o1 = nothing')
            listVbsStatements.append('set o1 = {0}.item(0)'.format(vbsCollVarName))
            listVbsStatements.append('stopIndex = {0}.count'.format(vbsCollVarName))
            listVbsStatements.append('startIndex = 1')
            listVbsStatements.append('if not o1 is nothing then: startIndex = 0: stopIndex = stopIndex - 1: end if')
            listVbsStatements.append('on error goto 0')
            strVbsStatements = ':'.join(listVbsStatements)
            self.send_vbs_command(strVbsStatements)
            strResp = self.send_query("vbs? 'strProps = \"\": for i = startIndex to stopIndex: set obj = {0}(i):strProps = strProps & \";\" & getProps(obj): next: return = strProps'".format(vbsCollVarName))

        # parse the response, stripping and splitting on the item and property separators.
        # strip leading semi-colon and split to get list of comma-sep property strings for each object
        listPropsResp = strResp.lstrip(';').split(';')
        listOutputItems = []
        for strProps in listPropsResp:

            # strip leading command and split to get list of properties
            listProps = strProps.lstrip(',').split(',')
            listOutputProps = []
            countPropsMatched = 0
            for idx in range(0, len(listProps)):

                if idx < len(propertyAndMatchSpec):
                    strProp = listProps[idx]
                    strOutput = ''
                    if (propertyAndMatchSpec[idx][1] is None or propertyAndMatchSpec[idx][1].search(strProp)):
                        countPropsMatched += 1
                        strOutput = strProp

                    # add to output list of properties
                    listOutputProps.append(strOutput)

            if (bMatchAll and countPropsMatched == len(propertyAndMatchSpec)) or (not bMatchAll and countPropsMatched > 0):
                # add to output list of objects
                listOutputItems.append(listOutputProps)

        if self.verbose == 3:
            # print to pyconsole if verbose mode 3
            strMsg = 'get_automation_coll_items({0}, {1}):response={2} => {3}'.format(vbsCollVarName, propertyAndMatchSpec, strResp, listOutputItems)
            self.logger.debug(strMsg)

        return listOutputItems

    #------------------------------------------------------------------------------------
    # return a list of all matching object names (in specified vbsObjName collection).
    # if no match specified, then all are returned.
    def get_object_names(self, vbsCollName, matching = None):
        listObjsInfo = self.get_automation_coll_items(vbsCollName, [('name', matching)])
        listObjNames = [objInfo[0] for objInfo in listObjsInfo]
        return listObjNames

    #------------------------------------------------------------------------------------
    # return True if specified vbsCollName has the specified object, False if it does not.
    def does_object_exist(self, vbsCollName, strName):
        listCvarsInfo = self.get_automation_coll_items(vbsCollName, [('name', re.compile('^{0}$'.format(strName), re.IGNORECASE))])
        return len(listCvarsInfo) > 0

    #------------------------------------------------------------------------------------
    # return True if specified vbsObjName has the specified cvar, False if it does not.
    def does_cvar_exist(self, vbsObjName, strName):
        listCvarsInfo = self.get_automation_coll_items(vbsObjName, [('name', re.compile('^{0}$'.format(strName), re.IGNORECASE))])
        return len(listCvarsInfo) > 0

    #------------------------------------------------------------------------------------
    # return True if specified vbsObjCvarEnumName has the specified value in its Range, False if it does not.
    def is_cvar_enum_value_in_range(self, vbsCvarEnumName, strEnumValue, strRangeProperty = 'RangeStringAutomation'):
        response = self.send_vbs_query('{0}.{1}'.format(vbsCvarEnumName, strRangeProperty))
        return re.search(r'(^|,){0}(,|$)'.format(strEnumValue), response, re.IGNORECASE)

    #------------------------------------------------------------------------------------
    # return list of cvar names, types and flags (3-tuple) for the specified automation object.
    def get_cvars_info(self, strVbsAutomationPath):
        self.send_vbs_command('s1 = \'\'') #for some reason, doing this in the send_vbs_query isn't sufficient... ugh
        response = self.send_vbs_query('s1 = \'\': for i=0 to {0}.count - 1: set ocv={0}.Item(i): a1 = Array(s1, ocv.name, ocv.type, ocv.flags): s1 = Join(a1, \',\'): next: return = s1'.format(strVbsAutomationPath))
        lTokens = response.upper().split(',')[1:] #convert to list and remove 0th element due to extra comma (this is easier than in the VBS code above)
        iterTokens = iter(lTokens)
        return zip(iterTokens, iterTokens, iterTokens)

    def get_panel_cvar_names(self, strVbsAutomationPath:str) -> list:
        """Return list of cvar names for cvars that are eligible for save in panel

        Args:
            strVbsAutomationPath ([str]): Automation start path

        Returns:
            [list]: Returns the Cvar names 
        """
        # CvarsValuesRemote property returns comma-sep list of cvar,name pairs for all cvars
        # that are eligible for the panel
        response = self.send_vbs_query('{0}.CvarsValuesRemote'.format(strVbsAutomationPath))
        lTokens = response.upper().split(',')
        # slice-spec to create a list containing every other element
        return lTokens[::2]

    def get_automation_cvar_names(self, strVbsAutomationPath:str) -> list:
        """Return list of cvar names for cvars that are available to the user

        Args:
            strVbsAutomationPath (str): Automation start path

        Returns:
            [list]: Returns the Cvar names
        """
        # these are the panel cvars and any that have cvarflags 16384 (ForcePublic)
        lPanelCvars = self.get_panel_cvar_names(strVbsAutomationPath)
        lCvarsInfo = self.get_cvars_info(strVbsAutomationPath)
        lForcePublic = [cvName for (cvName, cvType, cvFlags) in lCvarsInfo if int(cvFlags) & 16384 == 16384]
        lPanelCvars.extend(lForcePublic)
        return lPanelCvars





