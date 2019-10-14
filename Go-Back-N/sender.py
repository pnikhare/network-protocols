#!/usr/bin/python
import socket
import sys
import os

class Sender :

    def __init__(self,inputfile,port,numOfPkts) :

        self.host = "127.0.0.1"
        self.port = int(port)
        self.numOfPkts = numOfPkts

    def start(self) :
        
        # Initializing the sender process socket
        senderSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Sender process socket binds to given host,port
        senderSock.bind((self.host, self.port))

        # Sender process socket can listen to number of connections
        senderSock.listen(1)
        print ("Server listening on Port :"+ str(self.port))
        conn, addr = senderSock.accept()
        
        # Sender process runs infinitely untill interruption
        while True:
            # receiving 1024 bytes of data
            data = conn.recv(1024)
            print (data)
            if not data:
                break
        conn.sendall(data)
        conn.close()

def validateArgs() :
    
    if len(sys.argv) != 4 :
        print (" Please input 3 Arguments : ")
        print (" 1. Input file name")
        print (" 2. Port Number")
        print (" 3. Number of Packets to send")
        return False 

    # Check whether input file exits 
    if not os.path.isfile(sys.argv[1]) :
        print (" File does not exist")
        return False
    
    ################ FILE values validation #####
    
    # validate entered port number 
    if not sys.argv[2].isdigit() :
        print (" Please enter a valid port number")
        return False
    
    if not sys.argv[3].isdigit() :
        print (" Please enter a valid number of packets to send")
        return False

    return True    

if validateArgs() :
    proc = Sender(sys.argv[1],sys.argv[2],sys.argv[3])
    proc.start()



