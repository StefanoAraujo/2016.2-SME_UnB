from __future__ import unicode_literals
from abc import ABCMeta, abstractmethod
import socket
import struct
import sys


class SerialProtocol(object):
    """
    Base class for serial protocols.

    Attributes:
        transductor (Transductor): The transductor which will hold communication.
    """
    __metaclass__ = ABCMeta

    def __init__(self, transductor):
        self.transductor = transductor

    @abstractmethod
    def create_messages(self):
        """
        Abstract method responsible to create messages following the header patterns
        of the serial protocol used.
        """
        pass

    @abstractmethod
    def get_int_value_from_response(self, message_received_data):
        """
        Abstract method responsible for read an integer value of a message sent by a transductor.

        Args:
            message_received_data (str): The data from received message.
        """
        pass

    @abstractmethod
    def get_float_value_from_response(self, message_received_data):
        """
        Abstract method responsible for read an float value of a message sent by a transductor.

        Args:
            message_received_data (str): The data from received message.
        """
        pass


class RegisterAddressException(Exception):
    """
    Exception to signal that a register address from transductor model
    is in a wrong format.

    Attributes:
        message (str): The exception message.
    """
    def __init__(self, message):
        super(RegisterAddressException, self).__init__(message)
        self.message = message


class ModbusRTU(SerialProtocol):
    """
    Class responsible to represent the communication protocol Modbus in RTU mode.

    The RTU format follows the commands/data with a cyclic redundancy check checksum as an error
    check mechanism to ensure the reliability of data

    This protocol will be encapsulated in the data field of an transport protocol header.

    `Modbus reference guide <http://modbus.org/docs/PI_MBUS_300.pdf>`_
    """
    def __init__(self, transductor):
        super(ModbusRTU, self).__init__(transductor)

    def create_messages(self):
        """
        This method creates all messages based on transductor model register address
        that will be sent to a transductor seeking out their respective values.

        Returns:
            list: The list with all messages.

        Raises:
            RegisterAddressException: raised if the register address from transductor model
            is in a wrong format.
        """
        registers = self.transductor.model.register_addresses

        messages_to_send = []

        int_addr = 0
        float_addr = 1

        address_value = 0
        address_type = 1

        for register in registers:
            if register[address_type] == int_addr:
                packaged_message = struct.pack("2B", 0x01, 0x03) + struct.pack(">2H", register[address_value], 1)
            elif register[address_type] == float_addr:
                packaged_message = struct.pack("2B", 0x01, 0x03) + struct.pack(">2H", register[address_value], 2)
            else:
                raise RegisterAddressException("Wrong register address type.")

            crc = struct.pack("<H", self._computate_crc(packaged_message))

            packaged_message = packaged_message + crc

            messages_to_send.append(packaged_message)

        return messages_to_send

    def get_int_value_from_response(self, message_received_data):
        """
        `Source Code <http://www.ccontrolsys.com/w/How_to_read_WattNode_Float_Registers_in_the_Python_Language>`_

        Args:
            message_received_data (str): The data from received message.

        Returns:
            int: The value from response.
        """
        n_bytes = struct.unpack("1B", message_received_data[2])[0]

        msg = bytearray(message_received_data[3:-2])

        for i in range(0, n_bytes, 2):
            if sys.byteorder == "little":
                msb = msg[i]
                msg[i] = msg[i + 1]
                msg[i + 1] = msb

        value = struct.unpack("1h", msg)[0]
        return value

    def get_float_value_from_response(self, message_received_data):
        """
        `Source Code <http://www.ccontrolsys.com/w/How_to_read_WattNode_Float_Registers_in_the_Python_Language>`_

        Args:
            message_received_data (str): The data from received message.

        Returns:
            float: The value from response.
        """
        n_bytes = struct.unpack("1B", message_received_data[2])[0]

        msg = bytearray(message_received_data[3:-2])

        for i in range(0, n_bytes, 4):
            if sys.byteorder == "little":
                msb = msg[i]
                msg[i] = msg[i + 1]
                msg[i + 1] = msb

                msb = msg[i + 2]
                msg[i + 2] = msg[i + 3]
                msg[i + 3] = msb
            else:
                msb = msg[i]
                lsb = msg[i + 1]
                msg[i] = msg[i + 2]
                msg[i + 1] = msg[i + 3]
                msg[i + 2] = msb
                msg[i + 3] = lsb

        value = struct.unpack("1f", msg)[0]
        return value

    def _computate_crc(self, packaged_message):
        """
        Method responsible to computate the crc from a packaged message.

        A cyclic redundancy check (CRC) is an error-detecting code commonly
        used in digital networks and storage devices to detect accidental changes to raw data.

        `Modbus CRC documentation: <http://www.modbustools.com/modbus.html#crc>`_

        `Code Source <http://pythonhosted.org/pyModbusTCP/_modules/pyModbusTCP/client.html>`_

        Args:
            packaged_message (str): The packaged message ready to be sent/received.

        Returns:
            int: The CRC generated.
        """
        crc = 0xFFFF

        for index, item in enumerate(bytearray(packaged_message)):
            next_byte = item
            crc ^= next_byte
            for i in range(8):
                lsb = crc & 1
                crc >>= 1
                if lsb:
                    crc ^= 0xA001

        return crc

    def _check_crc(self, packaged_message):
        """
        Method responsible to verify if a CRC is valid.

        Args:
            packaged_message (str): The packaged message ready to be sent/received.

        Returns:
            bool: True if CRC is valid, False otherwise.
        """
        return (self._computate_crc(packaged_message) == 0)

class BrokenTransductorException(Exception):
    """
    Exception to signal that a transductor is broken when trying to send messages
    via Transport Protocol.

    Attributes:
        message (str): The exception message.
    """
    def __init__(self, message):
        super(BrokenTransductorException, self).__init__(message)
        self.message = message

class TransportProtocol(object):
    """
    Base class for transport protocols.

    Attributes:
        serial_protocol (SerialProtocol): The serial protocol used in communication.
        transductor (Transductor): The transductor which will hold communication.
        timeout (float): The serial port used by the transductor.
        port (int): The port used to communication.
        socket (socket._socketobject): The socket used in communication.
    """
    __metaclass__ = ABCMeta

    def __init__(self, serial_protocol, timeout, port):
        self.serial_protocol = serial_protocol
        self.transductor = serial_protocol.transductor
        self.timeout = timeout
        self.port = port
        self.socket = None

    @abstractmethod
    def create_socket(self):
        """
        Abstract method responsible to create the respective transport socket.
        """
        pass


class UdpProtocol(TransportProtocol):
    """
    Class responsible to represent a UDP protocol and handle all the communication.

    Attributes:
        receive_attemps (int): Total attempts to receive a message via socket UDP.
        max_receive_attempts (int): Maximum number of attemps to receive message via socket UDP.
    """
    def __init__(self, serial_protocol, timeout=10.0, port=1001):
        super(UdpProtocol, self).__init__(serial_protocol, timeout, port)
        self.receive_attempts = 0
        self.max_receive_attempts = 3

    def create_socket(self):
        """
        Method responsible to create and set timeout of a UDP socket.
        """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(self.timeout)

    def start_communication(self):
        """
        Method reponsible to start UDP socket and receive messages from it.

        Returns:
            list: The messages received from transductor response.

        Raises:
            BrokenTransductorException
        """
        if self.socket is None:
            self.create_socket()

        messages_to_send = self.serial_protocol.create_messages()

        try:
            messages_received = self.manage_received_messages(messages_to_send)
        except BrokenTransductorException:
            raise

        return messages_received

    def manage_received_messages(self, messages_to_send):
        """
        Method responsible to try receive message from socket based on maximum receive attempts.

        Everytime a message is not received from the socket the total of received attemps is increased.

        Args:
            messages_to_send (list): The packaged messages ready to be sent via socket.

        Returns: The messages received if successful, None otherwise.

        Raises:
            BrokenTransductorException: raised if the transductor can't send messages via
            UDP socket.
        """
        self.reset_receive_attempts()
        received_messages = []

        while not received_messages and self.receive_attempts < self.max_receive_attempts:
            received_messages = self.handle_messages_via_socket(messages_to_send)

            if not received_messages:
                self.receive_attempts += 1

        if self.receive_attempts == self.max_receive_attempts and not self.transductor.broken:
            raise BrokenTransductorException("Transductor is broken!")

        return received_messages

    def reset_receive_attempts(self):
        """
        Method responsible to reset the number of receive attempts.
        """
        self.receive_attempts = 0

    def handle_messages_via_socket(self, messages_to_send):
        """
        Method responsible to handle send/receive messages via socket UDP.

        Args:
            messages_to_send (list): The requests to be sent to the transductor via socket.

        Returns:
            The messages received if successful, None otherwise.
        """
        messages = []

        for i, message in enumerate(messages_to_send):
            try:
                self.socket.sendto(message, (self.transductor.ip_address, self.port))
                message_received = self.socket.recvfrom(256)
            except socket.timeout:
                return None
            except socket.error:
                # TODO: add exception
                pass

            messages.append(message_received[0])

        return messages
