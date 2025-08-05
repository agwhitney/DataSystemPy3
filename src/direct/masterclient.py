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

from create_log import create_log
from motorcontrol import MotorControl
from filepaths import configs_path, configstmp_path, data_path, genericclient
from genericparser import GenericParser


class MasterClient():
    def __init__(self, config: dict, log: logging.Logger):
        self.log = log
        
        # Parse the config
        self.parsing_cfg     : dict = config['parsing']  # Sub-config for parsing
        self.server_ip       : str = config['master_server']['ip']
        self.server_port     : int = config['master_server']['port']
        self.observer_client : bool = config['observer']['active']
        self.start_motor     : bool = config['motor_start']['value']
        self.stop_motor      : bool = config['motor_stop']['value']

        self.context         : str = config['context']
        self.instances       : list = config['instances']  # Not in py2 but trims a lot of typing
        self.num_files       : int = config['acquisition_time']['total_files']
        self.file_acqtime    : int = config['acquisition_time']['file_time']

        # Additional variables
        self.delay = 3  # used for sleep timer (but notably not used waiting for sub-clients)
        self.timestamp = datetime.now().strftime('%y_%m_%d__%H_%M_%S__')  # This will be slightly behind the log
        self.active_instruments = []  # AGW this and below should be a dict, again
        self.active_filenames = []
        self.active_instances = []  # AGW new

        # py2 runs get_serverconfig() in acquire(). It makes these vars
        self.motor : MotorControl
        self.items_rad : int
        self.items_thm : int
        self.items_gps : int
        self.get_serverconfig()
        

    def get_serverconfig(self):
        """
        This gets server config info from motorcontrol.py, which I believe actually does connect
        to the FGPA via TCP/IP. Why pass the data? Why not just call it again?
        """
        # Get the running system config from the motor-FPGA connection
        self.motor = MotorControl(self.server_ip, self.server_port)
        system_config = self.motor.send_getsysconfig()  # AGW changed this function to return rather than keep
        filename = self.timestamp + self.context + "_ServerInformation.bin"
        with open(data_path / filename, 'w') as f:
            f.write(json.dumps(system_config))

        for instrument in system_config.values():
            print(f"## SERVER: {instrument['name']} -- Active: {instrument['active']}")
            if not instrument['active']:
                continue

            if instrument['name'] == 'Radiometer':
                # This whole block is just for logging, I think. I've removed a lot of self.
                # It doesn't seem to be used (logging isn't implemented)
                mapkey = ('mw', 'mmw', 'snd')
                bytesPerDatagram = {'mw': 22, 'mmw': 14, 'snd': 38}  # MW = ARM; MMW = ACT. See fpga.py
                value = []
                length = []
                int_time = {}
                activated = {}
                meaning = []
                seq_length = {}
                for key in mapkey:
                    int_time[key] = instrument['characteristics'][key]['integration_time']
                    activated[key] = instrument['characteristics'][key]['active']
                    seq_length[key] = instrument['characteristics'][key]['sequence']['length']
                    # Below should fail because of badkey
                    print(f"## {key} -> Active: {activated[key]} Ts = {int_time[key]} ms")
                    if activated[key]:
                        data_throughput = bytesPerDatagram[key] / int_time[key]
                        print("## Running Sequence")
                        for i in range(seq_length[key]):
                            meaning.append(instrument['characteristics'][key]['sequence'][f'slot{i}']['meaning'])
                            value.append(instrument['characteristics'][key]['sequence'][f'slot{i}']['value'])
                            length.append(instrument['characteristics'][key]['sequence'][f'slot{i}']['length'])
                            print(f"## -- Slot{i} : {meaning[i]} -> repetitions: {length[i]}")

                ## Of course 0.57 is an empirical number, there is no other way to claculate that.
                ## XB - Feb 5, 2014 -> this empirical estimation needs further verification.
                # AGW unclear if XB is referring to above or below.
                self.items_rad = int(3.7 * 0.36 * self.file_acqtime * data_throughput)
                self.log.info(f"Estimated data throughput from radiometer: {data_throughput} kBps - {self.items_rad} items")
                self.items_rad = self.file_acqtime  # Each section has these three lines like this.
            
            elif instrument['name'] == 'Thermistors':
                polling_rate = instrument['characteristics']['polling_interval']
                addresses = instrument['characteristics']['addresses']
                print(f"## Polling interval {polling_rate}s - Active ADC: {addresses}")

                self.items_thm = int(self.file_acqtime / polling_rate)
                self.log.info(f"Estimated GPS-IMU data throughput: {5*8*len(addresses) / polling_rate} Bps - {self.items_thm} items")
                self.items_thm = self.file_acqtime

            elif instrument['name'] == 'GPS-IMU':
                update_freq = instrument['characteristics']['update_frequency']
                print(f"Update frequency = {update_freq} Hz")

                self.items_gps = int(self.file_acqtime * update_freq)
                self.log.info(f"Estimated GPS-IMU data throughput: {48 * update_freq} Bps - {self.items_gps} items")
                self.items_gps = self.file_acqtime
                
        if not self.observer_client:
            print(f"System will pause for {self.delay} seconds then continue.")
            time.sleep(self.delay)


    def sendto_parser(self, filename):
        if self.parsing_cfg['active']:
            print(f"Starting parser. Verbose: {self.parsing_cfg['verbose']}. Remove .bin: {self.parsing_cfg['delete_raw_files']}. Single file: {self.parsing_cfg['single_file']}")
            GenericParser(filename, self.parsing_cfg['verbose'], self.parsing_cfg['delete_raw_files'], self.parsing_cfg['single_file'])
            # AGW removed an unlabeled try-except.
        else:
            print("Not running L0a -> L0b(?) parser.")
        

    def acquire(self):
        # TODO This method does a lot, and some of its functions should maybe be separated for better understanding.
        print(f"For configuration using {self.server_ip} @ port {self.server_port}")

        if self.observer_client:
            self.timestamp = "ObserverMode_FileToBeDeleted_"
        print(f"""
              --------------------------------
              -- CLIENTS CONFIG INFORMATION --
              Total: {self.num_files} files of {self.file_acqtime} seconds each
              --------------------------------
              -- System will pause for {self.delay} seconds and then continue
              --------------------------------
        """)
        time.sleep(self.delay)

        # Prepare the parserfile
        for instance in self.instances:
            if not instance['active']:
                print(f"Warning: {instance['name']} is set to inactive and will not acquire data.")
                continue
            # This could be simplified with a key?
            match instance['name']:
                case 'Radiometer':
                    instance['num_items'] = self.items_rad

                    if self.start_motor:
                        print("-" * 30, "\nStarting motor.")
                        self.motor.send_start()
                        self.motor.disconnect()
                        print("-" * 30)

                case 'Thermistors':
                    instance['num_items'] = self.items_thm

                case 'GPS-IMU':
                    instance['num_items'] = self.items_gps

            self.active_instances.append(instance)
            self.active_instruments.append(instance['name'])
            self.active_filenames.append(configstmp_path / f"{self.timestamp}{instance['name']}.json")

        parserfile_name = data_path / f"{self.timestamp}{self.context}.bin"
        parserfile_obj = open(parserfile_name, 'w')
        file_merger = {
            'instruments': self.active_instruments,
            'filesID': parserfile_name.stem,
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
            file_merger['filename'].append(new_context)
            file_merger['description'].append(self.active_instances)
            parserfile_obj.seek(0)
            parserfile_obj.write(json.dumps(file_merger))
            print(f"----------\n{file_merger}\n----------")

            # Start client subprocesses
            processes = []
            for i in range(len(self.active_instances)):
                p = Popen(['.venv/Scripts/python', genericclient, self.active_filenames[i]], shell=False)
                processes.append(p)
                print(f"{self.active_filenames[i]} communication started, Pid: {p.pid}")
                print('--------------------')

            # Wait for them to finish
            t1 = time.time()
            while True:
                time.sleep(2)  # Not delay?
                active_proc = 0
                msg = "--------------------"
                for i in range(len(self.active_instances)):
                    if processes[i].poll() is None:
                        active_proc += 1
                        msg += f"\n({n+1} / {self.num_files}) -- {datetime.now().strftime('%y_%m_%d__%H_%M_%S__')} - Process # {processes[i].pid} -> STOPPED: {processes[i].poll()})"
                print(msg)
                if active_proc == 0:
                    break
            dt = time.time() - t1
            print(f"Total elapsed time: {dt} seconds")
            # update timestring for next file
            self.timestamp = datetime.now().strftime('%y_%m_%d__%H_%M_%S__')
        parserfile_obj.close()

        # Stop the motor if needed
        if not self.observer_client:
            for instance in self.active_instances:
                if instance['name'] == 'Radiometer' and self.stop_motor:
                    print("Stopping motor")
                    self.motor = MotorControl(self.server_ip, self.server_port)
                    self.motor.send_stop()
                    self.motor.disconnect()
                elif not self.stop_motor:
                    print("Motor is configured to NOT stop.")

        # Launch the parser
        self.sendto_parser(parserfile_name)


if __name__ == '__main__':
    # Create a log
    log = create_log(
        filename = "Client_ACQSystem.log",
        title = "ACQSystem Client - DAIS 2.0",
        timestamp = True
    )

    # Read the config file
    config_path = configs_path / 'client.json'
    with open(config_path, 'r') as f:
        config = json.load(f)

    client = MasterClient(config, log)
    client.acquire()