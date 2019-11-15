#!/usr/bin/python
import random 

def inject_error(probability):
    if probability > random.random():
        return True

    return False
