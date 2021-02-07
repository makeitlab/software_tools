import random

a = []
b = []
for i in range(16):
  a.append(random.randint(1, 31))
  b.append(random.randint(1, 15))

print str(a).replace('[','{').replace(']','}').replace(' ','')
print str(b).replace('[','{').replace(']','}').replace(' ','')

x = 0
input(x)