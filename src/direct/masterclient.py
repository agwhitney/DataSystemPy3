"""
py2 has a BasicClient protocol and factory, which don't get used. I've omitted them.
The log was implemented but not used. Most print statements could probably also get logged.
"""
import json
import logging
import time

from datetime import datetime

from motorcontrol import MotorControl


class MasterClient():
    genericclient = 'genericclient.py'

    def __init__(self, config, log):
        self.log = log
        
        # Parse the config
        self.server_ip : str = config['master_server']['ip']
        self.server_port : int = config['master_server']['port']
        self.observer_client : bool = config['observer']['active']

        self.context : str = config['context']
        self.instances : list = config['instances']  # Not in py2 but trims a lot of typing
        self.file_acqtime : int = config['acquisition_time']['file_time']

        # Additional variables
        self.delay = 3  # used for sleep timer
        self.timestamp = datetime.now().strftime('%y_%m_%d__%H_%M_%S__')  # This will be slightly behind the log
        

    def get_server_config(self):
        """
        This gets server config info from motorcontrol.py, which I believe actually does connect
        to the FGPA via TCP/IP. As a bonus, it has the same weird indexing hack that FPGA uses.
        Realistically... why pass the data? Why not just call it again?
        """
        self.motor = MotorControl(self.server_ip, self.server_port)
        system_config = self.motor.get_systemconfig()  # AGW changed this function to return rather than keep
        filename = self.timestamp + self.context + "_ServerInformation.bin"
        with open(filename, 'w') as f:
            f.write(json.dumps(system_config))

        for instrument in system_config.values():
            print(f"## SERVER: {instrument['name']} Active: {instrument['active']}")
            if instrument['name'] == 'Radiometer':
                # It does the bad indexing thing here, with both keys.
                # At least this whole block is just for logging, I think.
                # TODO check config varnames.
                mapkey = ('mw', 'mmw', 'snd')
                badmap = {'mw':'mw', 'mmw':'snd', 'snd':'mmw'}
                bytesPerDatagram = {'mw': 22, 'mmw': 14, 'snd': 38}
                value = []
                length = []
                int_time = {}
                activated = {}
                meaning = []
                seq_length = {}
                for key in mapkey:
                    badkey = badmap[key]  # AGW what the fuck is this
                    int_time[key] = instrument['characteristics'][key]['integration_time']
                    activated[key] = instrument['characteristics'][key]['activated']
                    seq_length[key] = instrument['characteristics'][key]['sequence']['length']
                    # Below should fail because of badkey
                    print(f"## {key} -> Active: {activated[badkey]} Ts = {int_time[badkey]} ms")
                    if activated[badkey]:
                        data_throughput = bytesPerDatagram[badkey] / int_time[badkey]
                        print("## Running Sequence")
                        for i in range(seq_length[badkey]):
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
        

    def acquire(self):
        ...


if __name__ == '__main__':
    # Create a log
    log_filename = datetime.now().strftime('%y_%m_%d__%H_%M_%S__') + "Client_ACQsystem.log"  # TODO needs the folder path
    logging.basicConfig(
        level = logging.DEBUG,
        format = "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        filename = log_filename,
        filemode = 'a'
    )
    log = logging.getLogger('ACQsystem Client - DAIS 2.0')
    log.addHandler(logging.StreamHandler())  # AGW logged events are also printed
    log.info('Welcome to ACQsystem Client - DAIS 2.0')

    # Read the config file
    config_filename = 'client.json'
    with open(config_filename, 'r') as f:
        config = json.load(f)

    client = MasterClient(log, config)
    client.acquire()