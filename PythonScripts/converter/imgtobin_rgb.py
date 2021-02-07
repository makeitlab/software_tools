from PIL import Image
import numpy as np
import sys

fname = sys.argv[1]
fbody, ftp = fname.split('.')
new_fname = fbody + '.txt'

im = Image.open(fname)
(width, height) = im.size
im = im.convert('RGB')
p = np.array(im)

print 'w = ', width
print 'h = ', height

def bin(i):
    if i == 0:
        return 'B00000000'
    s = ''
    for k in range(0,8):
        if i & (1 << k):
            s += '1'
        else:
            s += '0'
        
    return (s+'B')[::-1]

def clamp( v, min, max ):
    if v > max:
        return max
    if v < min:
        return min
    return v

f = open(new_fname, 'w')

width = range(width)
for y in range(height):
    line = ''
    k = 0
    s = 'B'

    for x in width:
        for b in [0,1,2]:
            s += (p[y][x][b] == 255 and '1' or '0')
            k += 1
            if k == 8:
                line += s + ', '
                s = 'B'
                k = 0
    if k > 0:
        s += '0'*(8-k)
        line += s
        if y < height-1:
            line += ', '

    f.write(line+'\n')

f.close()
    