"""Server and serial protocols for the radiometer, digitizers, and GPS-IMU.

Once the serial connection is established, data is streaming to the instrument server. The `write_down()` method in
`SerialTransport` broadcasts this data to connected clients, which simply record it as is.

The `Instrument` class is exported and creates the protocol and serial connection.
"""
import struct
import time

from logging import Logger
from twisted.internet import protocol, reactor, task
from twisted.protocols import basic

from fpga import FPGA, FPGAConfig
from filepaths import SERIAL_PORT, PATH_TO_CONFIGS
from telemetryhandler import ThermistorTelemetryHandler

# Used by the radiometer and this seems like the simplest way to provide it
FPGA_CONFIG = FPGAConfig.from_json(PATH_TO_CONFIGS / 'fpga.json')




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


class TCPInstrumentFactory(protocol.Factory):
    protocol = TCPInstrument
    
    def __init__(self, config: dict, log: Logger):
        self.clients = []
        self.name = config['name']
        self.log = log
        self.config = config

    
    def notifyAll(self, data: bytes):
        for client in self.clients:
            client.transport.write(data)




class SerialTransport(basic.LineReceiver):
    """Parent class for instrument-specific serial connections.

    Each instrument has `lineReceived()` or `dataReceived()` methods that handle data (the former will trim delimeters).
    The output is formatted as a line containing the iteration number, a character representing the instrument,
    a timestamp, and the data.
    """
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
        """Writes via transport to clients in network."""
        # print(data)  # Use for debugging, to check that data is streaming.
        self.network.notifyAll(data)


class SerialTransportRadiometer(SerialTransport):
    def __init__(self, network):
        """Configures the FPGA."""
        super().__init__(network)

        fpga = FPGA(systemconfig=self.network.config, fpgaconfig=FPGA_CONFIG, log=self.network.log)
        fpga.estimated_data_throughput()
        fpga.configure()
        fpga.reset_hardware()
        fpga.disconnect_tcp()


    def dataReceived(self, data: bytes):
        dataline = f"PAC{self.letterid}:{self.iteration}TIME:{time.time()}DATA:".encode() + data + ":ENDS\n".encode()
        self.iteration += 1
        self.write_down(dataline)


class SerialTransportThermistors(SerialTransport):
    """Serial transport for digitizers (thermistors).

    Works by calling a function at the polling interval defined, which triggers a loop that polls each digitizer.
    I get the impression that there's some timing weirdness here, and that it subtly shows up in post-processing.
    Also contains a telemetry handler object, called after data is broadcast with `write_down()`.
    """
    def __init__(self, network):
        super().__init__(network)
        self.delimiter        : bytes = self.network.config['characteristics']['delimiter'].encode()
        self.polling_interval : float = self.network.config['characteristics']['polling_interval']
        self.addresses        : list[str] = self.network.config['characteristics']['addresses']

        self.visited_adcs = 0
        self.data = b''
        self.total_adc = len(self.addresses)
        self.network.log.info(f"Number of ADCs = {self.total_adc}")

        self.handler = ThermistorTelemetryHandler(self.network.log)


    @staticmethod
    def poll_command(address: str) -> bytes:
        """Serial command to get thermistor temperatures from digitizers.

        Polling command to thermistor to read analog input, formatted as `#AA(cr)`
        where AA is the address (00 to FF) and (cr) is 0x0D == 13 -> chr(13) == \\r.
        Returns voltage data from all channels on address in format `>(data)(cr)`.
        Data looks like +1.2345 for each channel.
        """
        return struct.pack('>3sB', address.encode(), 13)


    def connectionMade(self):
        """Starts the polling loop.

        It's unclear to me why a line is explicitly sent before calling start_acquisition(),
        but this is probably why the saved data is offset.
        """
        super().connectionMade()
        self.network.log.info("Starting communcation with ADCs")
        cmd = self.poll_command(self.addresses[0])
        self.sendLine(cmd)
        self.start_acquisition()

    
    def start_acquisition(self):
        """Sets a loop to call `get_data()` at the polling interval (seconds)"""
        self.lc = task.LoopingCall(self.get_data)
        self.lc.start(self.polling_interval)

    
    def get_data(self):
        """Starts the polling. `lineReceived()` completes it."""
        self.visited_adcs = 0
        self.data = b''
        cmd = self.poll_command(self.addresses[self.visited_adcs])
        self.sendLine(cmd)

        self.iteration += 1
        self.data_header = f"PAC{self.letterid}:{self.iteration}TIME:{time.time()}DATA:".encode()


    def lineReceived(self, line: bytes):
        self.visited_adcs += 1

        # If there are still digitizers, this will poll the next one and effectively re-run this method.
        if self.visited_adcs < self.total_adc:
            self.data += line[:-1]  # strip default (cr)
            # "Next command gives some extratime to the SLAVE to release the comm. bus, further reducing this value could end with comm. problems... up to you! -XB(?)"
            time.sleep(0.2)
            cmd = self.poll_command(self.addresses[self.visited_adcs])
            self.sendLine(cmd)

        # If at the last digitizer, package and send the data to client and telemetry handler.
        elif self.visited_adcs == self.total_adc:
            self.data += line[:-1]  # strip default (cr)
            datagram = self.data_header + self.data + ':ENDS\n'.encode()
            self.write_down(datagram)
            self.handler.handle_data(self.data)


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
        """Calculates Cyclic Redundancy Check (CRC) value for a given command of size `buffer`. Manual pg. 7."""
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
        """Sends a configuration command to the GPS.

        This configuration sets continuous mode at the given update frequency (pgs. 7, 26).
        I'm not certain that the command actually gets acknowledged.
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
        self.iteration += 1
        line = f"PAC{self.letterid}:{self.iteration}TIME:{time.time()}DATA:".encode() + data + ":ENDS\n".encode()
        self.write_down(line)
    



class Instrument():
    """Combines a server protocol and serial transport protocol."""
    def __init__(self, config: dict, log: Logger):
        # Store connection details from config
        self.connection = config['serial_connection']
        self.connection['port'] = self.connection[SERIAL_PORT]  # SERIAL_PORT is determined by OS
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

