from PIL import Image
import numpy as np
import sys

fname = sys.argv[1]
fbody, ftp = fname.split('.')
new_fname = fbody + '.gcode'

im = Image.open(fname)
(width, height) = im.size
p = np.array(im)

print 'w = ', width
print 'h = ', height
print 's = ', len(p)

mul = 1.5
mono = False
curve = (50, 155)

header = """M107 S0
G90
G21
G0 F3000
"""

footer = """M107 S0
G0 X0 Y0
M18
"""

def clamp( v, min, max ):
    if v > max:
        return max
    if v < min:
        return min
    return v

f = open(new_fname, 'w')
f.write( header )

x = 0
y = 0
oldc = 0

xr = range(width)
xf = range(width)
xf.reverse()

for y in range(0, height, 2):
    for x in xr:
        if mono:
            c = p[y][x] == False and 255 or 0
        else:
            c = clamp((255-p[y][x][0])*mul*255.0/155.0, 0, 255)
        if c != oldc or x == width-1:
            f.write("G0 X%.2f Y%.2f\n" % (x/10.0, y/10.0))
            if c == 0:
                f.write("M107 S0\n")
            else:
                f.write("M106 S%d\n" % c)
            oldc = c

    for x in xf:
        if mono:
            c = p[y+1][x] == False and 255 or 0
        else:
            c = clamp((255-p[y][x][0])*mul*255.0/155.0, 0, 255)
        if c != oldc or x == 0:
            f.write("G0 X%.2f Y%.2f\n" % (x/10.0, (y+1)/10.0))
            if c == 0:
                f.write("M107 S0\n")
            else:
                f.write("M106 S%d\n" % c)
            oldc = c

f.write( footer )
f.close()
    