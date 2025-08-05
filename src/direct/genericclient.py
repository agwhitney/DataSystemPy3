"""
AGW Here, like in the servers, I've moved some pseudo-globals to the factory.
Also, like the servers, it would probably be more correct to have one reactor rather than micromanage three.
I've added a couple of file.close() to the failed-connection cases.
"""
import argparse
import json

from twisted.internet import protocol, reactor
from twisted.internet.error import ReactorNotRunning
from twisted.protocols import basic
from time import time

from filepaths import data_path


class TCPClient(basic.Int32StringReceiver):
    def connectionMade(self):
        print("genericclient.TCPClient.connectionMade Connected to TCP")  # AGW seems like logging was intended but not implemented. TODO
        start_time = time()  # seconds since epoch
        self.end_time = start_time + self.factory.measure_time
        print(f"Starting time: {start_time} - Ending time: {self.end_time}")

    
    def dataReceived(self, data: bytes):
        # print("genericclient.TCPClient.dataReceived")  # debug
        self.write_down(data)
    

    def write_down(self, data: bytes):
        # print("genericclient.TCPClient.write_down") # debug
        self.factory.file.write(data)

        if self.end_time <= time():
            print("Client: Stopping acquisition. Send STOP to server")
            self.factory.file.close()
            print("Data file closed.")

            try:
                reactor.stop()
            except ReactorNotRunning:  # This comes up I think because write_down is called again while closing
                print("Reactor already stopped.")
            

class TCPClientFactory(protocol.ClientFactory):
    protocol = TCPClient

    def __init__(self, file, num_items, name):
        self.name = name
        self.file = file
        self.measure_time = num_items  # py2 per comment `NumItems` contains seconds, not items.

    
    def clientConnectionFailed(self, connector, reason):
        print(f"Connection failed: {reason.getErrorMessage()}")
        self.file.close()
        print("Data file closed.")
        reactor.stop()


    def clientConnectionLost(self, connector, reason):
        print(f"Connection lost: {reason.getErrorMessage()}")

        self.file.close()
        print("Data file closed.")
        try:
            reactor.stop()
        except ReactorNotRunning: # Case: client shut down cleanly.
            print("Connection cleanly closed!")


class GenericClient():
    def __init__(self):
        """
        Like genericserver.py, this is called as a subprocess in masterclient.py for each instrument and is a class
        that only inits (could refactor as def main())
        """
        # Parse commandline arguments
        parser = argparse.ArgumentParser(description="Client for the Data Acquisition and Instrument control System (DAIS Client)")
        parser.add_argument('instance_config', help="Client file (.json) to work with")
        args = parser.parse_args()

        with open(args.instance_config, 'r') as f:
            config = json.load(f)
        name = config['name']
        ip = config['ip']
        port = config['port']
        num_items = config['num_items']
        context = config['context']  # TODO I don't think this is part of the instance. Check masterclient.py


        # Print some metadata
        print(f"Name: {name}\nIP: {ip}\nPort: {port}\nNumber of Items: {num_items}")

        # Open a file object that will be written to. Passed to and closed by protocol.
        filepath = data_path / f"{context}_{name}.bin"
        file = open(filepath, 'wb')

        # Create client
        factory = TCPClientFactory(file, num_items, name)
        reactor.connectTCP(ip, port, factory)
        reactor.run()


if __name__ == '__main__':
    GenericClient()