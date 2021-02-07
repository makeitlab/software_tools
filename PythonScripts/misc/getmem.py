import os
process = os.popen('wmic os get freephysicalmemory')
result = process.read()
print result
process.close()
totalMem = 0
for m in result.split("  \r\n")[1:-1]:
    totalMem += int(m)
print totalMem# / (1024**3)