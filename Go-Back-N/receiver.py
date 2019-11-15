#!/usr/bin/python

import socket
import sys
import os
import hashlib
import signal
from struct import unpack
from struct import pack

import os.path
common_dir = (os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) + '/common/')
sys.path.append(common_dir)

from checksum import isMsgCorrupted
from packet import Packet
from error import inject_error
from signal_handler import signal_handler

PACKET_LOSS_PROBABILITY = 0.01

class RequestHandler:

    def __init__(self, s):
        self.sock = s
        self.expected_seq_num = 0

    def set_expected_seq_num(self, seq_num):
        self.expected_seq_num = seq_num

    def get_expected_seq_num(self):
        return self.expected_seq_num

    def send_ack(self, seq_num, sender_addr):
        print("ACK Sent: " + str(seq_num))
        allZeros = int('0000000000000000', 2)
        header = int('1010101010101010', 2)
        packet = pack('IHH', seq_num, allZeros, header)
        self.sock.sendto(packet, sender_addr)

    def recv_pkts(self):

        temp = True
        while True:

            message, addr = self.sock.recvfrom(1024)
            pkt = unpack('IHHH' + str(len(message) - 10) + 's', message)

            # extract each parameter
            seq_num = pkt[0]
            checksum = pkt[1]
            max_seq_num = pkt[2]
            header = pkt[3]
            data = pkt[4]

            # if received pkt is corrupted then discard it
            if isMsgCorrupted(checksum, data):
                print("Received Corrupted Segment " + str(seq_num) + ". Discarding.")
                continue

            # if received pkt's seq num is not same as expected seq num then send ack with expected seq num - 1
            if seq_num != self.get_expected_seq_num():
                print("Received Segment Out of Order (seq num:" + str(seq_num) + ", expected seq num:" + str(self.get_expected_seq_num()) + ").")
                if self.get_expected_seq_num() != 0:
                    self.send_ack((self.get_expected_seq_num() - 1), addr)
                else:
                    self.send_ack((max_seq_num - 1), addr)
            else:
                print("Receiving Segment "+ str(seq_num))

                # Inject the packet loss
                if (inject_error(PACKET_LOSS_PROBABILITY)):
                    print("Injecting packet loss for segment " + str(seq_num))
                    continue

                self.set_expected_seq_num((seq_num + 1) % max_seq_num)
                self.send_ack(seq_num, addr)

class Server:

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

    server = Server(port_num)
    if server.bind():
        print("Starting receiver. Press Ctrl+C to terminate")
        signal.signal(signal.SIGINT, signal_handler)
        server.receive()
    #server.close()
