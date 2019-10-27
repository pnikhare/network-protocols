#!/usr/bin/python
import socket
import sys

class Client:

    def __init__(self,port) :
        self.port = int(port)
        

    def start(self) :

        socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Client connects to senders socket 
        socket.connect(('127.0.0.1', self.port))
        
        # Sends data in bulk
        socket.sendall('Hello, world')
        print("sent data to process at port "+ str(self.port))
        ack = socket.recv(1024)
        socket.close()
    
        print("Received " + repr(ack))


def validateArgs() :

    if len(sys.argv) != 2 :
        print (" Please provide input: ")
        print (" 1. Port Number")
        return False 

    # Validate entered port number 
    if not sys.argv[1].isdigit() :
        print (" Please enter a valid port number")
        return False
    
    return True


if validateArgs() :
    proc = Client(sys.argv[1])
    proc.start()
