
import serial, time

ser = serial.Serial(
			port="COM4",
			baudrate=9600,
			parity=serial.PARITY_NONE,
			stopbits=serial.STOPBITS_ONE,
			bytesize=serial.EIGHTBITS,
			timeout = 5)

if ser.isOpen():
	ser.close()
ser.open()

print(ser, ser.isOpen())

array 		=	[0xB4,0xC0]

while True:
    print('sending')
    ser.write(serial.to_bytes(array)) 
    ser.write("testing".encode('utf8'))
    time.sleep(5)