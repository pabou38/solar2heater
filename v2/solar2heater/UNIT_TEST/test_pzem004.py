#!/usr/bin/env python
# -*- coding: utf_8 -*-

from ensurepip import bootstrap
import serial
import sys

import modbus_tk
import modbus_tk.defines as cst
from modbus_tk import modbus_rtu

# pip install modbus_tk
# Requirement already satisfied: modbus_tk in /home/pi/.local/lib/python3.9/site-packages (1.1.2)

# https://www.framboise314.fr/utiliser-luart-port-serie-du-raspberry-pi-4/
# https://www.framboise314.fr/le-port-serie-du-raspberry-pi-3-pas-simple/


# default P3, S0 = mini uart = GPIO 14,15     AMA0 = full uart = BT
# disable console

tty = '/dev/ttyS0' # on PI3, PI4 , PI with BT

def main():
    """main"""
    logger = modbus_tk.utils.create_logger("console")

    try:
        print('connect to modbus slave')

        master = modbus_rtu.RtuMaster(
            serial.Serial(port=tty, baudrate=9600, bytesize=8, parity='N', stopbits=1, xonxoff=0)
        )

        master.set_timeout(5.0)
        master.set_verbose(True)

        logger.info("rtu master connected")
        #2023-02-25 10:18:56,100 INFO    modbus_rtu.__init__     MainThread      RtuMaster /dev/ttyS0 is opened
        #2023-02-25 10:18:56,101 INFO    read_pzem004.main       MainThread      rtu master connected
	

    except Exception as e:
        print('cannot create RTU master ', str(e))


    try:

        # Usage is the same as for modbus-tk, meaning that aside from initialisation any Python script written for modbus-tk should work with micropython-modbus.
        # For example, to perform a "read input registers" operation from device address 1 and register 0x00 for a length of two words:

        # 'execute' returns a pair of 16-bit words   word tuple

        # slave address 1, read starts at register 0, read 1 words
        # cst.READ_INPUT_REGISTERS

        """
        volt: 222.9
        amps:  0.0
        (0, 0)
        power W:  0.0
        """


        try:

            volt = master.execute(1, 4 , 0, 1) # 16 bits.  0.1V  (2323,) <class 'tuple'>  int
            #print(volt)
            volt = volt[0]/10.0
            print('volt: %0.1f' %volt)

            """
            2023-02-25 10:24:25,735 DEBUG   modbus.execute  MainThread      -> 1-4-0-0-0-1-49-202
            2023-02-25 10:24:25,775 DEBUG   modbus.execute  MainThread      <- 1-4-2-8-141-126-149
            volt: 218.9
            """
        except Exception as e:
            print('exception read input register: ', str(e))
            sys.exit(1)

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

            print('amps: ' , amp_low /1000.0) # assume same indianess
        except Exception as e:
            print('exception read input register: ', str(e))
            sys.exit(1)

        #  cleaner 3ams 6000 mw

        try:

            f_word_pair = master.execute(1, cst.READ_INPUT_REGISTERS, 0x03, 2) # 2 x 16 bits , 1st one is low 16 bits   milli amps
            # f word pair:  (0, 0) <class 'tuple'> <class 'int'>
            print(f_word_pair)

            power_low = f_word_pair[0] # low 16 bits  0.1W  65535 = 6500W max. so gigh 16 bit should always be zero in my case
            power_high = f_word_pair[1] # high 16 bits, to create 32 bit integer 
            assert power_high == 0

            print('power W: ' , power_low /10.0) # assume same indianess

        except Exception as e:
            print('exception read input register: ', str(e))
            sys.exit(1)



        #logger.info(master.execute(1, cst.READ_COILS, 0, 10))
        #logger.info(master.execute(1, cst.READ_DISCRETE_INPUTS, 0, 8))
        #logger.info(master.execute(1, cst.READ_INPUT_REGISTERS, 100, 3))
        #logger.info(master.execute(1, cst.READ_HOLDING_REGISTERS, 100, 12))
        #logger.info(master.execute(1, cst.WRITE_SINGLE_COIL, 7, output_value=1))
        #logger.info(master.execute(1, cst.WRITE_SINGLE_REGISTER, 100, output_value=54))
        #logger.info(master.execute(1, cst.WRITE_MULTIPLE_COILS, 0, output_value=[1, 1, 0, 1, 1, 0, 1, 1]))
        #logger.info(master.execute(1, cst.WRITE_MULTIPLE_REGISTERS, 100, output_value=xrange(12)))

    except modbus_tk.modbus.ModbusError as exc:
        logger.error("%s- Code=%d", exc, exc.get_exception_code())

if __name__ == "__main__":
    main()
