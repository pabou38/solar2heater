#!/usr/bin/python3

import datetime

def get_stamp():

    d = datetime.datetime.now()

    s = "%d/%d-%d:%d" %(d.month, d.day, d.hour, d.minute)

    return(s)