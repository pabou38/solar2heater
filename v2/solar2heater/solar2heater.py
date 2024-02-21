#!/usr/bin/python3

version = 3.1# 4 nov 2023. add remote pzem, use my_modules, blynk_client, add last actions
version = 3.2# 10 nov 2023. router_power = -1 for error
version = 3.21 # clean
version = 3.31 # 23 jan 2024 turn heaters OFF when automation disabled ? and when entering nite ?
version = 3.4 # 24 jan 2024 fix send_mail for monit error. system_error and system_warning. add parse_monit_summary() , web server 
version = 3.41 # 25 jan 2024. add button for behavior when automation disabled. feedback on automation button (incl button on/off label)
version = 3.50 # 26 jan 2024 clean logic
version = 3.51 # 27 jan 2024 catch signal (cron reboot at 2am)
version = 3.52 # 30 jan 2024 reverse input does not work (only for button) - for solar1 (pilot wire), so that logical ON = relay open/off = heater in "confort" mode (e ON)
version = 3.60 # 5 feb web server, remove manual on/off. automation/behavior button controlled by app (both GUI and web). color, label, content in vpins. action history uses widget's content vs labels
version = 3.61 # 12 feb  turn heaters off at app start only if automation is True
version = 3.62 # 14 feb. add HT temp sensor
version = 3.63 # 15 feb. add time stamp for HT sensor
version = 3.64 # 21 feb. move secret.py

import os
import sys
import time
from time import sleep
import signal

from typing import Tuple, Union, Optional

import RPi.GPIO as GPIO
from PIL import Image, ImageDraw, ImageFont

import my_arg
arg = my_arg.parse_arg()
print(arg)

local_pzem = arg["local"]

if local_pzem:
    print("use local (ie hardwired) PZEM")
else:
    print("use remote PZEM")

# convert UTC to local
from dateutil import tz
# pip install pytz
import pytz

#pip install suntime
# get sun rise, sun set
from suntime import Sun, SunTimeException
latitude = 45.12
longitude = 5.52

import logging
root = '/home/pi/APP/solar2heater/'
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
s = '--- solar2heater %0.2f starting ---'%version
print(s)
logging.info(s)

import _thread # low level
from threading import Lock
mutex1 = Lock() # automation is set from both GUI and web server

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


# PZEM only used for statistics, not required for automation loop 
# pip install modbus_tk Requirement already satisfied: modbus_tk in /home/pi/.local/lib/python3.9/site-packages (1.1.2)
import modbus_tk
import modbus_tk.defines as cst
from modbus_tk import modbus_rtu


from flask import Flask
from flask import request

sys.path.append("../Blynk/Blynk_client") # both new Blynk and legacy Blynk
sys.path.append("../PZEM_client") # python client for remote PZEM server running on ESP32
sys.path.append("../my_modules") # reusable modules
sys.path.append("../secret") # do not push this directory to github !!

import vpin
import my_blynk_new

# maintain only one version of the library
import remote_PZEM_python_client

import monit_mail

import my_st7789
import secret
import pushover

import my_web_server # reuse generic create and start from there. @app.route callbacks define in app
import my_log # time stamp

#################################
# send mail and pushover at start
# blynk event later (when blynk started)
#################################
pushover.send_pushover("solar2heater %0.2f starting" %version, title= "solar2heater", sound="cosmic")
monit_mail.send_mail(secret.sender_email, secret.email_passwd, secret.dest_email, subject="solar2heater starting", content = "version %0.2f. have fun" %version, html="False")

# GPIO
button = 20 # connected to gnd. pull up. used to long
led_red = 12 #  gpio out red
led_yellow = 24 #  gpio out yellow

# ISR from button
# long press = reboot
# short press = halt

def int_reboot(x):
    sleep(2) # sleeping in isr is not great, but will reboot or halt anyway
    if GPIO.input(button) == 0:
        s = 'reboot' # still pressed. long = reboot
    else:
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

################ Gpio config ############################
GPIO.setmode(GPIO.BCM)

# GPIO button
GPIO.setup(button, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# use interrupt. GPIO.RISING
GPIO.add_event_detect(button, GPIO.FALLING, callback=int_reboot, bouncetime=500)  

# gpio led
GPIO.setup(led_red, GPIO.OUT)
GPIO.setup(led_yellow, GPIO.OUT)

GPIO.output(led_red,0) # turn off 
GPIO.output(led_yellow,0) 

################ Blynk config ############################
BLYNK_TEMPLATE_ID = secret.BLYNK_TEMPLATE_ID
BLYNK_DEVICE_NAME = secret.BLYNK_DEVICE_NAME
BLYNK_AUTH_TOKEN  = secret.BLYNK_AUTH_TOKEN

server="blynk.cloud" # ping blynk.cloud
#server = "fra1.blynk.com"

################ remote PZEM config ############################
# 176 ac batter 177   eddi
pzem_server_ip = "192.168.1.177"
pzem_server_port = 5000


################ myenergi config ############################
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



eddi_dict = {1:"Paused", 3:"Diverting", 4:"Boost", 5:"Max Temp Reached", 6:"Stopped"}
#  It looks like properties that have the value zero are dropped from the object. Assuming that this is the same for Zappi too. **

###############
# get eddi power from myenergi cloud
###############
# returns power or None
# backup to PZEM
# not real time ?

def get_eddi_diversion(server_url):
    url = "https://" + server_url + '/cgi-jstatus-*'

    try:

        response = requests.get(url, auth=HTTPDigestAuth(hub_serial, hub_pwd))
        if response.status_code == 200:
            eddi_div = response.json()[0]['eddi'][0]['div']
            print("got eddi power from myenergi cloud", eddi_div)
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


# flat list , index in list 
primary_index = 0 # default primary. set by GUI

shelly_ip = ["http://192.168.1.188/", "http://192.168.1.189/"] # 1PM, plug S. 

# power vpin
shelly_power = [vpin.v_power_shelly, vpin.v_power_meross]

# temp vpin
shelly_temp = [vpin.v_temp_shelly, vpin.v_temp_meross]

# button on off vpin
#shelly_onoff_button = [vpin.v_shellyonoff, vpin.v_merossonoff]

# red led vpin. 
shelly_led = [vpin.v_led_shelly, vpin.v_led_meross]

# power. for fil pilote, shelly power is not meaningfull
shelly_pilote = [1200, False] 

# str to used eg as button label
shelly_name = ["living room", "kitchen"]

assert len(shelly_ip) == len(shelly_power)
assert len(shelly_ip) == len(shelly_temp)
#assert len(shelly_ip) == len(shelly_onoff_button)
assert len(shelly_ip) == len(shelly_led)
assert len(shelly_ip) == len(shelly_pilote)
assert len(shelly_ip) == len(shelly_name)

nb_shelly = len(shelly_ip)
print("%d shelly relay configured" %nb_shelly)


################ PZEM 004 ############################
# default P3, S0 = mini uart = GPIO 14,15     AMA0 = full uart = BT
# disable console
pzem_port = "/dev/ttyS0"

#################
# application config
#################

# used to turn OFF heater when entering nite, ie leave automation to a know state
# BUT do turn OFF ONLY ONCE, to enable other policy to manage heater
nite_only_once = True 

# do no do anything if grid is in this band
grid_max = 250 # 
grid_min = -grid_max # 

# index into array. default, updated at start up with GUI sync
shelly_heater = 0 


# keep track of which heater is on
# should match ison property of heater's RELAY ? NOT ALWAYS, if controlled externally by shelly app 
# set by react to overtemp, manual on/off, automation

# NOTE: because of thermostat, a heater could be physically on (ie confort mode), and not consume power
# NOTE: because of anti freeze, a heater could be physically off (ie HG), and consume power
# NOTE: this is the app view. the heater can still be in a different physical state, when directly controlled by shelly app
# NOTE: this does not scale to multiple primaries / secondaries, BUT ONE of each is enough to absord my max production 4 Kw)

primary_set_to_on_by_app = False 
secondary_set_to_on_by_app = False 

sleep_sec = 60 # sec sleep between automation loop. updated by GUI

sleep_after_react = 10 # when turning heater ON/OFF. allow eddi to stabilize ??

blynk_update_count = 5 # update Blynk GUI, check monit, .. every n loop

# default value. updated by gui 
# used for damping
react_to_surplus_max = 3 # decremented each time condition is set
react_to_surplus = react_to_surplus_max  # counter. react when this drops to zero (damping)

react_to_soutir_max = 3 
react_to_soutir = react_to_soutir_max

# if surplus exist and router below this, there is a problem (unless heater is disconnnected)
# assumes 2Kw heater, and always connectec
expected_solar_router_power = 1800 # 

max_temp_shelly = 55 # shut down temperature

#######################
# sun
########################

sun = Sun(latitude, longitude)

# Get today's sunrise and sunset in UTC
today_sr = sun.get_sunrise_time()
today_ss = sun.get_sunset_time()
print('sun rise, sun set as UTC:', today_sr, today_ss)

#convert from UTC to local

from_zone = tz.gettz('UTC')

local_zone = tz.tzlocal() # seems not to get it rigth. hardcode it
local_zone = tz.gettz("Europe/Paris") # or hardcode it

# Tell the datetime object that it's in UTC time zone since datetime objects are 'naive' by default
today_sr = today_sr.replace(tzinfo=from_zone)
today_ss = today_ss.replace(tzinfo=from_zone)

# Convert time zone
sr_local = today_sr.astimezone(local_zone)
ss_local = today_ss.astimezone(local_zone)

sun_rise = int(sr_local.strftime('%H'))
sun_set = int(ss_local.strftime('%H'))
print('sun rise local tz:%d, sun set local tz: %d' %(sun_rise, sun_set))

####################
# SPI 7789 display
####################

# set up SPI display, font, return None if cannot create display (eg hat not connected)
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
    # continue. application will test display variable to cope for missing display


#######
# print/log 
# pushover 

# blynk event
# blynk email
# blynk push notification

# events
# defined in template 
# (online, offline are default)

# blynk console event tab:
#  general:  define type (critical, warning), limit, show in timeline, apply tag
#  notification:  enable notif (email, push (critical mobile alert or not) , sms]
######

def log_and_notify_error(s, send_notif=True, warning = False):
    print(s)
    logging.error(s)
 
    if send_notif:

        # pushover

        pushover.send_pushover(s, title="solar2heater", priority=1, sound='cosmic')

        # depending on Blynk console event config (developer zone -> template -> even&notification)

        # General:
        #   Show event in Notifications section of mobile app
        #   Send event to Timeline
        #   Apply a Tag
        # Notification:
        #   Enable notifications  (push, email, sms)
        #   Deliver push notifications as alerts 
        #      When turned on, push notifications will use critical alert sounds. 
        #      End-users will need to turn this setting on in their app settings. They can also change a sound.
        #   Enable notifications management (end-users will access advanced notification management for this event)
        

        # NOTE: if push notifications as alerts, will ring the smartphone EACH TIME
        try:
            if warning:
                blynk.log_event("system_warning", s) # use event code
                # event name = system error  event code = system_error 
            else:
                blynk.log_event("system_error", s) # use event code

        except Exception as e:
            logging.error(e)


        #####################################
        # WARNING. .email and .notif not there anymore with new blynk ?
        #####################################

        """
        # blynk email
        try:
            blynk.email(secret.dest_email, "solar2heater error", s) 
        except Exception as e:
            s = "blynk email %s" %str(e)
            print(s)
            logging.error(s)

        # blynk notification
        try:
            blynk.notify('solar2heater error' + s) # send push notification to Blynk App 
        except Exception as e:
            s = "blynk notification %s" %str(e)
            print(s)
            logging.error(s)

        """  




#######################
# shelly routine
#######################

##########################
# react on overtemp
#########################
# stop automation. stop relay . note for fil pilote, this may need close rela
def shelly_turn_off_overtemp():
    global primary_set_to_on_by_app, secondary_set_to_on_by_app, automation

    automation = False

    print('overtemp, turn ALL heaters off')
    for index in [0,nb_shelly-1]:
        shelly_onoff_by_index(index, 'off', source = "turn off because overtemp")
        blynk.virtual_write(shelly_led[index], 0)

    primary_set_to_on_by_app = False
    secondary_set_to_on_by_app = False

#####################################
# role (primary/secondary) to index 
#####################################
# primary_index is index in config table. default 0 and set by GUI
# get index into config table from a logical role (primary or secondary)
def get_index(role) -> int:
    # convert logical "primary" into physical (index)
    # primary_index is a global set in GUI. is index in config table of heater considered as "primary"
    # TO DO: better, more generic

    index = -1

    # get index for primary
    if role == "primary" and primary_index == 0:
        index = 0
    if role == "primary" and primary_index == 1:
        index = 1

    # get index for secondary
    if role == "secondary" and primary_index == 0:
        index = 1
    if role == "secondary" and primary_index == 1:
        index = 0

    return(int(index))


#####################################
# index to role 
#####################################
def get_role(index):
    # convert physical (index) into role ("primary")
    if index == primary_index:
        return("primary")
    else:
        return("secondary")


#############################
# get power from index
############################
# index into table of IP addresses
# manage fixed power for fil pilote
# turn off and notify in case of overpower, overtemp, temp too large
# returns (status, last_shelly_power, temp, overt) or (None, ..)
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
            log_and_notify_error('shelly error http. statuis code: ' + str(res.status_code))
            return(None,None,None,None)
    except Exception as e:
        s = "exception shelly REST %s" %str(e)
        log_and_notify_error(s)
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
            log_and_notify_error(s)

    
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
            log_and_notify_error(s)
        

        overtemp = res.json()['overtemperature']
        if overtemp:
            # turn off
            shelly_turn_off_overtemp()

            s = 'shelly overtemp %0.1f detected' %overtemp
            log_and_notify_error(s)
    

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


###################
# turn on or off by index 
# called by shelly_turn_off_overtemp(), set_heater_by_role(), transition_turn_all_heaters_off()
###################
        
# use physical addressing, ie index into list, vs role (primary)
# convert index of actual heater into url
# set relay with shelly API
# 1st shelly is connected to fil pilote.  relay OFF = heater on. relay ON = anti freeze , ie heater off
# set led . NOTE: led in GUI is per physical, ie living room, kitchen
# update last_action_list (rolling)

# called by: shelly_turn_off_overtemp(), set_heater_by_role(), transition_turn_all_heaters_off()
# NOT manual_onoff() which is gone 

def shelly_onoff_by_index(index, command, source = None): # shelly_heater is index 0, 1
    global last_actions_list
    # source only used for logging

    print("onoff by index %d, command %s, source %s" %(index, command, source))

    if command == 'on':
        ################
        #  turn on
        ################

        if index == 0:
            # fil pilote relay = off , ie open to turn heater on ("confort" mode)
            url = shelly_ip[index] + "relay/0?turn=off" # fil pilote, device configured as reversed input does not work (only for button)

            last_actions_list.append("0:on/")
            last_actions_list.pop(0)
        else:
            # normal relay. relay on to turn heater on
            url = shelly_ip[index] + "relay/0?turn=on"

            last_actions_list.append("1:on/")
            last_actions_list.pop(0)

        print('turn shelly on: index %d, url %s' %(index, url))
        res = requests.post(url)

        if res.status_code != 200:
            log_and_notify_error('shelly error REST. status code: %s' %str(res.status_code))
        else:
            print("turn on index %d ok" %index)

            # set led
            blynk.virtual_write(shelly_led[index], 1)

            # on off button
            #blynk.set_property(shelly_switch[index], "OnLabel", "ON")
            #blynk.set_property(shelly_onoff_button[index], "label", shelly_name[index])
            #blynk.set_property(shelly_onoff_button[index], "color", "#D3435C")

    elif command == 'off':

        ################
        #  turn off
        ################
        if index == 0:
            url = shelly_ip[index] + "relay/0?turn=on" # fil pilote, device configured as reversed input 

            last_actions_list.append("0:off/")
            last_actions_list.pop(0)
            
        else:
            url = shelly_ip[index] + "relay/0?turn=off"

            last_actions_list.append("1:off/")
            last_actions_list.pop(0)

        print('turn shelly off. index: %d, url: %s' %(index, url))
        res = requests.post(url)
        if res.status_code != 200:
            log_and_notify_error('shelly error REST ' + str(res.status_code))
        else:
            print("turn off index %d: ok" %index)

            # led off
            blynk.virtual_write(shelly_led[index], 0)

            # on off button
            #blynk.set_property(shelly_onoff_button[index], "label", shelly_name[index])
            #blynk.set_property(shelly_switch[index], "OffLabel", "OFF")
            #blynk.set_property(shelly_onoff_button[index], "color", "#04C0F8")
 
    else:
        print('bad command')
        
    print("end processing onoff_by_index %d" %index)



##################
# turn on or off by role
##################
# set_heater('primary', 'on')
# logical. 
#    calls shelly_onoff_by_index(index, command) : do physical on/off and set led 
#    calls shelly_power(index) to get power after relay is set .sleep before getting back power
# update power and temp GUI (led GUI done in onoff_by_index)

def set_heater_by_role(heater, command):
    # heater is "primary" or "secondary"
    # record state is done in calling

    index = get_index(heater)

    print('set logical heaters %s to %s. primary index %s, physical index %s' %(heater, command, primary_index, index))

    # set actual shelly heater as designated by index
    # update led
    shelly_onoff_by_index(index, command, source = "heater set by automation") # shelly_heater global set by GUI. 0, 1, index into shelly_ip[]

    sleep(10) # time to get power reading

    # read power and temp
    (status, last_shelly_power, temp, overt) = get_shelly_power_by_index(index)
    print('shelly index %d:  ison %s, power %0.0f, temp %0.1f, overtemp %s ' %(index, str(status) , last_shelly_power, temp, str(overt)))

    # update blynk power and temp value
    if last_shelly_power != None:
        blynk.virtual_write(shelly_power[index], last_shelly_power)

    if temp != None:
        blynk.virtual_write(shelly_temp[index], temp)

    # led update done in shelly_onoff

    return()


###############################
# turn heaters OFF because of transition (auto on to off with behavior set to turn off, entering nite, app starts, catch signal)
###############################
# automation off: function of flag
# entering nite, app start: function of automation
# call shelly_onoff_by_index()
# reset all gauge to zero

def transition_turn_all_heaters_off(s):

    s = "in transition: turn all heaters off. because: " + s

    logging.info(s)
    print(s)

    blynk.virtual_write(vpin.v_terminal, s)

    # turns heaters off, so that zappy can grab surplus immediatly
    for index in range(nb_shelly):

        print("index %d" %index)

        # http request to turn heater of, set red led and on off button
        # source only used for logging

        shelly_onoff_by_index(index, "off", source = "in transition: force heater to OFF " + s)

        # set power meter to 0 (ie consumed power)
        blynk.virtual_write(shelly_power[index], 0)

    
    # set other (non shelly) power meter used in graph and gauge
    print("in transition: set ALL power meter to 0")
    blynk.virtual_write(vpin.v_power_grid, 0)
    blynk.virtual_write(vpin.v_power_production, 0)
    blynk.virtual_write(vpin.v_power_eddy, 0)
    blynk.virtual_write(vpin.v_total_heater, 0)



###################################################
# get production from ENVOY
###################################################

# local web server
# several tries
# TOTAL CONSO - PRODUCTION = NET CONSO (is <0 , export)
# TOTAL CONSO includes eddy  
# returns net_conso, production, total_conso

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
                    log_and_notify_error(s)
                    print(s)
                    return(None,None,None)
                else:
                    sleep(10)

            else:
                break
        
        except Exception as e:
            s = "exception getting envoy production %s" %(str(e))
            log_and_notify_error(s)
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
        log_and_notify_error('envoy json ' + str(e))
        return (None, None, None)

    try:
        x = content['consumption'][1]['measurementType']
        if x == 'net-consumption':
            net_conso = content['consumption'][1]['wNow'] # # net consumption. surplus negative
    except Exception as e:
        log_and_notify_error('envoy json ' + str(e))
        return (None, None, None)

    try:
        production = content['production'][1]['wNow']
    except Exception as e:
        log_and_notify_error('envoy json ' + str(e))
        return (None, None, None)


    # TOTAL CONSO - PRODUCTION = NET CONSO (is <0 , export)
    #print('total conso %0.2f production %0.2f net conso %0.2f  delta %0.2f' %(total_conso, production, net_conso, total_conso - production))

    return(net_conso, production, total_conso)


#################
# local pzem
#################

def init_local_pzem():
    try:
        master = modbus_rtu.RtuMaster( serial.Serial(port=pzem_port, baudrate=9600, bytesize=8, parity='N', stopbits=1, xonxoff=0))
        #master.set_timeout(5.0)
        #master.set_verbose(True)
        #logger.info("rtu master connected")
        return(master)
    except Exception as e:
        log_and_notify_error('cannot create RTU master %s. exit ' %str(e))
        sys.exit(1)


###################
# read router power from LOCAL PZEM 004T
##################
        
# try pzem, then myenergy cloud
# return (power/none, True/False) 
# True is local PZEM read ok , ie real time data
# False if used cloud . not sure how real time is cloud data
# eddy power used for stats only, not as condition for automation
# ->Tuple [Optional(float), bool]
# ->Tuple [Union(float,None)], bool]
def read_local_pzem_power():

    power = None
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
        return(power) 

    else: # will try myenergi api outside this function
        
        s = 'cannot read PZEM power after %d tries. try cloud' %max_try
        print(s)
        logging.error(s)

        return(None)


#################
# read router power from REMOTE PZEM 004T
#################
    
# close socket after each call
# return None on error or float
def read_remote_pzem(value="power"):

    sock = remote_PZEM_python_client.remote_pzem_connect(pzem_server_ip, pzem_server_port, log=None)
    if sock is None:
        s= "cannot connect to remote PZEM"
        print(s)
        # log or notify ?
        return(None)

    # default to power
    v = remote_PZEM_python_client.remote_pzem_get_value(sock, value, nb_retry=2)

    # do not leave socket hagging. more robust ?
    sock.close()

    if v == None:
        s= "remote PZEM. local error"
        print(s)
        return(None)

    elif v == "None":
        s= "remote PZEM. remote error"
        print(s)
        return(None)

    else:
        print("remote PZEM returned %s: %0.2f " %(value, v))
        return(v)


# will be synched later. global
# automation loop process inject/soutir if (automation and not nite)
# initialized in blynk call backs from widget status
automation = None


#####################################################
##### turning heater OFF when disabling automation ??
#####################################################
# Summer: yes, so that surplus is immediatly available to myenergi. this is a way to prioritize EV to heaters (1)
# Winter and in the house: 
#   when no surplus I do not want automation to run, as it would turn heater OFF, and I want them ON (ie started "manually")
#   ==> I would disable automation, to leave heaters alone
#    (2) if disabling automation turnd them off, (from their likely ON state) == > need to restart them to ON "manually"

# turn_heater_off_when_disabling_automation = True
# (2): each time automation is disabled, "manually" turn heater ON from Blynk GUI, or from shelly app
# (1) is not a problem

#turn_heater_off_when_disabling_automation = False
# (2) is not a problem
# (1): "manually" turn heater OFF from Blynk GUI, or from shelly app

#### similar problem: turning heaters OFF when entering nite ??
# Winter/in house case: I do not want heater to turn OFF when entering nite. I need them!!
# turn OFF when entering nite ONLY if automation is False


# when automation goes from on to off
#  turn heaters off in this flag is True
#  else leave alone
# NOTE: only used to manage automation on to off
#   entering nite and app start are function of automation 

automation_off_turn_heater_off = None # synced from button later (value != None indicate synced)

################################
# enabling, disabling automation 
##############################
# called by Blynk and web server , protected by mutex
# update led, 
# button update is done in automation_button_when_updating() (could come from Blynk GUI or web)
# use automation_off_turn_heater_off when disabling
# calls transition_turn_all_heaters_off()

def enabling_automation():
    global automation

    mutex1.acquire()

    automation = True
    s = "automation enabled"
    print(s)
    logging.info(s)
    blynk.virtual_write(vpin.v_terminal, s)

    blynk.virtual_write(vpin.v_led_automation, '1')

    print('automation flag:', automation)
    mutex1.release()

def disabling_automation():
    global automation

    mutex1.acquire()

    automation = False
    s = "automation disabled"
    print(s)
    logging.info(s)
    blynk.virtual_write(vpin.v_terminal, s)

    # automation led
    blynk.virtual_write(vpin.v_led_automation, '0')

    print('automation flag:', automation)

    # button must have synced for this not to be None
    if automation_off_turn_heater_off:
        s = "automation disabled. turns all heaters off (eg so that zappy can grab surplus). please turn them ON on your end, if needed"
        print(s)
        logging.info(s)

        blynk.virtual_write(vpin.v_terminal, "turning all heaters OFF")
        blynk.virtual_write(vpin.v_terminal, "turn them ON yourself- eg to keep heating")

        # relay, led, terminal, gauge
        transition_turn_all_heaters_off(s)

    else:
        s = "automation disabled. leave heaters as it (eg Winter and at home). please turn them OFF on your end, if needed"
        print(s)
        logging.info(s)

        blynk.virtual_write(vpin.v_terminal, "heaters NOT turned OFF")
        blynk.virtual_write(vpin.v_terminal, "turn them OFF yourself - eg for surplus to go EV")

    mutex1.release()


###############################
# feedback on automation or behavior button itself
##############################
# make it a separate function , to get consistent behavior when updating from GUI and web
# set label (small text on top), color, button content (onlabel, offlabel), and button value
# called  from callbacks from both gui and web

def automation_button_when_updating(enabled:bool, source:str):
    assert source in ["gui", "web"]

    # set onlabel and offlabel
    on_l = vpin.auto_enabled 
    off_l = vpin.auto_disabled

    if source == "web":
        on_l = on_l + vpin.web
        off_l = off_l + vpin.web

    if source == "gui":
        on_l = on_l + vpin.gui
        off_l = off_l + vpin.gui

    if enabled:
        color = vpin.auto_color_enabled
    else:
        color = vpin.auto_color_disabled

    # feeback on button itself
    blynk.set_property(vpin.v_automation, "label", vpin.auto_label)
    blynk.set_property(vpin.v_automation, "color", color)

    blynk.set_property(vpin.v_automation, "onLabel", on_l)
    blynk.set_property(vpin.v_automation, "offLabel", off_l)

    # also "force" value, as this can come from web
    if enabled: # could also write disabled bool directly
        blynk.virtual_write(vpin.v_automation, 1)
    else:
        blynk.virtual_write(vpin.v_automation, 0)


def behavior_button_when_updating(turn_off:bool, source:str):
    assert source in ["gui", "web"]

    # set onlabel and offlabel
    on_l = vpin.behavior_turn_off
    off_l = vpin.behavior_leave

    if source == "web":
        on_l = on_l + vpin.web
        off_l = off_l + vpin.web

    if source == "gui":
        on_l = on_l + vpin.gui
        off_l = off_l + vpin.gui

    if turn_off:
        color = vpin.behavior_color_turn_off
    else:
        color = vpin.behavior_color_leave

    # feeback on button itself
    blynk.set_property(vpin.v_automation_off_turn_heater_off, "label", vpin.behavior_label)
    blynk.set_property(vpin.v_automation_off_turn_heater_off, "color", color)

    blynk.set_property(vpin.v_automation_off_turn_heater_off, "onLabel", on_l)
    blynk.set_property(vpin.v_automation_off_turn_heater_off, "offLabel", off_l)

    # also "force" value, as this can come from web
    if turn_off: # could also write disabled bool directly
        blynk.virtual_write(vpin.v_automation_off_turn_heater_off, 1)
    else:
        blynk.virtual_write(vpin.v_automation_off_turn_heater_off, 0)


#####################
# blynk call back
#####################

# initialize blynk
blynk = my_blynk_new.create_blynk(BLYNK_AUTH_TOKEN, log=None)
print('blynk created')

#################################
# GUI automation on/off switch
# 0 = False = disabled
################################
# synched at start
s = "V%d" %vpin.v_automation
@blynk.on(s)
def f_v_automation(value):
    print('Blynk call back: set automation master switch: ', value) # automation:  ['0']
    if value[0] == '0':
        disabling_automation()
        automation_button_when_updating(False, "gui") # set label (small text on top), color, button content (onlabel, offlabel), and button value

    else:
        enabling_automation()
        automation_button_when_updating(True, "gui")


######################################
# set automation_off_turn_heater_off
# bool = True , turn off
######################################
# what to do when auto on to off
# synched at start
# set global and button, but does not touch anything else
s = "V%d" %vpin.v_automation_off_turn_heater_off
@blynk.on(s)
def f_v_behavior(value):
    global automation_off_turn_heater_off
    print('Blynk call back: automation_off_turn_heater_off: ', value)
    # set global needed when automation is actually disabled
    automation_off_turn_heater_off = bool(int(value[0]))

    behavior_button_when_updating(automation_off_turn_heater_off, "gui") # set label (small text on top), color, button content (onlabel, offlabel), and button value

    blynk.virtual_write(vpin.v_terminal, 'turn off heaters when auto off ?: %s' %automation_off_turn_heater_off)


###########
# set sleep
###########
s = "V%d" %vpin.v_sleep
@blynk.on(s)
def f_v_sleep(value):
    global sleep_sec
    print('Blynk call back: set sleep sec: ', value) # 
    sleep_sec = int(value[0])
    blynk.virtual_write(vpin.v_terminal, 'call back sleep between cycle: %d' %sleep_sec)

###################
# set damping
###################
# set max value init counter to max value
s = "V%d" %vpin.v_react_to_surplus
@blynk.on(s)
def f_v_react_to_surplus(value):
    global react_to_surplus, max_react_to_surplus
    print('Blynk call back: set max_react_to_surplus: ', value) # 
    max_react_to_surplus = int(value[0])
    react_to_surplus = max_react_to_surplus
    blynk.virtual_write(vpin.v_terminal, 'call back react to surplus : %d' %react_to_surplus)

s = "V%d" %vpin.v_react_to_soutir
@blynk.on(s)
def f_v_react_to_soutir(value):
    global react_to_soutir, max_react_to_soutir
    print('Blynk call back: set max_react_to_soutir: ', value) # 
    max_react_to_soutir = int(value[0])
    react_to_soutir = max_react_to_soutir
    blynk.virtual_write(vpin.v_terminal, 'call back react to soutir : %d' %react_to_soutir)

#####################
# log
#####################
# display last lines of log file in terminal. 
# display monit summary to another terminal
s = "V%d" %vpin.v_log
@blynk.on(s)
def f_v_log(value):
    nb = 15 # seems there is a pb if too large ?
    print('log button callback. log: ', value) # automation:  ['0']
    index = 0
    if value[0] == '0': # ['1'] , then 0
        pass
    else:
        ############################
        # display last n lines of log in terminal
        ############################
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines() # array
                n = min(nb, len(lines)) # # be carefull when deleting log file, and displaying log too fast. maybe not yet nb lines in there
                last_lines = lines[-n:]
                # ['INFO:root:2022-11-09 10:25:12.386019 \n', '-------------- surplus starting ...............\n', 'INFO:modbus_tk:RtuMaster /dev/ttyS0 is opened\n', 
                s = ""
                for line in last_lines:
                    s = s + line
                    blynk.virtual_write(vpin.v_terminal, line)

                print('writing log to vpin.v_terminal: ', s)

        except Exception as e:
            s = "exception reading log file %s" %str(e)
            print(s)
            blynk.virtual_write(vpin.v_terminal, s)

        ###################
        # monit summary
        ###################
        try:
            # TO DO add time stamp 
            s= monit_mail.monit_summary()
            print(s)
            # just display. do not analyze all are OK
            blynk.virtual_write(vpin.v_terminal, "look also at monit terminal")
            blynk.virtual_write(vpin.v_monit, s)
            

        except Exception as e:
            s = "exception monit summary %s" %str(e)
            print(s)
            blynk.virtual_write(vpin.v_terminal, s)
            blynk.virtual_write(vpin.v_monit, s)

##################################
# refresh gauge with real time data
##################################
s = "V%d" %vpin.v_refresh
@blynk.on(s)
def f_v_refresh(value):
    print('Blynk call back: refresh gauge: ', value) # automation:  ['0']
    index = 0
    if value[0] == '0':
        pass
    else:

        ##################
        # grid, production
        ##################
        # router, total heater

        (net_conso, production, total_conso) = envoy_get_production()
        if net_conso != None:
            blynk.virtual_write(vpin.v_power_grid, net_conso)
            blynk.virtual_write(vpin.v_power_production, production)
            # grid is net_conso
            blynk.virtual_write(vpin.v_terminal, "refreshing.. grid (envoy): %0.1f Kw, production: %0.1f Kw" %(net_conso, production))

        else:
            blynk.virtual_write(vpin.v_terminal, "refreshing.. error envoy")

        ############
        # shelly
        ############
        (status, last_shelly_0_power, temp_shelly, overt) = get_shelly_power_by_index(0)
        (status, last_shelly_1_power, temp_meross, overt) = get_shelly_power_by_index(1)

        blynk.virtual_write(shelly_power[0], last_shelly_0_power)
        blynk.virtual_write(shelly_temp[0], temp_shelly)

        blynk.virtual_write(shelly_power[1], last_shelly_1_power)
        blynk.virtual_write(shelly_temp[1], temp_meross)

        blynk.virtual_write(vpin.v_terminal, "refreshing.. %s: %0.1f Kw, %s: %0.1f Kw"  %(shelly_name[0], last_shelly_0_power, shelly_name[1], last_shelly_1_power))

        ##########################
        # router, total heater
        ##########################

        if local_pzem:
            (router_power) = read_local_pzem_power()

        else:
            (router_power) = read_remote_pzem() # default power

        if router_power != -1:
            blynk.virtual_write(vpin.v_power_eddy, router_power)

            total_heater = router_power + last_shelly_0_power + last_shelly_1_power
            blynk.virtual_write(vpin.v_total_heater, total_heater)

            blynk.virtual_write(vpin.v_terminal, "refreshing.. router: %0.1f Kw. total heater: %0.1f Kw"  %(router_power, total_heater))
        
        else:
            s = "refreshing.. error reading router power"
            blynk.virtual_write(vpin.v_terminal, s)
            print(s)
            logging.error(s)

########################
# blynk system call backs
########################
@blynk.on("connected")
def blynk_connected(ping):
    print('Blynk ready (connected). Ping:', ping, 'ms')
    #print("synching")
    #blynk.sync_virtual(vpin.v_automation, vpin.v_sleep, vpin.v_react_to_surplus, vpin.v_react_to_soutir)

@blynk.on("disconnected")
def blynk_disconnected():
    print('Blynk disconnected')



"""

#####################
# UPDATE
# do not allow to set heater from the app
# simpler if separation of concerns
# GUI less clutered
# led still there 
#####################

##################################
# processing for manual on/off button
###################################
# called ONLY by blynk call back for buttons, ie on/off from GUI, not from automation
# turn physical heater on off
# update logical is_on flag
# update led, power , temp, terminal
# update button label
# value int, 0 to turn off
# WARNING: does NOT turn automation off

def manual_onoff(index, value):

    global primary_set_to_on_by_app
    global secondary_set_to_on_by_app

    print('manual onoff switch (0 is off): ', value) # 
    print('should you ALSO turn automation off ??')

    role = get_role(index) # to set *-is_on flag   physical heater (index) to role as primary/secondary

    if value == 0:
        # set actual heater 
        shelly_onoff_by_index(index,'off', source = "manual turn off")

        # update onoff status
        if role == "primary":
            primary_set_to_on_by_app = False
        if role == "secondary":
            secondary_set_to_on_by_app = False
    else:
        shelly_onoff_by_index(index, 'on', source = "manual turn on")

        if role == "primary":
            primary_set_to_on_by_app = True
        if role == "secondary":
            secondary_set_to_on_by_app = True

    time.sleep(10)

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

    blynk.virtual_write(vpin.v_terminal, s)

    # feeback on on/off button itself
    blynk.set_property(she, "label", shelly_name[index])
    
    # let color and content as defined in widget definition in console
    #blynk.set_property(vpin.v_automation, "color", "#FF0000") #  "#FF00FF"
    #blynk.set_property(vpin.v_automation, "onlabel", "ON (GUI)")
    #blynk.set_property(vpin.v_automation, "offlabel", "OFF (GUI)")

#############################
# onoff button for index 1 and 0
#############################
# call  manual_onoff
s = "V%d" %vpin.v_merossonoff
@blynk.on(s)
def f_v_merossonoff(value):  # value ['1'] for ON
    index = 1
    value = int(value[0])
    s = "Blynk call back: shelly index: %d, on/off value: %d. call manual_onoff" %(index, value)
    print(s)
    logging.info(s)
    manual_onoff(index, value)

s = "V%d" %vpin.v_shellyonoff
@blynk.on(s)
def f_v_shellyonoff(value): # value ['1'] for ON
    index = 0 
    value = int(value[0])
    s = "Blynk call back: shelly index: %d, on/off value: %d. call manual_onoff" %(index, value)
    print(s)
    logging.info(s)
    manual_onoff(index, value)

"""
##########################
# select primary heater. drop down menu
##########################
# write to terminal
s = "V%d" %vpin.v_select
@blynk.on(s)
def f_v_select(value):
    global primary_index
    print('Blynk call back: select primary heater: ', value)
    
    if value[0] == '0': # shelly defined as 0 in widget
        blynk.virtual_write(vpin.v_terminal, 'primary heater is 0')
    elif value[0] == '1':
        blynk.virtual_write(vpin.v_terminal, 'primary heater is 1')
    else:
        pass

    # cannot set content (ie text for menu)

    # set global
    primary_index = int(value[0]) # index in array , primary heater
    s = 'index for primary %d' %primary_index
    print(s)
    logging.info(s)



#################################################################
#######################################
# MAIN
#######################################
#################################################################

def signal_handler(sig, frame):
    s= "got signal %s. automation: %s" %(str(sig), automation)
    print(s)
    logging.warning(s)

    if automation:
        s = "got SIGNAL: automation enabled. turns all heaters off."
        print(s)
        logging.info(s)

        blynk.virtual_write(vpin.v_terminal, "signal: turning all heaters OFF")

        # relay, led, terminal, gauge
        transition_turn_all_heaters_off(s)

    else:
        s = "got SIGNAL: automation disable. do nothing"
        print(s)
        logging.info(s)


    d = {
        2:"SIGINT, ie CTRL C. exit",
        9:"SIGKILL",
        15:"SIGTERM, (eg shutdown)",
    }

    if sig in d.keys():

        s = "SIGNAL: %s" %d[sig]
        print(s)
        logging.info(s)

        if sig == 2:
            sys.exit()

    


# The remaining processes, if any, are sent a SIGTERM. The ones that ignore SIGTERM or do not finish on time, are shortly thereafter sent a SIGKILL by init/systemd.
signal.signal(signal.SIGINT, signal_handler) # Interrupt from keyboard (CTRL + C). Default action is to raise KeyboardInterrupt.
signal.signal(signal.SIGHUP, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


#timer = my_blynk_new.create_blynk_timer()
#timer.set_timeout(2, hello) # run once
#timer.set_interval(4, power) # run multiple

# record last heaters on/off , fifo like, 5 char str, "1 on ", "0 off" 
# last action: list.append(), list.pop(0) 
last_actions_list = []  # 

# keep trace of last n actions
for i in range(10):
    last_actions_list.append("start/")

# updated when heater are updated, with .append and .pop(0) , so will also keep last 10 (fifo)


# start Blynk run thread
id1= _thread.start_new_thread(my_blynk_new.run_blynk, (blynk,None))

####################
# blynk: various way to says the application is starting
# after blynk is started
####################

start_msg = "solar2heater v%0.2f starting" %version

# terminal 
blynk.virtual_write(vpin.v_terminal, start_msg)

# event info
# also notif (email, push) enabled, but push not critical (otherwize keeps on beeping on smartphone and need to connect to app to make it stop)
blynk.log_event("starting", start_msg) # use event code

# email and notif not available with new blynk

"""
# blynk email
try:
    blynk.email(secret.dest_email, "blynk email", s) 
except Exception as e:
    s= "blynk email %s" %str(e)
    print(s)
    logging.error(s)

# blynk notification
try:
    blynk.notify('blynk notification' + s) # send push notification to Blynk App 
except Exception as e:
    s= "blynk notofication %s" %str(e)
    print(s)
    logging.error(s)
"""


print('synching vpins')
# NO synching done in connect call back
blynk.sync_virtual(vpin.v_automation_off_turn_heater_off, vpin.v_automation)
blynk.sync_virtual(vpin.v_select)
blynk.sync_virtual(vpin.v_sleep, vpin.v_react_to_surplus, vpin.v_react_to_soutir)

# WARNING: we need actual (widget) value for automation to decide whether we need to turn heaters OFF at start

print("wait for automation vpins to synch")
i = 0
max_i = 5
while automation is None:
    sleep(1)
    i = i + 1
    if i > max_i:
        break

if automation is None: # synced failed
    s= "blynk automation synced failed. This is VERY bad"
    print(s)
    logging.error(s)
else:
    s= "blynk automation synced OK."
    print(s)
    logging.info(s)

##################
# turn heaters off at app start, if autpmation is false
##################

if automation is False:
    s= 'automation false, leave heaters as it at application start'
    print(s)
    logging.info(s)
    
else:
    s= 'automation true, turn all heaters off at application start'
    print(s)
    logging.info(s)
    # otherwize house consumption reading will be off
    transition_turn_all_heaters_off("application start and automation is true: %s. turn off heaters" %automation)

if local_pzem:
    print("LOCAL PZEM: init modbus")
    # init MODBUS for PZEM 004T
    # no loggin to not polluate file dump to terminal 
    #logger = modbus_tk.utils.create_logger("console")
    master = init_local_pzem()

else:
    print("remote pzem, no modbus init")

    # try to get volt to make sure remote PZEM is ok
    for x in ["volt", "amps", "power"]:
        v = read_remote_pzem(value=x)
        if v not in [None, "None"]:
            s= "remote pzem %s: %0.2f" %(x,v)
            print(s)
            logging.info(s)

        else:
            log_and_notify_error('remote PZEM. cannot read %s' %x) # default is to send notif



#####################
# local web server
# curl http://127.0.0.1:5000/automation_off/
# used to turn automation on/off or set behavior when automation is turned off from an external system (ie physical swith)
#####################

flask_app = my_web_server.create_flask()

# use different url , vs parameters, for simplicity

commands = {
"/disable_automation": "disable control of heaters by application" ,
"/enable_automation": "enable control of heaters by application", 
"/automation" : "is automation enabled ?",
"/disabling_off" : "turns all heaters OFF when automation is disabled",
"/disabling_leave" : "leave heaters AS IT when automation is disabled",
"/disabling" : "will heaters be turned OFF when automation is disabled ?",
}

url = list(commands.keys())
comments = list(commands.values())

# beware of orders

# available commands
@flask_app.route("/", methods=['GET', 'POST'])
def f4():
    s = "<p>available commands<p>"
    for k in commands.keys():
        s = s + "<li> %s : %s </li>" %( k , commands[k]) 
    return "%s" %s

# auto off
@flask_app.route(url[0], methods=['GET', 'POST'])
def automation_off():
    print("inbound request:", request.method, request.path)

    s = "automation disabled from web"
    print(s)
    logging.info(s)

    disabling_automation()

    # update button
    automation_button_when_updating(False, "web") # set label (small text on top), color, button content (onlabel, offlabel), and button value

    s = "<p>%s</p>" %(comments[0])
    return s

# auto on
@flask_app.route(url[1], methods=['GET', 'POST'])
def automation_on():
    print("inbound request:", request.method, request.path)

    s = "automation enabled from web"
    print(s)
    logging.info(s)

    enabling_automation()
    automation_button_when_updating(True, "web")

    s = "<p>%s</p>" %(comments[1])
    return s

# auto status
@flask_app.route(url[2], methods=['GET', 'POST'])
def automation_status():
    print("inbound request:", request.method, request.path)

    s = "<p>%s: %s</p>" %(comments[2], automation)
    return s


# behavior when automation is turned off: turns all heater off
@flask_app.route(url[3], methods=['GET', 'POST'])
def automation_f1():
    print("inbound request:", request.method, request.path)

    s = "behavior when automation is turned off: turns all heater off. update from web"
    print(s)
    logging.info(s)

    # update button
    behavior_button_when_updating(True, "web") # set label (small text on top), color, button content (onlabel, offlabel), and button value

    s = "<p>%s</p>" %(comments[3])
    return s

# behavior when automation is turned off: leave heater alone
@flask_app.route(url[4], methods=['GET', 'POST'])
def automation_f2():
    print("inbound request:", request.method, request.path)

    s = "behavior when automation is turned off: leave heaters alone. update from web"
    print(s)
    logging.info(s)

    behavior_button_when_updating(False, "web")

    s = "<p>%s</p>" %(comments[4])
    return s


# behavior when automation is turned off: leave heater alone
@flask_app.route(url[5], methods=['GET', 'POST'])
def automation_f3():
    global automation_off_turn_heater_off

    print("inbound request:", request.method, request.path)

    s = "<p>%s: %s</p>" %(comments[5], automation_off_turn_heater_off)
    return s

# http://192.168.1.206:5000/temp/  in shelly app
#INFO 2024-02-14 17:20:05,567 HT data: ImmutableMultiDict([('hum', '45'), ('temp', '21.38'), ('id', 'shellyht-1BDD1B')])
#INFO 2024-02-14 17:20:05,572 192.168.1.50 - - [14/Feb/2024 17:20:05] "GET /temp/?hum=45&temp=21.38&id=shellyht-1BDD1B HTTP/1.1" 200 -
@flask_app.route("/temp/", methods=['GET', 'POST'])
def automation_f4():

    print("inbound request:", request.method, request.path)

    s = "HT data: %s" %str(request.args)
    print(s)
    #logging.info(s)

    try:

        t = float(request.args["temp"]) # defined as double 0 to 30, 
        h = int(request.args["hum"])  # defined as int 0 to 100

        s = my_log.get_stamp()

        blynk.virtual_write(vpin.v_HT_temp, t)
        blynk.virtual_write(vpin.v_HT_humid, h)
        blynk.virtual_write(vpin.v_HT_stamp, s)

        s = "HT: %s. temp %0.1f, humid %d" %(s, t,h)
        print(s)
        #logging.info(s)

    except Exception as e:
        s= 'exception getting HT data: %s' %str(e)
        print(s)
        logging.error(s)


    return ("")


# start Flask run thread
print("starting Flask web server as a separate thread")
id2= _thread.start_new_thread(my_web_server.start_flask, (flask_app,))




######################################################################################
########################## main automation loop ######################################
######################################################################################

# terminal 
blynk.virtual_write(vpin.v_terminal, start_msg + ". loop starts")

nb_loop = 0 # count automation loops. update GUI every n count

while True:

    updated_heater = False


    print('\n')

    # in local (time.gmtime for UTC). make sure timezone is set in raspi-config
    # sudo raspi-config to set timezone
    local_today = time.localtime(time.time()) # tuple

    d = local_today.tm_mday
    h = local_today.tm_hour
    m = local_today.tm_min

    # time stamp str. local
    stamp = "%d/%d:%d " %(d, h, m)

    # do nothing when there is no sun
    # sunrise Local 7am, 1kw production 9pm
    # 8:27 , still considered nite

    nite = (h >= sun_set-1 or h <= sun_rise+1)
    nite_definition = ">= %s, <= %d" %(sun_set-1, sun_rise+1)

    print ('\nLoop: Automation: %s, hour %d. Nite: %s, (%s).react to surplus: %d, react to soutir %d' %(automation, h, str(nite), nite_definition, react_to_surplus, react_to_soutir))

    router_power = -2 # ie not read. only read if surplus but printed at end of loop. -1 means error reading PZEM


    if automation and not nite:

        ########### AUTOMATION IS ON . let's go

        # do the automation, update SPI display, 
        # update (every so often OR if heater state changed) blynk (gauge, check monit, last_action_list)

        print("==> getting current power situation")
        #############################
        # read inject/draw from grid
        #############################
        # TOTAL CONSO - PRODUCTION = NET CONSO (is <0 , export)
        # net_conso = surplus or draw
        (net_conso, production, total_conso) = envoy_get_production() 

        if net_conso is None or production is None or total_conso is None:

            # cannot read envoy. exit and hope someone (systemd, monit) will restart
            # anyway, without grid reading there is nothing we can do
            log_and_notify_error('cannot read envoy. EXIT') # default is to send notif

            sys.exit(1) # will be restarted by systemd

        else:
            print('net conso from envoy: %0.1f Watt (surplus if negative). production %0.1f. Total home conso %0.1f '  %(net_conso, production, total_conso)) # negative if surplus
            pass


        #############
        # read eddi power
        # used for stats only. not used for automation logic
        #############
        if local_pzem:
            # read solar router using PZEM/modbus BEFORE acting on surplus or draw
            (router_power) = read_local_pzem_power()

        else:
            (router_power) = read_remote_pzem() # default power

        # PZEM failed
        if router_power is None:
            s = 'cannot read (local or remote) PZEM power. try myenergi cloud' 
            print(s)
            logging.error(s)
    
            # try with myenergi API
            # data may not be real time
            try:
                router_power = get_eddi_diversion(myenergi_server_url)
                if router_power is None:
                    s = "cannot read eddi power from myenergi cloud"
                    print(s)
                    logging.error(s)
                else:
                    print('eddi power diverted %0.1f, from cloud' %router_power)

            except Exception as e:
                s = "exception read eddi power from myenergi cloud %s" %str(e)
                print(s)
                logging.error(s)

                # do not fill log with that. keep log for state change
                #handle_error('cannot read PZEM power', False) # do not send pushover 
                blynk.virtual_write(vpin.v_terminal, 'cannot read eddi power')
                #sys.exit(1) eddy power used for stats only, not as condition for automation

                # means error , use numeric vs None, as this is to be added to shelly.
                # do no use 0 to distinguish from no power
                # when added, -1 should not distord, as this is in Watt
                router_power = -1  
                print("set router power to %d to signal error" %router_power)

        else:
            # PZEM OK
            print('router power diverted %0.1f, from PZEM (local or remote)' %(router_power))

        # router_pozer = -1 for error
            
        #######################
        # read power from shelly heaters
        ########################
        index = 0
        (status, last_shelly_0_power, temp_shelly_0, overt) = get_shelly_power_by_index(index)
        print('shelly power %s: index %d, ison %s, power %0.0f, temp %0.1f, overtemp %s ' %(shelly_name[index], index, str(status) , last_shelly_0_power, temp_shelly_0, str(overt)))
        
        index = 1
        (status, last_shelly_1_power, temp_shelly_1, overt) = get_shelly_power_by_index(index)
        print('shelly power %s: index %d, ison %s, power %0.0f, temp %0.1f, overtemp %s ' %(shelly_name[index], index, str(status) , last_shelly_1_power, temp_shelly_1, str(overt)))


        # we have all the data, let's act on it

        print("==> about to act on data. current power situation is: production %0.1f, eddy %0.1f, grid (- is inject) %0.1f, home conso (incl eddy) %0.1f" %(production, router_power, net_conso, total_conso))
        
        
        ###################
        # test "abnormal" cases
        ##################
        # could just be oscilation
        # not really an error condition. just log and write to terminal 

        # surplus exist, but router is not max'ed out.
        if net_conso < grid_min and  router_power < expected_solar_router_power and router_power not in [-1, -2]:
            s = 'WARNING: surplus %0.1f, while router not diverting enough %0.1f (expected %d)' %(net_conso, router_power, expected_solar_router_power)
            logging.warning(s)
            print(s)
            blynk.virtual_write(vpin.v_terminal, stamp + s)


        # drawing from grid and router not close to zero
        if net_conso > grid_max and router_power > 200 and router_power not in [-1,-2]:
            s = 'WARNING: drawing from grid %0.1f, while router is still somehow diverting %0.1f' %(net_conso, router_power)
            print(s)
            logging.warning(s)
            blynk.virtual_write(vpin.v_terminal, stamp + s)



        ##############################
        # net_conso (ie surplus, draw) in band. 
        ############################# 
        # we are GOOD
        # no heater change, reset damping

        if net_conso < grid_max and net_conso > grid_min:
            s = '==> net conso %0.0f within band %d. do nothing' %(net_conso, grid_max)
            print(s)

            react_to_soutir = max_react_to_soutir
            react_to_surplus = max_react_to_surplus


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
                # surplus exist = net_conso
                #################

                s = '==> we have surplus %0.1f, primary %s, secondary %s. react to surplus %d. solar router should be at its max %0.1f' %(net_conso, primary_set_to_on_by_app, secondary_set_to_on_by_app, react_to_surplus, router_power)
                print(s)
                logging.info(s)

                # do not react immediatly, caters for spurious reading, or sudden change
                if react_to_surplus !=0: # wait to see if condition persist 
                    react_to_surplus = react_to_surplus -1
                    print('do not react to surplus yet. wait. react_to_surplus %d' %react_to_surplus)


                else: # react when react_to_grid = 0

                    # reset damping
                    react_to_surplus = react_to_surplus_max

                    #################
                    # manage surplus
                    # turn heater based on stored is_on status
                    #################

                    s = 'react to surplus: primary %s. primary is on %s, secondary is on %s' %(shelly_heater, primary_set_to_on_by_app, secondary_set_to_on_by_app) 
                    print(s)
                    logging.info(s)
                    # as we have surplus, turn ONE heater on. 

                    if primary_set_to_on_by_app == False:
                        s = 'set primary on. surplus %0.0fW. router %0.0fW. production %0.0fW. total conso %0.0fW' %(net_conso, router_power, production, total_conso)
                        print(s)
                        logging.info(s)
                        blynk.virtual_write(vpin.v_terminal, stamp + s)

                        # turn heater ON
                        set_heater_by_role('primary', 'on')  # set Blynk power and temp led
                        primary_set_to_on_by_app = True

                        GPIO.output(led_red,1)
                        updated_heater = True

                        sleep(sleep_after_react)
                        

                    elif secondary_set_to_on_by_app == False:

                        s = 'set secondary on. surplus %0.0fW. router %0.0fW. production %0.0fW. total conso %0.0fW' %(net_conso, router_power, production, total_conso)
                        print(s)
                        logging.info(s)
                        blynk.virtual_write(vpin.v_terminal, stamp + s)

                        # turn heater ON
                        set_heater_by_role('secondary', 'on')
                        secondary_set_to_on_by_app = True

                        GPIO.output(led_red,1)
                        updated_heater = True

                        sleep(sleep_after_react)


                    else: # both heaters already on
                        s = 'cannot react to surplus, all heaters already on'
                        print(s)
                        logging.info(s)
                        blynk.virtual_write(vpin.v_terminal, stamp + s)

                        sleep(sleep_after_react)


            if net_conso >  grid_max:

                ####################################################
                # drawing power from grid
                # this is not nite
                # turn heaters off
                ####################################################

                # of course at nigth we are drawing power, but here we are not at nite
                # of course, during winter we are drawing power, but then PLEASE disable automation altogether
                assert nite is False
                assert automation is True

                # we would draw if production drops (cloud, sunset), in that case we need to turn heater(s) off
                s = '==> we are drawing from grid %0.1f. primary %s, secondary %s. react to soutir %d. solar router should be at its min %0.1f' %(net_conso, primary_set_to_on_by_app,  secondary_set_to_on_by_app, react_to_soutir, router_power)
                print(s)
                logging.info(s)


                # do not react immediatly, spurious reading, or sudden change
                # counter decrements from react_to_soutir_max
                if react_to_soutir != 0: # wait to see if condition persist 
                    print('do not react to soutir yet. wait. react to soutir %d' %react_to_soutir)
                    react_to_soutir = react_to_soutir -1

            
                else: # react to soutir

                    react_to_soutir = react_to_soutir_max

                    s  ='react to soutir. primary %s. primary is on %s, secondary is on %s' %(shelly_heater, primary_set_to_on_by_app, secondary_set_to_on_by_app) 
                    print(s)
                    logging.info(s)

                    # as we are drawing, turn ONE heater oFF. 
                    if secondary_set_to_on_by_app == True:
                        s = 'drawing from grid. set secondary off. surplus %0.0fW. router %0.0fW. production %0.0fW. total conso %0.0fW' %(net_conso, router_power, production, total_conso)
                        print(s)
                        logging.info(s)
                        blynk.virtual_write(vpin.v_terminal, stamp + s)

                        # turn heater OFF
                        set_heater_by_role('secondary', 'off') 
                        secondary_set_to_on_by_app = False

                        GPIO.output(led_red,0)
                        updated_heater = True

                        sleep(sleep_after_react)

                    elif primary_set_to_on_by_app == True:
                        s = 'drawing from grid. set primary off. surplus %0.0fW. router %0.0fW. production %0.0fW. total conso %0.0fW' %(net_conso, router_power, production, total_conso)
                        print(s)
                        logging.info(s)
                        blynk.virtual_write(vpin.v_terminal, stamp + s)

                        # turn heater OFF
                        set_heater_by_role('primary', 'off')
                        primary_set_to_on_by_app = False

                        GPIO.output(led_red,0)
                        updated_heater = True

                        sleep(sleep_after_react)

                    else:
                        s = 'drawing from grid. but all heaters already off.. net conso %0.0fW. router %0.0fW. production %0.0fW. total conso %0.0fW' %(net_conso, router_power, production, total_conso)
                        logging.info(s)
                        print(s)
                        blynk.virtual_write(vpin.v_terminal, stamp + s)

                        sleep(sleep_after_react)

        # end of grid band

        # end of one act on data

        ###############################
        # update TFT display (always) and Blynk (every so often or heater changed)
        ###############################

        # heaters could have been updated
        # values at start of loop. should see result in next loop
  
                        
        # all heaters (eddi + shellies)
        # router_power == -1 if cannot get it from neither PZEM nor cloud

        she = round(last_shelly_0_power + last_shelly_1_power, 0)
        all_heaters = she + router_power

        ####################
        # update SPI TFT for EACH automation loop
        ####################

        if display != None:

            # create new image and use draw to piant into it
            (image, draw) = my_st7789.st7789_new_image()

            space = 8 # between lines
            y = space

            # TO DO: better graphics
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

            # heaters status, ie is on
            s = "%s, %s" %(primary_set_to_on_by_app, secondary_set_to_on_by_app)
            size_x, size_y = draw.textsize(s, font)
            draw.text((0, y), s, font=font, fill=(0, 200, 200))
            y = y + size_y + space 

            # damping. react when counter is 0
            s= "draw%d export%d" %(react_to_soutir, react_to_surplus)
            draw.text((0, y), s, font=font, fill=(0, 200, 200))
            y = y + size_y + space 

            # current time
            draw.text((0, y), stamp, font=font, fill=(0, 255, 255))
            
            # display resulting image
            display.display(image)  
        else:
            # no display
            pass

        # end of TFT

        ######################################
        # update Blynk every so often OR if heater state changed
        #######################################

        # update all gauge (powers, temp)
        # check monit summary and send email if monit error
        # update last_action_list widget (label)
            
        # values at start of loop. should see result in next loop

        nb_loop = nb_loop + 1

        ##### CHECK: heater updated by value from start of the loop 
        if nb_loop == blynk_update_count or updated_heater: 

            if nb_loop == blynk_update_count:
                nb_loop = 0

            ############################
            # update blynk every so often
            ############################
            print('publish to blynk (value from loop start)')
            # values at start of loop. should see result in next loop

            blynk.virtual_write(vpin.v_power_grid, net_conso)
            blynk.virtual_write(vpin.v_power_production, production)

            # update even if router_power = -1
            # make sure gauge can display -1 , ie define datastream -2 to 2000
            blynk.virtual_write(vpin.v_power_eddy, router_power)
            blynk.virtual_write(vpin.v_total_heater, router_power + last_shelly_0_power + last_shelly_1_power)

            # update heaters power and temp. otherwize those are updated only in case of on/off
            blynk.virtual_write(shelly_power[0], last_shelly_0_power)
            blynk.virtual_write(shelly_temp[0], temp_shelly_0)

            blynk.virtual_write(shelly_power[1], last_shelly_1_power)
            blynk.virtual_write(shelly_temp[1], temp_shelly_1)

            #######
            # monit
            #######
            print('check monit summary')
            s = monit_mail.monit_summary()

            # parse output to look for error
            if not monit_mail.parse_monit_summary(s):

                s1 = "monit reported some error, sending email and push notification"
                logging.error(s1)
                print(s1)

                logging.error(s)
                print(s)

                blynk.virtual_write(vpin.v_terminal, s1)

                # send a push notif, but not as alert to not bother the user
                log_and_notify_error(s , warning=True)


                # send mail
                try:
                    monit_mail.send_mail(secret.sender_email, secret.email_passwd, secret.dest_email, subject="monit reported some error", content = "monit output:\n" + s , html="False")

                except Exception as e:
                    s = "exception sending email %s" %str(e)

                    log_and_notify_error(s)

                    blynk.virtual_write(vpin.v_terminal, s)

            else: # monit OK
                print("monit ok")

            ##################
            # last action list
            # maintained in shelly_onoff_by_index()
            ##################
                
            # write to widget content. better UI, even if not persistent
            s=""
            for i in last_actions_list:
                s = s + i

            blynk.set_property(vpin.v_last_actions, "label", "last actions")
            blynk.set_property(vpin.v_last_actions, "color", "#D3435C")
            blynk.virtual_write(vpin.v_last_actions, s)


        else: # do not update blynk yet
            pass 

        # TO DO garbage collection. ie eddy off and only heaters on.


    else: 
        #################################
        # automation and not nite is FALSE
        # not the "normal" automation loop
        #################################

        # write some status to display
        s = 'special processing (no automation or in nite): automation: %s, nite: %s' %(automation, nite)
        print(s)

        if nite:
            s = "in nigth"
        else:
            s = "automation OFF"

        spacing = 10 # for mulitiline str
        # align – If the text is passed on to multiline_text(), “left”, “center” or “right”.

        if display != None:
            # create new image and use draw to paint into it
            (image, draw) = my_st7789.st7789_new_image()
            draw.text((0, 20), s, font=font, fill=(255, 0, 0))
            draw.text((0, 100), stamp, font=font, fill=(0, 255, 0))

            s = "actif within:\n" + nite_definition
            draw.multiline_text((0, 180), s, font=font, fill=(100, 100, 100), spacing = spacing, align='right')
            display.display(image) 


        if nite:
            #################
            # nite. react once (ie when entering nite)
            #################

            if nite_only_once:
                nite_only_once = False
                # could be running all day and entering nite, or starting during nite
                s = "entering into/starting at nite while automation is: %s" %automation
                logging.info(s)

                if automation:

                    # leave system in a clean state. assume another process (manual) will take over
                    s = "entering into/starting at nite: automation %s. turn heaters off; let someone else care for it" %automation
                    print(s)
                    logging.info(s)
                    # relay, led/button, terminal, power values
                    # called also in automation button call back
                    transition_turn_all_heaters_off(s)

                else:
                    s = "entering into/starting at nite: automation %s. leave heater alone" %automation # someone needs them
                    print(s)
                    logging.info(s)
                    

            else:
                # within nite 
                # leave system state as it. 
                pass

        else: # not in automation
            # leave system state as it. someboby else is likely using it using it
            pass 

    #########################
    # sleep between automation loop
    #########################
    sleep(sleep_sec)




