#!/usr/bin/python

class Packet:

    def __init__(self, payload, checksum, seq_num):
        self.payload  = payload
        self.checksum = checksum
        self.seq_num  = seq_num
        self.sent_time = None
        self.ack_recv = False

    def get_payload(self):
        return self.payload

    def get_seq_num(self):
        return self.seq_num

    def get_checksum(self):
        return self.checksum

    def start_timer(self, time):
        self.sent_time = time

    def reset_sent_time(self, time):
        self.sent_time = time

    def ack_received(self):
        self.ack_recv = True

    def get_sent_time(self):
        return self.sent_time

    def is_ack_received(self):
        return self.ack_recv

    def stop_timer(self):
        self.sent_time = None
