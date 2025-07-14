import json
import socket

from io import StringIO


class MotorControl():
    def __init__(self, ip, port):
        self.tcp_address = (ip, port)
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect(self.tcp_address)


    def send_stop(self):
        print('Sending STOP to motor')
        self.client_socket.send("MSTOP")
        print(self.client_socket.recv(50))


    def send_start(self):
        print('Sending START to motor')
        self.client_socket.send("MSTART")
        print(self.client_socket.recv(50))

    
    def send_getconfig(self):
        self.client_socket.send("SYST")
        syst = StringIO(self.client_socket.recv(5000))
        self.config = json.load(syst)


    def disconnect(self):
        self.client_socket.close()