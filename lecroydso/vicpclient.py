import logging
import socket
import select
from struct import pack, unpack_from

import time

logger = logging.getLogger(__name__)

# VICP Headers:
#
#       Byte    Description
#       ------------------------------------------------
#        0      Operation
#        1      Version     1 = version 1
#        2      Sequence Number { 1..255 }, (was unused until June 2003)
#        3      Unused
#        4      Block size, LSB  (not including this header)
#        5      Block size
#        6      Block size
#        7      Block size, MSB
#
#   Operation bits:
#
#       Bit     Mnemonic    Purpose
#       -----------------------------------------------
#       D7      DATA        Data block (D0 indicates with/without EOI)
#       D6      REMOTE      Remote Mode
#       D5      LOCKOUT     Local Lockout (Lockout front panel)
#       D4      CLEAR       Device Clear (if sent with data, clear occurs before block is passed to parser)
#       D3      SRQ         SRQ (Device -> PC only)
#       D2      SERIALPOLL  Request a serial poll
#       D1      Reserved    Reserved for future expansion
#       D0      EOI         Block terminated in EOI


class VICPClient():
    DATA = 1 << 7
    REMOTE = 1 << 6
    LOCKOUT = 1 << 5
    CLEAR = 1 << 4
    SRQ = 1 << 3
    SERIALPOLL = 1 << 2
    Reserved = 1 << 1
    EOI = 1 << 0

    def __init__(self, ip: str, port: int):
        """VICP Client Class initialized with IP address and port

        Args:
            ip (str): IP Address to connect
            port (int): Port Index
        """
        self.ip = ip
        self.port = port
        self._timeout = 1.0
        self.sock = None
        self.seq_num = 1
        self.__connected = False

    def __del__(self):
        self.disconnect()
        self.__connected = False

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, timeout: float):
        """sets the timeout value used by the connection

        Args:
            timeout (float): timeout value in seconds

        """
        self._timeout = timeout

    def connect(self, timeout: float = 1.0) -> bool:
        """Connect to IP address and Port

        Args:
            timeout (float, optional): timeout value in seconds. Defaults to 10.0.

        Returns:
            [bool]: True on success, if not False
        """
        logger.debug("vicpclient.connect(timeout={0})".format(timeout))
        # command sending socket

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setblocking(0)

        starttime = time.process_time()
        while True:
            try:
                connect_result = self.sock.connect_ex((self.ip, self.port))    # noqa

                (rlist, wlist, elist) = select.select([], [self.sock], [], 0.2)

                if self.sock in wlist:
                    logger.debug("vicpclient.connect() connected")
                    self.__connected = True
                    return True
                elif time.process_time() - starttime > timeout:
                    logger.error("vicpclient.connect() timed out")
                    return False
            except OSError:
                self.sock = None
                return False

    def disconnect(self):
        """Disconnect the VICP connection
        """
        if self.sock is not None:
            self.sock.close()
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock = None

    def send_small_data_and_header(self, data: bytes) -> bool:
        """Send data and header

        Args:
            data (bytes): data as bytes

        Returns:
            bool: True on success, if not False
        """
        self.flush()
        d = data.encode()
        block_size = len(d)
        head = self.make_header(self.DATA | self.EOI, 1, block_size)
        logger.debug("sending data: {0}".format(data))
        (rlist, wlist, xlist) = select.select([], [self.sock], [], self._timeout)
        if len(wlist) == 0:
            logger.error("socket not ready, data not sent")
            return False
        else:
            sent = self.sock.send(head + d)
            if sent > 0:
                logger.debug("sent {0} bits of data: {1} done".format(sent, data[0:sent]))
            else:
                logger.error("error sending data")
                return False

        return True

    def make_header(self, operation: int, sequence_number: int, block_size: int) -> bytes:
        """Creates a series of bytes for the header for transfer

        Args:
            operation (int): Operation flags
            sequence_number (int): Sequence index
            block_size (int): size of the transfer

        Returns:
            bytes: packed bytes for header
        """
        version = 1
        dummy = 0
        return pack('>4Bi', operation, version, sequence_number, dummy, block_size)

    def receive(self) -> bytes:
        """Reads data from the VICP port

        Returns:
            bytes: return the data as bytes
        """
        number = 0
        data = b''
        logger.debug("receiving")
        while True:
            (operation, sequence_number, block_size) = self.receive_header()
            if sequence_number == -1:
                break
            logger.debug("operation: {0}".format(self.what_operation(operation)))
            logger.debug("sequence_number: {0}".format(sequence_number))
            logger.debug("block_size: {0}".format(block_size))
            current_data = 0
            if block_size > 0:
                current_data = self.receive_data(block_size)
                data += current_data
                logger.debug("data: {0}".format(current_data))

                if sequence_number == number + 1:
                    number = sequence_number
            if (operation & self.EOI) != 0:
                logger.debug("got EOI")
                break

        logger.debug("receiving done")
        logger.debug("data received")
        logger.debug(data)
        logger.debug("end of data")
        return data

    def receive_header(self) -> tuple:
        """Receives the header of the VICP communication

        Returns:
            tuple: returns (operation, sequence_numberm block_size)
        """
        # read the header
        (rlist, wlist, xlist) = select.select([self.sock], [], [], self._timeout)
        if len(rlist) == 0:
            logger.error("socket not ready to receive header")
            return (self.EOI, -1, 0)
        d = self.sock.recv(8)
        (operation, version, sequence_number, dummy, block_size) = unpack_from('>4Bi', d)
        logger.debug("header: {0:#08b} {1} {2} {3} {4}".format(operation, version, sequence_number, dummy, block_size))
        return (operation, sequence_number, block_size)

    def receive_data(self, block_size: int) -> bytes:
        """Receive data stream from the VICP port

        Args:
            block_size (int): Block size for the transfer

        Returns:
            bytes: data as a byte array
        """
        logger.debug("receiving data, blocksize {0}".format(block_size))
        (rlist, wlist, xlist) = select.select([self.sock], [], [], self._timeout)
        if len(rlist) == 0:
            logger.error("socket not ready to receive data")
            return (self.EOI, -1, 0)
        # read the data
        d = self.sock.recv(block_size)
#       data = unpack_from(str(block_size)+"b", d )
#       print("data", data)
        return d

    def device_clear(self):
        """Clears the Device buffers
        """
        head = self.make_header(self.CLEAR | self.EOI, 1, 1)
        self.sock.send(head + b'')
        self.receive()

    def flush(self):
        """Flushes the input and output buffers
        """
        (rlist, wlist, xlist) = select.select([self.sock], [], [], 0)
        socket_ready_to_read = len(rlist) > 0
        logger.debug("Flushing")
        while socket_ready_to_read:
            (operation, sequence_number, block_size) = self.receive_header()
            current_data = 0
            if block_size > 0:
                current_data = self.receive_data(block_size)        # noqa
            if (operation & self.EOI) != 0:
                break
        # if not socket_ready_to_read:
        #   print("### ERR: socket not ready")
        logger.debug("done")

    def what_operation(self, op: int) -> str:
        """Returns the operation as a string

        Args:
            op (int): operation

        Returns:
            str: string equivalent of the operation
        """
        out = ""
        if (op & self.DATA):
            out += "|DATA"
        if (op & self.REMOTE):
            out += "|REMOTE"
        if (op & self.LOCKOUT):
            out += "|LOCKOUT"
        if (op & self.CLEAR):
            out += "|CLEAR"
        if (op & self.SRQ):
            out += "|SRQ"
        if (op & self.SERIALPOLL):
            out += "|Reserved"
        if (op & self.Reserved):
            out += "|Reserved"
        if (op & self.EOI):
            out += "|EOI"
        return out
