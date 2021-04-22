#-----------------------------------------------------------------------------
# $Header: //SoftwareQA/Test/IR/Nightly_Automation/MergeStartXreplay/ActiveDSO.py#3 $
# Summary:		Implementation of LeCroyVISA class
# Authors:		Ashok Bruno
# Started:		02/10/2021
# Copyright 2021-2024 Teldyne LeCroy Corporation. All Rights Reserved.
#-----------------------------------------------------------------------------
#

from lecroydso.errors import DSOConnectionError
import time
import pyvisa
from lecroydso.dsoconnection import DSOConnection

maxLen = 1e6

class LeCroyVISA(DSOConnection):
    def __init__( self, connectionString:str, queryResponseMaxLength:int=maxLen ):
        """Makes a connection to the instrument using ActiveDSO

        Args:
            connectionString (str): string in a specified format
            queryResponseMaxLength (integer, optional): description. Defaults to maxLen.
        """
        self.connectionString = None
        self._visa = None
        self.connected = False
        
        rm = pyvisa.ResourceManager()
        resources = rm.list_resources()
        if connectionString not in resources:
            raise DSOConnectionError("Unable to connect to resource")
            self.connected = False
            return
        try:
            scope = rm.open_resource(connectionString)
            scope.read_termination = '\n'
            scope.write_termination = '\n'
            scope.query_delay = 0.001
            scope.timeout = 10000
            if 'TCPIP' in connectionString or 'VICP' in connectionString:
                scope.timeout = 1000
                self._timeout = 1.0
            idn = scope.query('*IDN?')
            if len(idn) <= 0:
                self.connected = False
                return
            (self._manufacturer, self._model, self._serialNumber, self._firmwareVersion) = idn.split(',')

            scope.write('CHDR OFF')
            chdr = scope.query('CHDR?')
            if 'WARNING' in chdr:
                scope.connected = False
                scope.close()
                return 

            self._visa = scope
            self.connectionString = connectionString
            self.connected = True
            self.queryResponseMaxLength = queryResponseMaxLength
        except:
            raise DSOConnectionError("Unable to make a LeCroyVISA connection")

    def __del__(self):
        self.disconnect()

    @property
    def errorString(self):
        return self._errorString

    @property
    def errorFlag(self):
        return self._errorFlag
  
    @property 
    def timeout(self):
        return float(self._visa.timeout) / 1000.0

    @timeout.setter
    def timeout(self, timeout:float):
        """sets the timeout value used by the connection

        Args:
            timeout (float): timeout value in seconds

        """
        self._timeout = timeout
        self._visa.timeout = int(timeout * 1000)

    def reconnect(self):
        """Reconnects to the instrument with the existing credentials
        """
        if self.connected:
            self._visa.close()
        self.__init__(self.connectionString)
            
    def send_command(self, message:str):
        """Sends the command 

        Args:
            message (str): command string
        """        
        written = self._visa.write(message)
        self._errorFlag = written != (len(message) + 1)
        self._errorString = ''

    def send_query(self, message:str, query_delay:float=None) -> str:
        """Send the query and returns the response

        Args:
            message (str): command to send
            query_delay (float, optional): delay between the command the response. Defaults to None.

        Returns:
            string: description
        """
        if self._visa.write(message) == (len(message) + 1):
            if query_delay is not None:
                time.sleep(query_delay)
            response = self._visa.read()
        else:
            self._errorFlag = True
            self._errorString = 'Write to device Failed'
            return None

        self._errorFlag = False
        self._errorString = ''
        return response

    def send_vbs_command(self, message:str):
        """Sends the command as a vbs formatted comamnd

        Args:
            message (str): command string
        """
        self.send_command('vbs \'' + message + '\'')

    def send_vbs_query(self, message:str, query_delay:float=None) -> str:
        """Formats the query as a VBS string response

        Args:
            message (str): query string

        Returns:
            string: returns the reponse as a string
        """
        response = self.send_query('vbs? \'Return = ' + message + '\'', query_delay)
        return response

    def wait_for_opc(self) -> bool:
        """Waits for the prior operation to complete

        Returns:
            boolean: True on success, False on failure
        """
        return self._visa.send_query('*OPC?')

    def disconnect(self):
        """Disconnects the connection
        """
        if self._visa is not None:
            self._visa.close()
        self.connected = False

    def write_raw(self, message:bytes, terminator:bool=True) -> bool:
        """Write binary data to the instrument

        Args:
            message (bytes): data to send
            terminator (bool, optional): Terminate the transfer after command. Defaults to True.

        Returns:
            bool: success on success, False on failure
        """
        self._visa.write_raw(message)
        if terminator:
            self._visa.write_termination()

    def read_raw(self, max_bytes:int) -> bytes:
        """Reads a binary response from the instrument

        Args:
            max_bytes (int): Maximum number of bytes to read

        Returns:
            bytes: returns the data as bytes
        """
        return self.read_bytes(max_bytes, break_on_termchar=True)

    def get_panel(self) -> str:
        """Reads the instrument control state into a string

        Returns:
            str: panel file returned as a string, trailing terminator removed
        """
        self._visa.write('PNSU?')
        time.sleep(0.1)

        # read the first 11 bytes, this gives us the length of the transfer
        header = self._visa.read_bytes(11)
        if 'WARNING' in str(header):
            return ''

        # get number of bytes in the response
        bytes = int(header.decode('utf-8').replace('#9', ''))

        # read the amount of data
        panel = self._visa.read_bytes(bytes)
        # convert from a bytes array to a string and remove the trailing ffffffff
        return (panel.decode('utf-8').strip('ffffffff'))

    def set_panel(self, panel: str) -> bool:
        """Set the instrument control state using a panel string, typically from the method get_panel

        Args:
            panel (str): description

        Returns:
            bool: True on success, False on failure
        """
        written = self._visa.write_binary_values('PNSU ', (panel + 'ffffffff').encode('utf-8'), datatype = 'b')
        return written >= len(panel)


    def transfer_file_to_dso(self, remote_device: str, remote_filename: str, local_filename: str) -> bool:
        """Transfers a file from the PC to the remote device

        Args:
            remote_device (str): The device name on the instrument end, typically CARD, HDD
            remote_filename (str): The name and path of the destination file on the instrument
            local_filename (str): The name and path of the source file on the PC

        Returns:
            bool: True on success, False on failure
        """
        with open(local_filename, 'rb') as fp:
            filearray = fp.read()
        filearray += 'ffffffff'.encode('utf-8')
        header = 'TRFL DISK,{0},FILE,"{1}",'.format(remote_device, remote_filename)
        written = self._visa.write_binary_values(header, filearray, datatype='B')
        return written >= len(filearray)

    def transfer_file_to_pc(self, remote_device: str, remote_filename: str, local_filename: str) -> bool:
        """Transfers a file from the remote device to the PC

        Args:
            remote_device (str): The device name on the instrument end, typically CARD, HDD
            remote_filename (str): The name and path of the destination file on the instrument
            local_filename (str): The name and path of the source file on the PC

        Returns:
            bool: True on success, False on failure
        """
        header = 'TRFL? DISK,{0},FILE,"{1}",'.format(remote_device, remote_filename)
        self._visa.write(header)
        time.sleep(0.1)

        # read the first 11 bytes, this gives us the length of the transfer
        header = self._visa.read_bytes(11)
        if 'WARNING' in str(header):
            return ''

        # get number of bytes in the response
        bytes = int(header.decode('utf-8').replace('#9', ''))

        # read the amount of data
        filedata = self._visa.read_bytes(bytes)
        # convert from a bytes array to a string and remove the trailing ffffffff
        try:
            with open(local_filename, 'w+b') as fp:
                fp.write(filedata.strip(b'ffffffff'))
        except PermissionError:
            return False

        return True

    def store_hardcopy_to_file(self, format:str, aux_format:str, filename:str):
        """Transfers a hardcopy image from the isntrument and stores it on the PC

        Args:
            format (str): Hardcopy format: BMP, JPEG, PNG, TIFF
            aux_format (str): Auxilary format, typically empty ("")
            filename (str): destination filename

        Returns:
            type: True on success, False on failure
        """
        return True
