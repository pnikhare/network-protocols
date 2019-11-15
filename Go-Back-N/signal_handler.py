#!/usr/bin/env python

import signal
import sys

def signal_handler(sig, frame):
    print('Terminating server because you pressed Ctrl+C!')
    sys.exit(0)

