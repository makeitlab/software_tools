from M2Crypto import SMIME, X509, BIO

# Instantiate an SMIME object.
s = SMIME.SMIME()

flags = 0
flags = SMIME.PKCS7_NOVERIFY

f = open('text.txt','r')
data_bio = BIO.MemoryBuffer(f.read())
f.close()

f = open('smime.txt','r')
sign_bio = BIO.MemoryBuffer(f.read())
f.close()

# Load the signer's cert.
if 1:
    #x509 = X509.load_cert('d:\dss\cert.crt')
    sk = X509.X509_Stack()
    #sk.push(x509)
    s.set_x509_stack(sk)

# Load the signer's CA cert. In this case, because the signer's
# cert is self-signed, it is the signer's cert itself.
if 1:
    st = X509.X509_Store()
    #st.load_info('d:\dss\cacert.pem')
    s.set_x509_store(st)

# Load the data, verify it.
p7, data = SMIME.smime_load_pkcs7_bio(sign_bio)
try:
    v = s.verify(p7, data_bio = data_bio, flags=flags)
except SMIME.PKCS7_Error:
    print 'bad signature'
else:
    print v
