import serial

MAX_PACKET_SIZE = 128

def _join_bytes( bs ):
    v = 0
    x = 0
    for idx, b in enumerate(bs):
        v |= (b << (idx<<3))
    return v

class SerialFlow():
    _serial = None
    _escape = 0
    _collecting = 0
    _separate = False

    _p_size = 0
    _v_length = 0
    _vs_idx = 0
    _vr_idx = 0

    _vs = []
    _vr = []
    _vr_val = [0,0,0,0];
    _cr_idx = 0

    def __init__( self, port, baudrate, 
                  parity=serial.PARITY_NONE, 
                  stopbits=serial.STOPBITS_ONE, 
                  timeout=None ):
        self._serial = serial.Serial( port, baudrate, parity=parity, stopbits=stopbits, timeout=timeout )
        self._vs = [0]*MAX_PACKET_SIZE
        self._vr = [0]*MAX_PACKET_SIZE

    def close( self ):
        self._serial.close()

    def setPacketFormat( self, v_length, p_size, separate ):
        self._separate = separate
        self._p_size = p_size
        self._v_length = v_length
        self._vs_idx = 0
        self._vr_idx = 0

    def setPacketValue( self, value ):
        if self._vs_idx < self._p_size:
            self._vs[ self._vs_idx ] = value
            self._vs_idx += 1

    def sendPacket( self ):
        self._serial.write( chr(0x12) )
        for i in range( self._vs_idx ):
            for b in range( self._v_length ):
                v = (self._vs[i]>>(b<<3)) & 0xFF
                if v==0x12 or v==0x13 or v==0x7D or (v==0x10 and self._separate):
                    self._serial.write( chr(0x7D) )
                self._serial.write( chr(v) )
     
            # separate values
            if self._separate and i < self._vs_idx-1:
                self._serial.write( chr(0x10) );
            
        self._serial.write( chr(0x13) )
        self._vs_idx = 0

    def receivePacket( self ):
        # Reading 1 byte, followed by whatever is left in the
        # read buffer, as suggested by the developer of PySerial.
        data = self._serial.read(1)
        data += self._serial.read(self._serial.in_waiting)

        for c in data:
            if( self._collecting ):
                if( self._escape ):
                    self._vr_val[self._cr_idx] = c
                    self._cr_idx += 1
                    self._escape = 0
                    if not self._separate and self._cr_idx == self._v_length:
                        self._vr[self._vr_idx] = _join_bytes( self._vr_val )
                        self._vr_idx += 1
                        self._cr_idx = 0

                # escape
                elif c == 0x7D:
                    self._escape = 1

                # value separator
                elif self._separate and c == 0x10:
                    self._vr[self._vr_idx] = _join_bytes( self._vr_val )
                    self._vr_idx += 1
                    self._cr_idx = 0

                # end
                elif c == 0x13:
                    if( self._separate ):
                        self._vr[self._vr_idx] = _join_bytes( self._vr_val )
                        self._vr_idx += 1
                    self._collecting = 0
                    return 1
                else:
                    self._vr_val[self._cr_idx] = c
                    self._cr_idx += 1
                    if not self._separate and self._cr_idx == self._v_length:
                        self._vr[self._vr_idx] = _join_bytes( self._vr_val )
                        self._vr_idx += 1
                        self._cr_idx = 0

            # begin
            elif c == 0x12:
                self._collecting = 1
                self._cr_idx = 0
                self._vr_idx = 0

        return 0

    def receiveByte( self ):
        # Reading 1 byte, followed by whatever is left in the
        # read buffer, as suggested by the developer of PySerial.
        data = self._serial.read(1)
        data += self._serial.read(self._serial.in_waiting)
        if len(data):
            return data[-1]
        else:
            return None

    def getPacketValue( self, idx ):
        return self._vr[idx]

    def listPacketValues( self ):
        return self._vr[:self._p_size]
