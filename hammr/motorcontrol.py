"""Communicates motor commands (start, stop) to the master server."""

import json
import socket


class MotorControl():
    def __init__(self, ip: str, port: int) -> None:
        self.tcp_address = (ip, port)
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.settimeout(3)  # AGW hoping this avoids lockout on interrupts.
        self.client_socket.connect(self.tcp_address)


    def send_stop(self) -> None:
        print('Sending STOP to motor')
        self.client_socket.send("MSTOP".encode())
        print(self.client_socket.recv(50).decode())


    def send_start(self) -> None:
        print('Sending START to motor')
        self.client_socket.send("MSTART".encode())
        print(self.client_socket.recv(50).decode())

    
    def send_getsysconfig(self) -> dict:
        """Gets the system.json config from the master server."""
        self.client_socket.send("SYST".encode())
        syst = self.client_socket.recv(5000)
        config = json.loads(syst.decode())
        return config


    def disconnect(self) -> None:
        self.client_socket.close()