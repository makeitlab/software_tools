from math import cos

def cross(a,b):
    v = [0,0,0]
    v[0]= (a[1]*b[2]) - (a[2]*b[1])
    v[1]= (a[2]*b[0]) - (a[0]*b[2])
    v[2]= (a[0]*b[1]) - (a[1]*b[0])
    print a[1], b[2], a[1]*b[2]
    print a[2], b[1], a[2]*b[1]
    print a[1]*b[2] - a[2]*b[1]

    return v

def mul(a,b):
    op = [0,0,0]

    c = [[0,0,0],
         [0,0,0],
         [0,0,0]]

    for x in (0,1,2):
        for y in (0,1,2):
            for w in (0,1,2):
                op[w] = a[x][w] * b[w][y]
            c[x][y] = op[0]+op[1]+op[2]

    return c

acc = [0.0, 0.5, 0.866025]
acc = [0.0, 512, 887]

dcm = [[1, 0, 0],
       [0, 1, 0], 
       [0, 0, 1]]

for a in range(0,120):
    um = [[0, 0, 0],
          [0, 0, -0.017453],
          [0, 0.017453, 0]]

    um = [[0, 0, 0],
          [0, 0, -0.004363],
          [0, 0.004363, 0]]

    tmp = mul(dcm,um)

    for x in (0,1,2):
        for y in (0,1,2):
            dcm[x][y] += tmp[x][y]

c = cross(dcm[2], acc)

print dcm, c