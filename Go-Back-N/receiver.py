#!/usr/bin/python
import socket
import sys

class Receiver :

    def __init__(self,port) :
        self.port = int(port)
        

    def start(self) :

        receiverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Client connects to senders socket 
        receiverSocket.connect(('127.0.0.1', self.port))
        
        # Sends data in bulk
        receiverSocket.sendall('Hello, world')
        print("sent data to process at port "+ str(self.port))
        data = receiverSocket.recv(1024)
        receiverSocket.close()
    
        print 'Received', repr(data)


def validateArgs() :

    if len(sys.argv) != 2 :
        print (" Please input 1 Arguments : ")
        print (" 1. Port Number")
        return False 

    # Validate entered port number 
    if not sys.argv[1].isdigit() :
        print (" Please enter a valid port number")
        return False
    
    return True


if validateArgs() :
    proc = Receiver(sys.argv[1])
    proc.start()
