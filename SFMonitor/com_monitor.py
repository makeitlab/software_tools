""" 
COM port listener for Serial Monitor.

Oleg Evsegneev (oleg.evsegneev@gmail.com)
Last modified: 13.10.2012

Author of original programm structure:
Eli Bendersky (eliben@gmail.com)
"""

import threading
import time

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
                    port_stopbits=serial.STOPBITS_ONE,
                    port_parity=serial.PARITY_NONE,
                    port_timeout=0.01,
                    data_format=None,
                    value_size=2,
                    separator=1):
        threading.Thread.__init__(self)

        self.serial_port = None
        self.serial_arg = dict( port=port_num,
                                baudrate=port_baud,
                                stopbits=port_stopbits,
                                parity=port_parity,
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
            if self.serial_port:
                self.serial_port.close()
            self.serial_port = serial.Serial(**self.serial_arg)
        except serial.IOError as e:
            self.error_q.put(e.message)
            return

        # Restart the clock
        tshift = time.clock()
        df = self.data_format
        escape = False
        collecting = False
        frame_buffer = [[]]
        while self.alive.isSet():
            # Reading 1 byte, followed by whatever is left in the
            # read buffer, as suggested by the developer of
            # PySerial.
            #
            data = self.serial_port.read(1)
            data += self.serial_port.read(self.serial_port.inWaiting())

            timestamp = time.clock() - tshift
            if len(data) > 0:
                if df == FMT_SIMPLE:
                    self.data_q.put((timestamp, data[-1]))
                elif df in (FMT_COMPLEX_VT, FMT_COMPLEX_YX):
                    for d in data:
                        d_ = d
                        if collecting:
                            if escape:
                                frame_buffer[-1].append(d)
                                if not self.separator and len(frame_buffer[-1]) == self.value_size:
                                    frame_buffer.append([])
                                escape = False
                            # escape
                            elif d_ == 0x7D:
                                escape = True
                            # value separator
                            elif self.separator and d_ == 0x10:
                                frame_buffer.append([])
                            # end
                            elif d_ == 0x13:
                                if not self.separator:
                                    frame_buffer = frame_buffer[:-1]
                                self.data_q.put((timestamp, frame_buffer))
                                collecting = False
                                v_idx = 0
                            else:
                                frame_buffer[-1].append(d)
                                if not self.separator and len(frame_buffer[-1]) == self.value_size:
                                    frame_buffer.append([])
                        # begin
                        elif d_ == 0x12:
                            frame_buffer = []
                            frame_buffer.append([])
                            collecting = True

        # clean up
        if self.serial_port:
            self.serial_port.close()

    def join(self, timeout=None):
        self.alive.clear()
        threading.Thread.join(self, timeout)
