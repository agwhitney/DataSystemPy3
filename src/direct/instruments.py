"""
https://stackoverflow.com/questions/4715340/python-twisted-receive-command-from-tcp-write-to-serial-device-return-response
I'm making a change - the serial client will have a reference to the TCP network, so it has access to the client list and log
This is in place of having the client list as a global. Fear is that the follow-up to the solution was used in py2, meaning this doesn't work.

I've removed the two Connection classes. It seems the plan was to introduce compatability for different types of connections,
but the final version only implements Serial. Literally all it does is load instr_config['serial_connection'] to a class.
"""
import json
import logging  # type hinting only
import struct
import time

from twisted.internet import protocol, reactor, task
from twisted.protocols import basic

from fpga import FPGA


class TCPInstrument(protocol.Protocol):
    def __init__(self):
        print("Creating TCPInstrument instance")

    
    def connectionMade(self):
        self.factory.log.info(
            f"{self.factory.name} - New TCP client received from {self.transport.getPeer()} - Instance {self}"
        )
        self.transport.write(
            f"Welcome to {self.factory.name} you are at {self.transport.getPeer()}\n".encode()
        )
        self.factory.clients.append(self)

    
    def connectionLost(self, reason):
        self.factory.log.info(
            f"{self.factory.name} - Connection lost from {self.transport.getPeer()} - Reason: {reason}"
        )
        self.factory.log.info(
            f"{self.factory.name} - Removing TCP client: {self} at {self.transport.getPeer()}"
        )
        self.factory.clients.remove(self)


    def dataReceived(self, data):
        self.factory.log.info(
            f"{self.factory.name} - Command received from {self.transport.getPeer()} - Command {data}"
        )
        if data == 'STOP':
            reactor.stop()

    # AGW Put this in the factory as notifyAll. See StackOverflow
    # def notifyClient(self, data):
    #     self.transport.write(data)


class TCPInstrumentFactory(protocol.Factory):
    protocol = TCPInstrument
    
    def __init__(self, config_data: dict, log: logging.Logger):
        self.clients = []
        self.name = config_data['name']
        self.log = log
        self.config = config_data

    
    def notifyAll(self, data: bytes):
        for client in self.clients:
            client.transport.write(data)




class SerialTransport(basic.LineReceiver, basic.Int32StringReceiver):
    iteration = 0  # AGW not sure if this needs to be persistent
    
    def __init__(self, network: TCPInstrumentFactory):
        self.network = network


    def connectionMade(self):
        self.network.log.info(
            f"{self.network.name} - Serial connection made."
        )

    
    def connectionLost(self, reason):
        self.network.log.error(
            f"{self.network.name} - Serial connection lost - Reason: {reason}"
        )


    def connectionFailed(self):
        self.network.log.error(
            f"{self.network.name} - Connection unsuccessful: {self}. {self.network.name} is not active."
        )
        reactor.stop()


    def write_down(self, data):
        """
        Writes via transport to clients in network.
        """
        self.network.notifyAll(data)


class SerialTransportRadiometer(SerialTransport):
    def __init__(self, network):
        super().__init__(network)
        self.letterid = self.network.config['letterid']  # unused?
        self.byte_order = self.network.config['byte_order']  # unused?

        fpga = FPGA(self.network.config, self.network.log)
        fpga.estimated_data_throughput()
        fpga.configure()
        fpga.hardware_reset()
        fpga.disconnect_tcp()


    def dataReceived(self, data):
        data = f"PAC{self.network.config['letterid']}:{self.iteration}TIME:{time.time()}DATA:{data}:ENDS\n"
        self.iteration += 1
        self.write_down(data.encode())


class SerialTransportThermistors(SerialTransport):
    def __init__(self, network):
        super().__init__(network)
        self.delimiter        : bytes = self.network.config['characteristics']['delimiter'].encode()
        self.polling_interval : float = self.network.config['characteristics']['polling_interval']
        self.letterid         : str = self.network.config['letterid']
        self.byte_order       : str = self.network.config['byte_order']
        self.addresses        : list = self.network.config['characteristics']['addresses']

        self.visited_adcs = 0
        self.adc_count = len(self.addresses)
        print("Number of ADCs = ", self.adc_count)


    def connectionMade(self):
        super().connectionMade()
        print("Starting communcation with ADCs")
        command = struct.pack('cccB', '#', '0', str(self.addresses[0]), 13)
        self.sendLine(command)
        self.start_acquisition()

    
    def start_acquisition(self):        
        self.lc = task.LoopingCall(self.get_data)
        self.lc.start(self.polling_interval)

    
    def get_data(self):
        self.visited_adcs = 0
        command = struct.pack('cccB', '#', '0', str(self.addresses[self.visited_adcs]), 13)
        self.sendLine(command)
        self.iteration += 1
        self.data2send = f"PAC{self.letterid}:{self.iteration}TIME:{time.time()}DATA:"


    def lineReceived(self, line):
        self.visited_adcs += 1
        if self.visited_adcs < self.adc_count:
            self.data2send += line[:-1]
            # TODO a small sleep command for IO buffer
            command = struct.pack('cccB', '#', '0', str(self.addresses[self.visited_adcs]), 13)
            self.sendLine(command)
        elif self.visited_adcs == self.adc_count:
            self.data2send += line[:-1] + 'ENDS\n'
            self.write_down(self.data2send.encode())


class SerialTransportGPSIMU(SerialTransport):
    def __init__(self, network):
        super().__init__(network)
        self.letterid    : str = self.network.config['letterid']
        self.byte_order  : str = self.network.config['byte_order']
        self.delimiter   : bytes = self.network.config['characteristics']['delimiter'].encode()
        self.update_freq : int = self.network.config['characteristics']['update_frequency']


    @staticmethod
    def crc16(buffer: bytes):
        """
        Calculates Cyclic Redundancy Check (CRC) value for a given command of size `buffer`.
        """
        poly = 0x8408
        crc = 0
        i = 0
        while i < len(buffer):
            ch = buffer[i]  # py2 uses ord because socket.recv returns str not bytes
            uc = 0
            while uc < 8:
                if (crc & 1)^(ch & 1):
                    crc = (crc >> 1)^poly
                else:
                    crc >>= 1
                ch >>= 1
                uc += 1
            i += 1
        return crc


    def connectionMade(self):
        """
        Sends a configuration command to the GPS.
        See the "IG Devices Serial Protocol Specifications.pdf" manual for detail on the serial interface with the GPS unit.
        This configuration sets continuous mode at the given update frequency (pgs. 7, 26)
        """
        super().connectionMade()

        # Header - Sync byte and Start of Tx byte (see manual pg. 7)
        header = struct.pack('>BB', 255, 2)

        # Command - SET_CONTINUOUS_MODE (manual pg. 26). Relevant bits are final two.
        # Penultimate byte sets mode (0 - cont_trigger disable, 1 - continuous enable, 2 - triggered enable)
        # "Final byte sets rate to Main loop filter frequency divided by continuous divider." (f = 60 / last_byte)
        # AGW 60 / (60 / update_freq) = update_freq?
        command = struct.pack('>6B', 83, 0, 3, 0, 1, int(60/self.update_freq))
        
        # Footer - CRC bytes (MSB, LSB) and end of Tx byte. CRC is calculated based on the command.
        crc = self.crc16(command)  # crc = 5439; confirmed same in Python 2 with online evaluator
        crc_msb = int((crc - crc % 256) / 256)  # msb = 21
        crc_lsb = crc % 256  # lsb = 63
        footer = struct.pack('>3B', crc_msb, crc_lsb, 3)

        # Send frame to device
        frame = header + command + footer
        self.sendLine(frame)

        # self.sendLine(header)
        # self.sendLine(command)
        # self.sendLine(footer)


    def dataReceived(self, data: bytes):
        self.iteration += 1  # AGW This is called a LOT so it seems silly to count it
        line = f"PAC{self.letterid}:{self.iteration}TIME:{time.time()}DATA:".encode() + data + ":ENDS\n".encode()
        self.write_down(line)
    



class Instrument():
    """
    Holds details to create an instrument server listening on a TCP port via a serial connection.
    Protocols are above, and connection details are provided in the passed config (forked from the server config).
    This is applied in genericserver.py.
    """
    def __init__(self, config_filename: str, log: logging.Logger):
        # Load in instrument config, which was passed as config[instrument].values()
        with open(config_filename, 'r') as fp:
            config = json.load(fp)
        log.info(config)

        # AGW py2 does a bunch of subsetting of the config file, but I say just keep it whole.
        # what was config['instrument'] is now just config.values() (but also includes serial and tcp data)
        self.connection = config['serial_connection']
        self.tcp_port = config['tcp_connection']['port']

        # Define the TCP connection
        self.factory = TCPInstrumentFactory(config, log)

        # Define the serial connection
        self.serial_client = None
        match config['name']:
            case 'Radiometer':
                self.serial_client = SerialTransportRadiometer(network=self.factory)
            case 'Thermistors':
                self.serial_client = SerialTransportThermistors(network=self.factory)
            case 'GPS-IMU':
                self.serial_client = SerialTransportGPSIMU(network=self.factory)