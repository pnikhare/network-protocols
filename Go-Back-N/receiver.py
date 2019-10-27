#!/usr/bin/python
import socket
import sys

class Server:

    def __init__(self,port) :
        self.port = int(port)
        

    def start(self) :

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Client connects to senders socket 
        s.bind(('127.0.0.1', self.port))
        s.listen(1);
        conn, addr = s.accept()
        #with conn:
        print("connected")
        while True:       
            data = conn.recv(1500)
	    if not data:
		break
            print("Received ", repr(data))
    
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
    proc = Server(sys.argv[1])
    proc.start()
