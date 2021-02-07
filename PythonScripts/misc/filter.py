          
# median filter
med = []

def shift( med, x ):
    for i,v in enumerate(med[:-1]):
        med[i] = med[i+1]
    med[-1] = x

def median_filter( x, med_size ):
    global med
    if not med:
        med = [x for k in range(med_size)]

    shift(med, x)

    tst = med[:]
    tst.sort()
    mx = tst[med_size/2]

    return mx

# low pass filter
class LowPass:
    lx = 0
    lpk = None
    def __init__( self, k ):
        self.lpk = k

    def filter( self, x ):
        self.lx = (1.0-self.lpk)*self.lx + x*self.lpk
        return self.lx

fl = open('data.txt','r')
data = fl.readlines()
fl.close()

lpf1 = LowPass(0.03)
lpf2 = LowPass(0.05)

fl = open('data_out.txt','w')
for i,d in enumerate(data):
    v1 = median_filter( float(data[i]), 11 )
    #v2 = lpf1.filter( float(data[i]))
    #v3 = lpf2.filter( v1 )
    #fl.write('%f\t%f\t%f\t%f\n' % (float(data[i]),v1,v2,v3))
    fl.write('%f\t%s' % (v1, data[i]))
fl.close()
