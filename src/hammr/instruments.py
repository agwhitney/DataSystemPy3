import struct
from twisted.internet import protocol, reactor, task
from twisted.protocols import basic

"""
Clients used in serial connections made in py2:GenericServer.py.
In that, it makes an instrument object with parameters including an object that just holds serial connection info,
a serial client, and a TCP factory that holds a different TCP protocol. I want to say that the serial client and
protocol don't need to be different, but I'm not sure. If I'm lucky, this will work better.

I've omitted a writeDown() method. I think all it did was broadcast information
to each of the clients, but I don't think those clients do anything with it...
"""


class SerialInstrumentProtocol(basic.LineReceiver):
    iteration = 0

    def __init__(self, config):
        self.connection = config['serial_connection']
        self.name = config['name']

    def connectionMade(self):
        # TODO print and log
        print(f"connected {self.name}")

    def connectionLost(self, reason = ...):
        # TODO print and log
        # py2 has a connectionFailed() method but that doesn't seem to exist in current twisted protocols, so I'm assuming this can go here
        print("lost", self.name)
        reactor.stop()


class GPSProtocol(SerialInstrumentProtocol):
    def __init__(self, config):
        config = config['gpsimu']
        super().__init__(config)
        self.name = config['name']
        self.letterid = config['letterid']
        self.byte_order = config['byte_order']
        self.delimiter = config['characteristics']['delimiter']
        self.update_freq = config['characteristics']['update_frequency']


    # def crc16(self, buffer):
    #     """Not sure what this does. Bitwise operations.
    #     Copied as-is, but with 'buffer' instead of 'buff'.
    #     """
    #     poly = 0x8408
    #     crc = 0
    #     i = 0
    #     while i < len(buffer):
    #         ch = ord(buffer[i])
    #         uc = 0
    #         while uc < 8:
    #             if (crc & 1)^(ch & 1):
    #                 crc = (crc >> 1)^poly
    #             else:
    #                 crc >>= 1
    #             ch >>= 1
    #             uc += 1
    #         i += 1
    #     return crc


    # def connectionMade(self) -> None:
    #     super().connectionMade()
    #     # Construct a command to be sent 
    #     header = struct.pack('>BB', 255, 2)
    #     # From py2: This is the continuous mode command (signified by the '83' to start); only relevant bytes are the second to last
    #     # which determines mode (0 = disable continues trigger mode, 1 = continuous mode enable, 2 = triggered mode enable)
    #     # and the last byte which is used to determine update frequency (freq = [60 / (lastByte)])
    #     # see page 26 of "IG Devices Serial Protocol Specifications.pdf" for more info
    #     command = struct.pack('>6B', 83, 0, 3, 0, 1, 60/self.update_freq)
    #     crc = self.crc16(command)
    #     # convert crc int into two unsigned int bytes
    #     crc_msb = (crc - crc%256) / 256
    #     crc_lsb = crc % 256
    #     # packet end: two bytes crc and then unsigned int byte '3'
    #     end = struct.pack('>3B', crc_msb, crc_lsb, 3)

    #     self.sendLine(header)
    #     self.sendLine(command)
    #     self.sendLine(end)


    # def lineReceived(self, line):
    #     self.iteration += 1


class ThermistorProtocol(SerialInstrumentProtocol):
    def __init__(self, config):
        config = config['thermistor']
        super().__init__(config)
        self.addresses = config['characteristics']['addresses']
        self.polling_interval = config['characteristics']['polling_interval']
        self.number_adcs = len(self.addresses)


    # def connectionMade(self):
    #     super().connectionMade()
    #     self.test_digitizers()


    # def test_digitizers(self):
    #     print("Starting communication with ADCs")
    #     command = struct.pack('cccB', '#', '0', str(self.addresses[0]), 13)
    #     self.sendLine(command)
    #     self.start_acquisition()


    # def start_acquisition(self):
    #     lc = task.LoopingCall(self.get_data)
    #     lc.start(self.polling_interval)


    # def get_data(self):
    #     self.visited_adcs = 0
    #     command = struct.pack('cccB', '#', '0', str(self.addresses[self.visited_adcs]), 13)
    #     self.sendLine(command)
    #     self.iteration += 1


    # def lineReceived(self, line):
    #     self.visited_adcs += 1
    #     if self.visited_adcs <= (self.number_adcs - 1):
    #         # Omitted a 0.2 second sleep but that might cause ordering problems.
    #         command = struct.pack('cccB', '#', '0', str(self.addresses[self.visited_adcs]), 13)
    #         self.sendLine(command)
    #     elif self.visited_adcs == self.number_adcs:
    #         # a writeDown thing
    #         print('writeDown in ', self.__repr__())


class RadiometerProtocol(SerialInstrumentProtocol):
    # This does surprisingly little? Just logs that are called in super()?
    # Does some stuff with the FPGA in __init__() (should it be connectionMade()?)
    def __init__(self, config):
        config = config['radiometer']
        super().__init__(config)
        self.letterid = config['letterid']
        self.byte_order = config['byte_order']



if __name__ == '__main__':
    import tomllib
    from twisted.internet import reactor


    with open("Config/system_config.toml", 'rb') as f:
        config = tomllib.load(f)

    
    gps = GPSProtocol(config)
    rad = RadiometerProtocol(config)
    thm = ThermistorProtocol(config)

    reactor.spawnProcess(gps, '.venv/Scripts/python.exe', ['pname'], {})
    reactor.spawnProcess(rad, '.venv/Scripts/python.exe', ['pname2'], {})
    reactor.spawnProcess(thm, '.venv/Scripts/python.exe', ['pname3'], {})
    # serialport.SerialPort(proto, proto.connection['port'], reactor, proto.connection['baud_rate'])
    reactor.run()