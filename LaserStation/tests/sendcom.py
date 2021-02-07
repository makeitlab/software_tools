# Script for SFMonitor testing
# generates sin function in 0..360 period

import serial, math
from time import sleep

MD_SIMPLE = 0
MD_COMPLEX_YT = 1
MD_COMPLEX_YX = 2


PORT = 'COM79'
VSIZE = 1
MODE = MD_COMPLEX_YX
DELAY = 0.05

def send_simple(port, y):
    port.write(chr(y))

def send_complex_yx(port, x, y):
    port.write(chr(0x12))
    if x in (0x12,0x13,0x10,0x7d):
        port.write(chr(0x7d))
    port.write(chr(x))
    port.write(chr(0x10))
    if y in (0x12,0x13,0x10,0x7d):
        port.write(chr(0x7d))
    port.write(chr(y))
    port.write(chr(0x13))


serial_arg = dict( port=PORT,
                   baudrate=9600,
                   stopbits=serial.STOPBITS_ONE,
                   parity=serial.PARITY_NONE,
                   timeout=0.01)

serial_port = serial.Serial(**serial_arg)

x = 0

print ('port ready')    

try:
    while(1):
        v = int(math.sin(x*3.1415/180.0)*127 + 128)
        if MODE == MD_SIMPLE:
            send_simple(serial_port, v)
        elif MODE == MD_COMPLEX_YX:
            send_complex_yx(serial_port, x, v)
        x += 1
        if x == 255:
            x = 0
        sleep(DELAY)

except KeyboardInterrupt:
    print ('turn off port')    
    serial_port.close()
