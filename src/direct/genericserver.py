import argparse
import logging

from datetime import datetime
from twisted.internet import reactor
from twisted.internet.serialport import SerialPort

from instruments import Instrument
from filepaths import configs_path, logs_path


class GenericServer():
    def __init__(self):
        """
        Called as a subprocess in masterserver.py. Makes an instrument-specific server using the classes in instruments.py.
        This actually just runs as a script. GenericServer.__init__() could just be main().
        """
        # Of these args, only the config_file is called in masterserver.py
        parser = argparse.ArgumentParser(description="Server for the Data Acquisition and Instrument control System (DAIS)")
        parser.add_argument('instr_config', help="Equipment file (.json) to work with")
        parser.add_argument('-d', '--background', action='store_true', default=False, help="Run in background")
        parser.add_argument('--http-logging', action='store_true', default=False, help="Log messages to GDAIS-control HTTP server")
        args = parser.parse_args()

        self.instr_config_file = configs_path / args.instr_config
        self.in_background = args.background
        self.http_logging = args.http_logging

        # Create another log. I think each instrument will get its own per the timestamp.
        log_filename = datetime.now().strftime('%y_%m_%d__%H_%M_%S__') + "Server_ACQsystem.log"
        logging.basicConfig(
            level = logging.DEBUG,
            format = "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            filename = logs_path / log_filename,
            filemode = 'a'
        )
        log = logging.getLogger('ACQsystem - DAIS 2.0 - Server')
        log.addHandler(logging.StreamHandler())  # AGW logged events are also printed
        log.info('Welcome to ACQsystem - DAIS 2.0')
        log.info("Welcome to DAIS-Server")

        # Create an instrument object, which contains protocol details
        # The TCP connection is made, and the SerialPort is instanced to be used as a transport.
        instrument = Instrument(self.instr_config_file, log)
        reactor.listenTCP(instrument.tcp_port, instrument.factory)
        SerialPort(instrument.serial_client, instrument.connection['port'], reactor, baudrate=instrument.connection['baudrate'])
        reactor.run()


if __name__ == '__main__':
    GenericServer()