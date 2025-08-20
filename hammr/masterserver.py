import json
import logging  # type checking

from datetime import datetime
from twisted.internet import protocol, reactor
from subprocess import Popen

from create_log import create_log
from fpga import FPGA
from filepaths import configs, configs_path, configstmp_path, generic_server_script, CONTROL_SERVER_PORT


class TCPHandler(protocol.Protocol):
    """
    AGW I think this protocol only interacts between the FPGA and motor. I think the master server is set up,
    and MotorControl connects to that port using socket. Instruments are controlled using the protocols in
    instruments.py.
    """
    def connectionMade(self):
        self.factory.log.info(
            f"MasterServer: New TCP client received from {self.transport.getPeer()} - Instance: {self}"
        )
        self.factory.clients.append(self)
        # Moved from init
        for i, p in enumerate(self.factory.processes):
            self.factory.log.debug(f"Process number {i} ID {p.pid}")


    def dataReceived(self, data: bytes) -> None:
        self.factory.log.info(
            f"MasterServer: Command received from {self.transport.getPeer()} - {data}"
        )
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
                print("Sending START to motor")
                fpga.MotorControl(fpga.StartMotor)
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
            f"MasterServer: Connection lost from {self.transport.getPeer()} - Reason: {reason}"
        )
        self.factory.log.info(
            f"MasterServer: Removing TCP client {self} at {self.transport.getPeer()}"
        )
        self.factory.clients.remove(self)



class TCPHandlerFactory(protocol.Factory):
    protocol = TCPHandler

    def __init__(self, log: logging.Logger, processes: list, motor_instr: dict, system_config: dict):
        # AGW py2 set protocol params here, but this is the preferred way.
        self.clients = []
        self.log = log
        self.processes = processes
        self.motor_instr = motor_instr
        self.system_config = system_config


class MasterServer():
    def __init__(self, system_config: dict, log: logging.Logger):
        """
        This loads the config and starts servers for each instrument as subprocesses.
        """
        self.log = log
        self.config = system_config

        # Instrument configs are extracted from the system config
        print("---------------------------------")
        timestamp = datetime.now().strftime('%y_%m_%d__%H_%M_%S__')
        for cfg in self.config.values():
            print("---------------------------------")
            filepath = configstmp_path / f"{timestamp}{cfg['name']}.json"
            cfg['filepath'] = str(filepath)
            with open(filepath, 'w') as f:
                f.write(json.dumps(cfg))  # Sub-config is saved with one change (filepath added)
        print("---------------------------------")

        # Start instrument subservers
        processes = self.start_servers()

        # Start master server
        self.log.info("Starting online control server -- FYI: the script won't come back while it's running!")
        factory = TCPHandlerFactory(self.log, processes, self.config['radiometer'], self.config)
        reactor.listenTCP(CONTROL_SERVER_PORT, factory)
        reactor.run()        

    
    def start_servers(self) -> list:
        processes = []
        server_count = 0
        
        # Subprocess servers for each instrument.
        for instrument in self.config.values():
            print(instrument['filepath'], instrument['active'])
            if instrument['active']:
                p = Popen(['.venv/Scripts/python', generic_server_script, instrument['filepath']], shell=False)
                self.log.info(f"Instrument in the configuration file: {instrument['name']} Active instrument: {server_count} {instrument['filepath']} started, Pid: {p.pid}")
                processes.append(p)
                server_count += 1
        print("---------------------------------")
        return processes


if __name__ == '__main__':
    # Create a log
    log = create_log(
        timestamp = True,
        filename = "Server_ACQSystem.log",
        title = "ACQSystem Server - DAIS 2.0",
    )

    # Read the config file
    config_filepath = configs / 'system.json'
    with open(config_filepath, 'r') as f:
        system_config = json.load(f)

    MasterServer(system_config, log)