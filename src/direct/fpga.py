"""
I believe this script is important and somewhat low-level,
in addition to the implicit indexing of things.

Only deals with the radiometer. A change I'm making is to have more dictionaries.
"""
import socket
import struct


class ConfigFPGA():
    # Defined parameters
    # py2 had mapkey below as a SET and also In = {'MW':0, 'MMW':2, 'SND':1}. It then later
    # used In as an index that DOES NOT AGREE with the order in the set. But sets don't keep order --
    # so why was it set that way? If the set is initialized as mw, mmw, snd, does it keep that? 
    # What dafuq?
    mapkey = ('MW', 'MMW', 'SND')
    header = {'MW': 85, 'MMW': 87, 'SND': 93}  # 'U' #85; 'W' #87 ']' #93
    OFF = {'MW': 0, 'MMW': 16, 'SND': 32}
    bytesPerDatagram = {'ARM': 22, 'ACT': 14, 'SND': 38}

    activate_val = 15
    deactivate_val = 0
    counter_val = 240
    nocounter_val = 0

    start_motor = 170
    stop_motor = 85
    
    inst = {'ac': 0, 'fr': 1, 'lt': 12}
    inst_s = (2, 3, 4, 5, 6, 7, 8, 9, 10, 11)  # py2 Inst_S#

    def __init__(self, config, log):
        self.log = log
        self.client_socket = None  # Set in connect()

        # load a bunch from the config
        self.tcp_buffer_size = config['characteristics']['configuration']['buffer_length']
        self.ip = config['characteristics']['configuration']['ip']
        self.port = config['characteristics']['configuration']['port']
        
        # py2 these were lists and 
        self.int_time = {}
        self.activated = {}
        self.counter = {}
        self.sequence_length = {}
        self.length = {}
        self.slot = {}
        for key in self.mapkey:
            cfg = config['characteristics'][key]
            self.int_time[key] = cfg['integration_time']
            self.activated[key] = cfg['activated']
            self.counter[key] = cfg['counter']
            self.sequence_length = cfg['sequence']['length']
            for i in range(10):
                slot = cfg['sequence'][f'slot{i}']
                self.length[key][str(i)] = slot['length']
                vals = slot['value']
                self.slot[key][str(i)] = sum(j*k for j,k in zip(vals, [16,8,4,2,1]))

        self.log.info(f"{self.ip} - {self.port} - {self.tcp_buffer_size} {type(self.ip)}")  # type(str) is str???
        self.connect()


    def connect(self):
        tcp_address = (self.ip, self.port)
        self.client_socket = socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect(tcp_address)
        self.log.info(f"TCP/IP connected @ {tcp_address} ---> ;^)")