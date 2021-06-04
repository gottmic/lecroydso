#-----------------------------------------------------------------------------
# Summary:		Implementation of ActiveDSO class
# Authors:		Ashok Bruno
# Started:		2/8/2021
# Copyright 2021-2024 Teledyne LeCroy Corporation. All Rights Reserved.
#-----------------------------------------------------------------------------
#


from lecroydso import DSOConnection
from lecroydso.errors import DSOConnectionError, DSOIOError
import time

maxLen = 1e6

class ActiveDSO(DSOConnection):
    def __init__(self, connection_string:str, query_response_max_length:int=maxLen):
        """Makes a connection to the instrument using ActiveDSO

        Args:
            connection_string (string): string in a specified format
            query_response_max_length (integer, optional): Default max bytes for query responses, Defaults to maxLen.
        """
        self.connection_string = None
        self.aDSO = None
        try:
            from win32com.client import DispatchEx
            self.aDSO = DispatchEx('LeCroy.ActiveDSOCtrl.1')

        except:
            self.connected = False
            raise DSOConnectionError('ActiveDSO not installed or registered')
            return

        if self.aDSO.MakeConnection(connection_string):
            if 'IP:' in connection_string or 'TCPIP:' in connection_string or 'VXI11:' in connection_string:
                self._timeout = 1.0
                self.aDSO.SetTimeout(1.0)  # set 1 second as timeout for these types of connections
            self.connected = True
            self.connection_string = connection_string
            self._query_response_max_length = query_response_max_length
            self._insert_wait_opc = False
        else:
            self.connected = False
            raise DSOConnectionError('ActiveDSO connection failed'.format(connection_string))
            return

    def __del__(self):
        self.disconnect()
    
    @property
    def error_string(self):
        """Contains the error message when the error_flag is True"""
        self._error_string = self.aDSO.errorString
        return self._error_string

    @property
    def error_flag(self):
        """Set to True when an error occurs"""
        self._error_flag = self.aDSO.errorFlag
        return self._error_flag
   
    @property 
    def timeout(self) -> float:
        """timeout value in seconds in float"""
        return self._timeout
    
    @property
    def query_response_max_length(self):
        """Maximum length for a response in a query.
        Can be set to an integer value
        """
        return self._query_response_max_length

    @query_response_max_length.setter
    def query_response_max_length(self, val:int):
        self._query_respose_max_length = val

    @timeout.setter
    def timeout(self, timeout:float):
        if timeout < 0.0:
            raise ValueError("Timeout can't be negative")
        self._timeout = timeout
        self.aDSO.SetTimeout(timeout)

    @property
    def insert_wait_opc(self):
        return self._insert_wait_opc

    @insert_wait_opc.setter
    def insert_wait_opc(self, val:bool):
        """Inserts a OPC command for reads and writes.
        This ensures that the command will execute sequentially.
        The default value for a connection is false.
        NOTE: There is a performance impact by setting this flag

        Args:
            val (bool): True to insert wait_opc, False otherwise. 
        """
        self._insert_wait_opc = val

    def reconnect(self):
        """Reconnects to the instrument with the existing credentials
        """
        if self.aDSO.MakeConnection(self.connection_string):
            self.connected = True
        else:
            self.connected = False
            raise DSOConnectionError('ActiveDSO connection failed')
            return
            
    def write(self, message:str, terminator:bool=True):
        """sends a strings to the DSO with or without a terminating character

        Args:
            message (str): description
            terminator (bool, optional): description. Defaults to True.
        """
        self.aDSO.WriteString(message, terminator)
        if self._insert_wait_opc:
            self.wait_opc()

    def read(self, max_bytes:int) -> str:
        """reads string from the instrument

        Args:
            max_bytes (int): maximum amount of characters to read. If more characters are available it will remain unread

        Returns:
            str: description
        """
        return self.aDSO.ReadString(max_bytes)

    def query(self, message:str, query_delay:float=None) -> str:
        """Send the query and returns the response

        Args:
            message (string): command to send
            query_delay (float, optional): description. Defaults to None.

        Returns:
            string: description
        """
        if self.aDSO.WriteString(message, True):
            if query_delay is not None:
                time.sleep(query_delay)
            response = self.aDSO.ReadString(self._query_response_max_length)
            if self._insert_wait_opc:
                self.wait_opc()
        else:
            raise DSOIOError('Write to device failed')

        return response

    def write_vbs(self, message:str):
        """sends the command as a vbs formatted comamnd

        Args:
            message (string): command string
        """
        self.aDSO.WriteString('vbs \'' + message + '\'', True)
        if self._insert_wait_opc:
            self.wait_opc()

    def query_vbs(self, message:str, query_delay:float=None) -> str:
        """formats the query as a VBS string response

        Args:
            message (string): query string

        Returns:
            string: 
        """
        if self.aDSO.WriteString('vbs? \'Return = ' + message + '\'', True):
            if query_delay is not None:
                time.sleep(query_delay)
            response = self.aDSO.ReadString(self._query_response_max_length)
            if self._insert_wait_opc:
                self.wait_opc()
        else:
            raise DSOIOError('Write to device failed')
        return response

    def wait_opc(self) -> bool:
        """Waits for the prior operation to complete

        Returns:
            bool: True on success, False on failure
        """
        return self.aDSO.WaitForOPC()

    def write_raw(self, message:bytes, terminator:bool=True) -> bool:
        """write binary data to the instrument

        Args:
            message (bytes): data to send
            bEOI (bool, optional): Terminate the transfer after command. Defaults to True.

        Returns:
            bool: success on success, False on failure
        """
        return self.aDSO.WriteBinary(message, len(message), terminator)

    def read_raw(self, max_bytes:int) -> memoryview:
        """reads a binary response from the instrument

        Args:
            max_bytes (int): Maximum number of bytes to read

        Returns:
            memoryview: returns the data as buffer
        """
        return self.aDSO.ReadBinary(max_bytes if max_bytes is not None else self._query_response_max_length)

    def disconnect(self):
        """Disconnects the ActiveDSO connection
        """
        if self.aDSO:
            self.aDSO.Disconnect()
        self.connected = False

    def get_panel(self) -> str:
        """reads the instrument control state into a string

        Returns:
            str: panel file returned as a string, trailing terminator removed
        """
        return self.aDSO.GetPanel().strip('ffffffff')   # remove the trailing ffffffff

    def set_panel(self, panel: str) -> bool:
        """Set the instrument control state using a panel string, typically from the method get_panel

        Args:
            panel (str): description

        Returns:
            bool: True on success, False on failure
        """
        return self.aDSO.SetPanel(panel + 'ffffffff')       # add the trailing ffffffff

    def transfer_file_to_dso(self, remote_device: str, remote_filename: str, local_filename: str) -> bool:
        """Transfers a file from the PC to the remote device

        Args:
            remote_device (str): The device name on the instrument end, typically CARD, HDD
            remote_filename (str): The name and path of the destination file on the instrument
            local_filename (str): The name and path of the source file on the PC

        Returns:
            bool: True on success, False on failure
        """
        response = self.aDSO.TransferFileToDso(remote_device, remote_filename, local_filename)
        return response >= 0.0

    def transfer_file_to_pc(self, remote_device: str, remote_filename: str, local_filename: str) -> bool:
        """Transfers a file from the remote device to the PC

        Args:
            remote_device (str): The device name on the instrument end, typically CARD, HDD
            remote_filename (str): The name and path of the destination file on the instrument
            local_filename (str): The name and path of the source file on the PC

        Returns:
            bool: True on success, False on failure
        """
        response = self.aDSO.TransferFileToPC(remote_device, remote_filename, local_filename)
        return response >= 0.0

    def store_hardcopy_to_file(self, format:str, aux_format:str, filename:str):
        """Transfers a hardcopy image from the isntrument and stores it on the PC

        Args:
            format (str): Hardcopy format: BMP, JPEG, PNG, TIFF
            aux_format (str): Auxilary format, typically empty ("")
            filename (str): destination filename

        Returns:
            type: True on success, False on failure
        """
        return self.aDSO.StoreHardcopyToFile(format, aux_format, filename)