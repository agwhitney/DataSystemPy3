from twisted.internet import protocol, reactor, task
from twisted.protocols import basic

import struct
import json

from configfpga import ConfigFPGA


"""
https://stackoverflow.com/questions/4715340/python-twisted-receive-command-from-tcp-write-to-serial-device-return-response
I'm making a change - the serial client will have a reference to the TCP network, so it has access to the client list and log
This is in place of having the client list as a global. Fear is that the follow-up to the solution was used in py2, meaning this doesn't work.

I've removed the two Connection classes. It seems the plan was to introduce compatability for different types of connections,
but the final version only implements Serial. Literally all it does is load instr_config['serial_connection'] to a class.
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
        self.network.log.info(
            f"ERROR {self.network.name} - Serial connection lost - Reason {reason}"
        )


    def connectionFailed(self):
        self.network.log.info(
            f"ERROR {self.network.name} - Connection unsuccessful: {self}. {self.network.name} is not active."
        )
        reactor.stop()


    def write_down(self, data):
        self.network.notifyAll(data)


class SerialClientRadiometer(SerialClient):
    def __init__(self, network):
        super().__init__(network)
        self.letterid = self.network.config['letterid']  # unused?
        self.byte_order = self.network.config['byte_order']  # unused?

        fpga = ConfigFPGA(self.network.config, self.network.log)
        fpga.estimated_data_throughput()
        fpga.configure()
        fpga.hardware_reset()
        fpga.disconnect_tcp()


    def dataReceived(self, data):
        data = f"PAC{self.network.config['letterid']}:{self.iteration}TIME:todoDATA:{data}:ENDS\n"
        self.iteration += 1
        self.write_down(data)


class SerialClientThermistors(SerialClient):
    def __init__(self, network):
        super().__init__(network)
        self.delimiter = self.network.config['characteristics']['delimiter']
        self.polling_interval = self.network.config['characteristics']['polling_interval']
        self.letterid = self.network.config['letterid']



class SerialClientGPSIMU(SerialClient):
    ...
    

class TCPInstrument(protocol.Protocol):
    def __init__(self):
        print("Creating TCPInstrument instance")

    
    def connectionMade(self):
        self.factory.log.info(
            f"{self.factory.name} - New TCP client received from {self.transport.getPeer()} - Instance {self}"
        )
        self.transport.write(
            f"Welcome to {self.factory.name} you are at {self.transport.getPeer()}\n"
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
                self.serial_client = SerialClientRadiometer(config, log)
            case 'Thermistors':
                self.serial_client = SerialClientThermistors(config, log)
            case 'GPS-IMU':
                self.serial_client = SerialClientGPSIMU(config, log)