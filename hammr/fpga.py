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
    header = {'mw': 85, 'mmw': 87, 'snd': 93}  # 'U' #85; 'W' #87 ']' #93  Used in .h5 structure?
    offmap = {'mw': 0, 'mmw': 16, 'snd': 32}
    bpd = {'arm': 22, 'act': 14, 'snd': 38}  # "Bytes per Datagram" py2 this is ordered ARM, SND, ACT
    bpd_remap = {'mw': bpd['arm'], 'mmw': bpd['act'], 'snd': bpd['snd']}

    ACTIVATE_VALUE = 15
    DEACTIVATE_VALUE = 0
    COUNTER_VALUE = 240
    NOCOUNTER_VALUE  = 0

    # These constants are called in masterserver.py to FPGA.motor_control
    START_VALUE = 170
    STOP_VALUE = 85
    
    inst = {'ac': 0, 'fr': 1, 'lt': 12}
    inst_base = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11]  # py2 Inst_S#, with # = 0--9.


    def __init__(self, config, log):
        self.log = log
        self.client_socket: socket.socket  # Set in init via connect()

        # load a bunch from the config (which is just the radiometer config, and really just a subset of that)
        self.tcp_buffer_size = config['characteristics']['configuration']['buffer_length']
        self.ip = config['characteristics']['configuration']['ip']
        self.port = config['characteristics']['configuration']['port']
        
        # py2 these were lists. `length` and `slot` were one-dimensional and accessed using multiples of 10
        self.activated = {}
        self.counter = {}
        self.int_time = {}
        self.sequence_length = {}
        self.length = {}
        self.slot = {}
        for key in self.mapkey:
            cfg = config['characteristics'][key]

            self.int_time[key] = cfg['integration_time']
            self.activated[key] = cfg['active']
            self.counter[key] = cfg['counter']
            self.sequence_length[key] = cfg['sequence']['length']

            _length = []
            _slot = []
            for i in range(10):
                slot = cfg['sequence'][f'slot{i}']
                vals = slot['value']
                _length.append(slot['length'])
                _slot.append(sum(j*k for j,k in zip(vals, [16,8,4,2,1])))  # powers of 2
            self.length[key] = _length
            self.slot[key] = _slot

        self.log.info(f"Init FPGA: IP {self.ip} Port {self.port} Buffer size {self.tcp_buffer_size}")
        self.connect(self.ip, self.port)


    @staticmethod
    def get_denominator(int_time):
        ratio_max = 16777215
        fmax = 50000  # kHz
        ftarget = 2 / int_time  # range 25 kHz - 2.9 Hz
        ratio = int(fmax / ftarget)  # int returns floor
        return min(ratio, ratio_max)  # Intersects at about int_time = 671 ms


    def connect(self, ip: str, port: int):
        tcp_address = (ip, port)
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.settimeout(3)  # AGW hoping this avoids lockout on interrupts if the ip is wrong for some reason
        self.client_socket.connect(tcp_address)
        self.log.info(f"TCP/IP connected @ {tcp_address}")


    def estimated_data_throughput(self):
        estimate = 0
        for key in self.mapkey:
            if self.activated[key]:
                estimate += self.bpd_remap[key] / self.int_time[key]
                self.log.info(f"{key} channels activated -> int_time = {self.int_time[key]} ms")
        
        self.log.info(f"Estimated data throughput: {estimate} kB")
        if estimate > 400:
            self.log.warning("Data throughput should be <400 kBps. This acquistiion could crash.")
            self.log.warning("DO NOT EXCEED 420 kBps, or you will need to reboot the acquisition system!")


    def configure(self):
        self.log.info("Configuring the FPGA.")
        for key in self.mapkey:
            self.log.info(f"Sending configuration for {key}. OFF value = {self.offmap[key]}")

            active_ch = self.ACTIVATE_VALUE if self.activated[key] else self.DEACTIVATE_VALUE
            active_ch += self.COUNTER_VALUE if self.counter[key] else 0  # Reads a little funny, but the False case is active += 0

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
        self.send_and_recv(activated, inst_ac, 0)
        
        int_val = self.get_denominator(int_time)
        self.send_and_recv(int_val, inst_fr, 0)

        self.configure_sequence(inst_seq, sequence, length)
        self.send_and_recv(sequence_length, inst_lt, 0)


    def configure_sequence(self, inst_seq, sequence, length):
        for i in range(10):
            self.send_and_recv(sequence[i] + 256*length[i], inst_seq[i], 0)


    def send_instruction(self, container, inst, processor_order) -> bytes:
        """Sends a command. Returns it for debugging."""
        data = struct.pack('>bbbI', 10, processor_order, inst, container)  # 10 -> \n
        self.client_socket.send(data)
        return data


    def recv_instruction(self) -> bytes:
        """Receives data. Returns it for debugging."""
        data = self.client_socket.recv(self.tcp_buffer_size)
        return data


    def send_and_recv(self, container, inst, processor_order) -> None:
        """Combined send and receive. Prints returns for debugging."""
        send = self.send_instruction(container, inst, processor_order)
        recv = self.recv_instruction()
        self.log.info(f"Sent {send}. Instruction: {inst} Slot value: {container}. Received {recv}.")



    def reset_hardware(self):
        self.send_and_recv(16777216, 0, 1)


    def disconnect_tcp(self):
        self.log.info("Sending TCP/IP disconnect sequence to FPGA.")
        self.send_and_recv(33554432, 0, 1)
        self.client_socket.close()
        self.log.info("FPGA socket closed.")


    def motor_control(self, control):
        self.send_and_recv(50331648 + control, 0, 1)


    def start_acquisition(self):
        self.send_and_recv(0, 0, 1)


if __name__ == '__main__':
    import json
    from utils import create_log
    from filepaths import PATH_TO_CONFIGS
    with open(PATH_TO_CONFIGS / 'system.json') as f:
        data = json.load(f)['radiometer']
    log = create_log('dummy.log', "Dummy")

    f = FPGA(data, log)
    f.reset_hardware()
    print()