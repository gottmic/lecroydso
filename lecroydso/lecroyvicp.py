# -----------------------------------------------------------------------------
# Summary:		Implementation of ActiveDSO class
# Authors:		Ashok Bruno
# Started:		2/8/2021
# Copyright 2021-2024 Teledyne LeCroy Corporation. All Rights Reserved.
# -----------------------------------------------------------------------------
#


from lecroydso import DSOConnection
from lecroydso.errors import DSOConnectionError, DSOIOError
from lecroydso.vicpclient import VICPClient
import time

maxLen = 1e6


class LeCroyVICP(DSOConnection):
    def __init__(self, connection_string: str, query_response_max_length: int = maxLen):
        """Makes a connection to the instrument using ActiveDSO

        Args:
            connection_string (string): string in a specified format
            query_response_max_length (integer, optional): Default max bytes for query responses, Defaults to maxLen.
        """
        self.connection_string = None
        self.vicp = VICPClient(connection_string, 1861)

        if self.vicp.connect(1.0):
            self.vicp.device_clear()
            self._timeout = 1.0
            self.connected = True
            self.connection_string = connection_string
            self._query_response_max_length = query_response_max_length
            self._insert_wait_opc = False
            self._error_flag = False
            self._error_string = ''
        else:
            self.connected = False
            raise DSOConnectionError('LeCroyVICP connection failed, {}'.format(connection_string))
            return

    def __del__(self):
        self.disconnect()

    @property
    def error_string(self):
        """Contains the error message when the error_flag is True"""
        return self._error_string

    @property
    def error_flag(self):
        """Set to True when an error occurs"""
        return self._error_flag

    @property
    def query_response_max_length(self):
        """Maximum length for a response in a query.
        Can be set to an integer value
        """
        return self._query_response_max_length

    @query_response_max_length.setter
    def query_response_max_length(self, val: int):
        self._query_respose_max_length = val

    @property
    def timeout(self) -> float:
        """timeout value in seconds in float"""
        return self._timeout

    @timeout.setter
    def timeout(self, timeout: float):
        if timeout < 0.0:
            raise ValueError("Timeout can't be negative")
        self._timeout = timeout

    @property
    def insert_wait_opc(self):
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

    def reconnect(self):
        """Reconnects to the instrument with the existing credentials
        """
        if self.vicp.connect(self._timeout):
            self.connected = True
        else:
            self.connected = False
            raise DSOConnectionError('LeCroyVICP connection failed')
            return

    def write(self, message: str, terminator: bool = True) -> bool:
        """sends a strings to the DSO with or without a terminating character

        Args:
            message (str): description
            terminator (bool, optional): description. Defaults to True.

        Returns:
            bool: True on success, False on failure
        """
        success = self.vicp.send_small_data_and_header(message)
        if self._insert_wait_opc:
            self.wait_opc()
        return success

    def read(self, max_bytes: int) -> str:
        """reads string from the instrument

        Args:
            max_bytes (int): maximum amount of characters to read. If more characters are available it will remain unread

        Returns:
            str: description
        """
        return (self.vicp.receive()).decode('utf-8').strip(' \t\r\n')

    def query(self, message: str, query_delay: float = None) -> str:
        """Send the query and returns the response

        Args:
            message (string): command to send
            query_delay (float, optional): description. Defaults to None.

        Returns:
            string: description
        """
        if self.write(message, True):
            if query_delay is not None:
                time.sleep(query_delay)
            response = self.read(self._query_response_max_length)
            if self._insert_wait_opc:
                self.wait_opc()
        else:
            raise DSOIOError('Write to device failed')

        return response

    def write_vbs(self, message: str):
        """sends the command as a vbs formatted comamnd

        Args:
            message (string): command string
        """
        self.write('vbs \'' + message + '\'', True)
        if self._insert_wait_opc:
            self.wait_opc()

    def query_vbs(self, message: str, query_delay: float = None) -> str:
        """formats the query as a VBS string response

        Args:
            message (string): query string

        Returns:
            string:
        """
        return self.query('vbs? \'Return = ' + message + '\'')

    def wait_opc(self) -> bool:
        """Waits for the prior operation to complete

        Returns:
            bool: True on success, False on failure
        """
        opc = self.query('*OPC?')
        return opc == 1

    def write_raw(self, message: bytes, terminator: bool = True) -> bool:
        """write binary data to the instrument

        Args:
            message (bytes): data to send
            bEOI (bool, optional): Terminate the transfer after command. Defaults to True.

        Returns:
            bool: success on success, False on failure
        """
        return self.vicp.WriteBinary(message, len(message), terminator)

    def read_raw(self, max_bytes: int) -> memoryview:
        """reads a binary response from the instrument

        Args:
            max_bytes (int): Maximum number of bytes to read

        Returns:
            memoryview: returns the data as buffer
        """
        return self.vicp.ReadBinary(max_bytes if max_bytes is not None else self._query_response_max_length)

    def disconnect(self):
        """Disconnects the ActiveDSO connection
        """
        if self.vicp:
            self.vicp.disconnect()
        self.connected = False

    def get_panel(self) -> str:
        """reads the instrument control state into a string

        Returns:
            str: panel file returned as a string, trailing terminator removed
        """
        pass

    def set_panel(self, panel: str) -> bool:
        """Set the instrument control state using a panel string, typically from the method get_panel

        Args:
            panel (str): description

        Returns:
            bool: True on success, False on failure
        """
        pass

    def transfer_file_to_dso(self, remote_device: str, remote_filename: str, local_filename: str) -> bool:
        """Transfers a file from the PC to the remote device

        Args:
            remote_device (str): The device name on the instrument end, typically CARD, HDD
            remote_filename (str): The name and path of the destination file on the instrument
            local_filename (str): The name and path of the source file on the PC

        Returns:
            bool: True on success, False on failure
        """
        pass

    def transfer_file_to_pc(self, remote_device: str, remote_filename: str, local_filename: str) -> bool:
        """Transfers a file from the remote device to the PC

        Args:
            remote_device (str): The device name on the instrument end, typically CARD, HDD
            remote_filename (str): The name and path of the destination file on the instrument
            local_filename (str): The name and path of the source file on the PC

        Returns:
            bool: True on success, False on failure
        """
        pass

    def store_hardcopy_to_file(self, format: str, aux_format: str, filename: str):
        """Transfers a hardcopy image from the isntrument and stores it on the PC

        Args:
            format (str): Hardcopy format: BMP, JPEG, PNG, TIFF
            aux_format (str): Auxilary format, typically empty ("")
            filename (str): destination filename

        Returns:
            type: True on success, False on failure
        """
        pass
