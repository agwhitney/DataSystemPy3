"""
py2 has a BasicClient protocol and factory, which don't get used. I've omitted them.
The log was implemented but not used. Most print statements could probably also get logged.
MasterClient basically runs as a script. There are a lot of self. variables that aren't 
used outside of the scope of the method that uses them. I've removed some, but really what
should happen is things should be moved into more specific methods.
"""
import json
import logging  # type hinting
import time

from datetime import datetime
from subprocess import Popen

from filepaths import PATH_TO_CONFIGS, ACQ_CONFIGS_TMP, l0adir, PATH_TO_GENCLIENT, PATH_TO_PYTHON
from genericparser import processL0b
from motorcontrol import MotorControl
from utils import create_log


class MasterClient():
    def __init__(self, config: dict, log: logging.Logger):
        self.log = log
        
        # Read the client configuration
        self.parse_cfg       : dict = config['parsing']  # Sub-config for parsing method
        self.server_ip       : str = config['master_server']['ip']
        self.server_port     : int = config['master_server']['port']
        self.observer_client : bool = config['observer']['active']
        self.start_motor     : bool = config['motor_start']['value']
        self.stop_motor      : bool = config['motor_stop']['value']

        self.num_files       : int = config['acquisition_time']['total_files']
        self.file_acqtime    : int = config['acquisition_time']['file_time']
        self.context         : str = config['context']
        self.instances       : list = config['instances']  # Not in py2 but trims a lot of typing

        # Additional variables
        self.delay = 3  # used for sleep timer
        self.wait_time = 2  # Used for progress lines during acquisition
        self.timestamp = datetime.now().strftime('%y_%m_%d__%H_%M_%S__')
        self.active_instruments = []
        self.active_filenames = []
        self.active_instances = []

        self.motor : MotorControl
        self.items = {
            'rad': 0,
            'thm': 0,
            'gps': 0,
        }
        self.get_serverconfig()


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
            channel['int_time'] = config['characteristics'][key]['integration_time']
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
        self.motor = MotorControl(self.server_ip, self.server_port)
        system_config = self.motor.send_getsysconfig()
        filename = self.timestamp + self.context + "_ServerInformation.bin"
        with open(l0adir / filename, 'w') as f:
            f.write(json.dumps(system_config))

        for instrument in system_config.values():
            self.log.info(f"## SERVER: {instrument['name']} -- Active: {instrument['active']}")
            if not instrument['active']:
                continue
            
            match instrument['name']:
                case 'Radiometer':
                    data_throughput = self.radiometer_metadata(instrument)
                    ## XB - Feb 5, 2014 -> this empirical estimation needs further verification.
                    self.items['rad'] = int(3.7 * 0.36 * self.file_acqtime * data_throughput)
                    self.log.info(f"Estimated data throughput from radiometer: {data_throughput} kBps - {self.items['rad']} items")
                    self.items['rad'] = self.file_acqtime
                
                case 'Thermistors':
                    polling_rate = instrument['characteristics']['polling_interval']
                    addresses = instrument['characteristics']['addresses']
                    print(f"## Polling interval {polling_rate}s - Active ADC: {addresses}")

                    self.items['thm'] = int(self.file_acqtime / polling_rate)
                    self.log.info(f"Estimated GPS-IMU data throughput: {5*8*len(addresses) / polling_rate} Bps - {self.items['thm']} items")
                    self.items['thm'] = self.file_acqtime

                case 'GPS-IMU':
                    update_freq = instrument['characteristics']['update_frequency']
                    print(f"Update frequency = {update_freq} Hz")

                    self.items['gps'] = int(self.file_acqtime * update_freq)
                    self.log.info(f"Estimated GPS-IMU data throughput: {48 * update_freq} Bps - {self.items['gps']} items")
                    self.items['gps'] = self.file_acqtime
                
        if not self.observer_client:
            print(f"System will pause for {self.delay} seconds then continue.")
            time.sleep(self.delay)


    def sendto_parser(self, filename: str):
        if self.parse_cfg['active']:
            verbose     : bool = self.parse_cfg['verbose']
            remove_bin  : bool = self.parse_cfg['delete_raw_files']
            single_file : bool = self.parse_cfg['single_file']
            print(f"Starting parser. Verbose: {verbose}. Remove .bin: {remove_bin}. Single file: {single_file}")
            processL0b(filename, verbose, remove_bin, single_file)
            # AGW removed an unlabeled try-except.
        else:
            print("Not running L0a -> L0b parser per config setting.")
        

    def start_clients(self) -> list:
        processes = []
        for i in range(len(self.active_instances)):
            p = Popen([PATH_TO_PYTHON, PATH_TO_GENCLIENT, self.active_filenames[i]], shell=False)
            processes.append(p)
            self.log.info(f"{self.active_filenames[i]} communication started, Pid: {p.pid}")
            print('--------------------')
        
        return processes


    def acquire(self):
        """
        Performs data acquisition by creating subprocess clients for each instrument. These connect to the subservers
        created in masterserver.py and handle data according to the protocols in genericclient.py
        """
        self.log.info(f"For configuration using {self.server_ip} @ port {self.server_port}")
        print(
            "-" * 30, "\n",
            "-- CLIENTS CONFIG INFORMATION --\n",
            f"Total: {self.num_files} files of {self.file_acqtime} seconds each\n",
            "-" * 30, "\n",
            f"-- System will pause for {self.delay} seconds and then continue --\n",
            "-" * 30, "\n",
        )
        time.sleep(self.delay)

        # Prepare the parserfile
        if self.observer_client:
            self.timestamp = "ObserverMode_FileToBeDeleted_"

        for instance in self.instances:
            if not instance['active']:
                self.log.info(f"Warning: {instance['name']} is set to inactive and will not acquire data.")
                continue

            match instance['name']:
                case 'Radiometer':
                    instance['num_items'] = self.items['rad']

                    if self.start_motor:
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

        parse_filename = l0adir / f"{self.timestamp}{self.context}.bin"
        parse_metadata = {
            'instruments': self.active_instruments,
            'filesID': parse_filename.stem,
            'filename': [],
            'description': [],
        }

        # Loop for as many files are required per the client config file
        for n in range(self.num_files):
            new_context = f"{self.timestamp}{n+1}of{self.num_files}_{self.context}"

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
                        msg += f"({n+1} / {self.num_files}) -- {datetime.now().strftime('%y_%m_%d__%H_%M_%S__')} - Process # {p.pid} -> STOPPED: {p.poll()})"
                print(msg)
                if active_proc == 0:
                    break
    
            # update timestring for next file
            print(f"Total elapsed time: {time.time() - t1:.1f} seconds")
            self.timestamp = datetime.now().strftime('%y_%m_%d__%H_%M_%S__')

        # Write metadata for parser to file 
        with open(parse_filename, 'w') as f:
            f.write(json.dumps(parse_metadata))
            print(f"----------\n{parse_metadata}\n----------")

        # Stop the motor if needed
        if not self.observer_client:
            if not self.stop_motor:
                self.log.info("Motor is set in client configuration to NOT stop.")

            else:
                for instance in self.active_instances:
                    if instance['name'] == 'Radiometer':
                        self.log.info("Stopping motor")
                        self.motor = MotorControl(self.server_ip, self.server_port)
                        self.motor.send_stop()
                        self.motor.disconnect()

        # Launch the parser, if configured to do so
        self.sendto_parser(parse_filename)


if __name__ == '__main__':
    # Create a log
    log = create_log(
        filename = "Client_ACQSystem.log",
        title = "ACQSystem Client - DAIS 2.0",
        timestamp = True,
    )

    # Read the config file
    config_path = PATH_TO_CONFIGS / 'client.json'
    with open(config_path, 'r') as f:
        config = json.load(f)

    client = MasterClient(config, log)
    client.acquire()