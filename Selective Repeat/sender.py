#!/usr/bin/python

import socket
import sys
import os
import hashlib
import string
import random
import math
import select
import time
import signal
from struct import pack
from struct import unpack
from threading import Thread
from threading import Lock
from threading import Event
from collections import OrderedDict
from multiprocessing import Queue

import os.path
common_dir = (os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) + '/common/')
sys.path.append(common_dir)

from checksum import computeChecksum
from log import print_log
from packet import Packet
from error import inject_error
from signal_handler import signal_handler
from input_parser import InputParser

ACK_LOSS_PROBABILITY = 0.01
BIT_ERROR_PROBABILITY = 0.05

LOCK = Lock()
QLOCK = Lock()

class Window:

    def __init__(self, seq_num_bits):
        self.max_seq_num = int(math.pow(2, seq_num_bits))
        self.max_ws = int(math.pow(2, seq_num_bits - 1))
        self.size = int(math.pow(2, seq_num_bits - 1))
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
            if seq_num in self.transmissionWindow:
                pkt = self.transmissionWindow[seq_num]
                if pkt is not None:
                    pkt.ack_received()
                    self.num_received_acks += 1

    def stop(self, seq_num):
        with LOCK:
            if seq_num in self.transmissionWindow:
                pkt = self.transmissionWindow[seq_num]
                pkt.stop_timer()

            if seq_num == self.expected_ack:
                for k, pkt in self.transmissionWindow.items():
                    if pkt is not None:
                        if pkt.get_sent_time() == None and pkt.is_ack_received() == True:
                            del self.transmissionWindow[k]
                        else:
                            break

            self.update_expected_ack()

            self.last_recv_ack = seq_num

    # After sending msg
    def reduceWindow(self, pkt):
        with LOCK:
            seq_num = pkt.get_seq_num()

            #time = time.time()

            pkt.start_timer(time.time())

            self.transmissionWindow[seq_num] = pkt

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

    def get_pkt_sent_time(self, seq_num):
        with LOCK:
            if seq_num in self.transmissionWindow:
                pkt = self.transmissionWindow[seq_num]
                if pkt is not None:
                    return pkt.get_sent_time()

            return -1

    def reset_pkt_sent_time(self, seq_num):
        with LOCK:
            #time = time.time()
            if seq_num in self.transmissionWindow:
                pkt = self.transmissionWindow[seq_num]
                if pkt is not None:
                    pkt.reset_sent_time(time.time())

    def is_ack_recv(self, seq_num):
        with LOCK:
            if seq_num in self.transmissionWindow:
                pkt = self.transmissionWindow[seq_num]
                if pkt is not None:
                    return pkt.is_ack_received()

            return False

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


class Timer(Thread):

    def __init__(self, sock, port, window, timeout, nPkt):
        Thread.__init__(self)
        self.shutdown_flag = Event()
        self.sock = sock
        self.port = port
        self.window = window
        self.timeout = timeout
        self.nPkts = nPkt
        self.q = Queue()

    def format_pkt(self, seq_num, payload):
        header = int('0101010101010101', 2)
        max_seq_num = self.window.get_max_seq_num()
        checksum = computeChecksum(payload)

        return pack('IHHH' + str(len(payload)) + 's', seq_num, checksum, max_seq_num, header, payload)

    def enqueue_pkt(self, pkt):
        with QLOCK:
            self.q.put(pkt)

    def get_pkt(self):
        with QLOCK:
            return self.q.get()

    def get_size(self):
        with QLOCK:
            return self.q.empty()

    def run(self):

        count = 0
        while not self.shutdown_flag.is_set():

            if count == self.nPkts:
                break

            if self.get_size() == True:
                continue

            packet = self.get_pkt();
            if packet is None:
                continue

            # start the timer
            if not self.window.is_ack_recv(packet.get_seq_num()):
                timeLapsed = (time.time() - self.window.get_pkt_sent_time(packet.get_seq_num()))

                if timeLapsed > self.timeout:

                    print_log("Timer expired; Resending the segment " + str(packet.get_seq_num()) + "; Timer started.")
                    # resend the pkt
                    final_pkt = self.format_pkt(packet.get_seq_num(), packet.get_payload())
                    self.sock.sendto(final_pkt, ("127.0.0.1", self.port))
                    self.window.reset_pkt_sent_time(packet.get_seq_num())

                self.enqueue_pkt(packet)
            else:
                #with LOCK:
                self.window.stop(packet.get_seq_num())
                count += 1

class RequestHandler(Thread):

    def __init__(self, sock, port, window, pkt_bucket):
        Thread.__init__(self)
        self.shutdown_flag = Event()
        self.sock = sock
        self.port = port
        self.pkt_bucket = pkt_bucket
        self.timeout = timeout
        self.window = window

    def format_pkt(self, seq_num, payload, pkt_num):
        header = int('0101010101010101', 2)
        max_seq_num = self.window.get_max_seq_num()
        checksum = computeChecksum(payload)

        # Inject corruption
        if pkt_num is not 0 and inject_error(BIT_ERROR_PROBABILITY):
            print_log("Injecting bit error for segment " + str(seq_num))
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
            final_pkt = self.format_pkt(seq_num, pkt.get_payload(), self.window.get_next_pkt())
            self.sock.sendto(final_pkt, ("127.0.0.1", self.port))

            pkt_num = pkt_num + 1
            self.window.reduceWindow(pkt)

        self.window.reset_retransmission()

    def send_pkts(self):

        timer = Timer(self.sock, self.port, self.window, self.timeout, self.pkt_bucket.get_size())
        timer.start()

        while not self.shutdown_flag.is_set():

            if self.window.completed_transmission():
                print_log("Finished sending all the packets.")
                break

            # if window is full then wait till we get some space to send packets
            if self.window.get_ws() == self.window.get_max_ws():
                continue

            if self.pkt_bucket.get_size() < self.window.get_next_pkt():
                continue

            curr_pkt = self.pkt_bucket.next_pkt(self.window.get_next_pkt())
            if curr_pkt is None:
                continue

            self.window.reduceWindow(curr_pkt)

            curr_pkt.start_timer(time.time())

            print_log("Sending " + str(curr_pkt.get_seq_num()) + "; Timer started")

            # send the pkt
            final_pkt = self.format_pkt(curr_pkt.get_seq_num(), curr_pkt.get_payload(), self.window.get_next_pkt())
            self.sock.sendto(final_pkt, ("127.0.0.1", self.port))

            timer.enqueue_pkt(curr_pkt)

        timer.shutdown_flag.set()

    def run(self):

        self.send_pkts()

class ResponseHandler(Thread):

    def __init__(self, sock, nPkts, timeout, window):
        Thread.__init__(self)
        self.shutdown_flag = Event()
        self.sock = sock
        self.nPkts = nPkts
        self.timeout = timeout
        self.window = window

    def handle_timeout(self):
        # update window parameter so that pkt handler can resend the pkts
        self.window.trigger_retransmission()

    def recv_pkts(self):

        while not self.shutdown_flag.is_set():

            if self.window.get_num_received_acks() == self.nPkts:
                self.window.markTransmissionFinished()
                print_log("Finished receiving all the acks")
                return

            # Add timer to make sure sender get back Ack with in a time T.
            data = select.select([self.sock], [], [], self.timeout)
            if not data[0]:
                continue

            pkt, addr = self.sock.recvfrom(8)
            response = unpack('IHH', pkt)
            ack_num = int(response[0])

            # Received ACK: ACK_NUM
            print_log("Received ACK: " + str(ack_num))

            if (self.window.ignore_ack(ack_num) == False):
                continue

            # inject ack loss
            if inject_error(ACK_LOSS_PROBABILITY):
                print_log("Injecting ack loss for ack " + str(ack_num))
                continue

            # increment the window size after receiving ack.
            self.window.recv_ack(ack_num)

    def run(self):

        self.recv_pkts()

        # After receiving all the ACKs, we should close the sockets
        self.sock.close()

class Sender:

    def __init__(self, filename, port, nPkts, seq_num_bits, timeout, segSize):
        self.filename = filename
        self.port = int(port)
        self.nPkts = nPkts
        self.sock = None
        self.window = Window(seq_num_bits)
        self.pkt_bucket = PacketBucket(nPkts, segSize, self.window.get_max_seq_num())
        self.timeout = timeout
        self.max_seg = segSize

    def connect(self):
        # handle exception

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        except Exception as e:
            print_log("Falied to create the UDP socket")
            return False

        return True

    def send(self):

        try:
            request_handler = RequestHandler(self.sock, self.port, self.window, self.pkt_bucket)
            response_handler = ResponseHandler(self.sock, self.nPkts, self.timeout, self.window)

            print_log("Generating packets. \nNote: This step may take little more time based on the segment size & no. of pkts which needs to be generated.")
            self.pkt_bucket.create_pkts()
            print_log("\nFinished generating packets\n")

            request_handler.start()
            response_handler.start()
        
        except ServiceExit:
            self.request_handler.shutdown_flag.set()
            self.response_handler.shutdown_flag.set()

            self.request_handler.join()
            self.response_handler.join()

    def close(self):

        self.sock.close()

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

    print_log("################ INFO ##################")
    print_log("Protocol Name : " + str(prot_name))
    print_log("Sequence of bits : " + str(seqNumBits))
    print_log("Window Size : " + str(windowSize))
    print_log("Timeout Value : " + str(timeout))
    print_log("Segment size : " + str(segSize))
    print_log("########################################")
    print_log("")

    sender = Sender(filename, int(port_num), int(nPkts), int(seqNumBits), int(timeout), int(segSize))
    if sender.connect():
        signal.signal(signal.SIGINT, signal_handler)
        sender.send()
