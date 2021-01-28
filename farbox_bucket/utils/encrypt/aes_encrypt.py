# coding: utf8
import base64
import zlib
from Crypto.Cipher import AES
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

BLOCK_SIZE = 32

def to_key_for_aes(key):
    # 16 or 24 or 32 bytes long
    key = to_md5(key)
    key += '0' * (32 - len(key))
    key = key[:32]
    return key


def get_aes(key):
    aes_key = to_key_for_aes(key)
    aes_iv = to_key_for_aes(aes_key)[:16]
    aes = AES.new(aes_key, AES.MODE_CBC, aes_iv)
    return aes


# encrpyt_aes & decrypt_aes 默认是 base64 编码，主要考虑到在实际传输过程中的数据不失真


def encrypt_aes(text, key, encode_type='base64'):
    if isinstance(text, dict):
        text = json.dumps(text, indent=4)
    text = to_bytes(text)
    aes = get_aes(key)
    reminder = len(text)%BLOCK_SIZE
    if reminder == 0:  # pad 8 bytes
        text += '\x08'*BLOCK_SIZE
    else:
        text += chr(BLOCK_SIZE-reminder) * (BLOCK_SIZE-reminder)
    encrypted = aes.encrypt(text)
    if encode_type == 'zip':
        encrypted_content = zlib.compress(encrypted)
    elif encode_type == 'raw':
        encrypted_content = encrypted
    else:
        #Base 64 encode the encrypted file
        encrypted_content = base64.b64encode(encrypted)
    return encrypted_content


def decrypt_aes(text, key, encode_type='base64'):
    if encode_type == 'zip':
        text = zlib.decompress(text)
    elif encode_type == 'raw':
        pass
    else:
        text = base64.b64decode(text)
    aes = get_aes(key)
    text = aes.decrypt(text)
    pad = ord(text[-1])
    return text[:-pad]




def encrypt_file(in_filepath, key, chunk_size=81920, out_filepath=None, is_content=False):
    pl = 32
    aes = get_aes(key)

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
                encrypted_chunk = aes.encrypt(to_pad)
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
        encrypted_chunk = aes.encrypt(chunk)
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


def decrypt_file(in_filepath, key, chunk_size=81920, out_filepath=None, is_content=False):
    aes = get_aes(key)
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
        chuck_to_write = aes.decrypt(chunk)

    # at last
    in_file.close()
    if out_file:
        out_file.close()
        return out_filepath
    else:
        return out_content



def test_encrypt_file(filepath):
    key = ''.join(random.sample(string.letters, 10))
    if not os.path.isfile(filepath):
        return
    with open(filepath, 'rb') as f:
        raw_content = f.read()
    tmp_filepath = tempfile.mktemp()
    tmp_filepath2 = tempfile.mktemp()
    encrypted_content = encrypt_file(in_filepath=filepath, key=key)
    encrypted_content2 = encrypt_file(raw_content, key=key, is_content=True)
    if encrypted_content != encrypted_content2:
        print('encrypted_content != encrypted_content2 for %s' % filepath)
        return False
    descrpted_content = decrypt_file(encrypted_content, key=key, is_content=True)
    if descrpted_content != raw_content:
        print('descrpted_content != raw_content for %s' % filepath)
        return False
    encrypt_file(filepath, key=key, out_filepath=tmp_filepath)
    decrypt_file(tmp_filepath, out_filepath=tmp_filepath2, key=key)
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





#if __name__ == '__main__':
#    print test_encrypt_file('/Users/hepochen/ImageBox/Inbox2/2018-12-05 17-16-30.jpg')

