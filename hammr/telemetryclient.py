from twisted.internet import protocol, reactor
from twisted.internet.error import ReactorNotRunning
from twisted.protocols import basic

from telemetryhandler import ThermistorTelemetryHandler
from utils import create_log


class TCPClient(basic.Int32StringReceiver):
    """Data receiver for a serial instrument, i.e., the radiometer, digitizers, and GPS-IMU.

    This client is basically an open file with a lifetime set at creation, and will collect data until that
    lifetime ends and the file and connection closes. The timing is only checked when data is successfully received.

    Attributes:
        `end_time`: Time after which the client will stop its reactor loop.
    """
    def connectionMade(self):
        self.factory.log.info("telemetryclient.TCPClient.connectionMade Connected to TCP")

    
    def dataReceived(self, data: bytes):
        try:
            self.factory.handler.handle_data(data, self.factory.log)
        except Exception as e:
            print(f"Telemetry handler error ignored: <{e}>")


class TCPClientFactory(protocol.ClientFactory):
    protocol = TCPClient

    def __init__(self, log):
        self.log = log
        self.handler = ThermistorTelemetryHandler()

    
    def clientConnectionFailed(self, connector, reason):
        self.log.info(f"Connection failed: {reason.getErrorMessage()}")
        reactor.stop()


    def clientConnectionLost(self, connector, reason):
        self.log.info(f"Connection lost: {reason.getErrorMessage()}")
        try:
            reactor.stop()
        except ReactorNotRunning: # Case: client shut down cleanly.
            self.log.info("Connection cleanly closed!")


def main():
    # Create another log analogous to the one in genericserver.py
    log = create_log(
        prepend_timestamp = True,
        filename = "Telemetry.log",
        title = "Telemetry SubClient - DAIS 2.0",
    )

    # Connect client
    factory = TCPClientFactory(log)
    reactor.connectTCP('127.0.0.1', 8055, factory)
    reactor.run()


if __name__ == '__main__':
    main()
