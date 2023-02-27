#!/usr/bin/python3

import os
import sys
from time import sleep
import datetime
import time

import RPi.GPIO as GPIO

from PIL import Image, ImageDraw, ImageFont

# convert UTC to local
from dateutil import tz
# pip install pytz
import pytz

#pip install suntime
from suntime import Sun, SunTimeException
latitude = 45.12
longitude = 5.52

import logging
root = '/home/pi/solar2heater/'
# debug, info, warning, error, critical. default warning
log_file = root + "solar2heater.log"
print ("logging to:  " , log_file) 

if os.path.exists(log_file) == False:
    print("creating log file ", log_file)
    with open(log_file, "wb") as f:
        pass


### WARNING configure log file before any module which may import logging
#logging.warning('starting')  BEFORE .basicConfig will log to terminal, and subscequent .basicConfig will NOT change this
# #Be sure to try the following in a newly started Python interpreter, and don’t just continue from the session described above:

# https://docs.python.org/3/library/logging.html#logrecord-attributes
logging.basicConfig(filename=log_file, format='%(levelname)s %(asctime)s %(message)s', encoding = 'utf-8', level=logging.INFO)
logging.info('-------------- solar2heater starting ...............')

import _thread # low level

# The httplib module has been renamed to http.client in Python 3.0.
# This module defines classes which implement the client side of the HTTP and H>
# the module urllib uses it to handle URLs that use HTTP and HTTPS.
import http.client as httplib  # httplib only P2
import urllib

import json
import requests 
# https://requests.readthedocs.io/en/latest/
from requests.exceptions import HTTPError
from requests.auth import HTTPDigestAuth

from requests.auth import HTTPDigestAuth # use hash , vs base64 in basic access auth
import pprint # insert nl, recursion, indent, depth, etc
# pip install pprintpp

# https://www.framboise314.fr/utiliser-luart-port-serie-du-raspberry-pi-4/
# https://www.framboise314.fr/le-port-serie-du-raspberry-pi-3-pas-simple/
import serial

import modbus_tk
import modbus_tk.defines as cst
from modbus_tk import modbus_rtu

# pip install modbus_tk
# Requirement already satisfied: modbus_tk in /home/pi/.local/lib/python3.9/site-packages (1.1.2)

import BlynkLib_1_0_0
from BlynkTimer import BlynkTimer

#sudo pip uninstall blynklib blynk V1.0
# pip install blynk-library-python  # V2.0 install v0.2.0. latest is 1.0.0 , on github 
# !!!!! only install Blynklib.py, not BlynkTimer
# https://github.com/vshymanskyy/blynk-library-python  v2

# application specific
import my_st7789
import secret
import pushover
import monit_mail

# send mail and pushover at start
pushover.send_pushover("solar2heater starting", title= "solar2heater", sound="cosmic")
monit_mail.send_mail(subject="solar2heater starting", content = "have fun")

# GPIO
button = 20 # connected to gnd. pull up
led_red = 12 #  gpio out red
led_yellow = 24 #  gpio out yellow

# ISR
def int_reboot(x):
    sleep(2) # sleeping in isr is not great, but will reboot or halt anyway
    if GPIO.input(button) == 0:
        # long press = reboot
        s = 'reboot'
    else:
        # short press = halt
        s = 'halt'

    print(s)
    logging.info(s)

    if display != None:
        # create new image and use draw to paint into it
        (image, draw) = my_st7789.st7789_new_image()
        draw.text((30, 30), s, font=font, fill=(255, 255, 255))
        display.display(image) 
        sleep(2)

    os.system("sudo " + s)
    

	
def blink_led(led,sec):
	GPIO.output(led,1)
	sleep(sec)
	GPIO.output(led,0)
	sleep(sec)


GPIO.setmode(GPIO.BCM)
GPIO.setup(button, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# use interrupt. GPIO.RISING
GPIO.add_event_detect(button, GPIO.FALLING, callback=int_reboot, bouncetime=500)  

GPIO.setup(led_red, GPIO.OUT)
GPIO.setup(led_yellow, GPIO.OUT)

GPIO.output(led_red,0) # turn off 
GPIO.output(led_yellow,0) 


BLYNK_TEMPLATE_ID = secret.BLYNK_TEMPLATE_ID
BLYNK_DEVICE_NAME = secret.BLYNK_DEVICE_NAME
BLYNK_AUTH_TOKEN  = secret.BLYNK_AUTH_TOKEN

server="blynk.cloud" # ping blynk.cloud
#server = "fra1.blynk.com"

# vpin
v_automation = 0 # manual master switch
v_led_automation = 1
v_select = 2 # select primary heater

v_power_shelly = 3 # power meter
v_power_meross = 4

v_terminal = 5

v_power_eddy = 6   # power meter
v_power_grid = 7
v_power_production = 8

v_shellyonoff = 9 # manual on off
v_merossonoff = 10

v_led_shelly = 11 # feedback led
v_led_meross = 12

v_temp_shelly = 13 # temperature
v_temp_meross = 14

v_log = 15 # push to display log in terminal
v_refresh = 17 # push refresh gauge (normally upodated only if automation update, or manual on:off, or every n cycle)
v_total_heater = 16 # eddy + all heaters 
v_monit = 18 # terminal, monit summary

v_sleep = 19 # sec beetween cycle
v_react_to_surplus = 20 # wait cycles before taking action
v_react_to_soutir = 21

# used to turn OFF heater when entering nite, ie leave automation to a know state
# BUT do turn OFF ONLY ONCE, to enable other policy to manage heater
nite_only_once = True 

################ myenergi ############################
hub_serial = secret.hub_serial
hub_pwd = secret.hub_pwd
director_url = secret.director_url

# Rather then basing the target server on the last digit of the hub serial number, 
# the preferred approach is to make an API call to the "Director" - https://director.myenergi.net

try:
    response = requests.get(director_url, auth=HTTPDigestAuth(hub_serial, hub_pwd))
    #print(response)
    #print(response.headers)
    myenergi_server_url = response.headers['X_MYENERGI-asn']
    print('myenergi server' , myenergi_server_url)

except Exception as e:
    s = 'exception getting myenergi server url %s' %str(e)
    print(s)
    logging.error(s)
    myenergi_server_url = None


###############
# eddi power from myenergi cloud
# returns power or None
###############

eddi_dict = {1:"Paused", 3:"Diverting", 4:"Boost", 5:"Max Temp Reached", 6:"Stopped"}
#  It looks like properties that have the value zero are dropped from the object. Assuming that this is the same for Zappi too. **


def get_eddi_diversion(server_url):
    url = "https://" + server_url + '/cgi-jstatus-*'

    try:

        response = requests.get(url, auth=HTTPDigestAuth(hub_serial, hub_pwd))
        if response.status_code == 200:
            eddi_div = response.json()[0]['eddi'][0]['div']
            return(eddi_div)
            #print('eddi energy added ', response.json()[0]['eddi'][0]['che'])
            #print('eddi status ', eddi_dict[response.json()[0]['eddi'][0]['sta']])

    except Exception as e:
        s = 'exception getting power from myenergi cloud %s' %str(e)
        print(s)
        logging.error(s)
        return(None)


################ ENVOY ############################
pp = pprint.PrettyPrinter(indent=4)

envoy_host = secret.envoy_host # IP address
envoy_password = secret.envoy_password
envoy_user = secret.envoy_user
auth = HTTPDigestAuth(envoy_user, envoy_password)

marker = b'data: '

################ shelly ############################
# https://shelly-api-docs.shelly.cloud/gen1/#shelly1-shelly1pm

# list with IP addresses, or virtual pins

shelly_ip = ["http://192.168.1.188/", "http://192.168.1.189/"] # 1PM, plug S. order specifies primary and secondary
shelly_led = [v_led_shelly, v_led_meross]
shelly_power = [v_power_shelly, v_power_meross]
shelly_temp = [v_temp_shelly, v_temp_meross]
shelly_switch = [v_shellyonoff, v_merossonoff]
shelly_pilote = [1200, False] # for fil pilote, shelly power is not meaningfull
shelly_name = ["living room", "kitchen"]


# to do. include meross and multiple secondaries
primary_index = 0 # default primary

################ PZEM 004 ############################
# default P3, S0 = mini uart = GPIO 14,15     AMA0 = full uart = BT
# disable console
pzem_port = "/dev/ttyS0"

#################
# config
#################

# do no do anything if grid is in this band
grid_max = 250 # 
grid_min = -grid_max # 

#primary_is_shelly = True # default, updated in Blynk GUI
shelly_heater = 0 # index into array. default, updated at start up with GUI sync

primary_is_on = False # keep track of which heater is on
secondary_is_on = False # should match ison property of heater. note, because of thermostat, a heater could be on, and not consume power

sleep_sec = 60 # sec sleep between automation loop. updated by GUI

sleep_after_react = 10 # when turning heater ON/OFF. allow eddi to stabilize ??

blynk_update_count = 5 # update Blynk GUI every n loop

# updated by gui (damping)
react_to_surplus_max = 3 # decremented 
react_to_surplus = react_to_surplus_max  # react when this drops to zero (damping)

react_to_soutir_max = 3 
react_to_soutir = react_to_soutir_max

# if surplus and router below this, there is a problem
# assumes 2Kw heater, and always connectec
expected_solar_router_power = 1800 # 

max_temp_shelly = 55 # shut down temperature

sun = Sun(latitude, longitude)

# Get today's sunrise and sunset in UTC
today_sr = sun.get_sunrise_time()
today_ss = sun.get_sunset_time()
print('sun rise set UTC', today_sr, today_ss)
#print('sun set UTC', today_ss)

#convert to UTC
local_zone = tz.tzlocal()

sr_local = today_sr.astimezone(local_zone)
ss_local = today_ss.astimezone(local_zone)

sun_rise = int(sr_local.strftime('%H'))
sun_set = int(ss_local.strftime('%H'))
print('sun rise local %d, sun set local %d' %(sun_rise, sun_set))

# set up SPI display, font, return None if cannot create display
(display, font) = my_st7789.st7789_create_display()

if display != None:
    s = "st7789 display ok"
    print(s)
    logging.info(s)

    # create new image and use draw to paint into it
    (image, draw) = my_st7789.st7789_new_image()
    
    # splash at start
    # writing stats will create new image each time
    my_st7789.st7789_splash_jpg("./meaudre.jpg", display)

else:
    s = "cannot create st7789 display"
    print(s)
    logging.error(s)



#######
# print/log 
# pushover 
# blynk notif
######

def notify_error(s, send_notif=True):
    print(s)
    logging.error(s)
 
    if send_notif:
        pushover.send_pushover(s, title="solar2heater error", priority=1, sound='cosmic')
        try:
            blynk.log_event("system_error", s) # use event code
        except:
            pass





#############
# shelly
# simple REST
# return(ison, power)
#############


###################
# react on overtemp
# stop automation
# stop relay . note for fil pilote, this may need close relay
##################

def shelly_turn_off_overtemp():
    global primary_is_on, secondary_is_on, automation

    automation = False

    print('overtemp, turn heaters off')
    for index in [0,1]:
        shelly_onoff_by_index(index, 'off')
        blynk.virtual_write(shelly_led[index], 0)
    primary_is_on = False
    secondary_is_on = False

# get index into config table from a logical role (primary or secondary)
def get_index(role) -> int:
    # convert logical "primary" into physical (index)
    # primary_index is a global set in GUI. is index in config table of heater considered as "primary"
    # TO DO: better, more generic

    index = -1

    if role == "primary" and primary_index == 0:
        index = 0
    if role == "primary" and primary_index == 1:
        index = 1
    if role == "secondary" and primary_index == 0:
        index = 1
    if role == "secondary" and primary_index == 1:
        index = 0

    return(int(index))

def get_role(index):
    # convert physical (index) into role ("primary")
    if index == primary_index:
        return("primary")
    else:
        return("secondary")


#############
# index into table of IP addresses
# manage fixed power for fil pilote
# turn off and notify in case of overpower, overtemp, temp too large
# returns (status, last_shelly_power, temp, overt) or (None, ..)
#############

def get_shelly_power_by_index(index):
    # get power and status

    # "relays":[{"ison":true,"has_timer":false,"timer_started":0,"timer_duration":0,"timer_remaining":0,"overpower":false,"source":"http"}]
    # "meters":[{"power":862.92,"overpower":0.00,"is_valid":true,"timestamp":1666956857,"counters":[684.519, 0.000, 0.000],"total":36447}]
    # "inputs":[{"input":0,"event":"","event_cnt":0}]
    # "temperature":35.87,"overtemperature":false,"tmp":{"tC":35.87,"tF":96.57, "is_valid":true},"temperature_status":"Normal",

    url = shelly_ip[index] + "status"
    #print('get shelly power status for ', shelly_heater, url)
    try:
        res = requests.post(url)
        if res.status_code != 200:
            notify_error('shelly error http. statuis code: ' + str(res.status_code))
            return(None,None,None,None)
    except Exception as e:
        s = "exception shelly REST %s" %str(e)
        notify_error(s)
        return(None,None,None,None)
        

    else:

        # status
        status = res.json()['relays'][0]['ison']

        # power
        if shelly_pilote[index] == False:
            power = res.json()['meters'] [0] ['power'] # Current real AC power being drawn, in Watts
        else:
            if status == False:  # hardcode power to known heater consumption if heater is on , ie relay if OFF 
                power = shelly_pilote[index] 
            else:
                power = 0.0
        
        # overpower, overtemp, temp
        overpower = res.json()['relays'][0] ['overpower']
        if float(overpower) > 0.0:

            shelly_turn_off_overtemp()

            s = 'shelly overpower detected %s' %str(overpower)
            notify_error(s)

    
        """
        # not available on shelly plug S. related to ext temp sensor ?
        temp_status = res.json()['temperature_status']
        if temp_status != "Normal":
            handle_error('error shelly temperature status')
        else:
            print('temp status ', temp_status)
        """

        temp = res.json()['temperature']
        if temp > max_temp_shelly:
            # turn off
            shelly_turn_off_overtemp()

            s = 'shelly temp %0.1f too large. limit %0.1f' %(temp, max_temp_shelly)
            notify_error(s)
        

        overtemp = res.json()['overtemperature']
        if overtemp:
            # turn off
            shelly_turn_off_overtemp()

            s = 'shelly overtemp %0.1f detected' %overtemp
            notify_error(s)
    

        return(status, float(power), temp, overtemp)

        """
        power drawn Watt 30.63
        meter self check  True
        time stamp  2022-10-19 12:16:12
        total Wmn  15
        last 3mn, in Wm  [0.0, 0.0, 0.0]
        is on  True
        overpower  False
        temp  33.78 Normal
        """


###################################################
# ENVOY
# local web server
# several tries
# TOTAL CONSO - PRODUCTION = NET CONSO (is <0 , export)
# TOTAL CONSO includes eddy  
# returns net_conso, production, total_conso
###################################################

def envoy_get_production():
    url = 'http://%s/production.json' % envoy_host # single shot response

    # no need for password
    max_try = 5
    for i in range (max_try):

        try:
            response = requests.get(url, auth=None, stream=False, timeout=5, params={},  headers={}, data={})

            if response.status_code != 200:
                i = i + 1
                if i > max_try:
                    s = "http error while getting envoy data. try: %d. response code: %s" %(i, response.status_code)
                    notify_error(s)
                    print(s)
                    return(None,None,None)
                else:
                    sleep(10)

            else:
                break
        
        except Exception as e:
            s = "exception getting envoy production %s" %(str(e))
            notify_error(s)
            print(s)
            return(None,None,None)



    # response.raise_for_status() returns an HTTPError object if an error has occurred during the process
    #response.raise_for_status() #  

    # headers
    headers = response.headers # dictionary-like object
    #print(headers) 
    # {'Date': 'Tue, 18 Oct 2022 08:20:41 GMT', 'Pragma': 'no-cache', 'Expires': '1', 'Cache-Control': 'no-cache', 'Connection': 'close', 'Content-Type': 'application/json', 'Transfer-Encoding': 'chunked'}
    # response.headers['Content-Type']) # content type  application/json
    
    # response.content # response’s content in bytes b'{"production":[{"type":"inverters","activeCount":12,
    
    # convert bytes to string
    #response.encoding = 'utf-8' or else try to guess

    # better use pprint
    #print('content as string\n' , response.text) # # convert them into a string  
    
    # 2 ways to get json
    content = response.json() # dict
    content1 = json.loads(response.text) 
    assert content == content1

    # pprint list tuple, dict
    #pp.pprint(content)

    # consumption [0] total-consumption, [1] net-consumption
    # production [0]  active count=12inverter wNow, [1] count=1 eim wNow

    try:
        x = content['consumption'][0]['measurementType']
        if x == 'total-consumption':
            total_conso = content['consumption'][0]['wNow'] # float
    except Exception as e:
        notify_error('envoy json ' + str(e))
        return (None, None, None)

    try:
        x = content['consumption'][1]['measurementType']
        if x == 'net-consumption':
            net_conso = content['consumption'][1]['wNow'] # # net consumption. surplus negative
    except Exception as e:
        notify_error('envoy json ' + str(e))
        return (None, None, None)

    try:
        production = content['production'][1]['wNow']
    except Exception as e:
        notify_error('envoy json ' + str(e))
        return (None, None, None)


    # TOTAL CONSO - PRODUCTION = NET CONSO (is <0 , export)
    #print('total conso %0.2f production %0.2f net conso %0.2f  delta %0.2f' %(total_conso, production, net_conso, total_conso - production))

    return(net_conso, production, total_conso)




def init_pzem():
    try:
        master = modbus_rtu.RtuMaster( serial.Serial(port=pzem_port, baudrate=9600, bytesize=8, parity='N', stopbits=1, xonxoff=0))
        #master.set_timeout(5.0)
        #master.set_verbose(True)
        #logger.info("rtu master connected")
        return(master)
    except Exception as e:
        notify_error('cannot create RTU master %s. exit ' %str(e))
        sys.exit(1)


###################
# read router power with PZEM 004T
# try pzem, then cloud
# return power, pzem or None, None
# pzem = True is PZEM read ok; means real time data
# not sure how real time is cloud data
# eddy power used for stats only, not as condition for automation
##################

def read_pzem():

    #volt = None
    #amps = None
    power = None

    #master = init_pzem()

    # I do not remember why I decided not to read amps and volt, but anyway only the power matters

    """
    try:
        volt = master.execute(1, 4 , 0, 1) # 16 bits.  0.1V  (2323,) <class 'tuple'>  int
        #print(volt)
        volt = volt[0]/10.0
        #print('pzem volt: %0.1f' %volt)
    except Exception as e:
        #handle_error('exception read PZEM input register: %s' %str(e)
        pass
 

        # 01 04 00 00 00 01 CRC  register start at 0 , 1 word
        # 01 04 02 09 09 CRC 0x0909 = 2313   231.1v

        # PZEM amps
        # 01 04 00 01 00 02 CRC    register start from 1 , 2 words
        # 25 ms
        # 01 04 04 00 15 00 00 CRC   0x15  = 21   returns 4 bytes
        #amps low ma:  21  
        #amp high ma:  0
        # 21 ma

    try:
        f_word_pair = master.execute(1, cst.READ_INPUT_REGISTERS, 0x01, 2) # 2 x 16 bits , 1st one is low 16 bits   milli amps
        # f word pair:  (0, 0) <class 'tuple'> <class 'int'>
        #print(f_word_pair)

        amp_low = f_word_pair[0] # low 16 bits   65536 ma = 65 amps. max read for me. can safely disgard high 16 bits 
        amp_high = f_word_pair[1] # high 16 bits, to create 32 bit integer (representing ma)
        assert (amp_high == 0)

        # TypeError: object with buffer protocol required
        #print(binascii.hexlify(amp_low))

        amps = amp_low/1000.0
        #print('pzem amps: ' , amps) # assume same indianess
    except Exception as e:
        #handle_error('exception read PZEM input register: %s' %str(e))
        pass
    """

    # read power
    max_try = 5

    for i in range(max_try):
    
        try:
            f_word_pair = master.execute(1, cst.READ_INPUT_REGISTERS, 0x03, 2) # 2 x 16 bits , 1st one is low 16 bits   milli amps
            # f word pair:  (0, 0) <class 'tuple'> <class 'int'>
            #print(f_word_pair)

            power_low = f_word_pair[0] # low 16 bits  0.1W  65535 = 6500W max. so gigh 16 bit should always be zero in my case
            power_high = f_word_pair[1] # high 16 bits, to create 32 bit integer 
            assert power_high == 0

            power = power_low / 10.0
            print('pzem power SUCCESS: ' , power, i) # assume same indianess
            break

        except Exception as e:
            print("exception PZEM", str(e))
            i = i + 1
            if i > max_try:
                print("TOO MANY exception PZEM", str(e))
                power = None
                break
            else:
                sleep(5)

    if power != None:
        # PZEM OK 
        return(power, True) # last bool says data comming from PZEM, so is real time

    if power is None:
        #handle_error('cannot read PZEM input register POWER')
        s = 'cannot read PZEM power after %d tries. try cloud' %max_try
        print(s)
        logging.error(s)

        # try with myenergi API
        # data may not be real time
        try:
            power = get_eddi_diversion(myenergi_server_url)
            print('eddi diverted power from cloud', power)
            return(power, False)

        except Exception as e:
            s = "cannot read power from myenergi %s" %str(e)
            print(s)
            logging.error(s)
            return(None,None)



        #logger.info(master.execute(1, cst.READ_COILS, 0, 10))
        #logger.info(master.execute(1, cst.READ_DISCRETE_INPUTS, 0, 8))
        #logger.info(master.execute(1, cst.READ_INPUT_REGISTERS, 100, 3))
        #logger.info(master.execute(1, cst.READ_HOLDING_REGISTERS, 100, 12))
        #logger.info(master.execute(1, cst.WRITE_SINGLE_COIL, 7, output_value=1))
        #logger.info(master.execute(1, cst.WRITE_SINGLE_REGISTER, 100, output_value=54))
        #logger.info(master.execute(1, cst.WRITE_MULTIPLE_COILS, 0, output_value=[1, 1, 0, 1, 1, 0, 1, 1]))
        #logger.info(master.execute(1, cst.WRITE_MULTIPLE_REGISTERS, 100, output_value=xrange(12)))

    #master._do_close()
    #del(master)

        return(volt, amps, power, False)

    #except modbus_tk.modbus.ModbusError as exc:
    #    logger.error("%s- Code=%d", exc, exc.get_exception_code())



###################
# set relay
# use physical addressing, ie index into list, ie not virtual (primary)
# convert index of actual heater into url
# set Blynk led
# 1st shelly is connected to fil pilote.  relay OFF = heater on. relay ON = anti freeze , ie heater off
###################

def shelly_onoff_by_index(index, command): # shelly_heater is index 0, 1
    if command == 'on':
        if index == 0:
            url = shelly_ip[index] + "relay/0?turn=off" # fil pilote
        else:
            url = shelly_ip[index] + "relay/0?turn=on"

        print('turn shelly on' , index, url)
        res = requests.post(url)
        if res.status_code != 200:
            notify_error('shelly error REST. status code: %s' %str(res.status_code))
        else:
            blynk.virtual_write(shelly_led[index], 1)
            # set property
            blynk.set_property(shelly_switch[index], "OnLabel", "set ON")
            blynk.set_property(shelly_switch[index], "color", "#D3435C")

    elif command == 'off':
        if index == 0:
            url = shelly_ip[index] + "relay/0?turn=on" # fil pilote
        else:
            url = shelly_ip[index] + "relay/0?turn=off"

        print('turn shelly off' , index, url)
        res = requests.post(url)
        if res.status_code != 200:
            notify_error('shelly error REST ' + str(res.status_code))
        else:
            blynk.virtual_write(shelly_led[index], 0)
            blynk.set_property(shelly_switch[index], "OffLabel", "set OFF")
            blynk.set_property(shelly_switch[index], "color", "#04C0F8")
 
    else:
        print('bad command')
        return(None,None)



#######
# set_heater('primary', 'on')
# logical. calls shelly_onoff(index, command) and shelly_power(index)
# sleep before getting back power
# update power and temp GUI  (led GUI done in onoff)
# return index, shelly power
############ for fil pilote, shelly power is not meaningfull
#######
def set_heater_by_role(heater, command):

    # heater is "primary" or "secondary"

    # record state is done in calling

    index = get_index(heater)

    print('set logical heaters %s to %s. primary index %s, physical index %s' %(heater, command, primary_index, index))

    # set actual shelly heater as designated by index
    # update led
    shelly_onoff_by_index(index, command) # shelly_heater global set by GUI. 0, 1, index into shelly_ip[]

    sleep(15) # time to get power reading

    # read power and temp
    (status, last_shelly_power, temp, overt) = get_shelly_power_by_index(index)
    print('shelly index %d:  ison %s, power %0.0f, temp %0.1f, overtemp %s ' %(index, str(status) , last_shelly_power, temp, str(overt)))

    # update blynk power and temp value
    if last_shelly_power != None:
        blynk.virtual_write(shelly_power[index], last_shelly_power)

    if temp != None:
        blynk.virtual_write(shelly_temp[index], temp)

    # led update done in shelly_onoff

    return



####################################
# Blynk thread
####################################

def run_blynk_thread(x):
    print('start blynk thread. endless loop')

    while True:
        blynk.run()
        timer.run()


#################################### MAIN #####################################


# will be synched later. global, set in blynk call backs
automation = True

# initialize blynk
blynk = BlynkLib_1_0_0.Blynk(BLYNK_AUTH_TOKEN, server=server)
print('blynk initialized')


#####################
# blynk call back
#####################

#@blynk.on("V11") with latest version


# master automation on/off switch
s = "V%d" %v_automation
@blynk.on(s)
def f_v_automation(value):
    global automation
    print('Blynk call back: set automation master switch: ', value) # automation:  ['0']
    if value[0] == '0':
        automation = False
        blynk.virtual_write(v_terminal, 'automation disabled')
    else:
        automation = True
        blynk.virtual_write(v_terminal, 'automation enabled')

    blynk.virtual_write(v_led_automation, value[0])
    print('automation ', automation)

# sleep
s = "V%d" %v_sleep
@blynk.on(s)
def f_v_sleep(value):
    global sleep_sec
    print('Blynk call back: set sleep sec: ', value) # 
    sleep_sec = int(value[0])
    blynk.virtual_write(v_terminal, 'sleep between cycle: %d' %sleep_sec)

# damping
s = "V%d" %v_react_to_surplus
@blynk.on(s)
def f_v_react_to_surplus(value):
    global react_to_surplus, max_react_to_surplus
    print('Blynk call back: set react_to_surplus: ', value) # 
    max_react_to_surplus = int(value[0])
    react_to_surplus = max_react_to_surplus
    blynk.virtual_write(v_terminal, 'react to surplus : %d' %react_to_surplus)


s = "V%d" %v_react_to_soutir
@blynk.on(s)
def f_v_react_to_soutir(value):
    global react_to_soutir, max_react_to_soutir
    print('Blynk call back: set react_to_soutir: ', value) # 
    max_react_to_soutir = int(value[0])
    react_to_soutir = max_react_to_soutir
    blynk.virtual_write(v_terminal, 'react to soutir : %d' %react_to_soutir)



###########
# display last lines of log file in terminal
# display monit summary
###########
s = "V%d" %v_log
@blynk.on(s)
def f_v_log(value):
    nb = 15 # seems there is a pb if too large ?
    print('log: ', value) # automation:  ['0']
    index = 0
    if value[0] == '0': # ['1'] , then 0
        pass
    else:
        # display log in terminal
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines() # array
                n = min(nb, len(lines))
                last_lines = lines[-n:]
                # ['INFO:root:2022-11-09 10:25:12.386019 \n', '-------------- surplus starting ...............\n', 'INFO:modbus_tk:RtuMaster /dev/ttyS0 is opened\n', 
                s = ""
                for line in last_lines:
                    s = s + line
                    blynk.virtual_write(v_terminal, line)

                print('writing log to v_terminal: ', s)

        except Exception as e:
            s = "exception reading log file %s" %str(e)
            print(s)
            blynk.virtual_write(v_terminal, s)

        try:
            s= monit_mail.monit_summary()
            print(s)
            blynk.virtual_write(v_monit, s)
            blynk.virtual_write(v_terminal, "writing to monit terminal")

        except Exception as e:
            s = "exception blynk summary %s" %str(e)
            print(s)
            blynk.virtual_write(v_terminal, s)
            blynk.virtual_write(v_monit, s)



###########
# refresh gauge with real time data
###########

s = "V%d" %v_refresh
@blynk.on(s)
def f_v_refresh(value):
    print('Blynk call back: refresh gauge: ', value) # automation:  ['0']
    index = 0
    if value[0] == '0':
        pass
    else:

        # grid, production
        # shelly
        # router, total heater

        (net_conso, production, total_conso) = envoy_get_production()
        if net_conso != None:
             blynk.virtual_write(v_power_grid, net_conso)
             blynk.virtual_write(v_power_production, production)
             # grid is net_conso
             blynk.virtual_write(v_terminal, "refreshing.. grid (envoy): %0.1f Kw, production: %0.1f Kw" %(net_conso, production))

        else:
             blynk.virtual_write(v_terminal, "refreshing.. error envoy")

        (status, last_shelly_0_power, temp_shelly, overt) = get_shelly_power_by_index(0)
        (status, last_shelly_1_power, temp_meross, overt) = get_shelly_power_by_index(1)

        blynk.virtual_write(shelly_power[0], last_shelly_0_power)
        blynk.virtual_write(shelly_temp[0], temp_shelly)

        blynk.virtual_write(shelly_power[1], last_shelly_1_power)
        blynk.virtual_write(shelly_temp[1], temp_meross)

        blynk.virtual_write(v_terminal, "refreshing.. %s: %0.1f Kw, %s: %0.1f Kw"  %(shelly_name[0], last_shelly_0_power, shelly_name[1], last_shelly_1_power))

        (router_power, pzem_was_ok) = read_pzem()

        if router_power != -1:
            blynk.virtual_write(v_power_eddy, router_power)

            total_heater = router_power + last_shelly_0_power + last_shelly_1_power
            blynk.virtual_write(v_total_heater, total_heater)

            blynk.virtual_write(v_terminal, "refreshing.. router: %0.1f Kw. total heater: %0.1f Kw . PZEM %s"  %(router_power, total_heater, pzem_was_ok ))
        else:
            blynk.virtual_write(v_terminal, "refreshing.. error router power")

@blynk.on("connected")
def blynk_connected(ping):
    print('Blynk ready. Ping:', ping, 'ms')
    print("synching")
    blynk.sync_virtual(v_automation, v_sleep, v_react_to_surplus, react_to_soutir)

@blynk.on("disconnected")
def blynk_disconnected():
    print('Blynk disconnected')


###########
# set heater on off manually using GUI
###########   

# generic processing of on/off switch
# turn heater on off, update is_on flag
# get power and temp, update blynk GUI incl led
# on off from GUI, not automation
# value int
def manual_onoff(index, value):

    global primary_is_on
    global secondary_is_on

    print('onoff switch: ', value) # 
    print('should you ALSO turn automation off ??')

    role = get_role(index)

    if value == 0:
        # set actual heater 
        shelly_onoff_by_index(index,'off')

        # update onoff status
        if role == "primary":
            primary_is_on = False
        if role == "secondary":
            secondary_is_on = False
    else:
        shelly_onoff_by_index(index, 'on')

        if role == "primary":
            primary_is_on = True
        if role == "secondary":
            secondary_is_on = True

    sleep(10)

    # read power and update blynk power, temp and led
    (status, last_shelly_power, temp, overt) = get_shelly_power_by_index(index)

    s = 'heater set manually: index %d, value %d. ison %s, power %0.0f, temp %0.1f, overtemp %s ' %(index, value, str(status) , last_shelly_power, temp, str(overt))
    print(s)
    logging.info(s)

    # update led, temperature, power gauge, 
    if last_shelly_power != None:
        blynk.virtual_write(shelly_power[index], last_shelly_power)

    blynk.virtual_write(shelly_led[index], value) # turn led on off
    blynk.virtual_write(shelly_temp[index], temp)
    blynk.virtual_write(v_terminal, s)

    # TO DO, change button state, ie color, text


# actually 2nd shelly 
s = "V%d" %v_merossonoff
@blynk.on(s)
def f_v_merossonoff(value):  # value ['1'] for ON
    index = 1
    value = int(value[0])
    s = "Blynk call back: shelly index: %d, on/off value: %d" %(index, value)
    print(s)
    logging.info(s)

    manual_onoff(index, value)


s = "V%d" %v_shellyonoff
@blynk.on(s)
def f_v_shellyonoff(value): # value ['1'] for ON
    index = 0 
    value = int(value[0])
    s = "Blynk call back: shelly index: %d, on/off value: %d" %(index, value)
    print(s)
    logging.info(s)

    manual_onoff(index, value)



# select primary heater, write to terminal

s = "V%d" %v_select
@blynk.on(s)
def f_v_select(value):
    global primary_index
    print('Blynk call back: select primary heater: ', value)
    
    if value[0] == '0': # shelly defined as 0 in widget
        blynk.virtual_write(v_terminal, 'primary heater is 0')
    elif value[0] == '1':
        blynk.virtual_write(v_terminal, 'primary heater is 1')
    else:
        pass

    primary_index = int(value[0]) # index in array , primary heater
    s = 'index for primary %d' %primary_index
    print(s)
    logging.info(s)


#######################################
# MAIN
#######################################

timer = BlynkTimer()
#timer.set_timeout(2, hello) # run once
#timer.set_interval(4, power) # run multiple


# start Blynk run thread

id1= _thread.start_new_thread(run_blynk_thread, ('pabou',))


# terminal and event
blynk.virtual_write(v_terminal, 'solar2heater starting')

#blynk.log_event("starting", "solar2heater starting") # use event code

# print('synch select primary and automation)
blynk.sync_virtual(v_select)
blynk.sync_virtual(v_automation)

print('turn heaters off at start')
# otherwize house consumption reading will be off
for i in [0,1]:
    shelly_onoff_by_index(i, 'off')

print("init modbus")
# init MODBUS for PZEM 004T
# no loggin to not polluate file dump to terminal 
#logger = modbus_tk.utils.create_logger("console")
master = init_pzem()

#############################################################################################################

### main automation loop 

#############################################################################################################


nb_loop = 0 # count automation loops. update GUI every n count


while True:

    updated_heater = False


    print('\n')

    d = time.localtime(time.time()).tm_mday
    h = time.localtime(time.time()).tm_hour
    m = time.localtime(time.time()).tm_min

    stamp = "%d/%d:%d " %(d, h, m)
    limit_nite = ">= %s, <= %d" %(sun_set-1, sun_rise+2)

    # do nothing when there is no sun
    # sunrise Local 7am, 1kw production 9pm

    # sun rise local 7
    # 9:27 , still considered nite
    nite = (h >= sun_set-1 or h <= sun_rise+2)

    print ('Nite: %s. react to surplus: %d, react to soutir %d' %(str(nite), react_to_surplus, react_to_soutir))

    router_power = -2 # ie not read. only read if surplus but printed at end of loop. -1 means error reading PZEM

    if automation == True and nite == False:

        # read inject/draw from grid
        # # TOTAL CONSO - PRODUCTION = NET CONSO (is <0 , export)

        (net_conso, production, total_conso) = envoy_get_production() 

        if net_conso is None or production is None or total_conso is None:

            # cannot read envoy. exit and hope someone (systemd, monit) will restart
            # anyway, without grid reading there is nothing we can do
            notify_error('cannot read envoy. EXIT')
            sys.exit(1)

        else:
            print('net conso from envoy: %0.1f Watt (surplus if negative). production %0.1f. Total home conso %0.1f '  %(net_conso, production, total_conso)) # negative if surplus
            pass

        # read solar router using PZEM/modbus BEFORE acting on surplus or draw
        (router_power, pzem_was_ok) = read_pzem()

        if router_power is None:

            # do not fill log with that. keep log for state change
            #handle_error('cannot read PZEM power', False) # do not send pushover 
            blynk.virtual_write(v_terminal, 'cannot read power')
            #sys.exit(1)
            # eddy power used for stats only, not as condition for automation

            router_power = -1  # means error 

        else:
            print('power diverted %0.1f, PZEM OK: %s' %(router_power, pzem_was_ok))


        # read power from heaters
        index = 0
        (status, last_shelly_0_power, temp_shelly_0, overt) = get_shelly_power_by_index(index)
        print('shelly power %s: index %d, ison %s, power %0.0f, temp %0.1f, overtemp %s ' %(shelly_name[index], index, str(status) , last_shelly_0_power, temp_shelly_0, str(overt)))
        
        index = 1
        (status, last_shelly_1_power, temp_shelly_1, overt) = get_shelly_power_by_index(index)
        print('shelly power %s: index %d, ison %s, power %0.0f, temp %0.1f, overtemp %s ' %(shelly_name[index], index, str(status) , last_shelly_1_power, temp_shelly_1, str(overt)))

        print("entering LOOP: production %0.0f, eddy %0.0f, grid (- is inject) %0.0f, home conso (incl eddy) %0.0f" %(production, router_power, net_conso, total_conso))
        
        
        # if surplus exist, the solar router should be max'ed out. 

        if net_conso < grid_min and  router_power < expected_solar_router_power and router_power not in [-1, -2]:
            # could be race condition
            s = 'surplus %0.1f, while solar router not diverting enough %0.1f (expected %d)' %(net_conso, router_power, expected_solar_router_power)
            logging.warning(s)
            print(s)
            blynk.virtual_write(v_terminal, stamp + s)

        # if drawing, the solar router should be at zero 
        if net_conso > grid_max and router_power > 200 and router_power not in [-1,-2]:
            s = 'drawing from grid %0.1f, while solar router is still diverting %0.1f' %(net_conso, router_power)
            print(s)
            logging.warning(s)
            blynk.virtual_write(v_terminal, stamp + s)


        # a low production could mean nite, or sudden cloud. 
        # in later case, we still run to run automation (in case we starts drawing)

        ##############################
        # in band. no heater change
        #############################
        if net_conso < grid_max and net_conso > grid_min:
            s = '>>> do nothing. net conso %0.0f within band %d' %(net_conso, grid_max)
            print(s)


        # thermostat. shelly conso primary drops, so seen as new surplus, 
        # system believes primary is still on, so fire secondary. 
        # now both on
        # should be OK. corrected in next loop, as it will show a grid draw 


        ###################
        # grid not within band
        ###################

        else:

            if net_conso < grid_min:
                #################
                # surplus exist
                #################

                s = '>>> we have surplus %0.1f, react to surplus %d. solar router should be at its max %0.1f' %(net_conso, react_to_surplus, router_power)
                print(s)
                logging.info(s)

                # do not react immediatly, spurious reading, or sudden change
                if react_to_surplus !=0: # wait to see if condition persist 
                    react_to_surplus = react_to_surplus -1
                    print('do nothing. wait. react_to_surplus %d' %react_to_surplus)


                else: # react when react_to_grid = 0

                    react_to_surplus = react_to_surplus_max

                    #################
                    # manage surplus
                    # turn heater based on stored is_on status
                    #################

                    s = 'react to surplus: primary %s. primary is on %s, secondary is on %s' %(shelly_heater, primary_is_on, secondary_is_on) 
                    print(s)
                    logging.info(s)
                    # as we have surplus, turn ONE heater on. 

                    if primary_is_on == False:
                        s = 'set primary on. surplus %0.0fW. router %0.0fW. production %0.0fW. total conso %0.0fW' %(net_conso, router_power, production, total_conso)
                        print(s)
                        logging.info(s)
                        blynk.virtual_write(v_terminal, stamp + s)

                        # turn heater ON
                        set_heater_by_role('primary', 'on')  # set Blynk power and temp led
                        primary_is_on = True

                        GPIO.output(led_red,1)
                        updated_heater = True

                        sleep(sleep_after_react)
                        

                    elif secondary_is_on == False:

                        s = 'set secondary on. surplus %0.0fW. router %0.0fW. production %0.0fW. total conso %0.0fW' %(net_conso, router_power, production, total_conso)
                        print(s)
                        logging.info(s)
                        blynk.virtual_write(v_terminal, stamp + s)

                        # turn heater ON
                        set_heater_by_role('secondary', 'on')
                        secondary_is_on = True

                        GPIO.output(led_red,1)
                        updated_heater = True

                        sleep(sleep_after_react)


                    else: # both heaters already on
                        s = 'cannot turn heater ON. all heaters already on'
                        print(s)
                        logging.info(s)
                        blynk.virtual_write(v_terminal, stamp + s)

                        sleep(sleep_after_react)


            if net_conso >  grid_max:
                #############
                # drawing power from grid
                # this is not nite
                # turn heaters off
                #############

                # of course at nigth we are drawing power, but this case is excluded there (tested earlier)
                # we would draw if production drops (cloud, sunset), in that case we need to turn heater(s) off
                s = '>>>>> we are drawning from grid %0.1f. react to soutir %d. solar router should be at its min %0.1f' %(net_conso, react_to_soutir, router_power)
                print(s)
                logging.info(s)

                # do not react immediatly, spurious reading, or sudden change
                if react_to_soutir != 0: # wait to see if condition persist 
                    print('do nothing. wait. react to soutir %d' %react_to_soutir)
                    react_to_soutir = react_to_soutir -1

            
                else: # react to soutir

                    react_to_soutir = react_to_soutir_max

                    s  ='react to soutir. primary %s. primary is on %s, secondary is on %s' %(shelly_heater, primary_is_on, secondary_is_on) 
                    print(s)
                    logging.info(s)

                    # as we are drawing, turn ONE heater oFF. 
                    if secondary_is_on == True:
                        s = 'drawing from grid. set secondary off. surplus %0.0fW. router %0.0fW. production %0.0fW. total conso %0.0fW' %(net_conso, router_power, production, total_conso)
                        print(s)
                        logging.info(s)
                        blynk.virtual_write(v_terminal, stamp + s)

                        # turn heater OFF
                        set_heater_by_role('secondary', 'off') 
                        secondary_is_on = False

                        GPIO.output(led_red,0)
                        updated_heater = True

                        sleep(sleep_after_react)

                    elif primary_is_on == True:
                        s = 'drawing from grid. set primary off. surplus %0.0fW. router %0.0fW. production %0.0fW. total conso %0.0fW' %(net_conso, router_power, production, total_conso)
                        print(s)
                        logging.info(s)
                        blynk.virtual_write(v_terminal, stamp + s)

                        # turn heater OFF
                        set_heater_by_role('primary', 'off')
                        primary_is_on = False

                        GPIO.output(led_red,0)
                        updated_heater = True

                        sleep(sleep_after_react)

                    else:
                        s = 'drawing from grid. but all heaters already off.. surplus %0.0fW. router %0.0fW. production %0.0fW. total conso %0.0fW' %(net_conso, router_power, production, total_conso)
                        logging.info(s)
                        print(s)
                        blynk.virtual_write(v_terminal, stamp + s)

                        sleep(sleep_after_react)

        # end of grid band

        # end of one automation loop


        # heaters could have been updated, but use value from entering the loop
        # update TFT display and Blynk

        she = round(last_shelly_0_power + last_shelly_1_power, 0)
        all_heaters = she + router_power

        ####################
        # update SPI TFT for EACH automation loop
        # ====== > values at start of loop. should see result in next loop
        ####################

        if display != None:

            # create new image and use draw to piant into it
            (image, draw) = my_st7789.st7789_new_image()

            space = 15
            y = space

            # to do, better graphics
            # 255,255,255 is white

            # grid , aka net conso
            s = "grid: %d" %int(net_conso)
            size_x, size_y = draw.textsize(s, font)
            draw.text((2, y), s, font=font, fill=(255, 0, 0))
            y = y + size_y + space

            # solar production
            s = "solar: %d" %int(production)
            size_x, size_y = draw.textsize(s, font)
            draw.text((2, y), s, font=font, fill=(0, 255, 0))
            y = y + size_y + space

            # edi
            s = "divert: %d" %int(router_power)
            size_x, size_y = draw.textsize(s, font)
            draw.text((0, y), s, font=font, fill=(0, 0, 255))
            y = y + size_y + space

            # all heaters controlled by shelly AND eddi
            s = "all heaters: %d" %int(all_heaters)
            size_x, size_y = draw.textsize(s, font)
            draw.text((0, y), s, font=font, fill=(255, 0, 255))
            y = y + size_y + space

            
            # display resulting image
            display.display(image)  

        # end of TFT

        ######################################
        # every Blynk every so often OR if heater state changed
        # update all powers in Bkynk GUI
        # check monit summary
        # send email if monit error
        # ====== > values at start of loop. should see result in next loop
        ######################################

        nb_loop = nb_loop + 1

        if nb_loop == blynk_update_count or updated_heater:

            if nb_loop == blynk_update_count:
                nb_loop = 0

            ######### blynk
            print('publish to blynk')
            # ====== > values at start of loop. should see result in next loop

            blynk.virtual_write(v_power_grid, net_conso)
            blynk.virtual_write(v_power_production, production)

            # only update power if it came from PZEM, ie real time
            if router_power != -1 and pzem_was_ok == True:
                blynk.virtual_write(v_power_eddy, router_power)
                blynk.virtual_write(v_total_heater, router_power + last_shelly_0_power + last_shelly_1_power)

            # update heaters power. otherwize those are updated only in case of on/off
            blynk.virtual_write(shelly_power[0], last_shelly_0_power)
            blynk.virtual_write(shelly_temp[0], temp_shelly_0)

            blynk.virtual_write(shelly_power[1], last_shelly_1_power)
            blynk.virtual_write(shelly_temp[1], temp_shelly_1)


            ######### monit
            print('check monit summary')
            s = monit_mail.monit_summary()
            if s.find('NOK',0,len(s)) != -1 or s.find('limit', 0, len(s)) != -1 or s.find('failed',0,len(s)) != -1: # ie found
                logging.error(s)
                print(s)

                s = "monit error, sending email"
                logging.error(s)
                print(s)

                blynk.virtual_write(v_terminal, s)


                try:
                    monit_mail.send_mail(subject = "monit error", content = s)

                except Exception as e:
                    s = "exception sending email %s" %str(e)
                    notify_error(s)

                    blynk.virtual_write(v_terminal, s)

            else: # monit OK
                pass


        else: # do not update blynk yet
            pass 

        # TO DO garbage collection. ie eddy off and only heaters on.


    else: # automation = False or nite
        s = 'no automation or nite'
        print(s)

        if nite:
            s = "nigth"
        else:
            s = "automation OFF"

        spacing = 10 # for mulitiline str
        # align – If the text is passed on to multiline_text(), “left”, “center” or “right”.

        if display != None:
            # create new image and use draw to paint into it
            (image, draw) = my_st7789.st7789_new_image()
            draw.text((0, 20), s, font=font, fill=(255, 0, 0))
            draw.text((0, 100), stamp, font=font, fill=(0, 255, 0))

            s = "limit\n" + limit_nite
            draw.multiline_text((0, 180), s, font=font, fill=(100, 100, 100), spacing = spacing, align='right')
            display.display(image) 


        if nite:
            if nite_only_once:
                nite_only_once = False
                s = "nite: turn heater off ONCE"
                print(s)
                logging.info(s)

                # leave system in a clean state. assume another process (manual) will take over
                for index in [0,1]:
                    shelly_onoff_by_index(index, 'off')
            else:
                pass # leave heater alone during nite. allow another policy to take over

        if automation == False:
            pass # decision: leave system state as it. someboby else is using it


    sleep(sleep_sec)




