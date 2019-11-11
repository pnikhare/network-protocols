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
from log import print_log
from packet import Packet

perform_corruption = False

LOCK = Lock()

class Window:

    def __init__(self, seq_num_bits):
        self.max_seq_num = int(math.pow(2, seq_num_bits))
        self.max_ws = int(math.pow(2, seq_num_bits) - 1)
        self.size = int(math.pow(2, seq_num_bits) - 1)
        self.retransmit = False
        self.last_recv_ack = -1
        self.transmissionWindow = OrderedDict()
        self.stop_transmission = False
        self.next_seq_num = 0
        self.next_pkt = 0
        self.expected_ack = 0
        self.num_received_acks = 0

    def get_max_seq_num(self):
        return self.max_seq_num

    def get_max_ws(self):
        return self.max_ws

    def get_ws(self):
        with LOCK:
            #return self.size
            return len(self.transmissionWindow)

    # Note: No need to take lock. This function is called under lock
    def update_expected_ack(self):
        # if we received ack for all the pkts then we should update the next_seq_num
        if len(self.transmissionWindow) == 0:
            self.expected_ack = self.next_seq_num
        else:
            self.expected_ack = self.transmissionWindow.items()[0][0]

    def get_num_received_acks(self):
        with LOCK:
            return self.num_received_acks

    # After receiving Ack
    def recv_ack(self, seq_num):
        with LOCK:
            self.transmissionWindow[seq_num] = True

            # delete all the entries for the pkts whose seq num is less than equal to
            # the received ack
            for k,v in self.transmissionWindow.items():

                self.size = self.size + 1

                if seq_num != self.last_recv_ack:
                    self.num_received_acks = self.num_received_acks + 1

                del self.transmissionWindow[k]

                if k == seq_num:
                    break

            self.update_expected_ack()
            
            self.last_recv_ack = seq_num

    # After sending msg
    def reduceWindow(self, seq_num):
        with LOCK:
            self.transmissionWindow[seq_num] = False

            # as we have consumed the window by one pkt, decrease the size by 1
            self.size = self.size - 1

            # increment the next pkt
            self.next_pkt = self.next_pkt + 1

            self.next_seq_num = (self.next_seq_num + 1) % self.max_seq_num

    def trigger_retransmission(self):
        with LOCK:
            self.retransmit = True
            self.next_seq_num = self.expected_ack

            # build the pkt nums string which we are going to retransmit
            pkt_nums = ""
            for k,v in self.transmissionWindow.items():
                pkt_nums += str(k)
                pkt_nums += ","

            print_log("Timer expired; Will be resending the pkts with seq num " + pkt_nums)

            self.next_pkt = self.next_pkt - len(self.transmissionWindow)
            self.transmissionWindow.clear()

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

    def set_next_seq_num(self, seq_num):
        with LOCK:
            self.next_seq_num = seq_num

    def get_next_seq_num(self):
        with LOCK:
            return self.next_seq_num

    def get_next_pkt(self):
        with LOCK:
            return self.next_pkt

    def get_expected_ack(self):
        with LOCK:
            return self.expected_ack

    def ignore_ack(self, seq_num):
        with LOCK:
            for k,v in self.transmissionWindow.items():
                if k == seq_num:
                    return True
        return False

class PacketBucket:

    def __init__(self, nPkts, mss, max_seq_num):
        self.nPkts = nPkts
        self.mss = mss
        self.mps = mss - 20 - 20 #TCP_HEADER_SZ - IP_HEADER_SZ;
        self.max_seq_num = max_seq_num
        self.pkt_list = [];

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
            seq_num = count % self.max_seq_num
            pkt = Packet(payload, checksum, seq_num)
            self.pkt_list.append(pkt);

            count = count + 1

    def next_pkt(self, index):
        # sent all the packets
        if (index > len(self.pkt_list) - 1):
            return None

        return self.pkt_list[index]

    def get_size(self):
        return len(self.pkt_list)

class RequestHandler(Thread):

    def __init__(self, sock, filename, nPkts, mss, window):
        Thread.__init__(self)
        self.sock = sock
        self.pkt_bucket = PacketBucket(nPkts, mss, window.get_max_seq_num())
        self.window = window

    def format_pkt(self, seq_num, payload):
        header = int('0101010101010101', 2)
        max_seq_num = self.window.get_max_seq_num()
        #cs = pack('IHH' + str(len(payload)) + 's', seq_num, max_seq_num, header, payload)
        # jsingh
        checksum = computeChecksum(payload)
        
        # To inject corruption
        global perform_corruption
        if perform_corruption == True:
            if seq_num == 2:
                perform_corruption = False
                checksum = 0
        
        return pack('IHHH' + str(len(payload)) + 's', seq_num, checksum, max_seq_num, header, payload)

    def resend_pkts(self, start_seq_num):

        pkt_num = start_seq_num
        while pkt_num < self.window.get_max_seq_num():
            pkt = self.pkt_bucket.next_pkt(self.window.get_next_pkt())

            if pkt is None:
                break

            seq_num = pkt.get_seq_num()

            print_log("Timer expired; Resending " + str(seq_num) + "; Timer started")
            final_pkt = self.format_pkt(seq_num, pkt.get_payload())
            self.sock.sendto(final_pkt, ("127.0.0.1", 16000))

            pkt_num = pkt_num + 1
            self.window.reduceWindow(seq_num)

        self.window.reset_retransmission()

    def send_pkts(self):

        # Generate packets
        self.pkt_bucket.create_pkts()

        while True:

            if self.window.completed_transmission():
                print_log("Finished sending all the packets.")
                break

            # if window is full then wait till we get some space to send packets
            if self.window.get_ws() == self.window.get_max_ws():
                continue

            # check for retransmission
            #if self.window.need_retransmission():
            #    print_log("retransmit")
            #    next_expected_pkt = self.window.get_expected_ack()
            #    self.resend_pkts(next_expected_pkt)
            #    continue

            if self.pkt_bucket.get_size() < self.window.get_next_pkt():
                continue

            curr_pkt = self.pkt_bucket.next_pkt(self.window.get_next_pkt())
            if curr_pkt is None:
                continue

            #seq_num = next_pkt % self.window.get_max_ws()
            seq_num = curr_pkt.get_seq_num()

            #Sending Sn; Timer started
            print_log("Sending " + str(seq_num) + "; Timer started")
            final_pkt = self.format_pkt(seq_num, curr_pkt.get_payload())
            self.sock.sendto(final_pkt, ("127.0.0.1", 16000))

            self.window.reduceWindow(seq_num)

    def run(self):

        self.send_pkts()

class ResponseHandler(Thread):

    def __init__(self, sock, nPkts, timeout, window):
        Thread.__init__(self)
        self.sock = sock
        self.nPkts = nPkts
        self.timeout = timeout
        self.window = window

    def handle_timeout(self):
        # update window parameter so that pkt handler can resend the pkts
        self.window.trigger_retransmission()

    def recv_pkts(self):

        while True:

            if self.window.get_num_received_acks() == self.nPkts:
                self.window.markTransmissionFinished()
                print_log("Finished receiving all the acks")
                return

            # Add timer to make sure client get back Ack with in a time T.
            data = select.select([self.sock], [], [], self.timeout)
            if not data[0]:
                #print_log("handling timeout")
                self.handle_timeout()
                continue

            # wait for a pkt to send
            #if self.window.get_ws() == self.window.get_max_ws():
            #    continue

            pkt, addr = self.sock.recvfrom(8)
            response = unpack('IHH', pkt)
            ack_num = int(response[0])

            # Received ACK: ACK_NUM
            print_log("Received ACK: " + str(ack_num))

            if (self.window.ignore_ack(ack_num) == False):
                continue

            # increment the window size after receiving ack.
            self.window.recv_ack(ack_num)

    def run(self):

        self.recv_pkts()

        # After receiving all the ACKs, we should close the sockets
        self.sock.close()

class Client:

    def __init__(self, filename, port, nPkts, seq_num_bits, timeout):
        self.filename = filename
        self.port = int(port)
        self.nPkts = nPkts
        self.sock = None
        self.request_handler = None
        self.response_handler = None
        self.window = Window(seq_num_bits)
        self.timeout = timeout

    def connect(self):
        # handle exception

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        except Exception as e:
            print_log("Falied to create the UDP socket")
            return False

        return True

    def send(self):

        self.request_handler = RequestHandler(self.sock, self.filename, self.nPkts, 80, self.window)
        self.response_handler = ResponseHandler(self.sock, self.nPkts, self.timeout, self.window)

        self.request_handler.start()
        self.response_handler.start()

    def close(self):

        self.sock.close()

class InputParser:

    def __init__(self, filename, port, nPkts):
        self.filename = filename
        self.port = port
        self.nPkts = nPkts

    def validateInputArgs(self):

        # validate file path
        if not os.path.exists(self.filename):
            print_log ("Mentioned file path is wrong")
            return False

        # Validate entered port number
        if not self.port.isdigit():
            print_log ("Please enter a valid port number")
            return False

        if not self.nPkts.isdigit():
            if self.nPkts <= 0:
                print_log ("Please provide the correct value for number of packets. It should be greater than 0.")
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
                print_log("Insufficient file content. Please correct the file content or format.")

        return prot_name, seqNumBits, windowSize, timeout, segSize

if __name__ == "__main__":

    if len(sys.argv) != 4:
        print_log (" Please provide all the expected input values.")
        print_log (" 1. File name with path")
        print_log (" 2. Port Number")
        print_log (" 3. Number of Packets")
        sys.exit()

    filename = sys.argv[1]
    port_num = sys.argv[2]
    nPkts    = sys.argv[3]

    parser = InputParser(filename, port_num, nPkts)
    if not parser.validateInputArgs():
        sys.exit()

    prot_name, seqNumBits, windowSize, timeout, segSize = parser.parse_input();

    print_log("Protocol Name : " + str(prot_name))
    print_log("Sequence of bits : " + str(seqNumBits))
    print_log("Window Size : " + str(windowSize))
    print_log("Timeout Value : " + str(timeout))
    print_log("Segment size : " + str(segSize))

    client = Client(filename, int(port_num), int(nPkts), int(seqNumBits), int(timeout))
    if client.connect():
        client.send()
