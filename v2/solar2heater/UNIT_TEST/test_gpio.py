#!/usr/bin/python3

from time import sleep

import RPi.GPIO as GPIO
import os

button = 20 # connected to gnd. pull up
led_red = 12 #  gpio out red
led_yellow = 24 #  gpio out yellow

#pip3 install RPi.GPIO

# ISR
def int_reboot(x):
    sleep(2) # sleeping in isr is not great, but will reboot or halt anyway

    if GPIO.input(button) == 0:
        # long press = reboot
        print('reboot')
        os.system("sudo reboot")

        
    else:
        # short press = halt
        print('halt')
        os.system("sudo halt")
	


def blink_led(led,sec):
	GPIO.output(led,1)
	sleep(sec)
	GPIO.output(led,0)
	sleep(sec)



GPIO.setmode(GPIO.BCM)

GPIO.setup(button, GPIO.IN, pull_up_down=GPIO.PUD_UP)


# use interrupt
# GPIO.RISING
GPIO.add_event_detect(button, GPIO.FALLING, callback=int_reboot, bouncetime=500)  

GPIO.setup(led_red, GPIO.OUT)
GPIO.setup(led_yellow, GPIO.OUT)

GPIO.output(led_red,0) # turn off 
GPIO.output(led_yellow,1) 

print("test GPIO")

while True:
    blink_led(led_red,2)
    blink_led(led_yellow,2)
    sleep(1)


