"""
py2 has a BasicClient protocol and factory, which don't get used. I've omitted them.
The log was implemented but not used. Most print statements could probably also get logged.
MasterClient basically runs as a script. There are a lot of self. variables that aren't 
used outside of the scope of the method that uses them. I've removed some, but really what
should happen is things should be moved into more specific methods.
"""
import argparse
import json
import logging  # type hinting
import time
import shutil

from dataclasses import dataclass, field
from datetime import datetime
from subprocess import Popen

from filepaths import PATH_TO_CONFIGS, ACQ_CONFIGS_TMP, L0A_SAVEDIR, PATH_TO_GENCLIENT, PATH_TO_PYTHON
from motorcontrol import MotorControl
from utils import create_log, write_to_log, create_timestamp

from processL0a.create_l0b import create_l0b



@dataclass
class ClientConfig():
    parsing_config : dict = field(default_factory=dict)  # Sub-config for parsing method (effectively removed)
    server_ip      : str = "127.0.0.1"
    server_port    : int = 9022
    is_observer    : bool = False
    start_motor    : bool = True
    stop_motor     : bool = True
    num_files      : int = 1
    file_acqtime   : int = 30
    context        : str = "context"
    instances      : list = field(default_factory=dict)

    @classmethod
    def from_json(cls, filename) -> 'ClientConfig':
        with open(filename, 'r') as f:
            config = json.load(f)
        return cls(
            parsing_config  = config['parsing'],
            server_ip       = config['master_server']['ip'],
            server_port     = config['master_server']['port'],
            is_observer     = config['observer']['active'],
            start_motor     = config['motor_start']['value'],
            stop_motor      = config['motor_stop']['value'],
            num_files       = config['acquisition_time']['total_files'],
            file_acqtime    = config['acquisition_time']['file_time'],
            context         = config['context'],
            instances       = config['instances']  # Not in py2 but trims a lot of typing
        )

    # TODO def dump_to_json



class MasterClient():
    def __init__(self, config: ClientConfig, log: logging.Logger):
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
        self.thermistor_map_path = L0A_SAVEDIR/f'{self.timestamp}thermistors.csv'
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
        with open(L0A_SAVEDIR / filename, 'w') as f:
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
                    print(f"## Polling interval {polling_rate}s - Active ADC: {addresses}")

                    self.items['thm'] = int(self.config.file_acqtime / polling_rate)
                    write_to_log(self.log, f"Estimated GPS-IMU data throughput: {5*8*len(addresses) / polling_rate} Bps - {self.items['thm']} items")
                    self.items['thm'] = self.config.file_acqtime

                case 'GPS-IMU':
                    update_freq = instrument['characteristics']['update_frequency']
                    print(f"Update frequency = {update_freq} Hz")

                    self.items['gps'] = int(self.config.file_acqtime * update_freq)
                    write_to_log(self.log, f"Estimated GPS-IMU data throughput: {48 * update_freq} Bps - {self.items['gps']} items")
                    self.items['gps'] = self.config.file_acqtime
                
        if not self.config.is_observer:
            print(f"System will pause for {self.delay} seconds then continue.")
            time.sleep(self.delay)


    def sendto_parser(self, filename: str) -> None:
        if self.config.parsing_config['active']:
            verbose     : bool = self.config.parsing_config['verbose']
            remove_bin  : bool = self.config.parsing_config['delete_raw_files']
            single_file : bool = self.config.parsing_config['single_file']
            print(f"Starting parser. Verbose: {verbose}. Remove .bin: {remove_bin}. Single file: {single_file}")
            create_l0b(filename, verbose=verbose, removebinfiles=remove_bin, singlefile=single_file)
            # AGW removed an unlabeled try-except.
        else:
            print("Not running L0a -> L0b parser per config setting.")
        

    def start_clients(self) -> list:
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
        write_to_log(self.log, f"For configuration using {self.config.server_ip} @ port {self.config.server_port}")
        print(
            "-" * 30, "\n",
            "-- CLIENTS CONFIG INFORMATION --\n",
            f"Total: {self.config.num_files} files of {self.config.file_acqtime} seconds each\n",
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
            self.active_filenames.append(ACQ_CONFIGS_TMP / f"{self.timestamp}{instance['name']}.json")

        parse_filename = L0A_SAVEDIR / f"{self.timestamp}{self.config.context}.bin"
        parse_metadata = {
            'instruments': self.active_instruments,
            'filesID': parse_filename.stem,
            'thermistorMap': str(self.thermistor_map_path),
            'filename': [],
            'description': [],
        }

        # Loop for as many files are required per the client config file
        for n in range(self.config.num_files):
            new_context = f"{self.timestamp}{n+1}of{self.config.num_files}_{self.config.context}"

            # Update raw file name
            for instance, filename in zip(self.active_instances, self.active_filenames):
                instance['context'] = new_context
                with open(filename, 'w') as f:
                    f.write(json.dumps(instance))
                
            # Keep raw file name for parsing
            parse_metadata['filename'].append(new_context)
            parse_metadata['description'].append(self.active_instances)

            # Start client subprocesses
            processes = self.start_clients()

            # Wait for them to finish
            t1 = time.time()
            while True:
                time.sleep(self.wait_time)
                active_proc = 0
                msg = "--------------------\n"
                for p in processes:
                    if p.poll() is None:  # Process is still running
                        active_proc += 1
                        msg += f"({n+1} / {self.config.num_files}) -- {datetime.now().strftime('%y_%m_%d__%H_%M_%S__')} - Process # {p.pid} -> STOPPED: {p.poll()})"
                print(msg)
                if active_proc == 0:
                    break
    
            # update timestring for next file
            print(f"Total elapsed time: {time.time() - t1:.1f} seconds")
            self.timestamp = datetime.now().strftime('%y_%m_%d__%H_%M_%S__')

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
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--filename', type=str, help="Provide a filename to load from config/, e.g., 'ln2.json'")
    parser.add_argument('-c', '--context', type=str, help="Context string applied to all files (no spaces)")
    parser.add_argument('-s', '--seconds', type=int, help="Seconds to run per created file")
    parser.add_argument('-n', '--numfiles', type=int, help="Number of files to create")
    args = parser.parse_args()

    if any([args.context, args.seconds, args.numfiles]):
        # Use what's given or defaults. Do not use a file.
        c = args.context.replace(' ', '') if args.context else "context"
        s = args.seconds if args.seconds else 30
        n = args.numfiles if args.numfiles else 1
        config = ClientConfig(
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
        config = ClientConfig.from_json(filepath)
    else:
        # Use default file 
        filepath = PATH_TO_CONFIGS / 'client.json'
        config = ClientConfig.from_json(filepath)

    # Create a log
    log = create_log(
        filename = "Client_ACQSystem.log",
        title = "ACQSystem Client - DAIS 2.0",
        timestamp = True,
    )
    client = MasterClient(config, log)
    client.acquire()


if __name__ == '__main__':
    main()