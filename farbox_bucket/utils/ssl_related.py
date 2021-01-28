# coding: utf8
from __future__ import absolute_import
from OpenSSL._util import lib as cryptolib
from OpenSSL import crypto
import base64, re, time, os

def dump_key(key):
    if isinstance(key, (str, unicode)): # ignore
        return key
    return crypto.dump_privatekey(crypto.FILETYPE_PEM, key)


def load_key_content(key_content):
    key_content = key_content.strip()
    head = '-----BEGIN PRIVATE KEY-----'
    tail = '-----END PRIVATE KEY-----'
    if not re.match("-{5,}BEGIN", key_content):
        key_content = head + '\n' + key_content
    if not re.search("[^-]-{5,}}$", key_content):
        key_content += '\n%s'%tail
    return crypto.load_privatekey(crypto.FILETYPE_PEM, key_content)


def load_cert_content(cert_content):
    cert_content = cert_content.strip()
    head = '-----BEGIN CERTIFICATE-----'
    tail = '-----END CERTIFICATE-----'
    if not re.match("-{5,}BEGIN", cert_content):
        cert_content = head + '\n' + cert_content
    if not re.search("[^-]-{5,}}$", cert_content):
        cert_content += '\n%s'%tail
    return crypto.load_certificate(crypto.FILETYPE_PEM, cert_content)


def load_cert_contents(cert_contents):
    # 多个证书合并的
    certs = []
    content_list = cert_contents.split('-----END CERTIFICATE-----')
    for content in content_list:
        content = content.strip()
        if not content:
            continue
        cert = load_cert_content(content)
        certs.append(cert)
    return certs



def load_key(key):
    if not isinstance(key, (str, unicode)):
        return key
    if os.path.isfile(key):
        with open(key, 'rb') as f:
            key = f.read()
    return load_key_content(key)


def load_cert(cert):
    if not isinstance(cert, (str, unicode)):
        return cert
    if os.path.isfile(cert):
        with open(cert, 'rb') as f:
            cert = f.read()
    return load_cert_content(cert)



def dump_cert(cert):
    if isinstance(cert, (str, unicode)):
        return cert
    return crypto.dump_certificate(crypto.FILETYPE_PEM, cert)


def get_pure_key(key_content):
    key_content = re.sub(r'---+.*?---+', '', key_content)
    key_content = key_content.replace('\n', '').strip()
    return key_content

def get_public_key(private_key):
    if not isinstance(private_key, crypto.PKey):
        private_key = crypto.load_privatekey(crypto.FILETYPE_PEM, private_key)
    bio = crypto._new_mem_buf()
    cryptolib.PEM_write_bio_PUBKEY(bio, private_key._pkey)
    public_key = crypto._bio_to_string(bio)
    return public_key


def create_private_key(bits=1024):
    pkey = crypto.PKey() # private key
    pkey.generate_key(crypto.TYPE_RSA, bits=bits)
    pkey_str = crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey)
    public_key = get_public_key(pkey)
    public_key = get_pure_key(public_key)
    #print pkey_str, '\n'*10 ,public_key
    #return pkey_str, public_key
    return pkey_str, public_key



def sha1_with_rsa(pkey, to_sign):
    if isinstance(pkey, (str, unicode)):
        pkey = crypto.load_privatekey(crypto.FILETYPE_PEM, pkey)
    result = crypto.sign(pkey, to_sign, 'sha1')
    base64_result = base64.standard_b64encode(result).decode()
    return base64_result



def create_cert_request(pkey, name, digest="sha256"):
    req = crypto.X509Req()
    subject = req.get_subject()
    subject.CN = name
    if isinstance(pkey, (str, unicode)):
        pkey = load_key(pkey)
    req.set_pubkey(pkey)
    req.sign(pkey, digest)
    return req


def create_certificate(req, issuer_key, issuer_cert, days=3650, serial=None, digest="sha256", return_text=True):
    # 也可以自行签发 cert
    """
    Generate a certificate given a certificate request.
    Arguments: req        - Certificate request to use
               issuer_cert - The certificate of the issuer
               issuer_key  - The private key of the issuer
               serial     - Serial number for the certificate
               not_before  - Timestamp (relative to now) when the certificate
                            starts being valid
               not_after   - Timestamp (relative to now) when the certificate
                            stops being valid
               digest     - Digest method to use for signing, default is sha256
    Returns:   The signed certificate in an X509 object
    """
    serial = serial or int(time.time() * 1000)

    issuer_key = load_key(issuer_key)
    issuer_cert = load_cert(issuer_cert)

    # not_before, not_after = validity_period
    not_before = int(time.time())
    not_after = int(time.time() + days*24*60*60)
    cert = crypto.X509()
    cert.set_serial_number(serial)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(days*24*60*60)
    cert.set_issuer(issuer_cert.get_subject())
    cert.set_subject(req.get_subject())
    cert.set_pubkey(req.get_pubkey())
    cert.sign(issuer_key, digest)
    if return_text:
        return dump_cert(cert)
    else:
        return cert



