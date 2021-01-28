# coding: utf8
import base64
import zlib
from Crypto.Cipher import DES, DES3
from farbox_bucket.utils import to_bytes, to_md5
import os
import tempfile
import random
import string
import json
try:
    from cStringIO import StringIO
except:
    from io import BytesIO as StringIO


def to_key_for_des(key, length=8):
    key = key.strip()
    key = key[:length]
    if len(key) < length:
        key += '0' * (length - len(key))
    return key

def get_key_and_iv_for_des(key):
    md5_key = to_md5(key)
    des_key = to_key_for_des(md5_key[:16], length=16)
    des_iv = to_key_for_des(md5_key[-8:])
    return des_key, des_iv

def get_key_for_des(key):
    md5_key = to_md5(key)
    des_key = to_key_for_des(md5_key[:8], length=8)
    return des_key



# encrpyt_des & decrypt_des 默认是 base64 编码，主要考虑到在实际传输过程中的数据不失真

def encrypt_des(text, key, encode_type='base64'):
    key = to_key_for_des(key)
    if isinstance(text, dict):
        text = json.dumps(text, indent=4)
    text = to_bytes(text)
    des = DES.new(key, DES.MODE_ECB)
    reminder = len(text)%8
    if reminder == 0:  # pad 8 bytes
        text += '\x08'*8
    else:
        text += chr(8-reminder) * (8-reminder)

    encrypted = des.encrypt(text)
    if encode_type == 'zip':
        encrypted_content = zlib.compress(encrypted)
    else:
        #Base 64 encode the encrypted file
        encrypted_content = base64.b64encode(encrypted)
    return encrypted_content


def decrypt_des(text, key, encode_type='base64'):
    key = to_key_for_des(key)
    if encode_type == 'zip':
        text = zlib.decompress(text)
    else:
        text = base64.b64decode(text)
    des = DES.new(key, DES.MODE_ECB)
    text = des.decrypt(text)
    pad = ord(text[-1])
    #if pad == '\x08':
    #    return text[:-8]
    return text[:-pad]




def encrypt_file(in_filepath, key, chunk_size=81920, out_filepath=None, is_content=False, fast=True):
    if fast:
        des_key = get_key_for_des(key)
        des = DES.new(des_key, DES.MODE_ECB)
        pl = 8
    else:
        des_key, des_iv = get_key_and_iv_for_des(key)
        des = DES3.new(des_key, DES3.MODE_CFB, des_iv)
        pl = 16 # part length

    if is_content:
        raw_content = to_bytes(in_filepath)
        in_file = StringIO(raw_content)
    else:
        if not os.path.isfile(in_filepath):
            return ''
        else:
            in_file = open(in_filepath, 'r')

    out_content = b''
    if out_filepath:
        out_file = open(out_filepath, 'wb')
    else:
        out_file = None
    padded = False
    while True:
        chunk = in_file.read(chunk_size)
        if len(chunk) == 0:
            if not padded:
                to_pad = chr(pl) * pl
                encrypted_chunk = des.encrypt(to_pad)
                if out_file:
                    out_file.write(encrypted_chunk)
                else:
                    out_content += encrypted_chunk
            break
        elif len(chunk) % pl != 0:
            reminder = len(chunk) % pl
            to_pad = chr(pl - reminder) * (pl - reminder)
            chunk += to_pad
            padded = True
        encrypted_chunk = des.encrypt(chunk)
        if out_file:
            out_file.write(encrypted_chunk)
        else:
            out_content += encrypted_chunk
    # at last
    in_file.close()
    if out_file:
        out_file.close()
        return out_filepath
    else:
        return out_content


def decrypt_file(in_filepath, key, chunk_size=81920, out_filepath=None, is_content=False, fast=True):
    if fast:
        des_key = get_key_for_des(key)
        des = DES.new(des_key, DES.MODE_ECB)
        pl = 8
    else:
        des_key, des_iv = get_key_and_iv_for_des(key)
        des = DES3.new(des_key, DES3.MODE_CFB, des_iv)
        pl = 16 # part length

    if is_content:
        raw_content = to_bytes(in_filepath)
        in_file = StringIO(raw_content)
    else:
        if not os.path.isfile(in_filepath):
            return ''
        else:
            in_file = open(in_filepath, 'r')

    out_content = b''
    if out_filepath:
        out_file = open(out_filepath, 'wb')
    else:
        out_file = None

    chuck_to_write = ''
    while True:
        chunk = in_file.read(chunk_size)
        if len(chunk) == 0:
            if chuck_to_write:
                pad_length = ord(chuck_to_write[-1])
                chuck_to_write = chuck_to_write[:-pad_length]
            if chuck_to_write:
                if out_file:
                    out_file.write(chuck_to_write)
                else:
                    out_content += chuck_to_write
            break
        if chuck_to_write:
            if out_file:
                out_file.write(chuck_to_write)
            else:
                out_content += chuck_to_write
        chuck_to_write = des.decrypt(chunk)

    # at last
    in_file.close()
    if out_file:
        out_file.close()
        return out_filepath
    else:
        return out_content



def do_test_encrypt_file(filepath, fast=False):
    key = ''.join(random.sample(string.letters, 10))
    if not os.path.isfile(filepath):
        return
    with open(filepath, 'rb') as f:
        raw_content = f.read()
    tmp_filepath = tempfile.mktemp()
    tmp_filepath2 = tempfile.mktemp()
    encrypted_content = encrypt_file(in_filepath=filepath, key=key, fast=fast)
    encrypted_content2 = encrypt_file(raw_content, key=key, is_content=True, fast=fast)
    if encrypted_content != encrypted_content2:
        print('encrypted_content != encrypted_content2 for %s' % filepath)
        return False
    descrpted_content = decrypt_file(encrypted_content, key=key, is_content=True, fast=fast)
    if descrpted_content != raw_content:
        print('descrpted_content != raw_content for %s' % filepath)
        return False
    encrypt_file(filepath, key=key, out_filepath=tmp_filepath, fast=fast)
    decrypt_file(tmp_filepath, out_filepath=tmp_filepath2, key=key, fast=fast)
    with open(tmp_filepath2, 'rb') as f:
        raw_content2 = f.read()
    try:
        os.remove(tmp_filepath)
    except:
        pass
    try:
        os.remove(tmp_filepath2)
    except:
        pass
    if raw_content != raw_content2:
        return False
    return True

def test_encrypt_file(filepath):
    if do_test_encrypt_file(filepath, fast=True) and do_test_encrypt_file(filepath, fast=False):
        return True
    else:
        return False




#if __name__ == '__main__':
#    print test_encrypt_file('/Users/hepochen/ImageBox/Inbox2/2018-12-05 17-16-30.jpg')
