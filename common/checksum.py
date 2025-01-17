#!/usr/bin/python

def carry_around_add(a, b):
    c = a + b
    return (c & 0xffff) + (c >> 16)

def computeChecksum(msg):
    s = 0
    for i in range(0, len(msg), 2):
        w = ord(msg[i]) + (ord(msg[i+1]) << 8)
        s = carry_around_add(s, w)
    return ~s & 0xffff

def isMsgCorrupted(orig_cksum, msg):
    if computeChecksum(msg) == orig_cksum:
        return False

    return True
