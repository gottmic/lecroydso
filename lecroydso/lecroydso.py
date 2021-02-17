#-----------------------------------------------------------------------------
# $Header: //SoftwareQA/Test/IR/Nightly_Automation/MergeStartXreplay/lecroy_dso.py#6 $
#-----------------------------------------------------------------------------
# Summary:		Implementation of LeCroyDSO class
# Authors:		Ashok Bruno
# Started:		2/9/2021
# Copyright 2021-2024 Teledyne LeCroy Corporation. All Rights Reserved.
#-----------------------------------------------------------------------------

from lecroydso.dsoconnection import DSOConnection
import time
import re
import logging
from datetime import datetime

verbose = 2     #set 1 (or 2) 


#------------------------------------------------------------------------------------
# Class: LeCroyDSO
class LeCroyDSO:
    """[Communication interface to a LeCroy Oscilloscope]
    """

    def __init__(self, myConnection: DSOConnection, log:bool=False):
        """[summary]

        Args:
            myConnection (DSOConnection): [A connection interface to the oscilloscope like ActiveDSO, LeCroyVISA]
            log (bool, optional): [creates a log output]. Defaults to False.
        """

        self._conn = myConnection
        self.connected = True
        self.verbose = verbose
        self.stopOnFailed = False
        self.logger = None
        self._conn.queryResponseMaxLength = 1000000
        if self.connected == True:
            if log:
                self.__createLogger(self._conn.connectionString)

            self.__init_vbs()
            
            #determine what model this scope is
            (self.manufacturer, self.model, self.serialNumber, self.firmwareVersion) = self.send_query('*IDN?').split(',')
            
            self.availableChannels = []
            self.availableDigitalChannels = []
            self.availableFunctions = []
            self.availableParameters = []
            self.availableMemories = []
            self.availableZooms = []

            try:
                self.execsAll = self.send_vbs_query('app.ExecsNameAll').split(',')
                # parse this to get numChannels, numFunctions, numMemories, numParameters
                for exec in self.execsAll:
                    if exec.startswith('C'):
                        self.availableChannels.append(exec)
                    elif exec.startswith('D'):
                        self.availableDigitalChannels.append(exec)
                    elif exec.startswith('F'):
                        self.availableFunctions.append(exec)
                    elif exec.startswith('P'):
                        self.availableParameters.append(exec)
                    elif exec.startswith('M'):
                        self.availableMemories.append(exec)
                    elif exec.startswith('Z1'):
                        self.availableZooms.append(exec)
            except ValueError:
                # some default values if unable to read the cvar
                self.availableChannels = ['C1', 'C2', 'C3', 'C4']
                self.availableDigitalChannels = ['D1', 'D2', 'D3', 'D4']
                self.availableFunctions = ['F1', 'F2', 'F3', 'F4']
                self.availableParameters = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6']
                self.availableMemories = ['M1', 'M2', 'M3', 'M4']
                self.availableZooms = ['Z1', 'Z2', 'Z3', 'Z4']

            iNumChannels = len(self.availableChannels)
            self.bAttenuatorUsed = True
            if (iNumChannels == 2):
                self.bAttenuatorUsed = False
            self.get_instrument_max_bandwidth()

    def __del__(self):
        if self.connected:
            self.disconnect_from_dso()
            self.disconnect()

    def __createLogger(self, suffix: str):
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

    def disconnect(self):
        if self.connected:
            self.connected = False

    def disconnect_from_dso(self):
        self._conn.disconnect()

    @property 
    def numChannels(self):
        return len(self.availableChannels)

    @property 
    def numDigitalChannels(self):
        return len(self.availableDigitalChannels)

    @property
    def numFunctions(self):
        return len(self.availableFunctions)

    @property 
    def numMemories(self):
        return len(self.availableMemories)
    
    @property
    def numParameters(self):
        return len(self.availableParameters)

    @property
    def numZooms(self):
        return len(self.availableZooms)

    @property
    def queryResponseMaxLength(self) -> int:
        return self._conn.queryResponseMaxLength

    @queryResponseMaxLength.setter
    def queryResponseMaxLen(self, val:int):
        self._conn.queryResponseMaxLength = val

    def send_command(self, strCmd: str):
        self._conn.send_command(strCmd)

    def send_vbs_command(self, strCmd: str):
        self._conn.send_vbs_command(strCmd)

    def send_query(self, strQuery: str) -> str:
        return self._conn.send_query(strQuery)

    def send_vbs_query(self, strQuery: str) -> str:
        return self._conn.send_vbs_query(strQuery)

    def set_default_state(self):
        """[Sets the default state of the DSO]
        """
        self.write_cvar('app.SystemControl.EnableMessageBox', 0)
        self.send_command('CHDR OFF')
        self.send_query('ALST?')
        self.wait_for_opc()
        self.send_command('*RST')
        self.send_command('CHDR OFF')
        self.send_vbs_command('app.SaveRecall.Setup.DoRecallDefaultPanelWithTriggerModeAuto')
        self.wait_for_opc()
        self.wait_for_opc()

    def restart_app(self):
        """[Restarts the scope application]
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

    def acquire(self, timeout:float=0.1, Force:bool =True) -> int:
        """[summary]

        Args:
            timeout (float, optional): [timeout in seconds for the acquisition to wait]. Defaults to 0.1.
            Force (bool, optional): [description]. Defaults to True.

        Returns:
            int: [description]
        """
        if Force == True:
            self.send_vbs_command('acq.acquire ' + str(timeout) + ',' + str(Force))
            self.waitForOpc()
            return True
        else:
            triggered = self.send_vbs_query('acq.acquire(' + str(timeout) + ')')
            if triggered == '0' or triggered == '1':
                return int(triggered)
            else:
                return 0

    #------------------------------------------------------------------------------------
    def write_cvar(self, path: str, value):
        self.send_vbs_command(path + '=' + str(value))

    #------------------------------------------------------------------------------------
    def read_cvar(self, path: str):
        return self.send_vbs_query(path)

    #------------------------------------------------------------------------------------
    def get_scope_setup(self, filename: str = None) -> str:
        setup = self._conn.GetPanel()

        if filename != None:
            setup = setup[0:-8]
            with open(filename,'w') as f:
                f.write(setup)
        return setup

    #------------------------------------------------------------------------------------
    def set_scope_setup(self, setup: str, filename: str = None):
        if filename == None:
            theSetup = setup
        else:
            with open(filename, 'r') as f:
                theSetup = f.read() + 'ffffffff'

        return self._conn.SetPanel(theSetup)


    def transfer_file_to_dso(self, remoteDevice: str, remoteFileName: str, localFileName: str) -> bool:
        """[Transfers a file from the PC to the remote device]

        Args:
            remoteDevice (str): [The device name on the instrument end, typically CARD, HDD]
            remoteFileName (str): [The name and path of the destination file on the instrument]
            localFileName (str): [The name and path of the source file on the PC]

        Returns:
            bool: [True on success, False on failure]
        """
        response = self._conn.transfer_file_to_dso(remoteDevice, remoteFileName, localFileName)
        return response >= 0.0

    def transfer_file_to_pc(self, remoteDevice: str, remoteFileName: str, localFileName: str) -> bool:
        """[Transfers a file from the remote device to the PC]

        Args:
            remoteDevice (str): [The device name on the instrument end, typically CARD, HDD]
            remoteFileName (str): [The name and path of the destination file on the instrument]
            localFileName (str): [The name and path of the source file on the PC]

        Returns:
            bool: [True on success, False on failure]
        """
        response = self._conn.transfer_file_to_pc(remoteDevice, remoteFileName, localFileName)
        return response >= 0.0


    #------------------------------------------------------------------------------------
    def pava(self, channel: str, measurement: str) -> tuple:

        result = self.send_query(channel + ':PAVA? ' + measurement).split(',')
        status = result[2]

        if status.upper() == 'OK':
            value = float(result[1])
        else:
            value = 0.0

        return value, status

    #------------------------------------------------------------------------------------
    def pava_one_parameter(self, source: str, param: str) -> str:
        if (source.upper() in self.availableChannels or source.upper() in self.availableDigitalChannels):
            ret = self.send_query(source.upper() + ':PAVA? ' + param)
            if ret != '':
                return ret.split(',')[1]
            else:
                return '-1.0'
        else:
            return None

    #------------------------------------------------------------------------------------
    def set_trigger_source(self, source: str):
        if (source.upper() in ['EXT', 'LINE'] or source.upper() in self.availableChannels or source.upper() in self.availableDigitalChannels):
            self.triggerSource = source.upper()
            self.send_vbs_command('acqTrig.source = "' + source.upper() + '"')
            return True
        else:
            return False

    #------------------------------------------------------------------------------------
    def set_trigger_mode(self, mode: str = 'STOPPED'):
        if mode.upper() in ['AUTO', 'NORMAL', 'SINGLE', 'STOPPED']:
            self.triggerMode = mode.upper()
            self.send_vbs_command('acq.triggermode = "' + mode.upper() + '"')
        self.waitForOpc()

    #------------------------------------------------------------------------------------
    def get_trigger_mode(self) -> str:
        mode = self.read_cvar('acq.TriggerMode')
        return mode.upper()

    #------------------------------------------------------------------------------------
    def set_trigger_coupling(self, channel: str, coupling: str = 'DC') -> bool:
        if ((channel.upper() in self.availableChannels) and (coupling.upper() in ('DC', 'AC', 'LFREJ', 'HFREJ'))):
            self.send_vbs_command('acqTrig.' + channel.upper() + 'Coupling = "' + coupling.upper() + '"')
            return True
        else:
            return False

    #------------------------------------------------------------------------------------
    def set_holdoff_type(self, type: str = 'OFF'):
        if type.upper() in ['OFF', 'TIME', 'EVENTS']:
            self.send_vbs_command('acqTrig.HoldoffType = "' + type.upper() + '"')

    #------------------------------------------------------------------------------------
    def set_holdoff_events(self, numEvents: int = 1):
        if numEvents >= 1 and numEvents <= 1000000000:
            self.send_vbs_command('acqTrig.HoldoffEvents = ' + str(numEvents))

    #------------------------------------------------------------------------------------
    def set_average_sweeps(self, channel: str, sweeps: int = 1):
        if (channel.upper() in self.availableChannels and sweeps >= 1 and sweeps <= 1000000):
            self.send_vbs_command('app.acquisition.' + channel.upper() + '.AverageSweeps = ' + str(sweeps))

    #------------------------------------------------------------------------------------
    def clear_sweeps(self):
        self.send_vbs_command('app.ClearSweeps.ActNow()')

    #------------------------------------------------------------------------------------
    def set_trigger_level(self, source: str, level:float=0.0):
        if (source.upper() in ('EXT') or source.upper() in self.availableChannels):
            self.send_vbs_command('acqTrig.' + source.upper() + 'Level = ' + str(level))
        elif (source.upper() in self.availableDigitalChannels):
            group = int(source.upper().replace('D', '')) / 9
            self.send_vbs_command('app.LogicAnalyzer.MSxxLogicFamily' + str(group) + ' = "UserDefined"')
            self.send_vbs_command('app.LogicAnalyzer.MSxxThreshold' + str(group) + ' = ' + str(level))

    #------------------------------------------------------------------------------------
    def set_digital_hysteresis_level(self, source: str, level:float=0.1):
        if (source.upper() in self.availableDigitalChannels and level >= .1 and level <= 1.4):
            group = int(source.upper().replace('D', '')) / 9
            self.send_vbs_command('app.LogicAnalyzer.MSxxLogicFamily' + str(group) + ' = "UserDefined"')
            self.send_vbs_command('app.LogicAnalyzer.MSxxHysteresis' + str(group) + ' = ' + str(level),True)

    #------------------------------------------------------------------------------------
    def set_trigger_type(self, type: str = 'EDGE'):
        if type.upper() in ['EDGE', 'WIDTH', 'QUALIFIED', 'WINDOW',
                            'INTERNAL', 'TV', 'PATTERN']:
            self.send_vbs_command('acqTrig.type = ' + type.upper())
            return True
        else:
            return False

    #------------------------------------------------------------------------------------
    def set_trigger_slope(self, channel: str, slope: str = 'POSITIVE') -> bool:
        if (slope.upper() in ['POSITIVE', 'NEGATIVE', 'EITHER']):
            if (channel.upper() in self.availableChannels):
                self.send_vbs_command('acqTrig.' + channel.upper() + '.slope = "' + slope.upper() + '"')
                return True
            elif channel.uppper in ['EXT', 'LINE']:
                self.send_vbs_command('acqTrig.' + channel.upper() + '.slope = "' + slope.upper() + '"')
                return True
            else:
                return False				
        else:
            return False

    #------------------------------------------------------------------------------------
    def set_coupling(self, source: str, coupling: str ='DC50'):
        if coupling.upper() not in ['DC50', 'DC1M', 'AC1M', 'GND','DC100k']:
            return
        if source.upper() in self.availableChannels:
            self.send_vbs_command('app.acquisition.' + source.upper() + '.Coupling = "' + coupling.upper() + '"')
        else:
            if source.upper() == 'EXT':
                source = 'AUXIN'
            if source.upper() == 'AUXIN':
                self.send_vbs_command('app.acquisition.' + source.upper() + '.Coupling = "' + coupling.upper() + '"')


    #------------------------------------------------------------------------------------
    def set_ver_offset(self, source: str, verOffset: float = 0.0):
        if source.upper() in self.availableChannels:
            self.send_vbs_command('app.acquisition.' + source.upper() + '.VerOffset = ' + str(verOffset))

    #------------------------------------------------------------------------------------
    def set_view(self, channel: str, view=True, digitalGroup:str = 'Digital1'):
        if (channel.upper() in self.availableChannels and (view in [True, False])):
            self.send_vbs_command('app.acquisition.' + channel.upper() + '.view = ' + str(view))
            return True
        elif (channel.upper() in self.availableDigitalChannels and view in (True, False) and digitalGroup.upper() in ('DIGITAL1', 'DIGITAL2', 'DIGITAL3', 'DIGITAL4')):
            self.send_vbs_command('app.LogicAnalyzer.' + digitalGroup.upper() + '.Digital' + channel.upper()[1:] + ' = ' + str(view))
            return True
        else:
            return False

    #------------------------------------------------------------------------------------
    def enable_digital_group(self,digitalGroup='Digital1',enable=True):
        if (enable in (True, False) and digitalGroup.upper() in ('DIGITAL1', 'DIGITAL2', 'DIGITAL3', 'DIGITAL4')):
            self.send_vbs_command('app.LogicAnalyzer.' + digitalGroup.upper() + '.View = ' + str(enable))

    #------------------------------------------------------------------------------------
    def set_bandwidth_limit(self, channel: str, bandwidth='FULL'):
        if ((channel.upper() in self.availableChannels) and (bandwidth.upper() in ['FULL', '350MHZ', '200MHZ', '100MHZ', '20MHZ', 'RAW'])):
            self.send_vbs_command('app.acquisition.' + channel.upper() + '.BandwidthLimit = "' + bandwidth.upper() + '"')

    #------------------------------------------------------------------------------------
    def set_ver_scale(self, source: str, verScale: float = 0.001):

        if source.upper() in self.availableChannels:
            self.send_vbs_command('acq.' + source.upper() + '.VerScale = ' + str(verScale))

    #------------------------------------------------------------------------------------
    def set_ver_scale_variable(self, source: str, variable:bool = False):
        if variable and source.upper() in self.availableChannels:
            self.send_vbs_command('acq.' + source.upper() + '.VerScaleVariable = 1')
        elif not variable and source.upper() in self.availableChannels:
            self.send_vbs_command('acq.' + source.upper() + '.VerScaleVariable = 0')

    #------------------------------------------------------------------------------------
    def set_sample_mode(self, sampleMode: str = 'REALTIME', segments = 10):
        if sampleMode.upper() in ['REALTIME', 'RIS', 'ROLL', 'SEQUENCE']:
            self.send_vbs_command('acqHorz.samplemode = "' + sampleMode.upper() + '"')
        if sampleMode.upper() in ['SEQUENCE']:
            if segments >= 2:
                self.send_vbs_command('acqHorz.numsegments = ' + str(segments))

    #------------------------------------------------------------------------------------
    def set_reference_clock(self, source: str = 'INTERNAL'):
        if source.upper() in ('INTERNAL', 'EXTERNAL'):
            self.send_vbs_command('acqHorz.referenceclock = "' + source.upper() + '"')
            return True
        else:
            return False

    #------------------------------------------------------------------------------------
    def set_hor_scale(self, horScale: float = 2e-011):
        if horScale >= 2e-011 and horScale <= 3200:
            self.send_vbs_command('acqHorz.horscale = ' + str(horScale))

    #------------------------------------------------------------------------------------
    def set_hor_offset(self, horOffset: float = 0.0):
        if horOffset >= -5e-5 and horOffset <= 5e-8:
            self.send_vbs_command('acqHorz.horoffset = ' + str(horOffset))

    #------------------------------------------------------------------------------------
    def set_num_points(self, numPoints:int = 20000):
        if numPoints <= 1000000000 and numPoints >= 1:
            self.send_vbs_command('acqHorz.numpoints = ' + str(numPoints))

    #------------------------------------------------------------------------------------
    def set_max_samples(self, maxSamples: int = 50000):
        self.write_cvar('acqHorz.MaxSamples', str(maxSamples))

    #------------------------------------------------------------------------------------
    def set_sample_rate(self, sampleRate: float = 2e09):
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
    def set_memory_mode(self, maximize: str = 'SetMaximumMemory'):
        if maximize.upper() in ['SETMAXIMUMMEMORY', 'FIXEDSAMPLERATE']:
            self.send_vbs_command('acqHorz.maximize = "' + maximize.upper() + '"')

    #------------------------------------------------------------------------------------
    def set_hardcopy_fileName(self, filename: str = 'wav000.jpg'):
        if filename != None:
            self.send_vbs_command('app.Hardcopy.PreferredFilename = "' + filename + '"')

    #------------------------------------------------------------------------------------
    def set_hardcopy_destination(self, destination: str = 'EMAIL'):
        if destination.upper() in ['CLIPBOARD', 'EMAIL', 'FILE', 'PRINTER', 'REMOTE']:
            self.send_vbs_command('app.Hardcopy.Destination = "' + destination.upper() + '"')

    #------------------------------------------------------------------------------------
    def set_hardcopy_area(self, area: str = 'DSOWINDOW'):
        if area.upper() in ['DSOWINDOW', 'FULLSCREEN', 'GRIDAREAONLY']:
            self.send_vbs_command('app.Hardcopy.HardCopyArea = "' + area.upper() + '"')

    #------------------------------------------------------------------------------------
    def set_hardopy_orientation(self, orientation: str ='LANDSCAPE'):
        if orientation.upper() in ['PORTRAIT', 'LANDSCAPE']:
            self.send_vbs_command('app.Hardcopy.Orientation = "' + orientation.upper() + '"')

    #------------------------------------------------------------------------------------
    def set_hardcopy_print(self):
        self.send_vbs_command('app.Hardopy.Print')

    #------------------------------------------------------------------------------------
    def set_hardcopy_color(self, color: str = 'BW'):
        if color.upper() in ['BW', 'PRINT', 'STD']:
            self.send_vbs_command('app.Hardcopy.UseColor = "' + color.upper() + '"')

    #------------------------------------------------------------------------------------
    def get_hor_scale(self):
        horScale = float(self.read_cvar('acqHorz.horscale'))
        return horScale

    #------------------------------------------------------------------------------------
    def get_num_points(self) -> float:
        horScale = float(self.read_cvar('acqHorz.numpoints'))
        return horScale

    #------------------------------------------------------------------------------------
    def getSampleRate(self) -> float:
        horScale = float(self.read_cvar('acqHorz.samplerate'))
        return horScale

    #------------------------------------------------------------------------------------
    def get_num_sweeps(self, source: str) -> int:
        if source.upper() in self.availableChannels:
            res = self.read_cvar('app.acquisition.' + source.upper() + '.Out.Result.Sweeps')
            try:
                numSweeps = int(res)
            except ValueError:
                numSweeps = 0
            return numSweeps
        else:
            return -1

    #------------------------------------------------------------------------------------
    def get_time_per_point(self) -> float:
        timePerPoint = float(self.read_cvar('acqHorz.timeperpoint'))
        return timePerPoint

    #------------------------------------------------------------------------------------
    def get_ver_scale(self, source: str) -> float:

        if source.upper() in self.availableChannels:
            verScale = float(self.read_cvar('app.acquisition.' + source.upper() + '.VerScale'))
            return verScale
        else:
            return 0.0

    #------------------------------------------------------------------------------------
    def get_ver_offset(self, source: str) -> float:

        if source.upper() in self.availableChannels:
            verScale = float(self.read_cvar('app.acquisition.' + source.upper() + '.VerOffset'))
            return verScale
        else:
            return 0.0

    #------------------------------------------------------------------------------------
    def recall_default_panel(self):
        self.send_vbs_command('app.SaveRecall.Setup.DoRecallDefaultPanel')
        self.waitForOpc()

    #------------------------------------------------------------------------------------
    def get_serial_number(self) -> str:
        self.scopeSerial = self.read_cvar('app.SerialNumber')
        return self.scopeSerial

    #------------------------------------------------------------------------------------
    def get_instrument_max_bandwidth(self) -> str:
        self.maxBandwidth = self.read_cvar('app.InstrumentMaxBandwidth')
        return self.maxBandwidth

    #------------------------------------------------------------------------------------
    def get_instrument_model(self) -> str:
        self.instrumentModel = self.read_cvar('app.InstrumentModel')
        return self.instrumentModel

    #------------------------------------------------------------------------------------
    def get_firmware_version(self) -> str:
        self.firmwareVersion = self.read_cvar('app.FirmwareVersion')
        return self.firmwareVersion

    #------------------------------------------------------------------------------------
    def set_measure_statistics(self, on:bool = True):
        self.MeasureStats = on
        if on:
            self.send_vbs_command('meas.StatsOn = 1')
        else:
            self.send_vbs_command('meas.StatsOn = 0')

    #------------------------------------------------------------------------------------
    def set_measure(self, parameterNumber: str, source1: str, source2: str = 'None', paramEngine: str = 'TimeAtLevel', view: bool = True):
        self.send_vbs_command('meas.' + parameterNumber.upper() + '.ParamEngine = "' + paramEngine.upper() + '"')
        self.send_vbs_command('meas.' + parameterNumber.upper() + '.Source1 = "' + source1.upper() + '"')
        self.send_vbs_command('meas.' + parameterNumber.upper() + '.Source2 = "' + source2.upper() + '"')
        if view:
            self.send_vbs_command('meas.View' + parameterNumber.upper() + ' = 1')
        else:
            self.send_vbs_command('meas.View' + parameterNumber.upper() + ' = 0')

    #------------------------------------------------------------------------------------
    def set_measure_channel(self, parameterNumber: str, source1: str, source2: str = 'None'):
        if (source1.upper() in self.availableChannels and (source2.upper() in self.availableChannels or source2.upper() == 'NONE')):

            self.send_vbs_command('meas.' + parameterNumber.upper() + '.Source1 = "' + source1.upper() + '"')
            self.send_vbs_command('meas.' + parameterNumber.upper() + '.Source2 = "' + source2.upper() + '"')
            return True
        else:
            return False

    #------------------------------------------------------------------------------------
    def get_measure(self, parameterNumber: str) -> tuple:
        if parameterNumber not in self.availableParameters:
            return None
        last = self.read_cvar('meas.' + parameterNumber + '.last.Result.Value')
        max = self.read_cvar('meas.' + parameterNumber + '.max.Result.Value')
        mean = self.read_cvar('meas.' + parameterNumber + '.mean.Result.Value')
        min = self.read_cvar('meas.' + parameterNumber + '.min.Result.Value')
        num = self.read_cvar('meas.' + parameterNumber + '.num.Result.Value')
        sdev = self.read_cvar('meas.' + parameterNumber + '.sdev.Result.Value')
        status = self.read_cvar('meas.' + parameterNumber + '.Out.Result.Status')
        self.waitForOpc()
        return (last, max, mean, min, num, sdev, status)

    #------------------------------------------------------------------------------------
    def get_measure_value(self, parameterNumber: str):
        if parameterNumber not in self.availableParameters:
            return None
        last = self.read_cvar('meas.' + parameterNumber + '.last.Result.Value')
        self.waitForOpc()
        try:
            fLast = float(last)
        except:
            fLast = -999999.99
        return fLast

    #------------------------------------------------------------------------------------
    def get_measure_mean(self, parameterNumber: str = 'P1'):
        mean = self.read_cvar('meas.' + parameterNumber + '.mean.Result.Value')
        self.waitForOpc()
        try:
            fMean = float(mean)
        except:
            fMean = -999999.99
        return fMean

    #------------------------------------------------------------------------------------
    def set_zoom(self, zoomNum: str, source: str):
        self.send_vbs_command('zoom.' + zoomNum.upper() + '.Source = "' + source.upper() + '"')
        self.show_zoom(zoomNum)

    #------------------------------------------------------------------------------------
    def show_zoom(self, zoomNum: str, show: bool = True):
        self.send_vbs_command('zoom.' + zoomNum.upper() + '.View = ' + str(-1) if show else str(0))

    #------------------------------------------------------------------------------------
    def set_zoom_segment(self, zoomNum: str, startSeg: int = 1,numToShow: int = 1):
        self.send_vbs_command('zoom.' + zoomNum.upper() + '.Zoom.SelectedSegment = "' + str(startSeg) + '"' )
        self.send_vbs_command('zoom.' + zoomNum.upper() + '.Zoom.NumSelectedSegments = "' + str(numToShow) + '"')

    #------------------------------------------------------------------------------------
    def set_aux_mode(self, mode:str = 'FASTEDGE'):
        if mode.upper() in ['TRIGGERENABLED', 'TRIGGEROUT', 'PASSFAIL', 'FASTEDGE', 'OFF']:
            self.send_vbs_command('app.Acquisition.AuxOutput.AuxMode = "' + mode.upper() + '"')

    #------------------------------------------------------------------------------------
    def set_show_measure(self, show: bool =True):
        if show:
            self.send_vbs_command('meas.ShowMeasure = 1')
        else:
            self.send_vbs_command('meas.ShowMeasure = 0')

    #------------------------------------------------------------------------------------
    def set_auxin_attenuation(self, attenuation: str = 'X1'):
        if attenuation.upper() in ['X1', 'DIV10']:
            self.send_vbs_command('app.acquisition.AuxIn.Attenuation = "' + attenuation + '"')

    #------------------------------------------------------------------------------------
    def wait_for_opc(self):
        self._conn.wait_for_opc()

    #------------------------------------------------------------------------------------
    def instrument_sleep(self, t):
        self.send_vbs_command('app.Sleep {0}'.format(t))

    #------------------------------------------------------------------------------------
    def force_trigger(self):
        self.send_command('FRTR')

    #------------------------------------------------------------------------------------
    def vbs(self, vbsCommand, expectingReturnValue: bool = False):
        if not expectingReturnValue:
            self.send_vbs_command(vbsCommand)
            response = 0
        else:
            response = self.send_vbs_query(vbsCommand)
        return response

    #------------------------------------------------------------------------------------
    def is_popup_dialog_open(self):
        strResponse = self.send_vbs_query('not syscon.dialogontop.widgetpageontop.value is Nothing')
        return re.match('0', strResponse) is None

    #------------------------------------------------------------------------------------
    def close_popup_dialog(self):
        self.send_vbs_command('syscon.DialogOnTop.ClosePopup')

    #------------------------------------------------------------------------------------
    def click_popup_dialog(self, strPopupAction: str):
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
    def is_docked_dialog_open(self, bRight) -> bool:
        strPage = self.get_docked_dialog_selected_page(bRight)
        return strPage.len > 0

    #------------------------------------------------------------------------------------
    def close_docked_dialog(self):
        self.send_vbs_command('syscon.CloseDialog')

    #------------------------------------------------------------------------------------
    def is_option_enabled(self, strOpt: str) -> bool:
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
            strResp = self.send_query("vbs? 'strProps = \"\": for each obj in {0}: strProps = strProps & \";\" & getProps(obj): next: return = strProps'".format(vbsCollVarName))
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
            strResp = self.send_query("vbs? 'strProps = \"\": for i = startIndex to stopIndex: set obj = {0}(i): strProps = strProps & \";\" & getProps(obj): next: return = strProps'".format(vbsCollVarName))

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

    #------------------------------------------------------------------------------------
    # return list of cvar names for cvars that are eligible for save in panel.
    def get_panel_cvar_names(self, strVbsAutomationPath):
        # CvarsValuesRemote property returns comma-sep list of cvar,name pairs for all cvars
        # that are eligible for the panel
        response = self.send_vbs_query('{0}.CvarsValuesRemote'.format(strVbsAutomationPath))
        lTokens = response.upper().split(',')
        # slice-spec to create a list containing every other element
        return lTokens[::2]

    #------------------------------------------------------------------------------------
    # return list of cvar names for cvars that are visible in xstreambrowser.
    def get_automation_cvar_names(self, strVbsAutomationPath):
        # these are the panel cvars and any that have cvarflags 16384 (ForcePublic)
        lPanelCvars = self.get_panel_cvar_names(strVbsAutomationPath)
        lCvarsInfo = self.get_cvars_info(strVbsAutomationPath)
        lForcePublic = [cvName for (cvName, cvType, cvFlags) in lCvarsInfo if int(cvFlags) & 16384 == 16384]
        lPanelCvars.extend(lForcePublic)
        return lPanelCvars





