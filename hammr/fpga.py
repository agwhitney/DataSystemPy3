"""
Only deals with the radiometer. py2 uses implicit ordering with lists, and I am actively changing those to dictionaries
(XB confirms this is the idea he prefers as well). Note that py2 used a set for keys = {'MW', 'MMW', 'SND'} and this was
unordered. This consistently returns with the order set(['MW', 'SND', 'MMW']), and a key was made to adjust and correct
the order. It was weird and confusing and I confirmed with XB that the config should in fact not be swapped.

In general (i.e., in the config) I've brought keys to lowercase. 
"""
from dataclasses import dataclass, field
from logging import Logger
import json
import socket
import struct

from utils import write_to_log

@dataclass
class FPGAChannelConfig:
    """Channel specific configuration values used by the FPGA."""
    off : int
    bytes_per_datagram : int
    header : list


@dataclass
class FPGAConfig:
    """Configuration values used by the FPGA"""
    activate   : int
    deactivate : int
    reset      : int
    disconnect : int
    counter    : int  # Something to do with debugging
    nocounter  : int
    motorbase  : int  # Start and Stop are added to this value
    motorstart : int
    motorstop  : int
    amr : FPGAChannelConfig
    mmw : FPGAChannelConfig
    snd : FPGAChannelConfig

    @classmethod
    def from_json(cls, filename) -> 'FPGAConfig':
        with open(filename, 'r') as f:
            config = json.load(f)
        amr : dict = config['amr']
        mmw : dict = config['mmw']
        snd : dict = config['snd']

        return cls(
            activate = config['activate'],
            deactivate = config['deactivate'],
            reset = config['reset'],
            disconnect = config['disconnect'],
            counter = config['counter'],
            nocounter = config['no_counter'],
            motorbase = config['motor']['base'],
            motorstart = config['motor']['start'],
            motorstop = config['motor']['stop'],
            amr = FPGAChannelConfig(
                off=amr['off'], bytes_per_datagram=amr['bytes_per_datagram'], header=amr['datagram_header']
            ),
            mmw = FPGAChannelConfig(
                off=mmw['off'], bytes_per_datagram=mmw['bytes_per_datagram'], header=mmw['datagram_header']
            ),
            snd = FPGAChannelConfig(
                off=snd['off'], bytes_per_datagram=snd['bytes_per_datagram'], header=snd['datagram_header']
            ),
        )



class FPGA:
    inst = {'ac': 0, 'fr': 1, 'lt': 12}
    inst_base = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11]  # py2 Inst_S#, with # = 0--9.
    

    def __init__(
        self,
        systemconfig: dict,
        fpgaconfig: FPGAConfig,
        log: Logger | None
    ):
        self.fpgaconfig = fpgaconfig
        self.log = log
        self.client_socket: socket.socket  # Set in init via connect()
        self.channel_map = {'mw': self.fpgaconfig.amr, 'mmw': self.fpgaconfig.mmw, 'snd': self.fpgaconfig.snd}

        # Load a bunch from the config (which is just the radiometer config, and really just a subset of that)
        self.tcp_buffer_size = systemconfig['characteristics']['configuration']['buffer_length']
        self.ip = systemconfig['characteristics']['configuration']['ip']
        self.port = systemconfig['characteristics']['configuration']['port']
        
        # py2 these were lists. `length` and `slot` were one-dimensional and accessed using multiples of 10
        self.activated = {}
        self.counter = {}
        self.int_time = {}
        self.sequence_length = {}
        self.length = {}
        self.slot = {}
        for key in self.channel_map:
            cfg = systemconfig['characteristics'][key]

            self.int_time[key] = cfg['integration_time_ms']
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

        write_to_log(self.log, f"Init FPGA: IP {self.ip} Port {self.port} Buffer size {self.tcp_buffer_size}")
        self.connect(self.ip, self.port)


    @staticmethod
    def get_denominator(int_time_ms, fmax_khz=50000, ratio_max=16777215) -> int:  # fmax kHz
        ftarget = 2 / int_time_ms  # range 25 kHz - 2.9 Hz
        ratio = int(fmax_khz / ftarget)
        return min(ratio, ratio_max)  # Intersects at about int_time = 671 ms


    def connect(self, ip: str, port: int) -> None:
        tcp_address = (ip, port)
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.settimeout(3)  # AGW hoping this avoids lockout on interrupts if the ip is wrong for some reason
        self.client_socket.connect(tcp_address)
        write_to_log(self.log, f"TCP/IP connected @ {tcp_address}")


    def estimated_data_throughput(self) -> None:
        estimate = 0
        for key, channelcfg in self.channel_map.items():
            if self.activated[key]:
                estimate += channelcfg.bytes_per_datagram / self.int_time[key]
                write_to_log(self.log, f"{key} channels activated -> int_time = {self.int_time[key]} ms")
        
        write_to_log(self.log, f"Estimated data throughput: {estimate} kB")
        if estimate > 400:
            write_to_log(self.log, "Data throughput should be <400 kBps. This acquistiion could crash.", level='warn')
            write_to_log(self.log, "DO NOT EXCEED 420 kBps, or you will need to reboot the acquisition system!", level='warn')


    def configure(self) -> None:
        write_to_log(self.log, "Configuring the FPGA.")
        for key, channelcfg in self.channel_map.items():
            write_to_log(self.log, f"Sending configuration for {key}. OFF value = {channelcfg.off}")

            active_ch = self.fpgaconfig.activate if self.activated[key] else self.fpgaconfig.deactivate
            active_ch += self.fpgaconfig.counter if self.counter[key] else 0  # False case is active_ch += 0

            int_time_ch = self.int_time[key]
            inst_seq = [i + channelcfg.off for i in self.inst_base]
            inst_ac = self.inst['ac'] + channelcfg.off
            inst_fr = self.inst['fr'] + channelcfg.off
            inst_lt = self.inst['lt'] + channelcfg.off

            length_ch = self.length[key]
            sequence_ch = self.slot[key]
            sequencelength_ch = self.sequence_length[key]

            write_to_log(self.log, 
                f"{active_ch} - {int_time_ch} - {inst_seq} - {inst_ac} - {inst_fr} - {inst_lt} - {length_ch} - {sequence_ch} - {sequencelength_ch}"
            )
            self.configure_channel(
                activated=active_ch, int_time=int_time_ch,
                inst_ac=inst_ac, inst_fr=inst_fr, inst_lt=inst_lt, inst_seq=inst_seq,
                sequence=sequence_ch, length=length_ch,  sequence_length=sequencelength_ch
            )
        write_to_log(self.log, "Finished configuring FPGA.")


    def configure_channel(
        self, activated, int_time,
        inst_seq, inst_ac, inst_fr, inst_lt,
        sequence, length, sequence_length
    ) -> None:
        self.send_and_recv(activated, inst_ac, 0)
        
        int_val = self.get_denominator(int_time)
        self.send_and_recv(int_val, inst_fr, 0)

        self.configure_sequence(inst_seq, sequence, length)
        self.send_and_recv(sequence_length, inst_lt, 0)


    def configure_sequence(self, inst_seq, sequence, length) -> None:
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
        write_to_log(self.log, f"Sent {send}. Instruction: {inst} Slot value: {container}. Received {recv}.", level='debug')


    def reset_hardware(self) -> None:
        self.send_and_recv(self.fpgaconfig.reset, 0, 1)


    def disconnect_tcp(self) -> None:
        write_to_log(self.log, "Sending TCP/IP disconnect sequence to FPGA.")
        self.send_and_recv(self.fpgaconfig.disconnect, 0, 1)
        self.client_socket.close()
        write_to_log(self.log, "FPGA socket closed.")


    def motor_control(self, command: int) -> None:
        self.send_and_recv(self.fpgaconfig.motorbase + command, 0, 1)


    def start_acquisition(self) -> None:
        self.send_and_recv(0, 0, 1)



if __name__ == '__main__':
    from filepaths import PATH_TO_CONFIGS

    fpgaconfig = FPGAConfig.from_json(PATH_TO_CONFIGS / 'fpga.json')
    
    with open(PATH_TO_CONFIGS / 'system.json') as f:
        data = json.load(f)['radiometer']

    f = FPGA(data, fpgaconfig, None)
    print('starting motor')
    f.motor_control(f.fpgaconfig.motorstart)
    input("press enter to send STOP")
    f.motor_control(f.fpgaconfig.motorstop)

    f.disconnect_tcp()

