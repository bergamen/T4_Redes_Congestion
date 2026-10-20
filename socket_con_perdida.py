import socket
import random

class Sock(socket.socket):
    
    def sendto(self, data,address):
        if random.random() > 0:
            return super().sendto(data,address)