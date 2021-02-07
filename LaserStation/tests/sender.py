#!/usr/bin/python
import time
from math import sin, cos
from SerialFlow import SerialFlow
 
SEND_TIMEOUT = 0.1

COM_PORT = "COM79"
BAUD = 19200

sf = SerialFlow(COM_PORT, BAUD, timeout=0.5)
sf.setPacketFormat( 1, 2, 0 )

send_time = time.time()

x = 0

try:
    while True:
        now = time.time()
        if now > send_time + SEND_TIMEOUT:
            send_time = now
            sf.setPacketValue( int(sin(x*3.1415/180.0)*100) )
            sf.setPacketValue( int(cos(x*3.1415/180.0)*100) )
            sf.sendPacket()
            x += 1
            if x == 360:
                x = 0

except KeyboardInterrupt:
    pass

sf.close()
