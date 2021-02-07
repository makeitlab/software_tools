# -*- coding: cp1251 -*-
#t = 'код 555777 на'
#z = t.decode('cp1251')
#print repr(z)

udigits = ['%04d' % x for x in range(30,40)]
t = '003500350036003600370037'
r = ''
for i in range(len(t)/4):
  r += str(udigits.index(t[i*4:i*4+4]))
print r
