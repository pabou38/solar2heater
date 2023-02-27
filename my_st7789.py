#!/bin/python3

import ST7789  

print('TFT ST7789')

# https://github.com/pimoroni/st7789-python
#sudo apt-get install  python-pip
#sudo pip install st7789 spidev numpy RPi.GPIO Pillow
# Requirement already satisfied: st7789 in /usr/local/lib/python3.9/dist-packages (0.0.4)

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

# Pillow, the friendly PIL fork. PIL is an acronym for Python Imaging Library.
# https://pillow.readthedocs.io/en/stable/handbook/tutorial.html

from time import sleep 
import logging

_RES= 13  # reset active low
_DC = 19 # data command
_BLK = 26 # backligth. if NC on  low for off
# no CS, spi mode 3

def st7789_create_display():

    try:
        # rot 90 to have pins on top. default is pins on left
        display = ST7789.ST7789(height=240,width=240, rotation=90, port=0, cs=0, rst=_RES, 
        dc=_DC, backlight=_BLK, spi_speed_hz=80 * 1000 * 1000, offset_left=0, offset_top=0) 
    
    except Exception as e:
        s = "cannot create st7789 SPI display %s" %str(e)
        print(s)
        try: # in case looging not set up
            logging.error(s)
        except:
            pass
        return(None, None)

    display._spi.mode=3   # for board without CS ??
    display.reset()  
    display._init() 
    #display.begin()

    # Some other nice fonts to try: http://www.dafont.com/bitmap.php
    #font = ImageFont.load_default()
    font = ImageFont.truetype('Minecraft.ttf', 30) # font size
    return(display, font)

# use draw to paint into image
def st7789_new_image():
    image=Image.new('RGB',(240,240),(0,0,0))  

    # do graphics in image just created, using draw
    draw = ImageDraw.Draw(image)
    return(image, draw)


def st7789_splash_jpg(file, display):
    image=Image.open(file)  
    image=image.resize((240,240),resample=Image.LANCZOS)  
    display.display(image)  

if __name__ == "__main__":

    print("running from main")

    (display, font) = st7789_create_display()

    print("display created")

    (image, draw) = st7789_new_image()

    # elipse, line, polygon
    draw.rectangle((10, 10, display.width - 10, display.height - 10), outline=(255, 0, 0), fill=(0, 0, 255))

    s = "thea"
    size_x, size_y = draw.textsize(s, font) # This method is supposed to take a string and a font, and return the width and height that the string would occupy when rendered in that font
    print("size of %s: x:%d, y:%d" %(s,size_x, size_y)) # # get text size in pixels

    draw.text((30, 30), 'Minecraft', font=font, fill=(255, 255, 255))
    # display resulting image
    display.display(image)  
    sleep(5)  

    st7789_splash_jpg("./meaudre.jpg", display)
    st7789_splash_jpg("./thea.jpg", display)
    sleep(5)
