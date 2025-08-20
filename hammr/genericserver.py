import argparse
import json

from twisted.internet import reactor
from twisted.internet.serialport import SerialPort

from create_log import create_log
from instruments import Instrument
from filepaths import ACQ_CONFIGS


def main():
    """
    Called as a subprocess in masterserver.py. Makes an instrument-specific server using the protocols in instruments.py.
    """
    # Of these args, only the config_file is called in masterserver.py
    parser = argparse.ArgumentParser(description="Server for the Data Acquisition and Instrument control System (DAIS)")
    parser.add_argument('instr_config', help="Equipment file (.json) to work with")
    parser.add_argument('-d', '--background', action='store_true', default=False, help="Run in background")
    parser.add_argument('--http-logging', action='store_true', default=False, help="Log messages to GDAIS-control HTTP server")
    args = parser.parse_args()

    instr_config_file = ACQ_CONFIGS / args.instr_config
    in_background = args.background
    http_logging = args.http_logging

    # Open config to pass to Instrument object.
    with open(instr_config_file, 'r') as f:
        config = json.load(f)

    # Create another log. I think each instrument will get its own per the timestamp.
    log = create_log(
        timestamp = True,
        filename = f"{config['name']}_Server_ACQSystem.log",
        title = f"{config['name']}_ACQSystem SubServer - DAIS 2.0",
    )

    # Create an instrument object, which contains connection details
    # The TCP connection is made, and the SerialPort is instanced to be used as a transport.
    instrument = Instrument(config, log)
    reactor.listenTCP(instrument.tcp_port, instrument.factory)
    SerialPort(instrument.serial_client, instrument.connection['port'], reactor, baudrate=instrument.connection['baudrate'])
    reactor.run()


if __name__ == '__main__':
    main()