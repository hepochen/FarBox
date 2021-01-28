# coding: utf8
from __future__ import absolute_import
from farbox_bucket.utils.mime import guess_type
import datetime
from farbox_bucket.utils.date import utc_date_parse as date_parse
from farbox_bucket.utils.date import timestamp_to_date
from farbox_bucket.utils import get_md5, get_sha1, string_types, to_int, to_float, string_to_int, is_email_address
from farbox_bucket.server.template_system.model.date import Date
#from json import loads as json_loads, dumps as json_dumps
from farbox_bucket.utils.data import json_dumps, json_loads



def debug_obj(obj):
    # 主要是开发时候debug用的，可以确定obj是什么类型的对象
    return obj



def auto_value(obj):
    if isinstance(obj, datetime.datetime):
        return Date(obj)
        # at last
    return obj

def md5(obj):
    # 返回 md5 值
    try:
        return get_md5(obj)
    except:
        return obj


def sha1(obj):
    # 返回 sha1 值
    try:
        return get_sha1(obj)
    except:
        return obj


def date(obj):
    if isinstance(obj, datetime.datetime):
        return Date(obj)
    if isinstance(obj, (int, float)):
        try:
            date_obj = timestamp_to_date(obj, is_utc=True)
            return Date(date_obj)
        except:
            pass
    if isinstance(obj, string_types):
        try:
            return Date(date_parse(obj))
        except:
            pass
    return Date(datetime.datetime.utcnow()) # by default


def json(obj):
    """
    unicode
    {"is_property": true}
    """
    if isinstance(obj, (tuple, list, dict, str, unicode)):
        try:
            return json_dumps(obj, indent=4)
        except:
            return obj
        # todo 缓存策略
        # return cache_result(cache_key)(json_dumps)(obj)
    else:
        return obj

def from_json(obj):
    # 将一个字符串，重新载入为一个dict/list等类型的py 数据
    if not obj:
        return obj
    if not isinstance(obj, string_types) and hasattr(obj, 'core'):
        # 可能是 Text/ Date 等wrap后的数据对象
        obj = obj.core
    if isinstance(obj, string_types):
        try:
            return json_loads(obj)
        except:
            return obj
    return obj


def __int(obj):
    if isinstance(obj, (int, float, str, unicode)):
        return to_int(obj, default_if_fail=int)
    return obj

def force_int(obj):
    # 主要是字符串类型，强制提取一个整数出来
    if isinstance(obj, (float, int)):
        return int(obj)
    else:
        return string_to_int(obj)

def __float(obj):
    if isinstance(obj, (int, float, str, unicode)):
        return to_float(obj, default_if_fail=int)
    return obj


def is_int(obj):
    return isinstance(obj, int)

def is_number(obj):
    return isinstance(obj, (int, float))

def is_float(obj):
    return isinstance(obj, float)

def is_str(obj):
    return isinstance(obj, (str, unicode))

def is_unicode(obj):
    return isinstance(obj, (str, unicode))


def is_array(obj):
    return isinstance(obj, (list, tuple))

def is_list(obj):
    return isinstance(obj, list)

def is_tuple(obj):
    return isinstance(obj, tuple)



def is_dict(obj):
    return isinstance(obj, dict)

def is_email(obj): # 是否是邮箱地址
    if isinstance(obj, (str, unicode)) and is_email_address(obj):
        return True
    else:
        return False

def is_image(obj): # 一个字符串是否是图片的 url
    if isinstance(obj, (str, unicode)):
        mime_type = guess_type(obj)
        if mime_type and mime_type.startswith('image/'):
            return False
    return False


def type(obj):
    types = {int: 'int', float:'float', bool:'bool', unicode:'str', str:'str', list:'list', tuple:'tuple'}
    for t, ts in types.items():
        if isinstance(obj, t):
            return ts
    if isinstance(obj, dict) and '_type' in obj:
        return obj['_type']
    # at last
    return ''



def get(obj, *args, **kwargs):
    if isinstance(obj, dict):
        return obj.get(*args, **kwargs)
    elif isinstance(obj, (list, tuple)) and len(args)==1 and isinstance(args[0], int):
        # list 获得第几个元素
        i = args[0]
        try:
            return obj[i]
        except:
            return None
    elif args:
        field = args[0]
        default = args[1] if len(args)>=2 else None
        try:
            return getattr(obj, field, default)
        except:
            return default
    else:
        return # ignore


def absolute(obj):
    if isinstance(obj, (float, int)):
        return abs(obj)
    return obj





