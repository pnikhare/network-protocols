#!/usr/bin/python

from threading import Lock

PLOCK = Lock()

def print_log(msg):
    with PLOCK:
        print(msg)
