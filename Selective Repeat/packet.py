#!/usr/bin/python

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
