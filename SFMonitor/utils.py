import re, itertools
import winreg

import random, time
import queue

# Serial utils
#  
def full_port_name(portname):
    """ Given a port-name (of the form COM7, 
        COM12, CNCA0, etc.) returns a full 
        name suitable for opening with the 
        Serial class.
    """
    m = re.match('^COM(\d+)$', portname)
    if m and int(m.group(1)) < 10:
        return portname    
    return '\\\\.\\' + portname    
    

def enumerate_serial_ports():
    """ Uses the Win32 registry to return an 
        iterator of serial (COM) ports 
        existing on this computer.
    """
    path = 'HARDWARE\\DEVICEMAP\\SERIALCOMM'
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
    except WindowsError:
        raise IterationError

    for i in itertools.count():
        try:
            val = winreg.EnumValue(key, i)
            yield str(val[1])
        except EnvironmentError:
            break

# Queue utils
#  
class Timer(object):
    def __init__(self, name=None):
        self.name = name
    
    def __enter__(self):
        self.tstart = time.time()
        
    def __exit__(self, type, value, traceback):
        if self.name:
            print ('[%s]' % self.name),
        print ('Elapsed: %s' % (time.time() - self.tstart))


def get_all_from_queue(Q):
    """ Generator to yield one after the others all items 
        currently in the queue Q, without any waiting.
    """
    try:
        while True:
            yield Q.get_nowait( )
    except queue.Empty:
        raise StopIteration


def get_item_from_queue(Q, timeout=0.01):
    """ Attempts to retrieve an item from the queue Q. If Q is
        empty, None is returned.
        
        Blocks for 'timeout' seconds in case the queue is empty,
        so don't use this method for speedy retrieval of multiple
        items (use get_all_from_queue for that).
    """
    try: 
        item = Q.get(True, 0.01)
    except queue.Empty: 
        return None
    
    return item

def join_bytes(bytes, unsigned, size):
    if unsigned:
        if size == 1:
            return ushort8(bytes[0])
        elif size == 2:
            return ushort16(bytes[0] + (bytes[1]<<8))
    else:
        if size == 1:
            return short8(bytes[0])
        elif size == 2:
            return short16(bytes[0] + (bytes[1]<<8))

def typecast(v, unsigned=1):
    if unsigned:
        return ushort8(v)
    else:
        return short8(v)

def ushort8(x):
    if x>0xFF:
        raise OverflowError
    return x

def short8(x):
    if x>0xFF:
        raise OverflowError
    if x>0x7F:
        x=int(0x100-x)
        if x<128:
            return -x
        else:
            return -128
    return x

def ushort16(x):
    if x>0xFFFF:
        raise OverflowError
    return x

def short16(x):
    if x>0xFFFF:
        raise OverflowError
    if x>0x7FFF:
        x=int(0x10000-x)
        if x<32768:
            return -x
        else:
            return -32768
    return x

def strToColor(s):
    return (int('0x'+s[1:3], 16), int('0x'+s[3:5], 16), int('0x'+s[5:7], 16))

def colorToStr(c):
    return '#%02x%02x%02x' % c
