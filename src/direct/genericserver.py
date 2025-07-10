from twisted.internet import reactor
from twisted.internet.serialport import SerialPort

import argparse
import logging

from instruments import Instrument


class GenericServer():
    def __init__(self):
        """
        Called as a subprocess in masterserver.py. Makes an instrument-specific server using the classes in instruments.py.
        This actually just runs as a script. GenericServer.__init__() could just be main().
        """
        # Only the config_file is called in masterserver.py
        parser = argparse.ArgumentParser(description="Server for the Data Acquisition and Instrument control System (DAIS)")
        parser.add_argument('config_file', help="Equipment file (.json) to work with")
        parser.add_argument('-d', '--background', action='store_true', default=False, help="Run in background")
        parser.add_argument('--http-logging', action='store_true', default=False, help="Log messages to GDAIS-control HTTP server")
        args = parser.parse_args()

        self.config_file = args.config_file
        self.in_background = args.background
        self.http_logging = args.http_logging

        # Create another log
        log_file = 'todo-datetime.log'  #TODO see py2 line 35
        logging.basicConfig(
            level = logging.DEBUG,
            format = "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            filename = log_file,
            filemode = 'a'
        )
        log = logging.getLogger('ACQsystem - DAIS 2.0 - Server')
        log.addHandler(logging.StreamHandler())  # AGW logged events are also printed
        log.info('Welcome to ACQsystem - DAIS 2.0')
        log.info("Welcome to DAIS-Server")

        # Create an instrument object, which contains protocol details
        # AGW I'm pretty sure a SerialPort doesn't need a listenTCP associated with it, but I'm not sure
        instrument = Instrument(self.config_file, log)
        reactor.listenTCP(instrument.tcp_port, instrument.factory)
        SerialPort(instrument.serial_client, instrument.connection.serial_port, reactor, baudrate=instrument.connection.baudrate)
        reactor.run()


if __name__ == '__main__':
    GenericServer()