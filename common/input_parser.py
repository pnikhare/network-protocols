#!/usr/bin/python

import sys
import os

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


