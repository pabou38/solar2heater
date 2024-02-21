#!/usr/bin/python3

################################
# new blynk
#################################


import time, sys
import _thread

import logging

blynk_server="blynk.cloud" # ping blynk.cloud
#server = "fra1.blynk.com"

version = 2.2 # normlize file path across linux and windows

print("%s: v%0.2f" %(__name__, version))

################### import ##############

######################
# normalize file path for linux (Pi) and Windows
######################


# root is DEEP (windows) or APP (linux)
# root/Blynk/Blynk_client/ # used by python and micropython

# root/Blynk/Blynk_client/my_blynk_private.py
# root/Blynk/Blynk_client/my_blynk_new.py
# root/Blynk/Blynk_client/blynk libs

# PYTHON (win, linux)
# projects in root/<project> 
# so import ../Blynk/Blynk_client

# MICROPYTHON 
# projects in micropython/<project>
# sym link to micropython/MY MODULES 
# sym link to Blynk/Blynk_client


# lib patacaisse

################################## NEW BlynkLib #################################
#Python 2, Python 3, MicroPython support
#Linux,  Windows,  MacOS support
#virtual_write sync_virtual set_property log_event
#events: Vn, connected, disconnected, invalid_auth
#TCP and secure TLS/SSL connection support
#can run on embedded hardware, like ESP8266, ESP32, W600 or OpenWrt

# https://github.com/vshymanskyy/blynk-library-python is the NEW library
# Note: The library has been updated for Blynk 2.0. Please remain on v0.2.0 for legacy Blynk

# NEW
# v1.0.0 on github, v0.2.0 on pip install
# BlinkLib.py (2 uppercases)
# https://github.com/vshymanskyy/blynk-library-python  v1.0.0    BlinkLib.py (2 uppercases)
# pip install blynk-library-python


##### WARNING: pip only install v0.2.0 and does not install BlynkTimer.py, so MUCH better to install rev 1.0.0 from github  for Python v1.0.0 (linux)
# import BlynkLib
#  -> import BlynkLib_1_0_0 as BlynkLib

# BlynkLib.py, BlynkLibTimer.py


# Python 2, Python 3, MicroPython support . Linux,  Windows,  MacOS support
# 1.0.0
# log_event, set_property
# same lib for python and micropython
# run on ESP
# Edgent_linux_rpi

####### @blynk.on("V3")   (even if README uses @blynk.VIRTUAL_WRITE(1) 
# @blynk.on("connected")@blynk.on("internal:utc")


################################## LEGACY blynklib #################################
# https://github.com/blynkkk/lib-python is legacy
# sudo pip install blynklib
# certificates
# blynklib.py, blynklib_mp.py, blynktimer.py
# 0.2.6
# import blynklib_legacy_0_2_6.py as blynklib
#######################

### for linux, make sure to download latest version 1.0.0 from github


# already done ?
if sys.platform in ["win32"]:
    #sys.path.insert(1, '../../Blynk/Blynk_client')
    sys.path.insert(1, '../Blynk/Blynk_client') # now same as on Linux
else:
    sys.path.insert(1, '../Blynk/Blynk_client')
    

# should be in /lib for ESP , or in Blynk for Raspberry
# ASSUMES this module is a sym link in the project directory
import BlynkLib_new as BlynkLib  # for Python v1.0.0 
import BlynkTimer_new as BlynkTimer

# will connect
# connect call back executed when blynk.run() thread started
# with legacy , blynk_con object has a property is_connected, so no real need to monitor connect call back
# with new, no such property ? AND AS connect call back defined in main (ie where blynk is returned), 
#   no way to define a generic method in my_blynk_new to check connection happened. do it in main 

def create_blynk(token, log=None):
    # log=print
    try:
        blynk = BlynkLib.Blynk(token, server=blynk_server, log=log, insecure=False)
        print('%s: blynk created. connecting to server ..' %__name__) 
        return(blynk)
    
    except Exception as e:
        # eg no route to host
        s = "%s: exception: %s when creating Blynk and connecting to server" %(__name__, str(e))
        print(s)
        logging.error(s)
        return(None)


def create_blynk_timer():
    timer = BlynkTimer()
    #timer.set_timeout(2, hello) # run once
    #timer.set_interval(4, power) # run multiple
    return(timer)


def run_blynk(blynk, blynk_timer=None):
    print('%s: start blynk.run() endless loop as thread' %__name__)

    while True:
        try:
            blynk.run()
            if blynk_timer is not None:
                blynk_timer.run()
        except Exception as e:
            print("exception blynk.run %s" %str(e))
            sys.exit(1)


if __name__ == "__main__":

    import secret_test
    import vpin_test

    ############ change to current application
    secret_test = secret_test.blynk_token_victron_remote_operation

    print("blynk token" , secret_test)

    blynk = create_blynk(secret_test, log=None) # connect
    if blynk is None:
        print("cannot connect")


    #####################
    # blynk call back
    # connect, disconnect can be generic, but control need application vpin
    #####################
    
    blynk_connected = False

    @blynk.on("connected")
    def blynk_connected(ping):
        global blynk_connected
        blynk_connected = True
        print('Blynk connect call back. Ping:', ping, 'ms')
        blynk.send_internal("utc", "time")
        blynk.send_internal("utc", "tz_name")
        
        #blynk.sync_virtual(v_automation, v_sleep, v_react_to_surplus, v_react_to_soutir)


    @blynk.on("disconnected")
    def blynk_disconnected():
        print('Blynk disconnected')


    # get time from server
    @blynk.on("internal:utc")
    def on_utc(value):
        if value[0] == "time":
            ts = int(value[1])//1000

            if sys.platform in ['esp32', 'esp8266']:
                # on embedded systems, you may need to subtract time difference between 1970 and 2000
                ts -= 946684800
                #tm = time.gmtime(ts) # gmtime not available in micropython
                print("server UTC time: ", time.localtime(ts)) # tuple from sec

            else:
                tm = time.gmtime(ts) 
                print("server UTC time: ", time.asctime(tm)) #UTC time:  Tue Jun  6 05:11:38 2023


        elif value[0] == "tz_name":
            print("server Timezone: ", value[1]) #Timezone:  Europe/Paris


    # control widgets call back
    s = "V%d" %0
    @blynk.on(s)
    def f1(value):
        print(value)
        #call back multi on off: ['0']
        val = int(value[0])

    # start blynk.run thread
    id1= _thread.start_new_thread(run_blynk, (blynk,None))

    # sync
    blynk.sync_virtual(0)

    while blynk_connected is False:
        time.sleep(1)
    print("blynk is connected")

    while True:
  
        #blynk.virtual_write(vpin.vpin_power,200)
        #blynk.set_property(shelly_switch[index], "label", "ON")
        #blynk.set_property(shelly_switch[index], "color", "#D3435C")
        #blynk.log_event("starting", "solar2heater starting") # use event code
        
        time.sleep(10)



"""
Connecting to blynk.cloud:443...
< 29 1 | nIgi4nCJ6yvwXmLqCzD-nq-YdCiIpM3t
blynk initialized
start blynk.run() endless loop
> 0 1 | 200
< 17 2 | ver 1.0.0 h-beat 50 buff-in 1024 dev linux-py
Blynk ready. Ping: 8170 ms
< 17 3 | utc time
< 17 4 | utc tz_name
> 0 2 | 200
> 17 3 | utc,time,1686028215569
UTC time:  Tue Jun  6 05:10:15 2023
> 17 4 | utc,tz_name,Europe/Paris
Timezone:  Europe/Paris
< 16 5 | vr 0
> 20 5 | vw,0,0
['0']
< 20 6 | vw 10 200
< 20 7 | vw 9 test blynk
> 0 7 | 2
"""
