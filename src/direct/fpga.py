"""
Only deals with the radiometer. py2 uses implicit ordering with lists, and I am actively changing those to dictionaries
(XB confirms this is the idea he prefers as well). Note that py2 used a set for keys = {'MW', 'MMW', 'SND'} and this was
unordered. This consistently returns with the order set(['MW', 'SND', 'MMW']), and a key was made to adjust and correct
the order. It was weird and confusing and I confirmed with XB that the config should in fact not be swapped.

In general (i.e., in the config) I've brought keys to lowercase. 
"""
import socket
import struct


class FPGA():
    # Defined parameters
    mapkey = ('mw', 'mmw', 'snd')
    header = {'mw': 85, 'mmw': 87, 'snd': 93}  # 'U' #85; 'W' #87 ']' #93  # Unused
    offmap = {'mw': 0, 'mmw': 16, 'snd': 32}
    bytesPerDatagram = {'arm': 22, 'act': 14, 'snd': 38}  # py2 this is ordered ARM, SND, ACT. bytes_remap = {'mw': 22, 'mmw': 14, 'snd': 38}

    activate_val = 15
    deactivate_val = 0
    counter_val = 240
    nocounter_val = 0

    start_motor = 170  # Unused
    stop_motor = 85  # Unused
    
    inst = {'ac': 0, 'fr': 1, 'lt': 12}
    inst_base = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11]  # py2 Inst_S#, with # = 0--9.


    @staticmethod
    def get_denominator(int_time):
        ratio_max = 16777215
        fmax = 50000  # Units of kHz
        ftarget = 2 * (1 / int_time)
        ratio = int(fmax / ftarget)  # This was in py2 also, though in py2 integers divide to an integer.
        return max(ratio, ratio_max)


    def __init__(self, config, log):
        self.log = log
        self.client_socket: socket.socket = None  # Set in init via connect()

        # load a bunch from the config
        self.tcp_buffer_size = config['characteristics']['configuration']['buffer_length']
        self.ip = config['characteristics']['configuration']['ip']
        self.port = config['characteristics']['configuration']['port']
        
        # py2 these were lists. `length` and `slot` were one-dimensional and accessed using multiples of 10
        self.int_time = {}
        self.activated = {}
        self.counter = {}
        self.sequence_length = {}
        self.length = {}
        self.slot = {}
        for key in self.mapkey:
            cfg = config['characteristics'][key]

            self.int_time[key] = cfg['integration_time']
            self.activated[key] = cfg['active']
            self.counter[key] = cfg['counter']
            self.sequence_length = cfg['sequence']['length']

            _length = []
            _slot = []
            for i in range(10):
                slot = cfg['sequence'][f'slot{i}']
                vals = slot['value']
                _length.append(slot['length'])
                _slot.append(sum(j*k for j,k in zip(vals, [16,8,4,2,1])))  # powers of 2
            self.length[key] = _length
            self.slot[key] = _slot

        self.log.info(f"{self.ip} - {self.port} - {self.tcp_buffer_size} {type(self.ip)}")  # type(str) is str???
        self.connect()


    def connect(self):
        tcp_address = (self.ip, self.port)
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect(tcp_address)
        self.log.info(f"TCP/IP connected @ {tcp_address} ---> ;^)")


    def estimated_data_throughput(self):
        estimate = 0
        for key in self.mapkey:
            bytes_remap = {'mw': 22, 'mmw':14, 'snd':38}  # this is `self.bytesPerDatagram` adjusted for explicit keying

            if self.activated[key]:
                estimate += bytes_remap[key] / self.int_time[key]
                self.log.info(f"{key} channels activated -> int_time = {self.int_time[key]} ms")
        
        self.log.info(f"Estimated data throughput: {estimate} kB")
        if estimate > 400:
            self.log.info("Warning --> Data throughput should be <400 kBps. This acquistiion could crash.")
            self.log.info("Warning --> DO NOT EXCEED 420 kBps, or you will need to reboot the acquisition system!")


    def configure(self):
        self.log.info("Configuring the FPGA.")
        for key in self.mapkey:
            self.log.info(f"Sending configuration for {key}. OFF value = {self.offmap[key]}")

            active_ch = self.activate_val if self.activated[key] else self.deactivate_val
            active_ch += self.counter_val if self.counter[key] else 0  # Reads a little funny, but the False case is active += 0

            int_time_ch = self.int_time[key]
            inst_seq = [i + self.offmap[key] for i in self.inst_base]
            inst_ac = self.inst['ac'] + self.offmap[key]
            inst_fr = self.inst['fr'] + self.offmap[key]
            inst_lt = self.inst['lt'] + self.offmap[key]

            length_ch = self.length[key]
            sequence_ch = self.slot[key]
            sequencelength_ch = self.sequence_length[key]

            self.log.info(
                f"{active_ch} - {int_time_ch} - {inst_seq} - {inst_ac} - {inst_fr} - {inst_lt} - {length_ch} - {sequence_ch} - {sequencelength_ch}"
            )
            self.configure_channel(
                activated=active_ch, int_time=int_time_ch,
                inst_ac=inst_ac, inst_fr=inst_fr, inst_lt=inst_lt, inst_seq=inst_seq,
                sequence=sequence_ch, length=length_ch,  sequence_length=sequencelength_ch
            )
        self.log.info("Finished configuring FPGA.")


    def configure_channel(self, activated, int_time, inst_seq, inst_ac, inst_fr, inst_lt, sequence, length, sequence_length):
        data2send = self.send_instruction(activated, inst_ac, 0)
        self.recv_instruction(data2send)
        
        int_val = self.get_denominator(int_time)
        data2send = self.send_instruction(int_val, inst_fr, 0)
        self.recv_instruction(data2send)

        self.configure_sequence(inst_seq, sequence, length)
        data2send = self.send_instruction(sequence_length, inst_lt, 0)
        self.recv_instruction(data2send)


    def configure_sequence(self, inst_seq, sequence, length):
        for i in range(10):
            data2send = self.send_instruction(sequence[i] + 256*length[i], inst_seq[i], 0)
            self.recv_instruction(data2send)


    def send_instruction(self, container, inst, processor_order):
        # AGW I think `inst` is instruction, which means maybe it is throughout
        porder = struct.pack('<b', processor_order)
        value = struct.pack('>I', container)
        instruction = struct.pack('<b', inst)
        flusher = struct.pack('<b', 10)
        data2send = flusher + porder + instruction + value

        self.client_socket.send(data2send)
        self.log.info(f"Sending instruction: {instruction} Slot value: {container}")
        return data2send  # Only seems to be used in configure_sequence


    def recv_instruction(self, data):
        # py2 has some print-checks on this received data
        self.client_socket.recv(self.tcp_buffer_size)

    
    def reset_hardware(self):
        self.send_instruction(16777216, 0, 1)
        self.recv_instruction(self.tcp_buffer_size)


    def disconnect_tcp(self):
        self.log.info("Sending TCP/IP disconnect sequence")
        self.send_instruction(33554432, 0, 1)
        self.recv_instruction(self.tcp_buffer_size)
        self.client_socket.close()


    def motor_control(self, control):
        self.send_instruction(50331648)
        self.recv_instruction(self.tcp_buffer_size)


    def start_acquisition(self):
        self.send_instruction(0, 0, 1)
