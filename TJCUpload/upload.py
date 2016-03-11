# Originally created by Jorge Mesquita
# Modified by Bjorn Schrader
# coding=utf-8

import threading
import time
import os
import sys
import serial

from config import *

FFF = chr(0xff)+chr(0xff)+chr(0xff)

if len(sys.argv) != 2:
	print('usage: python %s file_to_upload.tft' % sys.argv[0])
	exit(-2)

file_path = sys.argv[1]

if os.path.isfile(file_path):
	print('uploading %s (%i bytes)...' % (file_path, os.path.getsize(file_path)))
else:
	print('file not found')
	exit(-1)

fsize = os.path.getsize(file_path)
print('Filesize: ' + str(fsize))

ser = serial.Serial(PORT, BAUDCOMM, timeout=.1, )

def upload():
    global ser
    ser.write('tjchmi-wri %i,%i,0' % (fsize, BAUDUPLOAD))
    ser.write(FFF)
    ser.flush()
    time.sleep(.5)

    print('waiting response')
    ser.baudrate = BAUDUPLOAD
    ser.timeout = 0.1
    time.sleep(BAUDRATE_SWITCH_TIMEOUT)

    # wait for response
    b = 0
    while b<>chr(0x05):
        b = ser.read(1)

    time.sleep(.2)

    print('Uploading...')
    with open(file_path, 'rb') as hmif:
        dcount = 0
        while True:
            data = hmif.read(4096)
            if len(data) == 0: break
            dcount += len(data)
            ser.write(data)
            time.sleep(0.2)
            sys.stdout.write('\rDownloading, %3.1f%%...' % (dcount/ float(fsize)*100.0))
            sys.stdout.flush()

            # wait for response
            b = 0
            while b<>chr(0x05):
                b = ser.read(1)

no_connect = True

ser.baudrate = BAUDCOMM
ser.timeout = 3000/BAUDCOMM + 0.2
print('Trying with ' + str(BAUDCOMM) + '...')
ser.write(FFF)
ser.write('connect')
ser.write(FFF)
r = ser.read(128)
if 'comok' in r:
    print('Connected with ' + str(BAUDCOMM) + '!')
    no_connect = False
    status, unknown1, model, unknown2, version, serial, flash_size = r.strip("\xff\x00").split(',')
    print('Status: ' + status)
    print('Model: ' + model)
    print('Version: ' + version)
    print('Serial: ' + serial)
    print('Flash size: ' + flash_size)
    if fsize > flash_size:
        print('File too big!')
    if not CHECK_MODEL in model:
        print('Wrong Display!')
    upload()

if no_connect:
    print('No connection!')
else:
    print('File written to Display!')

ser.close()

