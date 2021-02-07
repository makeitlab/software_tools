import base64

f = open('text.txt', 'r')
tdata = f.read()
f.close()

#tdata = tdata.encode('utf-16')
#tdata = base64.b64encode(tdata)

f = open('signature.txt', 'r')
sdata = f.read()
f.close()

#sdata = base64.b64encode(sdata)

if 1:
    msg = """MIME-Version: 1.0
Content-Disposition: attachment; filename="smime.p7m"
Content-Type: application/x-pkcs7-mime; smime-type: signed-data; name="smime.p7m"
Content-Transfer-Encoding: base64

%(sdata)s
""" % {'tdata':tdata, 'sdata':sdata}

f = open('smime.txt', 'w')
f.write(msg)
f.close()
