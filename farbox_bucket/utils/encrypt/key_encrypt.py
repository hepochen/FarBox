#coding: utf8
from __future__ import absolute_import
import base64
import zlib
import re
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import padding, rsa, ec
from cryptography.hazmat.primitives import hashes


from farbox_bucket.utils import unicode, to_bytes, to_unicode, get_md5



def create_private_public_keys(password=None, is_clean=True, key_size=4096):
    private_key = rsa.generate_private_key(
         public_exponent=65537,
         key_size=key_size,
         backend=default_backend()
    )
    public_key = private_key.public_key()
    if password:
        password = to_bytes(password)
    if password:
        encryption_algorithm = serialization.BestAvailableEncryption(password)
    else:
        encryption_algorithm = serialization.NoEncryption()
    private_key_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8, #.TraditionalOpenSSL,
        encryption_algorithm=encryption_algorithm,
    )
    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    private_key_s = to_unicode(private_key_bytes)
    public_key_s = to_unicode(public_key_bytes)
    if is_clean:
        private_key_s = to_clean_key(private_key_s)
        public_key_s = to_clean_key(public_key_s)
    return private_key_s, public_key_s


def create_private_key(is_clean=True):
    private_key, public_key = create_private_public_keys(is_clean=is_clean)
    return private_key


def get_public_key_from_private_key(private_key, password=None, is_clean=True):
    private_key = to_key(private_key, is_public_key=False)
    if password:
        password = to_bytes(password)
    try:
        private_key = serialization.load_pem_private_key(private_key, password=password, backend=default_backend())
        public_key = private_key.public_key()
        public_key_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        public_key_s = to_unicode(public_key_bytes)
        if is_clean:
            public_key_s = to_clean_key(public_key_s)
        return public_key_s
    except:
        print('failed to get_public_key_from_private_key')
        return




def to_public_key(public_key):
    public_key = to_key(public_key, is_public_key=True)
    try:
        public_key = serialization.load_pem_public_key(public_key,  backend=default_backend())
        return public_key
    except:
        return None


def to_private_key(private_key, password=None):
    private_key = to_key(private_key, is_public_key=False)
    if password:
        password = to_bytes(password)
    private_key = serialization.load_pem_private_key(private_key, password=password, backend=default_backend())
    return private_key

def is_valid_public_key(public_key):
    if not public_key:
        return False
    public_key = to_public_key(public_key)
    if public_key:
        return True
    else:
        return False


def is_valid_private_key(private_key, password=None):
    if not private_key:
        return False
    try:
        to_private_key(private_key, password=password)
        return True
    except:
        return False



def to_key(key, is_public_key=False):
    key = to_unicode(key)
    if is_public_key:
        head = '-----BEGIN PUBLIC KEY-----'
        tail = '-----END PUBLIC KEY-----'
    else:
        head = '-----BEGIN PRIVATE KEY-----'
        tail = '-----END PRIVATE KEY-----'
    if '-----BEGIN ' not in key:
        key = head + '\n' + key
    if '-----END ' not in key:
        key = key.strip() + '\n' + tail + '\n'
    key = to_bytes(key)
    return key


def to_clean_key(key):
    key = re.sub(r'-----(BEGIN|END).*? (PRIVATE|PUBLIC) KEY-----', '', to_unicode(key))
    key = key.strip()
    return key





############ sign and verify starts ###########

def get_sign_content(dict_data, excludes=None):
    # for python dict object, 如果 k,v 中的 v 本身是 '', 则不会进行 sign
    excludes = excludes or []
    dict_data = {
        k: v
        for k, v in dict_data.items()
        if len(str(v)) and k not in excludes
    }
    sign_content = '&'.join('%s=%s'%(k, v) for k, v in sorted(dict_data.items()))
    sign_content = to_bytes(sign_content)
    return sign_content



def verify_by_public_key(public_key, signature, content, decode_base64=True):
    if not public_key or not signature or not content:
        return False
    public_key = to_public_key(public_key)
    if not public_key:
        return False
    padding_obj = padding.PSS(
        mgf = padding.MGF1(hashes.SHA256()),
        salt_length = padding.PSS.MAX_LENGTH
    )
    if decode_base64:
        try:
            signature = base64.b64decode(signature)
            signature = to_bytes(signature)
        except:
            pass
    if isinstance(content, dict):
        content = get_sign_content(content)
    content = to_bytes(content)
    try:
        public_key.verify(signature, content, padding_obj, hashes.SHA256())
        return True
    except:
        return False



def sign_by_private_key(private_key, content, encode_base64=True, excludes_fields=None):
    private_key = to_private_key(private_key)
    padding_obj = padding.PSS(
        mgf = padding.MGF1(hashes.SHA256()),
        salt_length = padding.PSS.MAX_LENGTH
    )
    if isinstance(content, dict):
        content = get_sign_content(content, excludes=excludes_fields)
    content = to_bytes(content)
    signature = private_key.sign(content, padding_obj, hashes.SHA256())
    if encode_base64:
        signature = base64.b64encode(signature)
    return signature


############ sign and verify ends ###########



def encrypt_blob(blob, public_key, encode_type='zip'):
    blob = to_bytes(blob)
    public_key = to_key(public_key, is_public_key=True)

    pkey = serialization.load_pem_public_key(public_key,  backend=default_backend())

    blob = zlib.compress(blob)

    chunk_size = 470  # 470+42=512
    offset = 0
    end_loop = False
    encrypted =  b""

    padding_obj = padding.PKCS1v15()

    while not end_loop and offset < len(blob):
        #The chunk
        chunk = blob[offset:offset + chunk_size]

        #If the data chunk is less then the chunk size, then we need to add
        #padding with " ". This indicates the we reached the end of the file
        #so we end loop here
        if len(chunk) % chunk_size != 0:
            end_loop = True
            chunk += b" " * (chunk_size - len(chunk))

        #Append the encrypted chunk to the overall encrypted file
        encrypted += pkey.encrypt(chunk, padding_obj)

        #Increase the offset by chunk size
        offset += chunk_size

    if encode_type == 'zip':
        encrypted_content = zlib.compress(encrypted)
    else:
        #Base 64 encode the encrypted file
        encrypted_content = base64.b64encode(encrypted)
    return encrypted_content


def decrypt_blob(encrypted_blob, private_key, password=None, encode_type='zip'):
    private_key = to_key(private_key, is_public_key=False)
    password = to_bytes(password)
    pkey = serialization.load_pem_private_key(private_key, password=password, backend=default_backend())
    padding_obj = padding.PKCS1v15()

    if encode_type == 'zip':
        encrypted_blob = zlib.decompress(encrypted_blob)
    else:
        #Base 64 decode the data
        encrypted_blob = base64.b64decode(encrypted_blob)

    #In determining the chunk size, determine the private key length used in bytes.
    #The data will be in decrypted in chunks
    chunk_size = 512
    offset = 0
    decrypted = b""

    #keep loop going as long as we have chunks to decrypt
    while offset < len(encrypted_blob):
        #The chunk
        chunk = encrypted_blob[offset: offset + chunk_size]

        #Append the decrypted chunk to the overall decrypted file
        decrypted += pkey.decrypt(chunk, padding_obj)

        #Increase the offset by chunk size
        offset += chunk_size

    #return the decompressed decrypted data
    decrypted = zlib.decompress(decrypted)
    return decrypted



def get_md5_for_key(key):
    clean_key = re.sub('\s', '', key, flags=re.M)
    return get_md5(clean_key)



if __name__ == '__main__':
    import time
    t1 = time.time()
    for i in range(1):
        #for i in range(1):
        pr_key, pb_key = create_private_public_keys(is_clean=False)
    #print(pr_key)
    #print(pb_key)
    print(time.time()-t1)
