import serial

ser = serial.Serial('COM19', 56700, timeout=0)
while 1:
    if( ser.inWaiting()):
        s = ser.read(1)
        print "-->", s

