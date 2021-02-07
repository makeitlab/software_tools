import os

vmsize_regex = re.compile('python.exe(\s+)(\d+)(\s+)Console(\s+)(\d+)(\s+)(\d+)\s(+d) VmSize:\s+(\d+)')

process = os.popen('wmic os get freephysicalmemory')
result = process.read()
print result
process.close()

tm = vmsize_regex.findall(out)[0]

print tm