version = "1.0"

from utime import ticks_ms, ticks_diff
start_time=ticks_ms() # note t=time() is in seconds. to measure execution time

print('\n\n================== PZEM 004T modbus micropython. version %s. =====================\n' %(version))

"""
pzem red led on AC side  = AC
red led on tx/rx side = 5v supplied by microcontroler. present even if AC Off. need 5V and rx connected WTF. lit even if gnd not connected
seems actually rx led
red led when tx and rx
"""

import gc
import os
import sys

from utime import sleep_ms, sleep, sleep_us, localtime, gmtime, mktime
from machine import Pin, RTC, I2C, ADC, reset, Timer, DEEPSLEEP, deepsleep, reset_cause, DEEPSLEEP_RESET, PWRON_RESET, HARD_RESET  
from machine import UART

import struct
# converting between strings of bytes and native Python data types such as numbers and strings.
# format specifiers made up of characters representing the type of the data 
#     and optional count and endian-ness indicators
"""
endianness = [
    ('@', 'native, native'),
    ('=', 'native, standard'),
    ('<', 'little-endian'),
    ('>', 'big-endian'),
    ('!', 'network'),
    ]
"""

# http://pymotw.com/2/struct/

# s = struct.Struct('I 2s f')    to pack unsigned Integer (4 bytes), 2char,  float (4 bytes)
# https://docs.python.org/2.7/library/struct.html#format-characters   for ALL format
# h short 2 bytes  <h little indian

import binascii

# binascii.hexlify to print as hex ascii  binascii.hexlify(packed_data) 0100000061620000cdcc2c40
# packed_data = binascii.unhexlify('0100000061620000cdcc2c40')


import logging # from micropython-lib-master  a single logging.py vs logging dir

print('create logger, will display on stdout')
logging.basicConfig(level=logging.CRITICAL)

log = logging.getLogger("pzem") # INFO:pzem:Test message2: 100(foobar).  uses pzem as log name
log.debug("Test message: %d(%s)", 100, "foobar")
log.info("Test message2: %d(%s)", 100, "foobar")
log.warning("Test message3")
log.error("Test message4")
#log.critical("test critical error")

logging.info("Test message6") # INFO:root:Test message6  uses root as log name

"""
try:
    1/0
except:
    log.exception("Some trouble (%s)", "expected")
    # AttributeError: 'module' object has no attribute 'exc_info'
"""    
class MyHandler(logging.Handler):
    def emit(self, record):
        print("levelname=%(levelname)s name=%(name)s message=%(message)s" % record.__dict__)

logging.getLogger().addHandler(MyHandler())
logging.info("Test message7")


# Installing is easy - just copy the modbus folder to your MicroPython board. It can live either in the root, or in a /lib folder.
import modbus # a directory under /. contains init.py
import modbus.defines as cst # modbus/defines.py
from modbus import modbus_rtu # modbus/modbus_rtu.py  (rtu is async version , vs tcp)

# dir(module) help(module)

print('create uart')
# UART 2 @ ESP32. rx 16, tx 17
# UART0 is used by REPL. vscode'
# uart1 tx gpio10 rx gpio9  may not be exposed
# https://www.engineersgarage.com/micropython-esp8266-esp32-uart/

"""
MicroPython allows multiplexing any GPIO with the hardware UARTs of ESP32. 
Therefore, irrespective of which default pins are exposed or not, all three UARTs can be used in a MicroPython script. 
While instantiating a UART object for ESP32, the Rx and Tx pins should also be passed as arguments.
"""
tx = 17
rx = 16
uart = UART(2, 9600, bits=8, parity=None, stop=1, timeout=1000, timeout_char=50, 
    tx=tx, rx=rx, flow =0, invert=0) # invert tx not ok
    # invert = 0 invert=UART.INV_TX. default idle = high
    # parity: 0 even
# spec PZEM 8 bit
print(uart)


"""
# logic analyzer, sample at 50khz
# write some char to avoid initial scrambling (seen with bitscope and salea logic analyzer)
a = [5,6,7,8] # avoid modbus address 1
b = bytes (a)
n = uart.write(b) # Write the buffer of bytes to the bus
assert n == len(a)
sleep_ms(4) # 2ms on logic analyzer. write to buffer is not synch to data put on the line

a = [1,2,3,4]
b = bytes (a)
for i in range(4):
    n = uart.write(b) # Write the buffer of bytes to the bus
    assert n == len(a)
sleep_ms(1)


# salea logic analyzer 24 Mhz
# decode lsb first. 
# 5ksamples 50Khz 
# invert = 0 , trigger falling edge
#40 A0 20 50   frame error
# 02 03 04 01 02 03 04 01 02 03 04  missing one seq and 01
# FF FE FF FE FF FE
#01 04 00 00 00 01 31 CA 

a = [0xff,0xfe]
b = bytes (a)
for i in range(3):
    n = uart.write(b)
    assert n == len(a)
sleep_ms(1)

uart.write('AAAA'.encode('utf-8'))
sleep_ms(1)
uart.write('BBB')
sleep_ms(1)
uart.write('C'.encode('utf-8'))
uart.write(bytes("test", 'utf-8'))
sleep_ms(1)
uart.write(b'titi')
"""


#master = modbus_rtu.RtuMaster(uart, serial_prep_cb=serial_prep) # in example, toggle cts
try:
    master = modbus_rtu.RtuMaster(uart)
    print('RTU master created')
except Exception as e:
    log.critical("cannot create RTU master")
    print('exception: cannot create RTU master ', str(e))
    sys.exit(1)


# Usage is the same as for modbus-tk, meaning that aside from initialisation any Python script written for modbus-tk should work with micropython-modbus.
# For example, to perform a "read input registers" operation from device address 1 and register 0x00 for a length of two words:

# 'execute' returns a pair of 16-bit words   word tuple
print('read input register 0x04')

# slave address 1, read starts at register 0, read 1 words

# 1st exchange not captured by logic analyzer
try:
    volt = master.execute(1, cst.READ_INPUT_REGISTERS, 0x00, 1) # 16 bits.  0.1V  (2323,) <class 'tuple'>  int
except Exception as e:
    print('exception read input register: ', str(e))
    log.critical(str(e))
    sys.exit(1)

# 01 04 00 00 00 01 CRC  register start at 0 , 1 word
# 01 04 02 09 09 CRC 0x0909 = 2313   231.1v

volt = volt[0]/10.0
print('volt: %0.1f' %volt)

# PZEM amps
# 01 04 00 01 00 02 CRC    register start from 1 , 2 words
# 25 ms
# 01 04 04 00 15 00 00 CRC   0x15  = 21   returns 4 bytes
#amps low ma:  21  
#amp high ma:  0

# 21 ma
f_word_pair = master.execute(1, cst.READ_INPUT_REGISTERS, 0x01, 2) # 2 x 16 bits , 1st one is low 16 bits   milli amps
# f word pair:  (0, 0) <class 'tuple'> <class 'int'>

amp_low = f_word_pair[0] # low 16 bits   65536 ma = 65 amps. max read for me. can safely disgard high 16 bits 
amp_high = f_word_pair[1] # high 16 bits, to create 32 bit integer (representing ma)

print("amps low ma: ", amp_low)
print("amp high ma: ", amp_high)
assert (amp_high == 0)

# TypeError: object with buffer protocol required
#print(binascii.hexlify(amp_low))

print('amps: ' , amp_low /1000.0) # assume same indianess

# Re-pack the pair of words into a single byte, then un-pack into a float
#<h short 2 bytes , little indian
# val = struct.unpack('<f', struct.pack('<h', int(f_word_pair[1])) + struct.pack('<h', int(f_word_pair[0])))[0]

while True:
    volt = master.execute(1, cst.READ_INPUT_REGISTERS, 0x00, 1)
    f_word_pair = master.execute(1, cst.READ_INPUT_REGISTERS, 0x01, 2)
    sleep(2)


print('end')