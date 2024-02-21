#!/usr/bin/env python


# pip3 install adafruit-circuitpython-rgb-display
# https://docs.circuitpython.org/projects/rgb_display/en/latest/
# https://github.com/adafruit/Adafruit_CircuitPython_RGB_Display/blob/main/examples/rgb_display_pillow_stats.py

from time import sleep
from PIL import Image, ImageDraw, ImageFont
# The ImageDraw module provides simple 2D graphics for Image objects

####################################
# library for multiple TFT SPI
# BUT ... my ST7789 board has no CS pin. not sure if this driver works
####################################


import busio
import digitalio
import board
from board import SCK, MOSI, MISO, D6, D13,  CE0

from adafruit_rgb_display import ili9341
from adafruit_rgb_display import st7789  
from adafruit_rgb_display import color565


import ST7789 


#width: number of pixels wide  
#height: number of pixels high

# https://github.com/pimoroni/st7789-python
#sudo apt-get install  python-pip
#sudo pip install st7789 spidev numpy RPi.GPIO Pillow
# Requirement already satisfied: st7789 in /usr/local/lib/python3.9/dist-packages (0.0.4)

def create_st7789():

    _RES= 13  # reset active low
    _DC = 19 # data command
    _BLK = 26 # backligth. if NC on  low for off
    # no CS, spi mode 3

    try:

        display = ST7789.ST7789(height=240,width=240, rotation=0,port=0, cs=0, rst=_RES, dc=_DC, backlight=_BLK, spi_speed_hz=80 * 1000 * 1000)  
        display._spi.mode=3   # for board without CS ??

        display.reset()  
        display._init() 

        width = display.width
        height = display.height
        print("display: w%d, h%d" %(width, height))

        #display.begin()

        #font = ImageFont.load("arial.pil") # bitmap font
        font = ImageFont.truetype("arial_narrow_7.ttf", 30) # TrueType font, size in pixels

        # Some other nice fonts to try: http://www.dafont.com/bitmap.php

        return(display, font, width, height)

    except Exception as e:
        print("cannot create st7789 SPI display %s" %str(e))
        return(None, None, None, None)

def create_ili9341(rotation=0):

    # Setup SPI bus using hardware SPI:
    spi = busio.SPI(clock=SCK, MOSI=MOSI, MISO=MISO)
    #spi1 = board.SPI()

    CS_PIN = CE0
    DC_PIN = D6
    RST_PIN = D13

    try:
        display = ili9341.ILI9341(spi, rotation= rotation, cs=digitalio.DigitalInOut(CS_PIN), dc=digitalio.DigitalInOut(DC_PIN), rst= digitalio.DigitalInOut(RST_PIN))
        #display = st7789.ST7789(spi, rotation=90, width=172, height=320, x_offset=34, # 1.47" ST7789
    except Exception as e:
        print('cannot create display ', str(e))
        return (None, None, None, None)

    else:
        width = display.width
        height = display.height
        print("display: w%d, h%d" %(width, height))

        # we swap height/width to rotate it to landscape!
        if rotation == 90: # landscape, pins on the left
            width = display.height
            height = display.width

    # os.getcwd /home/pi
    font = ImageFont.truetype("arial_narrow_7.ttf", 25)
    #font = ImageFont.load('file.pil')
    #font = ImageFont.load_default()

    return(display, font, width, height)


def new_image(width=320, height=240):
    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)
    return(image, draw)


def splash(file, w=320, h=240):
    image=Image.open(file)  
    image=image.resize((w,h),resample=Image.LANCZOS)  
    return(image)
    

if __name__ == "__main__":

    (display, font, w, h) = create_ili9341(rotation=90)

    image = splash("./meaudre.jpg")
    display.image(image)
    sleep(3)

    (image, draw) = new_image(w, h)

    # Main loop:
    for i in range(5):

        draw.rectangle((0,0,w,h), fill=(0,0,0)) # black
    
        # with adafruit RGB lib
        #display.fill(0)
        #display.pixel(120, 160, color565(255, 0, 0)) # Draw a red pixel in the center.
        #display.fill(color565(0, 0, 255)) # Clear the screen blue.

        y = 10
        y_space = 10

        s = 'testing %d' %i
        size_x, size_y = draw.textsize(s, font)
        draw.text((10, y), s, font=font, fill="#FFFFFF")
        y = y + size_y + y_space

        s = 'tft display %d' %i
        size_x, size_y = draw.textsize(s, font)
        draw.text((10, y), s, font=font, fill=(255, 0, 0))
        y = y + size_y + y_space

        s = 'adafruit RGB driver %d' %i
        size_x, size_y = draw.textsize(s, font)
        draw.text((10, y), s, font=font, fill=(255, 0, 255))
        y = y + size_y + y_space

        display.image(image)

        sleep(3)


