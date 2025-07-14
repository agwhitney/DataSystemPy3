import json
import logging


class MasterClient():
    generic_client = 'genericclient.py'

    def __init__(self, log, client_config):
        self.log= log
        self.config = client_config
        
        # vars from config
        self.count_clients : int = len(self.client['instances'])
        self.acqtime : int = self.config['acquisition_time']['file_time']
        self.count_files : int = self.config['acquisition_time']['total_files']
        self.context : str = self.config['context']
        self.observer_client : bool = self.config['observer']['active']

        # other vars
        self.C = []  # I think this is the motor connection
        self.instance_config_filename = []
        self.processes = []
        self.client_instruments = []
        self.count_operational_clients = 0
        self.observing_delay = 3

        self.count_thermistors = 0
        self.count_gps = 0
        self.count_radiometer = 0

    
    def get_server_config(self):
        ...


    def acquire(self):
        ...


if __name__ == '__main__':
    # Create a log
    log_filename = 'todo-datetime.log'  #TODO see py2 line 347
    logging.basicConfig(
        level = logging.DEBUG,
        format = "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        filename = log_filename,
        filemode = 'a'
    )
    log = logging.getLogger('ACQsystem - DAIS 2.0')
    log.addHandler(logging.StreamHandler())  # AGW logged events are also printed
    log.info('Welcome to ACQsystem - DAIS 2.0')

    # Read the config
    config_filename = 'client.json'
    with open(config_filename, 'r') as f:
        config = json.load(f)

    # Start client and data acquisition
    client = MasterClient(log, config)
    client.acquire()