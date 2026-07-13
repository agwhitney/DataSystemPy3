""" 
This is the main acquisition logic. The MasterClient object communicates with a running MasterServer (masterserver.py)
to get the system configuration and then creates subprocesses for each active instrument to acquire data. The subprocesses
use the protocols defined in genericclient.py to connect to the subservers created in masterserver.py and acquire data.
The MasterClient also handles metadata management and can launch a parser (create_l0b) after acquisition if configured to do so.
(summary by copilot)
"""
import argparse
import json
import os
import time
import shutil

from dataclasses import dataclass
from datetime import datetime
from dotenv import load_dotenv
from logging import Logger
from pathlib import Path
from subprocess import Popen

from filepaths import PATH_TO_CONFIGS, PATH_TO_GENCLIENT, PATH_TO_PYTHON
from motorcontrol import MotorControl
from utils import create_log, write_to_log, create_timestamp

from processL0a.create_l0b import create_l0b

load_dotenv()
CONFIGS_PATH = Path( os.path.expandvars(os.getenv('CONFIGS_PATH')) )
DATA_PATH = Path( os.path.expandvars(os.getenv('DATA_PATH')) )


@dataclass
class ParsingConfig:
    """Functionally a child of ClientConfig"""
    active : bool = False
    delete_raw_files : bool = False
    verbose : bool = False
    single_file : bool = False

    @classmethod
    def from_dict(cls, data: dict) -> 'ParsingConfig':
        return cls(
            active = data['active'],
            delete_raw_files = data['delete_raw_files'],
            verbose = data['verbose'],
            single_file = data['single_file'],
        )



@dataclass
class ClientConfig:
    parsing_config : ParsingConfig  # Sub-config for parsing method (effectively removed)
    instances      : list
    server_ip      : str = "127.0.0.1"
    server_port    : int = 9022
    is_observer    : bool = False
    start_motor    : bool = True
    stop_motor     : bool = True
    num_files      : int = 1
    file_acqtime   : int = 30
    context        : str = "context"

    @classmethod
    def from_json(cls, filename) -> 'ClientConfig':
        with open(filename, 'r') as f:
            config = json.load(f)
        parsing_config = ParsingConfig.from_dict(config['parsing'])
        return cls(
            parsing_config  = parsing_config,
            instances       = config['instances'],  # Not in py2 but trims a lot of typing
            server_ip       = config['master_server']['ip'],
            server_port     = config['master_server']['port'],
            is_observer     = config['observer']['active'],
            start_motor     = config['motor_start']['value'],
            stop_motor      = config['motor_stop']['value'],
            num_files       = config['acquisition_time']['total_files'],
            file_acqtime    = config['acquisition_time']['file_time'],
            context         = config['context'],
        )



class MasterClient:
    def __init__(self, config: ClientConfig, log: Logger):
        self.log = log
        self.config = config

        # Additional variables
        self.delay = 3  # "System will wait {self.delay} before starting"
        self.wait_time = 2  # Used for progress lines during acquisition
        self.timestamp = create_timestamp()
        self.active_instruments = []
        self.active_filenames = []
        self.active_instances = []

        self.motor : MotorControl
        self.items = {'rad': 0, 'thm': 0, 'gps': 0,}
        self.get_serverconfig()

        # Copy thermistor map to data folder for use in post-processing.
        # Having this here makes sense, I think?, but is a bit irrelevant to the rest.
        # TODO have this done at server creation
        self.thermistor_map_path = DATA_PATH/f'{self.timestamp}thermistors.csv'
        shutil.copy(PATH_TO_CONFIGS/'thermistors.csv', self.thermistor_map_path)


    def radiometer_metadata(self, config: dict) -> float:
        """
        I moved this from get_serverconfig(). It's mostly info printing. I think this is also done elsewhere?
        Note that `data_throughput` is calculated and returned.
        """
        data_throughput = 0
        # MW = ARM; MMW = ACT. See fpga.py
        channel_data = {
            'mw': {'bytesPerDatagram': 22},
            'mmw': {'bytesPerDatagram': 14},
            'snd': {'bytesPerDatagram': 38},
        }
        value = []
        length = []
        meaning = []
        for key in channel_data:
            channel = channel_data[key]
            channel['int_time'] = config['characteristics'][key]['integration_time_ms']
            channel['activated'] = config['characteristics'][key]['active']
            channel['seq_length'] = config['characteristics'][key]['sequence']['length']
            print(f"## {key} -> Active: {channel['activated']} Ts = {channel['int_time']} ms")

            if channel['activated']:
                data_throughput = channel['bytesPerDatagram'] / channel['int_time']
                print("## Running Sequence")
                for i in range(channel['seq_length']):
                    meaning.append(config['characteristics'][key]['sequence'][f'slot{i}']['meaning'])
                    value.append(config['characteristics'][key]['sequence'][f'slot{i}']['value'])
                    length.append(config['characteristics'][key]['sequence'][f'slot{i}']['length'])
                    print(f"## -- Slot{i} : {meaning[i]} -> repetitions: {length[i]}")

        return data_throughput
        

    def get_serverconfig(self):
        # Get the running system config from the motor-FPGA connection
        self.motor = MotorControl(self.config.server_ip, self.config.server_port)
        system_config = self.motor.send_getsysconfig()
        filename = self.timestamp + self.config.context + "_ServerInformation.bin"
        with open(DATA_PATH / filename, 'w') as f:
            f.write(json.dumps(system_config))

        for instrument in system_config.values():
            write_to_log(self.log, f"## SERVER: {instrument['name']} -- Active: {instrument['active']}")
            if not instrument['active']:
                continue
            
            match instrument['name']:
                case 'Radiometer':
                    data_throughput = self.radiometer_metadata(instrument)
                    ## XB - Feb 5, 2014 -> this empirical estimation needs further verification.
                    self.items['rad'] = int(3.7 * 0.36 * self.config.file_acqtime * data_throughput)
                    write_to_log(self.log, f"Estimated data throughput from radiometer: {data_throughput} kBps - {self.items['rad']} items")
                    self.items['rad'] = self.config.file_acqtime
                
                case 'Thermistors':
                    polling_rate = instrument['characteristics']['polling_interval']
                    addresses = instrument['characteristics']['addresses']
                    write_to_log(self.log, f"## Polling interval {polling_rate}s - Active ADC: {addresses}")

                    self.items['thm'] = int(self.config.file_acqtime / polling_rate)
                    write_to_log(self.log, f"Estimated GPS-IMU data throughput: {5*8*len(addresses) / polling_rate} Bps - {self.items['thm']} items")
                    self.items['thm'] = self.config.file_acqtime

                case 'GPS-IMU':
                    update_freq = instrument['characteristics']['update_frequency']
                    write_to_log(self.log, f"Update frequency = {update_freq} Hz")

                    self.items['gps'] = int(self.config.file_acqtime * update_freq)
                    write_to_log(self.log, f"Estimated GPS-IMU data throughput: {48 * update_freq} Bps - {self.items['gps']} items")
                    self.items['gps'] = self.config.file_acqtime
                
        if not self.config.is_observer:
            print(f"System will pause for {self.delay} seconds then continue.")
            time.sleep(self.delay)


    def sendto_parser(self, filename: str | Path) -> None:
        """This is a convenience that IMO shouldn't exist like this"""
        if self.config.parsing_config.active:
            verbose     : bool = self.config.parsing_config.verbose
            remove_bin  : bool = self.config.parsing_config.delete_raw_files
            single_file : bool = self.config.parsing_config.single_file
            print(f"Starting parser. Verbose: {verbose}. Remove .bin: {remove_bin}. Single file: {single_file}")
            create_l0b(filename, verbose=verbose, removebinfiles=remove_bin, singlefile=single_file)
            # AGW removed an unlabeled try-except.
        else:
            print("Not running L0a -> L0b parser per config setting.")
        

    def start_clients(self) -> list[Popen]:
        processes = []
        for i in range(len(self.active_instances)):
            p = Popen([PATH_TO_PYTHON, PATH_TO_GENCLIENT, self.active_filenames[i]], shell=False)
            processes.append(p)
            write_to_log(self.log, f"{self.active_filenames[i]} communication started, Pid: {p.pid}")
            print('--------------------')
        
        return processes


    def acquire(self) -> None:
        """
        Performs data acquisition by creating subprocess clients for each instrument. These connect to the subservers
        created in masterserver.py and handle data according to the protocols in genericclient.py
        """
        continuous_mode = True if self.config.num_files == -1 else False
        write_to_log(self.log, f"For configuration using {self.config.server_ip} @ port {self.config.server_port}")
        write_to_log(
            self.log,
            f"Running continuously - filetime = {self.config.file_acqtime} seconds" if continuous_mode
                else f"Total: {self.config.num_files} files of {self.config.file_acqtime} seconds each"
        )
        print(
            "-" * 30, "\n",
            "-- CLIENTS CONFIG INFORMATION --\n",
            f"Running continuously, producing files of {self.config.file_acqtime} seconds each" if continuous_mode
                else f"Total: {self.config.num_files} files of {self.config.file_acqtime} seconds each\n",
            "-" * 30, "\n",
            f"-- System will pause for {self.delay} seconds and then continue --\n",
            "-" * 30, "\n",
        )
        time.sleep(self.delay)

        # Prepare the parserfile
        if self.config.is_observer:
            self.timestamp = "ObserverMode_FileToBeDeleted_"

        for instance in self.config.instances:
            if not instance['active']:
                write_to_log(self.log, f"Warning: {instance['name']} is set to inactive and will not acquire data.")
                continue

            match instance['name']:
                case 'Radiometer':
                    instance['num_items'] = self.items['rad']

                    if self.config.start_motor:
                        print("-" * 30, "\n", "Starting motor.")
                        self.motor.send_start()
                        self.motor.disconnect()
                        print("-" * 30, "\n")

                case 'Thermistors':
                    instance['num_items'] = self.items['thm']

                case 'GPS-IMU':
                    instance['num_items'] = self.items['gps']

                case _:
                    raise NotImplementedError("Typo in instrument name, or instrument not implemented.")

            self.active_instances.append(instance)
            self.active_instruments.append(instance['name'])
            self.active_filenames.append(CONFIGS_PATH / f"{self.timestamp}{instance['name']}.json")

        parse_filename = DATA_PATH / f"{self.timestamp}{self.config.context}.json"
        parse_metadata = {
            'instruments': self.active_instruments,
            'filesID': parse_filename.stem,
            'thermistorMap': str(self.thermistor_map_path),
            'filename': [],
            'description': [],
        }

        # Loop for as many files are required per the client config file
        n = 0
        while True:
            n += 1
            if continuous_mode:
                new_context = f"{self.timestamp}{n}_{self.config.context}"
            else:
                if n > self.config.num_files:
                    write_to_log(self.log, f"Completed {self.config.num_files} files. Ending acquisition.")
                    break
                new_context = f"{self.timestamp}{n}of{self.config.num_files}_{self.config.context}"

            # Update raw file name
            for instance, filename in zip(self.active_instances, self.active_filenames):
                instance['context'] = new_context
                with open(filename, 'w') as f:
                    f.write(json.dumps(instance))
                
            # Keep raw file name for parsing
            parse_metadata['filename'].append(new_context)
            parse_metadata['description'].append(self.active_instances)

            # Start client subprocesses. Yes, they start again with every loop.
            processes = self.start_clients()

            # The clients stop themselves, hopefully. They record a stop time and check against it - but only when they receive data.
            # If they don't stop, most likely the data is not being received, probably due to a bad connection.
            try:
                t1 = time.time()
                while True:
                    time.sleep(self.wait_time)
                    active_proc = 0
                    msg = "--------------------\n"
                    for p in processes:
                        if p.poll() is None:  # Process is still running
                            active_proc += 1
                            msg += f"({n} / {self.config.num_files}) -- {create_timestamp()} - Process # {p.pid} -> STOPPED: {p.poll()})\n"
                    print(msg)
                    if active_proc == 0:
                        break
                
                # update timestring for next file
                write_to_log(self.log, f"Closing file {n}. Total elapsed time: {time.time() - t1:.1f} seconds")
                self.timestamp = create_timestamp()

            # This intercepts CTRL+C. It also intercepts SIGKILL sent from systemd, but it may be more correct to use a different signal handler pattern.
            except KeyboardInterrupt:
                write_to_log(self.log, "Received a keyboard interrupt: escaping the acquisition process.")
                write_to_log(self.log, f"Total elapsed time: {time.time() - t1:.1f} seconds")
                for p in processes:
                    print(f"Sending SIGKILL to {p.pid}")
                    p.kill()
                break

        # Write metadata for parser to file 
        with open(parse_filename, 'w') as f:
            f.write(json.dumps(parse_metadata, indent=4))
            print(f"----------\n{parse_metadata}\n----------")

        # Stop the motor if needed
        if not self.config.is_observer:
            if not self.config.stop_motor:
                write_to_log(self.log, "Motor is set in client configuration to NOT stop.")

            else:
                for instance in self.active_instances:
                    if instance['name'] == 'Radiometer':
                        write_to_log(self.log, "Stopping motor")
                        self.motor = MotorControl(self.config.server_ip, self.config.server_port)
                        self.motor.send_stop()
                        self.motor.disconnect()

        # Launch the parser, if configured to do so
        self.sendto_parser(parse_filename)



def main():
    # Create a log
    log = create_log(
        filename = "Client_ACQSystem.log",
        title = "ACQSystem Client - DAIS 2.0",
        timestamp = True,
    )

    # Create a command-line parser
    parser = argparse.ArgumentParser(
        prog = "uv run hammr/masterclient.py",
        description = "No argument is equivalent to '-f client.json'. Passing any of -c, -s, or -n will not refer to a file.",
    )
    parser.add_argument('-f', '--filename', type=str, help="Provide a filename to load from config/, e.g., 'ln2.json'")
    parser.add_argument('-c', '--context', type=str, help="Context string applied to all files (no spaces) (default 'context')")
    parser.add_argument('-s', '--seconds', type=int, help="Seconds to run per created file (default 30)")
    parser.add_argument('-n', '--numfiles', type=int, help="Number of files to create (default 1) (-1 for continuous mode)")
    args = parser.parse_args()

    if any([args.context, args.seconds, args.numfiles]):
        # Use what's given or defaults. Do not use a file.
        write_to_log(log, "Loading client config from passed parameters")
        c = args.context.replace(' ', '') if args.context else "context"
        s = args.seconds if args.seconds else 30
        n = args.numfiles if args.numfiles else 1
        config = ClientConfig(
            parsing_config = ParsingConfig(),
            context = c,
            file_acqtime = s,
            num_files = n,
            instances = [
                {"name": "Thermistors", "active": True, "ip": "127.0.0.1", "port": 8055, "num_items": 0},
                {"name": "Radiometer", "active": True, "ip": "127.0.0.1", "port": 7555, "num_items": 0},
                {"name": "GPS-IMU", "active": True, "ip": "127.0.0.1", "port": 9055, "num_items": 0}
            ]
        )
    elif args.filename:
        # Use given file
        filepath = PATH_TO_CONFIGS / args.filename
        write_to_log(log, f"Loading client config from {filepath}")
        config = ClientConfig.from_json(filepath)
    else:
        # Use default file "client.json"
        filepath = PATH_TO_CONFIGS / 'client.json'
        write_to_log(log, f"Loading client config from {filepath}")
        config = ClientConfig.from_json(filepath)

    # Create the client and run it
    client = MasterClient(config, log)
    client.acquire()


if __name__ == '__main__':
    main()