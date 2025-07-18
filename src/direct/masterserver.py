import json
import logging

from datetime import datetime
from twisted.internet import protocol, reactor
from subprocess import Popen

from fpga import FPGA
from filepaths import configs_path, configstmp_path, logs_path, genericserver, CONTROL_SERVER_PORT


class TCPHandler(protocol.Protocol):
    """
    AGW I think this protocol only interacts between the FPGA and motor. I think the master server is set up,
    and MotorControl connects to that port using socket.
    """
    # AGW self.transport and therefore presumably self.factory are set in makeConnection(), so this doesn't work
    # def __init__(self):
    #     self.factory.log.info("Creating an online control server instance")
    #     for i, p in enumerate(self.factory.processes):
    #         self.factory.log.debug(f"Process number {i} ID: {p.pid}\n")
        
    
    def connectionMade(self):
        self.factory.log.info(
            f"New TCP client received from {self.transport.getPeer()} - Instance: {self}"
        )
        self.factory.clients.append(self)
        # Moved from init
        for i, p in enumerate(self.factory.processes):
            self.factory.log.debug(f"Process number {i} ID {p.pid}")


    def dataReceived(self, data: bytes) -> None:
        self.factory.log.info(
            f"Command received from {self.transport.getPeer()} - {data}"
        )
        # AGW I think this is handled (or passed between) the MotorControl script
        match data.decode():
            case 'STOP':  # AGW py2 labels this is not working, with lots of !
                # Stops all processes
                msg = "STOP -> Running processes are:\n"
                for i, p in enumerate(self.factory.processes):
                    msg += f"Process #{i} -> ID: {p.pid}\n"
                print(msg)
                self.transport.write(msg.encode())
                msg += "Status:\n"
                for i, p in enumerate(self.factory.processes):
                    msg += f"Process #{i} -> ID: {p.poll()}\n"
                print(msg)
                self.transport.write(msg.encode())
                for p in self.factory.processes:
                    if p.poll() != 1:
                        p.terminate()
                msg = "Status after termination:\n"
                for i, p in enumerate(self.factory.processes):
                    msg += f"Process #{i} -> ID: {p.poll()}\n"
                print(msg)
                self.transport.write(msg.encode())

            case 'INFO':  # AGW py2 same as STOP, but commented out.
                msg = "INFO -> Running processes are:\n"
                self.transport.write(msg.encode())
                for i, p in enumerate(self.factory.processes):
                    msg += f"Process #{i} -> ID: {p.pid}\n"
                print(msg)
                # AGW below here doesn't make sense to me. Maybe it was for testing. It can probably be removed.
                self.transport.write(msg.encode())
                msg += "Status:\n"
                print(msg)
                msg += str(self.processes[0])
                print(msg)
                # AGW i and p are out of scope, but will probably have the last values from above
                msg += f"Process #{i} -> STOPPED? -> {p.poll()} -> Says -> #"
                print(msg)
                self.transport.write(msg.encode())

            case 'SYST':
                print("Sending configuration file to client.")
                self.transport.write(json.dumps(self.factory.system_config).encode())
            
            case 'MSTART':
                print("Starting motor")
                fpga = FPGA(self.factory.motor_instr, self.factory.log)
                fpga.MotorControl(fpga.StartMotor)
                print("Sending START to motor")
                fpga.DisconnectTCP()
                self.transport.write("Starting motor".encode())
            
            case 'MSTOP':
                print("Stopping motor")
                fpga = FPGA(self.factory.motor_instr, self.factory.log)
                fpga.MotorControl(fpga.StopMotor)
                print("Sending STOP to motor")
                fpga.DisconnectTCP()
                self.transport.write("Stopping motor".encode())



    def connectionLost(self, reason=None) -> None:
        self.factory.log.error(
            f"Connection lost from {self.transport.getPeer()} - Reason: {reason}"
        )
        self.factory.log.info(
            f"Removing TCP client {self} at {self.transport.getPeer()}"
        )
        self.factory.clients.remove(self)



class TCPHandlerFactory(protocol.Factory):
    protocol = TCPHandler

    def __init__(self, log, processes, motor_instr, system_config):
        # AGW py2 set protocol params here, but this is the preferred way.
        self.clients = []
        self.log = log
        self.processes = processes
        self.motor_instr = motor_instr
        self.system_config = system_config


class MasterServer():
    def __init__(self, log, system_config):
        """
        This loads the config and starts servers for each instrument as subprocesses.
        """
        self.log = log
        self.config = system_config

        self.instr_count = len(self.config)

        # These are set in the dumping section below
        self.motor_instr_config = {}  # py2 motor_instr
        self.instr_config_filenames = []  # py2 fname
        self.instr_names = []  # py2 InstrumentName  # not used
        self.instr_active = []  #py2 active

        # Parse config. Also copies sub-configs to files
        print("---------------------------------")
        timestamp = datetime.now().strftime('%y_%m_%d__%H_%M_%S__')
        for cfg in self.config.values():
            print("---------------------------------")
            if cfg['name'] == 'Radiometer':
                self.motor_instr_config = cfg  # AGW updated json config this includes connection info
            self.instr_names.append(cfg['name'])
            self.instr_active.append(cfg['active'])
            
            filepath = configstmp_path / f"{timestamp}{cfg['name']}.json"
            self.instr_config_filenames.append(filepath)
            with open(filepath, 'w') as f:
                f.write(json.dumps(cfg))  # unchanged sub-config
        print("---------------------------------")
        self.start_servers()

    
    def start_servers(self):
        tcp_port = CONTROL_SERVER_PORT
        processes = []
        server_count = 0
        
        for i in range(self.instr_count):
            print(self.instr_config_filenames[i], self.instr_active[i])
            if self.instr_active[i]:
                p = Popen(['.venv/Scripts/python', genericserver, self.instr_config_filenames[i]], shell=False)
                print(f"Instrument in the configuration file: {i} Active instrument: {server_count} {self.instr_config_filenames[server_count]} started, Pid: {p.pid}")
                processes.append(p)
                server_count += 1
        print("---------------------------------")
        self.log.info("Starting online control server -- FYI: the script won't come back while it's running!")
        factory = TCPHandlerFactory(self.log, processes, self.motor_instr_config, self.config)
        reactor.listenTCP(tcp_port, factory)
        reactor.run()        


if __name__ == '__main__':
    # Create a log
    log_filename = datetime.now().strftime('%y_%m_%d__%H_%M_%S__') + "Server_ACQsystem.log"
    logging.basicConfig(
        level = logging.DEBUG,
        format = "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        filename = logs_path / log_filename,
        filemode = 'a'
    )
    log = logging.getLogger('ACQsystem - DAIS 2.0')
    log.addHandler(logging.StreamHandler())  # AGW logged events are also printed
    log.info('Welcome to ACQsystem - DAIS 2.0')

    # Read the config file
    config_filepath = configs_path / 'system.json'
    with open(config_filepath, 'r') as f:
        system_config = json.load(f)
    MasterServer(log, system_config)