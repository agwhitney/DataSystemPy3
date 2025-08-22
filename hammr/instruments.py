"""
https://stackoverflow.com/questions/4715340/python-twisted-receive-command-from-tcp-write-to-serial-device-return-response
I'm making a change - the serial client will have a reference to the TCP network, so it has access to the client list and log
This is in place of having the client list as a global. Fear is that the follow-up to the solution was used in py2, meaning this doesn't work.

I've removed the two Connection classes. It seems the plan was to introduce compatability for different types of connections,
but the final version only implements Serial. Literally all it does is load instr_config['serial_connection'] to a class.
"""
import logging  # type hinting only
import struct
import time

from twisted.internet import protocol, reactor, task
from twisted.protocols import basic

from fpga import FPGA
from filepaths import SERIAL_PORT


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
    
    def __init__(self, config: dict, log: logging.Logger):
        self.clients = []
        self.name = config['name']
        self.log = log
        self.config = config

    
    def notifyAll(self, data: bytes):
        for client in self.clients:
            client.transport.write(data)




class SerialTransport(basic.LineReceiver):
    iteration = 0
    
    def __init__(self, network: TCPInstrumentFactory):
        self.network = network

        # Common configuration settings        
        self.letterid   : str = self.network.config['letterid']
        self.byte_order : str = self.network.config['byte_order']
        self.delimiter = b'\r\n'  # Default


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

        fpga = FPGA(self.network.config, self.network.log)
        fpga.estimated_data_throughput()
        fpga.configure()
        fpga.hardware_reset()
        fpga.disconnect_tcp()


    def dataReceived(self, data: bytes):
        dataline = f"PAC{self.letterid}:{self.iteration}TIME:{time.time()}DATA:".encode + data + ":ENDS\n".encode()
        self.iteration += 1
        self.write_down(dataline)


class SerialTransportThermistors(SerialTransport):
    def __init__(self, network):
        super().__init__(network)
        self.delimiter        : bytes = self.network.config['characteristics']['delimiter'].encode()
        self.polling_interval : float = self.network.config['characteristics']['polling_interval']
        self.addresses        : list[str] = self.network.config['characteristics']['addresses']

        self.visited_adcs = 0
        self.total_adc = len(self.addresses)
        self.network.log.info(f"Number of ADCs = {self.total_adc}")


    @staticmethod
    def poll_command(address: str):
        """
        Polling command to thermistor to read analog input.
        I assume it is from all channels, and reads in Celsius per the manual?
        """
        return struct.pack('>3sB', address.encode(), 13)  # chr(13) == '\r' 


    def connectionMade(self):
        super().connectionMade()
        self.network.log.info("Starting communcation with ADCs")
        cmd = self.poll_command(self.addresses[0])
        self.sendLine(cmd)
        self.start_acquisition()

    
    def start_acquisition(self):
        # Calls self.get_data() at the polling interval (seconds)
        self.lc = task.LoopingCall(self.get_data)
        self.lc.start(self.polling_interval)

    
    def get_data(self):
        self.visited_adcs = 0
        cmd = self.poll_command(self.addresses[self.visited_adcs])
        self.sendLine(cmd)
        self.iteration += 1
        self.dataline = f"PAC{self.letterid}:{self.iteration}TIME:{time.time()}DATA:".encode()


    def lineReceived(self, line: bytes):
        self.visited_adcs += 1
        if self.visited_adcs < self.total_adc:
            self.dataline += line[:-1]
            # "Next command gives some extratime to the SLAVE to release the comm. bus, further reducing this value could end with comm. problems... up to you!"
            time.sleep(0.2)
            cmd = self.poll_command(self.addresses[self.visited_adcs])
            self.sendLine(cmd)

        elif self.visited_adcs == self.total_adc:
            self.dataline += line[:-1] + 'ENDS\n'.encode()
            self.write_down(self.dataline)


class SerialTransportGPSIMU(SerialTransport):
    """
    Serial connection details for the IG-500N unit are contained in the "IG Devices Serial Protocol Specifications" manual by SBG.
    This has been saved as a .pdf. Page numbers refer to this manual.
    """
    def __init__(self, network):
        super().__init__(network)
        # Delimiter is set as the wrapper of a frame, minus the CRC at the suffix. Manual pg. 7
        # I don't think it really matters, since data is sent in frames. Trimming now vs later. A wrapping delimiter seems odd.
        self.delimiter   : bytes = struct.pack(">6B", *self.network.config['characteristics']['delimiter'])
        self.update_freq : int = self.network.config['characteristics']['update_frequency']


    @staticmethod
    def crc16(buffer: bytes):
        """
        Calculates Cyclic Redundancy Check (CRC) value for a given command of size `buffer`. Manual pg. 7.
        """
        poly = 0x8408
        crc = 0
        i = 0
        while i < len(buffer):
            ch = buffer[i]
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
        This configuration sets continuous mode at the given update frequency (pgs. 7, 26).
        I'm fairly convinced that this doesn't get acknowledged...
        Time and position data is provided by connected GPS satellite.
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


    def lineReceived(self, data: bytes):
        """
        LineReceiver.dataReceived() trims the delimiter and calls LineReceiver.lineReceived().
        """
        self.iteration += 1
        line = f"PAC{self.letterid}:{self.iteration}TIME:{time.time()}DATA:".encode() + data + ":ENDS\n".encode()
        self.write_down(line)
    



class Instrument():
    """
    Holds details to create an instrument server listening on a TCP port via a serial connection.
    Protocols are above, and connection details are provided in the passed config (forked from the server config).
    This is applied in genericserver.py.
    """
    def __init__(self, config: dict, log: logging.Logger):
        # Store connection details from config
        self.connection = config['serial_connection']
        self.connection['port'] = self.connection[SERIAL_PORT]
        self.tcp_port = config['tcp_connection']['port']

        # Define the TCP connection
        self.factory = TCPInstrumentFactory(config, log)

        # Define the serial connection
        self.serial_client : SerialTransport
        match config['name']:
            case 'Radiometer':
                self.serial_client = SerialTransportRadiometer(network=self.factory)
            case 'Thermistors':
                self.serial_client = SerialTransportThermistors(network=self.factory)
            case 'GPS-IMU':
                self.serial_client = SerialTransportGPSIMU(network=self.factory)