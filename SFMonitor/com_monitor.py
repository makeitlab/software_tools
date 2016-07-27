""" 
COM port listener for Serial Monitor.

Oleg Evsegneev (oleg.evsegneev@gmail.com)
Last modified: 13.10.2012

Author of original programm structure:
Eli Bendersky (eliben@gmail.com)
"""

import threading
import time
from SerialFlow.SerialFlow import SerialFlow

import serial

FMT_SIMPLE = 0
FMT_COMPLEX_VT = 1
FMT_COMPLEX_YX = 2

frame_buffer = []

class ComMonitorThread(threading.Thread):
    """ A thread for monitoring a COM port. The COM port is
        opened when the thread is started.

        data_q:
            Queue for received data. Depending on data format, 
            items in the queue are (timestamp, data.byte ) pairs or
            (timestamp, [[bit1,bit2],[bit,bit2],...]).

        error_q:
            Queue for error messages. In particular, if the
            serial port fails to open for some reason, an error
            is placed into this queue.

        port:
            The COM port to open. Must be recognized by the
            system.

        port_baud/stopbits/parity:
            Serial communication parameters

        port_timeout:
            The timeout used for reading the COM port. If this
            value is low, the thread will return data in finer
            grained chunks, with more accurate timestamps, but
            it will also consume more CPU.
    """
    def __init__(   self,
                    data_q, error_q,
                    port_num,
                    port_baud,
                    port_timeout=0.01,
                    data_format=None,
                    value_size=2,
                    separator=1):
        threading.Thread.__init__(self)

        self.sf = None
        self.serial_arg = dict( port=port_num,
                                baudrate=port_baud,
                                timeout=port_timeout)

        self.data_q = data_q
        self.error_q = error_q

        self.data_format = data_format
        self.value_size = value_size
        self.separator = separator

        self.alive = threading.Event()
        self.alive.set()

    def run(self):
        try:
            if self.sf is not None:
                self.sf.close()
            self.sf = SerialFlow(**self.serial_arg)
        except serial.IOError as e:
            self.error_q.put(e.message)
            return

        if self.data_format == FMT_SIMPLE:
            self.sf.setPacketFormat(1, 0, 0)
        elif self.data_format in (FMT_COMPLEX_VT, FMT_COMPLEX_YX):
            self.sf.setPacketFormat(self.value_size, 3, self.separator)

        # Restart the clock
        tshift = time.clock()
        while self.alive.isSet():
            timestamp = time.clock() - tshift
            if self.data_format == FMT_SIMPLE:
                bt = self.sf.receiveByte()
                if bt is not None:
                    self.data_q.put((timestamp, bt))
            elif self.data_format in (FMT_COMPLEX_VT, FMT_COMPLEX_YX):
                if self.sf.receivePacket():
                    self.data_q.put((timestamp, self.sf.listPacketValues()))

        # clean up
        if self.sf is not None:
            self.sf.close()

    def join(self, timeout=None):
        self.alive.clear()
        threading.Thread.join(self, timeout)
