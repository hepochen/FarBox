#coding: utf8
import sys, re, os, time, subprocess
import uuid
import hashlib
import datetime
import urllib
try:
    from urllib import parse as urllib_parse
except:
    urllib_parse = None
try:
    from urllib.parse import urlparse, parse_qs, urlencode
except:
    from urlparse import urlparse, parse_qs
    from urllib import urlencode

import ujson as json
from collections import OrderedDict
from dateutil.parser import parse as parse_date


PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

if PY3:
    string_types = (str, bytes)
    unicode = str
    unicode_type = str
    str_type = bytes
else:
    string_types = basestring
    unicode = unicode
    unicode_type = unicode
    str_type = str

class UnicodeWithAttrs(unicode):
    pass


def to_bytes(s):
    if isinstance(s, unicode):
        s = s.encode('utf8')
    else:
        try:
            s = str_type(s)
        except:
            pass
    return s

def smart_str(s):
    return to_bytes(s)


ENCODINGS = [
    "utf8",
    "gb18030",
    "latin1",
    "ascii"
]

def to_unicode(s):
    if not isinstance(s, unicode):
        try:
            s = unicode(s)
            return s
        except:
            pass
        for encoding in ENCODINGS:
            try:
                s = unicode(s, encoding)
                return s
            except:
                pass
    return s


def is_str(text, includes=''):
    if not isinstance(text, (str, unicode)):
        return False
    text = text.strip()
    if includes:
        for s in includes: text=text.replace(s, '')
    if not text:
        return False
    return bool(re.match(r'[a-z0-9_\-]+$', text, flags=re.I))


def unique_list(data):
    # 类似 set 功能，但是保留原来的次序
    new_data = []
    for row in data:
        if row not in new_data:
            new_data.append(row)
    return new_data

def string_to_list(value):
    if not value:
        return []
    if isinstance(value, (str, unicode)) and value:
        value = value.strip()
        if re.match("\\[.*?\\]$", value):
            value = value[1:-1]
        elif re.match("\\(.*?\\)$", value):
            value = value[1:-1]
        value = value.strip()
        if ',' in value:
            ls = value.split(',')
        elif u'，' in value:
            ls = value.split(u'，')
        else:
            ls = value.split(' ')
        ls = [item.strip() for item in ls if item]
        return unique_list(ls)
    elif type(value) in [list, tuple]:
        value = unique_list(value)
        return [smart_unicode(row).strip() for row in value if row]
    else:
        return [smart_str(value)]


def count_words(content):
    # http://www.khngai.com/chinese/charmap/tbluni.php?page=0
        # 4e00 - 9fff是中文字符集的头尾 # 19968 - 40959
        # 3000 - 4db0 日文   # 3000-19888
        # 1100–11FF  # 韩文
        # 44032 - 55203 3130-12687 43360-43391  55216-55295
        # 0.5s 大概可以处理 176w的unicode
        # 2k字算的话，大概0.0005s，应该不会有性能问题
    content = smart_unicode(content)
    total_words = len(re.findall(ur'[\w\-_/]+|[\u1100-\ufde8]', content)) # 直接 1100 - 65000
    return total_words



def smart_unicode(s):
    return to_unicode(s)


def to_md5(text):
    if not isinstance(text, string_types):
        text = to_unicode(text)
    text = to_bytes(text)
    return hashlib.md5(text).hexdigest()

def md5(text):
    return to_md5(text)

def get_md5(text):
    return to_md5(text)

def get_sha1(content):
    return hashlib.sha1(smart_str(content)).hexdigest()

def md5_for_file(file_path, block_size=2**20): # block_size=1Mb
    if os.path.isdir(file_path):
        return 'folder'
    if not os.path.exists(file_path):
        return ''
    f = open(file_path, 'rb')
    md5_obj = hashlib.md5()
    while True:
        data = f.read(block_size)
        if not data:
            break
        md5_obj.update(data)
    f.close()
    return md5_obj.hexdigest()


def get_md5_for_file(file_path, block_size=2**20):
    return md5_for_file(file_path, block_size=block_size)


def are_letters(s):
    if not isinstance(s, string_types):
        return False
    if not re.match(r'[a-z]+$', s, flags=re.I):
        return False
    else:
        return True



def to_number(value, default_if_fail=None, max_value=None, min_value=None, number_type_func=None):
    if isinstance(value, (str, unicode)):
        value = value.strip()
    if not value and type(value)!=int:
        return default_if_fail
    try:
        value = float(value)
        if number_type_func:
            value = number_type_func(value)
    except:
        value = default_if_fail
    if max_value is not None and value > max_value:
        value = max_value
    if min_value is not None and value < min_value:
        value = min_value
    return value


def to_float(value, default_if_fail=None, max_value=None, min_value=None):
    if isinstance(value, (str, unicode))  and '/' in value and value.count('/')==1: # 分数
        k1, k2 = value.split('/', 1)
        k1 = to_float(k1)
        k2 = to_float(k2)
        if k1 and k2:
            value = k1/k2
    return to_number(value, default_if_fail=default_if_fail, max_value=max_value, min_value=min_value, number_type_func=float)


def to_int(value, default_if_fail=None, max_value=None, min_value=None):
    int_value = to_number(value, default_if_fail=default_if_fail, max_value=max_value, min_value=min_value, number_type_func=int)
    return int_value



def to_date(value):
    if not value:
        return None
    if isinstance(value, datetime.datetime):
        return value
    elif isinstance(getattr(value, 'core', None), datetime.datetime): # 被Date给wrap了
        return getattr(value, 'core', None)
    else:
        try:
            return parse_date(value)
        except:
            return None

def auto_type(value):
    # 自动类型，主要是 str 类的转为 number 的可能
    if not isinstance(value, (str, unicode)):
        return value
    value = value.strip()
    if re.match('^\d+$', value):
        return int(value)
    if re.match('^\d+\.(\d+)?$', value):
        return float(value)
    if re.match('^\d+/\d+$', value): # 分数
        new_value = to_float(value)
        if new_value:
            return new_value
    if value in ['True', 'true', 'yes']:
        return True
    if value in ['False', 'false', 'no']:
        return False
    # at last
    return value

def string_to_int(value):
    if not value:
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, (str, unicode)): # 提取字符串中的整数部分，作为value
        re_s = re.search('\d+', value)
        if re_s:
            int_value = re_s.group()
            return to_int(int_value)
    # at last
    return to_int(value)


def is_public(value):
    if value in [True, 'public', 'open', 'on', 'published', 'true', 'yes']:
        return True
    else:
        return False

is_on = is_public

def is_closed(value):
    if value in ['no', 'false', False, 'off', 'close']:
        return True
    else:
        return False

def to_sha1(content):
    return hashlib.sha1(to_bytes(content)).hexdigest()


def get_uuid():
    return uuid.uuid1().hex


def get_random_html_dom_id():
    return 'd_%s' % get_uuid()

def hash_password(password):
    return to_sha1(to_md5(password))



def force_to_json(data):
    if isinstance(data, string_types):
        try:
            data = json.loads(data)
        except:
            data = {}
    return data



def get_value_from_data(data, attr, default=None):
    if not isinstance(attr, string_types):
        return default
    if isinstance(data, dict) and attr in data:
        # dict 类型，直接返回value，attr本身可能包含 .
        return data[attr]
    try:
        attrs = attr.split('.')[:25] # 最多允许25个遍历
        for attr in attrs:
            # 最后一个dt是真实的value
            if type(data) in [dict, OrderedDict]:
                data = data.get(attr, None)
            else:
                try:
                    data = getattr(data, attr, None)
                except: # jinja 中的 Undefined 会触发错误
                    return data
            if data is None:  # 到底了
                if default is not None:
                    return default
                else:
                    return None
    except RuntimeError: # 一般是在外部调用g/request的时候会遇到
        return None
    return data


def get_dict_from_dict(data, key):
    if not isinstance(data, dict):
        return {}
    value = data.get(key) or {}
    if not isinstance(value, dict):
        value = {}
    return value


def bytes2human(num):
    if not num:
        return '0'
    for x in ['bytes', 'KB', 'MB', 'GB', 'PB']:
        if num < 1024.0:
            return "%3.1f%s" % (num, x)
        num /= 1024.0
    return "%3.1f%s" % (num, 'TB')




def get_kwargs_from_console():
    kwargs = {}
    for arg in sys.argv:
        if '=' not in arg:
            continue
        else:
            k, v = arg.split('=', 1)
            k = k.strip()
            v = v.strip()
            kwargs[k] = v
    return kwargs


def split_list(ls, size_per_part):
    for i in range(0, len(ls), size_per_part):
        yield ls[i:i + size_per_part]


def make_content_clean(content):
    content = smart_unicode(content)
    content = content.replace(u'\xa0', u' ')
    content = re.sub('\x07|\x08|\x10|\x11|\x12|\x13|\x14|\x15|\x16|\x17|\x18|\x19|\x1a|\x1b|\x1c|\x1d|\x1e|\x1f', '', content)
    return content




email_re = re.compile(
    r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"  # dot-atom
    r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-011\013\014\016-\177])*"' # quoted-string
    r')@(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?$', re.I)  # domain


# 头(a0开头结尾，中间的a0允许-_ or 全部a0). + az可能的二级子域名. + 后缀
domain_re = re.compile(r'^([a-z0-9][a-z0-9-_]+[a-z0-9]\.|[a-z0-9]+\.)+([a-z]{2,3}\.)?[a-z]{2,9}$', flags=re.I)

def is_email_address(email):
    if not isinstance(email, (str, unicode)):
        return False
    else:
        email = email.strip()
        return bool(email_re.match(email))



def sort_objects_by(objects, attr):
    if not isinstance(objects, (list,tuple)):
        return objects
    if attr.startswith('-'):
        reverse = True
        attr = attr.lstrip('-')
    else:
        reverse = False
    if reverse == '-':
        reverse = True
    if attr:
        new_objects = sorted(objects, key=lambda o: get_value_from_data(o, attr))
    else:
        new_objects = objects # 原始的就可以了。
    if reverse:
        new_objects.reverse()
    return new_objects



MARKDOWN_EXTS = ['.txt', '.md', '.markdown', '.mk']

def is_a_markdown_file(path):
    if not path:
        return False
    ext = os.path.splitext(path)[1].lower()
    return ext in MARKDOWN_EXTS