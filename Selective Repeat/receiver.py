#!/usr/bin/python

import socket
import sys
import os
import hashlib
import math
import signal
from struct import unpack
from struct import pack

import os.path
common_dir = (os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) + '/common/')
sys.path.append(common_dir)

from checksum import isMsgCorrupted
from packet import Packet
from error import inject_error
from collections import OrderedDict
from signal_handler import signal_handler

PACKET_LOSS_PROBABILITY = 0.01

class Window:

    def __init__(self, seq_num):
        self.basePkt = 0
        self.endPkt = seq_num - 1
        self.max_ws = int(math.pow(2, seq_num - 1))
        self.max_seq_num = seq_num
        self.receivingWindow = OrderedDict()

    def get_max_ws(self):
        return self.size

    def duplicate(self, seq_num):
        return False
        if seq_num in self.receivingWindow:
            return True

        return False

    def slide(self, seq_num):
        if seq_num != self.basePkt:
            sequenceNumber = self.basePkt

            while sequenceNumber != seq_num:
                if sequenceNumber not in self.receivingWindow:
                    self.receivingWindow[sequenceNumber] = False

                sequenceNumber = (sequenceNumber + 1) % self.max_seq_num

        self.receivingWindow[seq_num] = True

        if len(self.receivingWindow) and self.receivingWindow.items()[0][0]:
            seq_num = self.receivingWindow.items()[0]
            self.basePkt = (self.receivingWindow.items()[0] + 1) % self.max_seq_num
            self.endPkt = (self.basePkt + self.get_max_ws() - 1) % self.max_seq_num
            del self.receivingWindow[seq_num]

    def get_base_pkt(self):
        return self.basePkt

    def get_end_pkt(self):
        return self.endPkt

class RequestHandler:

    def __init__(self, s):
        self.sock = s
        self.window = None
        self.window_created = False

    def set_window(self, window):
        self.window = window

    def get_window(self):
        return self.window

    def send_ack(self, seq_num, sender_addr):
        print("ACK Sent: " + str(seq_num))
        allZeros = int('0000000000000000', 2)
        header = int('1010101010101010', 2)
        packet = pack('IHH', seq_num, allZeros, header)
        self.sock.sendto(packet, sender_addr)

    def recv_pkts(self):

        while True:

            message, addr = self.sock.recvfrom(1024)
            pkt = unpack('IHHH' + str(len(message) - 10) + 's', message)

            # extract each parameter
            seq_num = pkt[0]
            checksum = pkt[1]
            max_seq_num = pkt[2]
            header = pkt[3]
            data = pkt[4]

            if not self.window_created:
                self.window = Window(max_seq_num)
                self.window_created = True

            # if received pkt is corrupted then discard it
            if isMsgCorrupted(checksum, data):
                print("Received Corrupted Segment " + str(seq_num) + ". Discarding.")
                continue


            # If received pkt is out of order then
            #
            # 1. Send the ack with seq_num
            # 2. Dont update the window. Just ignore the received pkt.
            #
            if self.window.get_base_pkt() < self.window.get_end_pkt():
                if seq_num < self.window.get_base_pkt() and seq_num > self.window.get_end_pkt():
                    print("Received Segment Out of Order (Base seq num:" + str(self.window.get_base_pkt()) + ", Last seq num:" + str(self.get_end_pkt()) + ").")
                    self.send_ack(seq_num, addr)
                    continue
            else:
                if seq_num < self.window.get_base_pkt() or seq_num > self.window.get_end_pkt():
                    print("Received Segment Out of Order (seq num:" + str(seq_num) + ", expected seq num:" + str(self.get_expected_seq_num()) + ").")
                    self.send_ack(seq_num, addr)
                    continue
                           
            # if received pkt is duplicate then discard it
            if self.window.duplicate(seq_num):
                print("Received Duplicate Segment " + str(seq_num) + ". Discarding")
                continue
            else:
                print("Receiving Segment "+ str(seq_num))

                # Inject the packet loss
                if (inject_error(PACKET_LOSS_PROBABILITY)):
                    print("Injecting packet loss for segment " + str(seq_num))
                    continue

                self.send_ack(seq_num, addr)
                self.window.slide(seq_num)
                continue

class Receiver:

    def __init__(self, port):
        self.port = int(port)
        self.sock = None
        self.request_handler = None

    def bind(self):

        try:
            # create & bind
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind(("127.0.0.1", self.port))
        except Exception as e:
            print_log("Falied to create the UDP socket")
            return False

        return True

    def receive(self):

        self.request_handler = RequestHandler(self.sock)
        self.request_handler.recv_pkts()

    def close(self):

        self.sock.close()

class InputParser:

    def __init__(self, port):
        self.port = port

    def validateInputArgs(self):

        # Validate entered port number
        if not self.port.isdigit():
            print ("Please enter a valid port number")
            return False

        return True

if __name__ == "__main__":

    if len(sys.argv) != 2:
        print (" Please provide all the expected input values.")
        print (" 1. Port Number")
        sys.exit()

    port_num = sys.argv[1]

    parser = InputParser(port_num)
    if not parser.validateInputArgs():
        sys.exit()

    receiver = Receiver(port_num)
    if receiver.bind():
        print("Starting receiver. Press Ctrl+C to terminate")
        signal.signal(signal.SIGINT, signal_handler)
        receiver.receive()
    #receiver.close()
