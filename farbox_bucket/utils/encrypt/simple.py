#coding: utf8
import base64
from Crypto.Cipher import DES
from farbox_bucket.utils import to_bytes
from itsdangerous import TimedSerializer, base64_decode, base64_encode


class ServerSerializer(TimedSerializer):
    # .loads/lazy_loads(string)
    # .loads/lazy_loads(string, max_age)
    def loads(self, s, *args, **kwargs):
        if '"' not in s and "{" not in s:
            try:
                s = base64_decode(s)
            except:
                pass
        return TimedSerializer.loads(self, s, *args, **kwargs)

    def lazy_loads(self, s, *args, **kwargs):
        # 忽略 loads 会产生的错误，包括超时、解码错误
        try:
            return self.loads(s, *args, **kwargs)
        except:
            return ''

    def dumps(self, obj, *args, **kwargs):
        s = TimedSerializer.dumps(self, obj, *args, **kwargs)
        try:
            s = base64_encode(s)
        except:
            pass
        return s



def encrypt_des(key, text):
    key = key[:8]
    text = to_bytes(text)
    des = DES.new(key, DES.MODE_ECB)
    reminder = len(text)%8
    if reminder == 0:  # pad 8 bytes
        text += '\x08'*8
    else:
        text += chr(8-reminder) * (8-reminder)
    return base64.b64encode(des.encrypt(text))


def decrypt_des(key, text):
    key = key[:8]
    text = base64.b64decode(text)
    des = DES.new(key, DES.MODE_ECB)
    text = des.decrypt(text)
    pad = ord(text[-1])
    if pad == '\x08':
        return text[:-8]
    return text[:-pad]


def simple_encrypt(text, password):
    return encrypt_des(password, text)


def simple_decrypt(text, password):
    try:
        return decrypt_des(password, text)
    except:
        return ''