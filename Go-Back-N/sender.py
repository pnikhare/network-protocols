#!/usr/bin/python
import socket
import sys

class Packet:
    
    def __init__(self, payload, checksum, seq_num):
        self.payload  = payload
        self.checksum = checksum
        self.seq_num  = seq_num
    
    def get_payload():
        return payload

    def get_seq_num():
        return seq_num
        
    def get_checksum():
        return checksum

class PacketBucket:
    
    def __init__(self, filename, mss):
        self.filename = filename
        self.mss = mss
        self.mps = mss - 20 - 20 #TCP_HEADER_SZ - IP_HEADER_SZ;
        self.pkt_bucket = [];

    def create_pkts(self):
        
        try:
            fd = open(filename, 'rb')
            try:
                seq_num = 0;
                while True:
                    # handle exception
                    # read data from file to generate payload
                    payload = fd.read(mps)
            
                    if payload is None:
                        break
            
                    checksum = hashlib.md5(payload.encode())
                    pkt = Packet(payload, checksum, seq_num)
                    pkt_bucket.append(pkt);
            
                    seq_num = seq_num + 1;
            finally:
                fd.close()
                
        except IOError:
            print("Failed to open or read file in rb mode")
            
    def next_pkt(self, next_seq_num):
        
        if (next_seq_num > len(pkt_bucket) - 1):
            return None
            
        return pkt_bucket[next_seq_num]
    
class PktHandler:
    
    def __init__(self, socket, filename, nPkts, mss):
        self.socket = socket
        self.nPkts = nPkts
        self.pkt_bucket = PacketBucket(filename, mss)
        self.last_pkt = None
        
    def send_pkts(self):
        
        while True: 
            curr_pkt = pkt_bucket.next_pkt(last_pkt.get_seq_num() + 1)
            
            if curr_pkt == None:
                break
        
            print("Sending pkt with seq num "+ str(curr_pkt.get_seq_num()))
        
            # Sends data in bulk
            socket.sendall(curr_pkt)
        
            last_pkt = curr_pkt
        
        print("Finished sending all the packets")

class Client:

    def __init__(self, filename, port, nPkts):
        self.filename = filename
        self.port = int(port)
        self.nPkts = nPkts
        self.socket = None;
        self.pkt_handler = PktHandler(socket,filename, nPkts, 1500)
        
    def connect(self):

        # handle exception 
        socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Client connects to senders socket 
        socket.connect(('127.0.0.1', self.port))
        
        send()
        
    def send(self):
    
        pkt_bucket.send_pkts();
        
    def close(self):
        
        socket.close()

def validateInputArgs(filename, port, nPkts) :

    # validate file path
    if os.path.exists(filename):
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

if __name__ == "__main__":
    
    if len(sys.argv) != 3:
        print (" Please provide all the expected input values.")
        print (" 1. File name with path")
        print (" 2. Port Number")
        print (" 3. Number of Packets")
        sys.exit()
    
    filename = sys.argv[0]
    port_num = sys.argv[1]
    nPkts    = sys.argv[2]
    
    if not validateInputArgs(filename, port_num, nPkts):
        sys.exit()
    
    if nPkts is None:
        nPkts = "ALL"
        
    client = Client(filename, port_num, nPkts)
    client.connect()
    client.send()
    Client.close()
