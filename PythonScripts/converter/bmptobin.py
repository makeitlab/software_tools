#!/usr/bin/python
from PIL import Image
import numpy as np
import sys, os
from mod_python import apache

def convert(req, file, mode):
    #fileitem = req.form['file']
    req.content_type = "text/plain"

    im = Image.open(file.file)
    (width, height) = im.size
    p = np.array(im)

    for y in range(height):
        line = ''
        k = v = 0

        for x in range(width):
            if p[y][x] == 255:
                b = 0
            else:
                b = 1
            v = v | (b << (7-k))
            k += 1

            if k == 8:
                line += tos(v,mode) + ', '
                v = k = 0

        if k > 0:
            line += tos(v, mode)
            if y < height-1:
                line += ', '

	req.write(line+'\n')

    return apache.OK

def tos(v,m):
    if m == 'bin':
        return bin(v)
    elif m == 'hex':
        return hex(v)

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

