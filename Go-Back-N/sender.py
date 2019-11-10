#!/usr/bin/python

import socket
import sys
import os
import hashlib
import string
import random
from struct import pack
from struct import unpack
from threading import Thread
from threading import Lock
import math
import select
from collections import OrderedDict
from checksum import computeChecksum

LOCK = Lock()

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

class Window:

    def __init__(self, seq_num_bits):
        self.max_ws = int(math.pow(2, seq_num_bits))
        self.size = int(math.pow(2, seq_num_bits))
        self.retransmit = False
        self.last_recv_ack = 0
        self.transmissionWindow = OrderedDict()
        self.stop_transmission = False

    def get_max_ws(self):
        return self.max_ws;

    def get_ws(self):
        with LOCK:
            return self.size

    # After receiving Ack
    def inc_ws(self, key):
        with LOCK:
            self.transmissionWindow[key] = True
            self.size = self.size + 1
            return self.size

    # After sending msg
    def dec_ws(self, key):
        with LOCK:
            self.transmissionWindow[key] = False
            self.size = self.size - 1
            return self.size

    def trigger_retransmission(self):
        with LOCK:
            self.retransmit = True

            # update the last ack from which we want to start the retransmission
            for k,v in self.transmissionWindow.items():
                if v == False:
                    self.last_recv_ack = k

    def get_last_recv_ack(self):
        with LOCK:
            return self.last_recv_ack

    def need_retransmission(self):
        with LOCK:
            return self.retransmit

    def reset_retransmission(self):
        with LOCK:
            self.retransmit = False

    def markTransmissionFinished(self):
        with LOCK:
            self.stop_transmission = True

    def completed_transmission(self):
        with LOCK:
            return self.stop_transmission

class PacketBucket:

    def __init__(self, nPkts, mss, max_ws):
        self.nPkts = nPkts
        self.mss = mss
        self.mps = mss - 20 - 20 #TCP_HEADER_SZ - IP_HEADER_SZ;
        self.max_ws = max_ws
        self.pkt_bucket = [];

    def randomData(self, len):
        """Generate a random string of fixed length """
        letters = string.ascii_lowercase
        return ''.join(random.choice(letters) for i in range(len))

    def create_pkts(self):
        count = 0
        while count < self.nPkts:
            payload = self.randomData(self.mps)
            if not payload:
                break

            checksum = "" 
            seq_num = count % self.max_ws
            pkt = Packet(payload, checksum, seq_num)
            self.pkt_bucket.append(pkt);

            count = count + 1

    def next_pkt(self, next_seq_num):
        # sent all the packets
        if (next_seq_num > len(self.pkt_bucket) - 1):
            return None

        return self.pkt_bucket[next_seq_num]

class PktHandler(Thread):

    def __init__(self, s, filename, nPkts, mss, window):
        Thread.__init__(self)
        self.s = s
        self.pkt_bucket = PacketBucket(nPkts, mss, window.get_max_ws())
        self.window = window

    def format_pkt(self, seq_num, payload):
        header = int('0101010101010101', 2)
        cs = pack('IH' + str(len(payload)) + 's', seq_num, header, payload)
        checksum = computeChecksum(cs)
        return pack('IHH' + str(len(payload)) + 's', seq_num, checksum, header, payload)

    def resend_pkts(self, start_pkt, num_pkts):
        
        print("start pkt & num pkts ", start_pkt, num_pkts)
        
        idx = 0
        while idx < num_pkts:
            pkt = self.pkt_bucket.next_pkt(start_pkt + idx)
            # seq_num = (start_pkt + idx) % self.window.get_max_ws()
            seq_num = pkt.get_seq_num()
            print("Resending pkt with seq num ", seq_num)
            final_pkt = self.format_pkt(seq_num, pkt.get_payload())
            self.s.sendto(final_pkt, ("127.0.0.1", 16000))

            idx = idx + 1

        self.window.reset_retransmission()

    def send_pkts(self):

        # Generate packets
        self.pkt_bucket.create_pkts()

        next_pkt = 0
        while True:

            if self.window.completed_transmission():
                print("Finished sending all the packets.")
                return

            # if we have consumed the whole window then we should wait till we get some space
            if self.window.get_ws() == 0:
                continue

            # check for retransmission
            if self.window.need_retransmission():
                num_pkts = self.window.get_ws() - self.window.get_last_recv_ack() + 1
                start_pkt = next_pkt - num_pkts
                self.resend_pkts(start_pkt, num_pkts)

            curr_pkt = self.pkt_bucket.next_pkt(next_pkt)
            if curr_pkt == None:
                continue

            #seq_num = next_pkt % self.window.get_max_ws()
            seq_num = curr_pkt.get_seq_num()

            print("Sending pkt with seq num ", seq_num)
            final_pkt = self.format_pkt(seq_num, curr_pkt.get_payload())
            self.s.sendto(final_pkt, ("127.0.0.1", 16000))

            self.window.dec_ws(seq_num)
            next_pkt = next_pkt + 1

    def run(self):

        self.send_pkts()

class AckHandler(Thread):

    def __init__(self, s, nPkts, timeout, window):
        Thread.__init__(self)
        self.s = s
        self.nPkts = nPkts
        self.timeout = timeout
        self.window = window

    def handle_timeout(self):
        # update window parameter so that pkt handler can resend the pkts
        self.window.trigger_retransmission()

    def recv_pkts(self):

        count = 0
        while True:

            if count == self.nPkts:
                self.window.markTransmissionFinished()
                print("Finished receiving Ack for all the pkts")
                return

            # Add timer to make sure client get back Ack with in a time T.
            fd_sets = select.select([self.s], [], [], self.timeout)
            if not fd_sets[0]:
                print("handling timeout")
                self.handle_timeout()
                count = count - 1
                continue

            pkt, addr = self.s.recvfrom(8)
            response = unpack('IHH', pkt)
            ack_num = response[0]
            print("Received ack with seq num ", int(ack_num))

            # increment the window size after receiving ack.
            self.window.inc_ws(int(ack_num))

            count = count + 1


    def run(self):

        self.recv_pkts()

        # After receiving all the ACKs, we should close the sockets
        self.s.close()

class Client:

    def __init__(self, filename, port, nPkts, seq_num_bits, timeout):
        self.filename = filename
        self.port = int(port)
        self.nPkts = nPkts
        self.s = None
        self.pkt_handler = None
        self.ack_handler = None
        self.window = Window(seq_num_bits)
        self.timeout = timeout

    def connect(self):
        # handle exception
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self):

        self.pkt_handler = PktHandler(self.s, self.filename, self.nPkts, 80, self.window)
        self.ack_handler = AckHandler(self.s, self.nPkts, self.timeout, self.window)

        self.pkt_handler.start()
        self.ack_handler.start()

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
                secondLine = fd.readline().strip().split(' ')
                seqNumBits = int(secondLine[0])
                windowSize = int(secondLine[1])
                timeout    = int(fd.readline().strip())
                segSize    = int(fd.readline().strip())
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

    print("Protocol Name : ", prot_name)
    print("Sequence of bits : ",seqNumBits)
    print("Window Size : ", windowSize)
    print("Timeout Value : ", timeout)
    print("Segment size : ", segSize)

    client = Client(filename, int(port_num), int(nPkts), int(seqNumBits), int(timeout))
    client.connect()
    client.send()
