#!/usr/bin/python
import socket
import sys
import os
import hashlib

class Packet:
    
    def __init__(self, payload, checksum, seq_num):
        self.payload  = payload
        self.checksum = checksum
        self.seq_num  = seq_num
    
    def get_payload(self):
        return self.payload

    def get_seq_num(self):
        return self.seq_num
        
    def get_checksum(self):
        return self.checksum

class PacketBucket:
    
    def __init__(self, nPkts, mss):
        self.nPkts = nPkts
        self.mss = mss
        self.mps = mss - 20 - 20 #TCP_HEADER_SZ - IP_HEADER_SZ;
        self.pkt_bucket = [];

    def randomData(self, len):
        """Generate a random string of fixed length """
        letters = string.ascii_lowercase
        return ''.join(random.choice(letters) for i in range(len))
    
    def create_pkts(self):
        count = 0
        seq_num = 0;
        while count < nPkts:
            payload = self.randomData(self.mps)
            if not payload:
                break
            
            checksum = hashlib.md5(payload.encode())
            pkt = Packet(payload, checksum, seq_num)
            self.pkt_bucket.append(pkt);
            
            seq_num = seq_num + 1
            count = count + 1    
                    
    def next_pkt(self, next_seq_num):
        # sent all the packets 
        if (next_seq_num > len(self.pkt_bucket) - 1):
            return None
            
        return self.pkt_bucket[next_seq_num]
    
class PktHandler:
    
    def __init__(self, s, filename, nPkts, mss):
        self.s = s
        self.pkt_bucket = PacketBucket(nPkts, mss)
        
    def send_pkts(self):
  
        # Generate packets 
	    self.pkt_bucket.create_pkts()
     
	    seq_num = 0
	    while True: 
	        curr_pkt = self.pkt_bucket.next_pkt(seq_num)
	        if curr_pkt == None:
	            break
	        
	        print("Sending pkt with seq num "+ str(curr_pkt.get_seq_num()))
	        data_stream = str(curr_pkt.get_seq_num()) + str(curr_pkt.get_checksum()) + str(curr_pkt.get_payload())
	        self.s.sendall(str(data_stream))
	        seq_num = seq_num + 1

class Client:

    def __init__(self, filename, port, nPkts):
        self.filename = filename
        self.port = int(port)
        self.nPkts = nPkts
        self.s = None
        self.pkt_handler = None        

    def connect(self):
        # handle exception 
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Client connects to senders socket 
        self.s.connect(('127.0.0.1', self.port))
    
    def send(self):
    
        self.pkt_handler = PktHandler(self.s, self.filename, self.nPkts, 80)
        self.pkt_handler.send_pkts()
        
    def close(self):
        
        self.s.close()

def validateInputArgs(filename, port, nPkts):

    # validate file path
    if not os.path.exists(filename):
        print ("Mentioned file path is wrong")
        return False

    # Validate entered port number 
    if not port.isdigit():
        print ("Please enter a valid port number")
        return False

    if nPkts is not None:
        if nPkts.isdigit():
            if nPkts <= 0:
                print ("Please provide the correct value for number of packets. It should be greater than 0.")
                return False
        else:
            print ("Value of expected number of packets should be integer")
            return False
    return True

class InputParser:
    
    def __init__(self, filename, port, nPkts):
        self.filename = filename
        self.port = port
        self.nPkts = nPkts
        
    def validateInputArgs(self):
        
        # validate file path
        if not os.path.exists(self.filename):
            print ("Mentioned file path is wrong")
            return False

        # Validate entered port number 
        if not self.port.isdigit():
            print ("Please enter a valid port number")
            return False

        if not self.nPkts.isdigit():
            if self.nPkts <= 0:
                print ("Please provide the correct value for number of packets. It should be greater than 0.")
                return False
        
        return True

    def parse_input(self):
        
        prot_name  = None
        seqNumBits = None
        windowSize = None
        timeout    = None
        segSize    = None
        
        with open(self.filename, 'r') as fd:
            try:
                prot_name  = fd.readline().strip()
                seqNumBits = fd.readline().strip()
                windowSize = fd.readline().strip()
                timeout    = fd.readline().strip()
                segSize    = fd.readline().strip()
            except IOError:
                print("Insufficient file content. Please correct the file content or format.")
        
        return prot_name, seqNumBits, windowSize, timeout, segSize
            
if __name__ == "__main__":
    
    if len(sys.argv) != 4:
        print (" Please provide all the expected input values.")
        print (" 1. File name with path")
        print (" 2. Port Number")
        print (" 3. Number of Packets")
        sys.exit()
    
    filename = sys.argv[1]
    port_num = sys.argv[2]
    nPkts    = sys.argv[3]
    
    parser = InputParser(filename, port_num, nPkts)
    if not parser.validateInputArgs():
        sys.exit()
    
    prot_name, seqNumBits, windowSize, timeout, segSize = parser.parse_input();
    
    client = Client(filename, port_num, nPkts)
    client.connect()
    client.send()
    client.close()
