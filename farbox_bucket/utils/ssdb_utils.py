#coding: utf8
from __future__ import absolute_import
#import ujson as json
import re
from functools import partial
from farbox_bucket.settings import db_client
from farbox_bucket.utils import string_types, to_unicode, bytes2human, to_md5
from farbox_bucket.utils.data import json_dumps, json_loads

def py_data_to_ssdb_data(py_data):
    # just string
    if isinstance(py_data, string_types):
        return py_data
    else:
        try:
            ssdb_data = json_dumps(py_data)
        except:
            ssdb_data = ''
        return ssdb_data


ssdb_data_to_py_data_cache = {}
def ssdb_data_to_py_data(ssdb_data, hit_cache=False):
    # 为了避免从 ssdb 中获得数据，反复转为 python 中使用， 增加了 cache_id 的逻辑，以避免重复计算性能消耗的问题
    if not isinstance(ssdb_data, string_types):
        return ssdb_data
    if hit_cache:
        data_cache_key = to_md5(ssdb_data)
        cached_value = ssdb_data_to_py_data_cache.get(data_cache_key)
        if cached_value:
            return cached_value
    else:
        data_cache_key = None
    if re.match('\s*[\[\{\(]', ssdb_data): # dict list tuple
        try:
            py_data = json_loads(ssdb_data)
            if data_cache_key:
                ssdb_data_to_py_data_cache[data_cache_key] = py_data
        except:
            py_data = to_unicode(ssdb_data)
    else:
        py_data = to_unicode(ssdb_data)
    return py_data



def hset(namespace, key, value, ignore_if_exists=False):
    if not db_client:
        return
    if not namespace:
        return
    if ignore_if_exists:
        if hexists(namespace, key):
            return
    value = py_data_to_ssdb_data(value)
    db_client.hset(namespace, key, value)
    return True


def hincr(namespace, key,  num=1):
    if not num:
        return # ignore
    try:
        new_value = db_client.hincr(namespace, key, num)
        new_value = int(new_value)
    except:
        new_value = int(num) # failed
        db_client.hset(namespace, key, num)
    return new_value

def hdel(namespace, key):
    if not key:
        return
    done = db_client.hdel(namespace, key)
    return bool(done)


def hdel_many(namespace, keys):
    if not keys:
        return True
    done = db_client.multi_hdel(namespace, *keys)
    return bool(done)


def hclear(namespace):
    done = db_client.hclear(namespace)
    return bool(done)



def hget(namespace, key, force_dict=False):
    if not db_client:
        return
    if not namespace:
        return
    if not key:
        return
    value = db_client.hget(namespace, key)
    value = ssdb_data_to_py_data(value)
    if force_dict and not isinstance(value, dict):
        value = {}
    return value

def just_hget(namespace, key):
    """
    :param namespace:
    :param key:
    :return: None 或 原始的字符串
    """
    if not db_client:
        return
    if not namespace:
        return
    if not key:
        return
    value = db_client.hget(namespace, key)
    return value



def hget_many(namespace, keys, return_raw=True, force_dict=False, ):
    if not db_client:
        return []
    if not namespace:
        return []
    if not keys:
        return []
    if not isinstance(keys, (list, tuple)):
        return []
    keys = [key for key in keys if isinstance(key, string_types)]
    raw_result = db_client.multi_hget(namespace, *keys) # 获得的是一个纯 list， 需要转化
    result = [(raw_result[i], raw_result[i + 1]) for i in xrange(0, len(raw_result), 2)]
    if return_raw:
        return result
    records = []
    for record_id, raw_record in result:
        record = ssdb_data_to_py_data(raw_record)
        if not record:
            continue
        if force_dict and not isinstance(record, dict):
            continue
        records.append(record)
    return records


def hexists(namespace, key):
    if not db_client:
        return False
    if not namespace:
        return False
    if not key:
        return False
    exists = db_client.hexists(namespace, key)
    try:
        exists = int(exists)
    except:
        pass
    return bool(exists)


def hsize(namespace):
    return db_client.hsize(namespace)



def hscan(namespace, key_start='', key_end='', limit=1000, reverse_scan=False):
    # (key_start, key_end]
    if not db_client:
        return []
    if not namespace:
        return []
    key_start = key_start or ''
    key_end = key_end or ''
    if reverse_scan:
        #key_start, key_end = key_end, key_start
        raw_result = db_client.hrscan(namespace, key_start, key_end, limit)
    else:
        raw_result = db_client.hscan(namespace, key_start, key_end, limit)
    result = [(raw_result[i],raw_result[i+1]) for i in xrange(0, len(raw_result), 2)]
    #result = {raw_result[i]: raw_result[i+1] for i in xrange(0, len(raw_result), 2)}
    return result


def hscan_for_dict_docs(namespace, key_start='', key_end='', limit=1000, reverse_scan=False):
    raw_result = hscan(namespace, key_start, key_end, limit=limit, reverse_scan=reverse_scan)
    return to_py_dict_records_from_ssdb_hscan_records(raw_result)


def hgetall(namespace):
    if not db_client:
        return []
    if not namespace:
        return []
    raw_result = db_client.hgetall(namespace)
    result = [(raw_result[i], raw_result[i + 1]) for i in xrange(0, len(raw_result), 2)]
    return result



def hkeys(namespace, key_start='', key_end='', limit=1000):
    # (key_start, key_end]
    if not db_client:
        return []
    if not namespace:
        return []
    if not limit:
        limit = '' # list all
    keys = db_client.hkeys(namespace, key_start, key_end, limit) or []
    return keys


def hlist(name_start='', name_end='', limit=1000):
    # all namespaces under  Hashmap
    if not db_client:
        return []
    if not limit:
        limit = '' # list all
    namespaces = db_client.hlist(name_start, name_end, limit)
    return namespaces


def zset(namespace, key, score):
    # name is zset_key, key is zset_score
    if not db_client:
        return
    score = to_unicode(int(score))
    db_client.zset(namespace, key, score)


def zincr(namespace, key,  num=1):
    if not num:
        return # ignore
    try:
        new_value = db_client.zincr(namespace, key, num)
        new_value = int(new_value)
    except:
        new_value = int(num) # failed
        db_client.zset(namespace, key, num)
    return new_value


def zget(namespace, name):
    if not db_client:
        return
    value = db_client.zget(namespace, name)
    return value

def zget_max(namespace):
    # [key, score] or []
    if not db_client:
        return
    result = db_client.zrscan(namespace, '', '', '', 1)
    if result and len(result)==2:
        return [result[0], float(result[1])]
    else:
        return None

def zget_min(namespace):
    if not db_client:
        return
    result = db_client.zscan(namespace, '', '', '', 1)
    if result and len(result)==2:
        return [result[0], float(result[1])]
    else:
        return None

def zsize(namespace):
    return db_client.zsize(namespace)

def zlist(namespace, name_start='', name_end=''):
    return db_client.zlist(namespace, name_start, name_end)

def zcount(namespace, name_start='', name_end=''):
    return db_client.zcount(namespace, name_start, name_end)


def zdel(namespace, key):
    if not namespace:
        return
    done = db_client.zdel(namespace, key)
    return bool(done)


def zclear(namespace):
    done = db_client.zclear(namespace)
    return bool(done)


def zget_many(namespace, keys):
    if not keys:
        return []
    raw_result = db_client.multi_zget(namespace, *keys)
    result = [(raw_result[i], raw_result[i + 1]) for i in xrange(0, len(raw_result), 2)]
    return result





def zscan(namespace, key_start='', score_start='', score_end='', limit=1000):
    # 如果 key_start 为空, 那么对应权重值大于或者等于 score_start 的 key 将被返回.
    # 如果 key_start 不为空, 那么对应权重值大于 score_start 的 key, 或者大于 key_start 且对应权重值等于 score_start 的 key 将被返回.
    #  key 在 (key.score == score_start && key > key_start || key.score > score_start),
    # 并且key.score <= score_end 区间. 先判断 score_start, score_end, 然后判断 key_start._
    # return [(key, socre), (key, score)]

    # 如果 score_start == score_end, 就会返回唯一 score 对应的， 如果 score_end 不指定，那么后面 >= score_start 的都会返回
    if not db_client:
        return []
    raw_result = db_client.zscan(namespace, key_start, score_start, score_end, limit)
    result = [(raw_result[i],raw_result[i+1]) for i in xrange(0, len(raw_result), 2)]
    return result


def zrscan(namespace, key_start='', score_start='', score_end='', limit=1000):
    if not db_client:
        return []
    raw_result = db_client.zrscan(namespace, key_start, score_start, score_end, limit)
    result = [(raw_result[i],raw_result[i+1]) for i in xrange(0, len(raw_result), 2)]
    return result



def zrange(namespace, offset=0, limit=100, reverse=False):
    # 根据下标索引区间 [offset, offset + limit) 获取 key-score 对, 下标从 0 开始. zrrange 是反向顺序获取.
    offset = int(offset)
    limit = int(limit)
    if not reverse:
        raw_result = db_client.zrange(namespace, offset, limit)
    else:
        raw_result = db_client.zrrange(namespace, offset, limit)
    result = [(raw_result[i], raw_result[i + 1]) for i in xrange(0, len(raw_result), 2)]
    return result



def auto_cache_by_ssdb(key, value_func, ttl=60, force_update=False):
    cached_value = db_client.get(key)
    if cached_value is not None and not force_update:
        value = ssdb_data_to_py_data(cached_value, hit_cache=True)
    else:
        value = value_func()
        data = py_data_to_ssdb_data(value)
        db_client.setx(key, data, ttl)
    return value



def ssdb_cache_set(key, value, ttl=60):
    data = py_data_to_ssdb_data(value)
    db_client.setx(key, data, ttl)


def ssdb_set(key, value):
    data = py_data_to_ssdb_data(value)
    db_client.set(key, data)

def ssdb_get(key):
    value = db_client.get(key)
    if value is not None:
        value = ssdb_data_to_py_data(value)
    return value

def ssdb_cache_get(key):
    cached_value = db_client.get(key)
    if cached_value is not None:
        value = ssdb_data_to_py_data(cached_value, hit_cache=True)
        return value



def get_hlist_and_count(name_start='', result=None):
    # hashmap 的所有统计
    name_start = name_start
    if result is None:
        result = {}
    per_page = 1000
    hashmap_names = hlist(name_start=name_start, limit=per_page)
    for hashmap_name in hashmap_names:
        named_hashmap_size = hsize(hashmap_name)
        result[hashmap_name] = named_hashmap_size
        name_start = hashmap_name # as new name_start
    if len(hashmap_names) == per_page: # next page goes on.
        get_hlist_and_count(name_start=name_start, result=result)
    return result



def get_hlist_and_count_and_cache(ttl=10*60):
    value_func = partial(get_hlist_and_count, db_client=db_client)
    key = 'hlist_and_count'
    result = auto_cache_by_ssdb(key, value_func=value_func, ttl=ttl)
    return result

def get_hlist_all_records_count():
    hlist_count_result = get_hlist_and_count()
    records_count = sum(hlist_count_result.values())
    return records_count



# List starts
def qpush_front(name, *items):
    items = [py_data_to_ssdb_data(item) for item in items]
    result = db_client.qpush_front(name, *items)
    return result

def qpush_back(name, *items):
    items = [py_data_to_ssdb_data(item) for item in items]
    result = db_client.qpush_back(name, *items)
    return result

def qrange(name, offset=0, limit=1000):
    # 返回下标处于区域 [offset, offset + limit] 的元素.
    raw_items = db_client.qrange(name, offset, limit) or []
    items = [ssdb_data_to_py_data(item) for item in raw_items]
    return items

def qtrim_front(name, size):
    # 从头部删除元素
    db_client.qtrim_front(name, size)

def qtrim_back(name, size):
    # 从尾部删除元素
    db_client.qtrim_back(name, size)


def qpop_front(name, size=''):
    # raw result 可能是 None/True/List/String
    raw_items = db_client.qpop_front(name, size) or []
    if raw_items and isinstance(raw_items, string_types):
        raw_items = [ssdb_data_to_py_data(raw_items)]
    if not isinstance(raw_items, (list, tuple)):
        raw_items = []
    items = [ssdb_data_to_py_data(item) for item in raw_items]
    return items

def qpop_back(name, size=''):
    raw_items = db_client.qpop_back(name, size) or []
    if raw_items and isinstance(raw_items, string_types):
        raw_items = [ssdb_data_to_py_data(raw_items)]
    if not isinstance(raw_items, (list, tuple)):
        raw_items = []
    items = [ssdb_data_to_py_data(item) for item in raw_items]
    return items

def qclear(name):
    db_client.qclear(name)

# List ends



def get_db_system_status():
    if not db_client:
        return {}
    raw_db_info = db_client.info()
    db_size = db_client.dbsize()
    db_size_for_human = bytes2human(db_size)
    leveldb_status = raw_db_info.get('leveldb.stats') or ''
    leveldb_status = leveldb_status.split('\n')
    status_info = {
        'size': db_size_for_human,
        'version': raw_db_info.get('version'),
        'calls': raw_db_info.get('total_calls'),
        'db_status': leveldb_status,
    }
    return status_info




def get_path_related_key_start_end(path):
    # chr(48)='0', chr(47)='/'
    path = path.strip().strip('/').lower()
    if not path:
        key_start = ''
        key_end = ''
    else:
        key_start = path + '/'
        key_end = path + '0'
    return key_start, key_end




def to_py_dict_records_from_ssdb_hscan_records(records):
    # 直接从 ssdb 过来的数据， 第一个是 record_id
    # record 必须是一个 dict 类型
    records_to_return = []
    for record_id, raw_record in records:
        record = ssdb_data_to_py_data(raw_record)
        if not record:
            continue
        if not isinstance(record, dict):
            continue
        record['_id'] = record_id
        records_to_return.append(record)
    return records_to_return