#coding: utf8
from __future__ import absolute_import
import base64
from Crypto.Cipher import DES
from farbox_bucket.utils import to_bytes


def simple_encrypt(key, text):
    key = key[:8]
    text = to_bytes(text)
    des = DES.new(key, DES.MODE_ECB)
    reminder = len(text)%8
    if reminder == 0:  # pad 8 bytes
        text += '\x08'*8
    else:
        text += chr(8-reminder) * (8-reminder)
    return base64.b64encode(des.encrypt(text))


def simple_decrypt(key,text):
    key = key[:8]
    text = base64.b64decode(text)
    des = DES.new(key, DES.MODE_ECB)
    text = des.decrypt(text)
    pad = ord(text[-1])
    if pad == '\x08':
        return text[:-8]
    return text[:-pad]
