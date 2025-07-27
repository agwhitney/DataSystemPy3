from twisted.internet import protocol, reactor, task
from twisted.protocols import basic

import struct
import json

from fpga import FPGA


"""
https://stackoverflow.com/questions/4715340/python-twisted-receive-command-from-tcp-write-to-serial-device-return-response
I'm making a change - the serial client will have a reference to the TCP network, so it has access to the client list and log
This is in place of having the client list as a global. Fear is that the follow-up to the solution was used in py2, meaning this doesn't work.

I've removed the two Connection classes. It seems the plan was to introduce compatability for different types of connections,
but the final version only implements Serial. Literally all it does is load instr_config['serial_connection'] to a class.

The serial client is connected to a SERVER protocol in genericserver.py, so it should be renamed to Serial Transport or something.
"""


class SerialClient(basic.LineReceiver, basic.Int32StringReceiver):
    iteration = 0  # AGW not sure if this needs to be persistent
    
    def __init__(self, network):
        self.network = network


    def connectionMade(self):
        self.network.log.info(
            f"{self.network.name} - Serial connection made"
        )

    
    def connectionLost(self, reason):
        self.network.log.error(
            f"{self.network.name} - Serial connection lost - Reason {reason}"
        )


    def connectionFailed(self):
        self.network.log.error(
            f"{self.network.name} - Connection unsuccessful: {self}. {self.network.name} is not active."
        )
        reactor.stop()


    def write_down(self, data):
        self.network.notifyAll(data)


class SerialClientRadiometer(SerialClient):
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
        data = f"PAC{self.network.config['letterid']}:{self.iteration}TIME:todoDATA:{data}:ENDS\n"
        self.iteration += 1
        self.write_down(data.encode())


class SerialClientThermistors(SerialClient):
    def __init__(self, network):
        super().__init__(network)
        self.delimiter : bytes = self.network.config['characteristics']['delimiter'].encode()
        self.polling_interval = self.network.config['characteristics']['polling_interval']
        self.letterid = self.network.config['letterid']
        self.byte_order = self.network.config['byte_order']
        self.addresses = self.network.config['characteristics']['addresses']

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
        self.data2send = f"PAC{self.letterid}:{self.iteration}TIME:todoDATA:"  # TODO


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


class SerialClientGPSIMU(SerialClient):
    def __init__(self, network):
        super().__init__(network)
        self.letterid = self.network.config['letterid']
        self.byte_order = self.network.config['byte_order']
        self.delimiter : bytes = self.network.config['characteristics']['delimiter'].encode()
        self.update_freq = self.network.config['characteristics']['update_frequency']


    def crc16(self, buffer):
        """Not sure what this does. Bitwise operations.
        Copied as-is, but with 'buffer' instead of 'buff'.
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
        super().connectionMade()
        # Construct a command to be sent 
        header = struct.pack('>BB', 255, 2)
        # From py2: This is the continuous mode command (signified by the '83' to start); only relevant bytes are the second to last
        # which determines mode (0 = disable continues trigger mode, 1 = continuous mode enable, 2 = triggered mode enable)
        # and the last byte which is used to determine update frequency (freq = [60 / (lastByte)])
        # see page 26 of "IG Devices Serial Protocol Specifications.pdf" for more info
        command = struct.pack('>6B', 83, 0, 3, 0, 1, int(60/self.update_freq))
        crc = self.crc16(command)
        # convert crc int into two unsigned int bytes
        crc_msb = int((crc - crc%256) / 256)
        crc_lsb = crc % 256
        # packet end: two bytes crc and then unsigned int byte '3'
        end = struct.pack('>3B', crc_msb, crc_lsb, 3)

        self.sendLine(header)
        self.sendLine(command)
        self.sendLine(end)


    def dataReceived(self, data):
        print("instruments.SerialClientGPSIMU.dataReceived")
        self.iteration += 1
        data = f"PAC{self.letterid}:{self.iteration}TIME:todoDATA:{data}:ENDS\n"  # TODO py2 line 286
        self.write_down(data.encode())
    

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
    
    def __init__(self, config_data, log):
        self.clients = []
        self.name = config_data['name']
        self.log = log
        self.config = config_data

    
    def notifyAll(self, data):
        for client in self.clients:
            client.transport.write(data)
        

class Instrument():
    def __init__(self, config_file, log):
        # Load in instrument config, which was passed as config[instrument].values()
        with open(config_file, 'r') as fp:
            config = json.load(fp)
        log.info(config)

        # AGW py2 does a bunch of subsetting of the config file, but I say just keep it whole.
        # what was config['instrument'] is now just config.values() (but also includes serial and tcp data)
        self.connection = config['serial_connection']
        self.tcp_port = config['tcp_connection']['port']

        # Define the TCP connection
        self.factory = TCPInstrumentFactory(config, log)

        # Define the serial connection
        match config['name']:
            case 'Radiometer':
                self.serial_client = SerialClientRadiometer(self.factory)
            case 'Thermistors':
                self.serial_client = SerialClientThermistors(self.factory)
            case 'GPS-IMU':
                self.serial_client = SerialClientGPSIMU(self.factory)