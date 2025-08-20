"""
AGW Here, like in the servers, I've moved some pseudo-globals to the factory.
Also, like the servers, it would probably be more correct to have one reactor rather than micromanage three.
I've added a couple of file.close() to the failed-connection cases.
"""
import argparse
import json
import io, logging  # Type checking (ruff override for oneliner ->) # noqa: E401

from twisted.internet import protocol, reactor
from twisted.internet.error import ReactorNotRunning
from twisted.protocols import basic
from time import time

from create_log import create_log
from filepaths import ACQ_DATA


class TCPClient(basic.Int32StringReceiver):
    def connectionMade(self):
        self.factory.log.info("genericclient.TCPClient.connectionMade Connected to TCP")
        start_time = time()  # seconds since epoch
        self.end_time = start_time + self.factory.measure_time
        self.factory.log.info(f"Starting time: {start_time} - Ending time: {self.end_time}")

    
    def dataReceived(self, data: bytes):
        self.write_down(data)
    

    def write_down(self, data: bytes):
        self.factory.file.write(data)

        if self.end_time <= time():
            self.factory.log.info("Client: Stopping acquisition. Send STOP to server")
            self.factory.file.close()
            self.factory.log.info("Data file closed.")

            try:
                reactor.stop()
            except ReactorNotRunning:  # This comes up I think when write_down is called again while closing
                self.factory.log.info("Reactor already stopped.")
            

class TCPClientFactory(protocol.ClientFactory):
    protocol = TCPClient

    def __init__(self, open_file: io.TextIOWrapper, num_items: int, name: str, log: logging.Logger):
        self.name = name
        self.file = open_file
        self.measure_time = num_items  # py2 per comment `NumItems` contains seconds, not items.
        self.log = log

    
    def clientConnectionFailed(self, connector, reason):
        self.log.info(f"Connection failed: {reason.getErrorMessage()}")
        self.file.close()
        self.log.info("Data file closed.")
        reactor.stop()


    def clientConnectionLost(self, connector, reason):
        self.log.info(f"Connection lost: {reason.getErrorMessage()}")

        self.file.close()
        self.log.info("Data file closed.")
        try:
            reactor.stop()
        except ReactorNotRunning: # Case: client shut down cleanly.
            self.log.info("Connection cleanly closed!")


def main():
    """
    Like genericserver.py, this is called as a subprocess in masterclient.py for each instrument.
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
    context = config['context']

    # Create another log analogous to the one in genericserver.py
    log = create_log(
        timestamp = True,
        filename = f"{name}_Client_ACQSystem.log",
        title = f"{name}_ACQSystem SubClient - DAIS 2.0",
    )

    # Print some metadata
    log.info(f"Name: {name}\nIP: {ip}\nPort: {port}\nNumber of Items: {num_items}")

    # Open a file object that will be written to. Passed to and closed by protocol.
    filepath = ACQ_DATA / f"{context}_{name}.bin"
    file = open(filepath, 'wb')

    # Create client
    factory = TCPClientFactory(file, num_items, name, log)
    reactor.connectTCP(ip, port, factory)
    reactor.run()


if __name__ == '__main__':
    main()