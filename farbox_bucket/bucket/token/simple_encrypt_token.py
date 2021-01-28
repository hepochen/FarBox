# coding: utf8
from farbox_bucket.utils import string_types
from farbox_bucket.utils.ssdb_utils import hset, hget, hexists
from farbox_bucket.utils.encrypt.simple import simple_encrypt, simple_decrypt
from farbox_bucket.utils.data import json_dumps, json_loads


# simple_bucket_token 是唯一不可更改的，主要是做加密和解密的；不能暴露给任何人

def get_simple_bucket_token(bucket):
    token = hget('_simple_bucket_token', bucket) or ''
    return token


def set_simple_bucket_token(bucket, private_key_md5):
    if not bucket:
        return
    if isinstance(private_key_md5, string_types) and len(private_key_md5)<100:
        old_value = get_simple_bucket_token(bucket)
        if old_value == private_key_md5:
            return
        hset('_simple_bucket_token', bucket, private_key_md5)



def get_normal_data_by_simple_token(bucket, encrypted_data, force_py_data=True, default_if_failed=None):
    # force_py_data = True 的时候，必须是 list/tuple/dict 的数据类型
    if not encrypted_data:
        return encrypted_data
    token = get_simple_bucket_token(bucket)
    if token and isinstance(encrypted_data, string_types):
        result = simple_decrypt(encrypted_data, token)
        try: result = json_loads(result)
        except: pass
    else:
        result = encrypted_data
    if force_py_data:
        if isinstance(result, (list, tuple, dict)):
            return result
        else:
            return default_if_failed
    else:
        return result






