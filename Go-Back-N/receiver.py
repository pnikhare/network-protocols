#!/usr/bin/python
import socket
import sys
import os
import hashlib
from struct import unpack
from struct import pack
from checksum import isMsgCorrupted

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

class PktHandler:

    def __init__(self, s):
        self.s = s

    def recv_pkts(self):

        temp = True
        while True:

            message, addr = self.s.recvfrom(1024)
            pkt = unpack('IHH' + str(len(message) - 8) + 's', message)

            # extract each parameter
            seq_num = pkt[0]
            checksum = pkt[1]
            header = pkt[2]
            data = pkt[3]

            print("Receiving pkt with seq num "+ str(seq_num))

            if isMsgCorrupted(checksum, message):
                print "Received corrupted message"
                continue

            if temp and int(seq_num) == 2:
                temp = False
                continue

            allZeros = int('0000000000000000', 2)
            header = int('1010101010101010', 2)
            packet = pack('IHH', seq_num, allZeros, header)
            self.s.sendto(packet, addr)

            print("Sending ACK for pkt with seq num "+ str(seq_num))

class Server:

    def __init__(self, port):
        self.port = int(port)
        self.s = None
        self.pkt_handler = None

    def bind(self):
        # handle exception
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Server binds to senders socket
        self.s.bind(("127.0.0.1", self.port))

    def receive(self):

        self.pkt_handler = PktHandler(self.s)
        self.pkt_handler.recv_pkts()

    def close(self):

        self.s.close()

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
    server.bind()
    server.receive()
    #server.close()
