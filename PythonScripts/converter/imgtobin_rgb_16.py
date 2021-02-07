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
            if k == 6:
                line += s + '00, '
                s = 'B'
                k = 0

    f.write(line+'\n')

f.close()
    