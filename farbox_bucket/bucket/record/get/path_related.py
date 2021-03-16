# coding: utf8
from __future__ import absolute_import
import os
from farbox_bucket.utils import string_types, smart_unicode, to_date, to_float, MARKDOWN_EXTS, is_a_markdown_file
from farbox_bucket.utils.gzip_content import ungzip_content
from farbox_bucket.utils.data import json_loads
from farbox_bucket.utils.date import date_to_timestamp
from farbox_bucket.utils.ssdb_utils import hscan, hget, hexists, zrange, hget_many, hgetall
from farbox_bucket.bucket.utils import get_bucket_name_for_path, get_bucket_name_for_order
from farbox_bucket.bucket import get_bucket_site_configs

from farbox_bucket.server.utils.request_context_vars import get_context_value_from_request, set_context_value_from_request

from .get import get_records_by_ids



########## utils starts ##########
def filter_paths_under_path(paths, under):
    # path should be lower and unicode
    if under:
        under = under.strip('/').lower()
    if under:
        under += '/'
        under = smart_unicode(under)
    if not under:
        return paths
    filtered_paths = []
    for path in paths:
        if path.startswith(under):
            filtered_paths.append(path)
    return filtered_paths

def just_get_record_id(raw_record_id):
    if ',' in raw_record_id:
        record_id = raw_record_id.split(',')[0]
    else:
        record_id = raw_record_id
    return record_id

########## utils ends ##########


############## basic starts ##########

def get_record_id_by_path(bucket, path):
    path_bucket = get_bucket_name_for_path(bucket)
    path = path.strip().lstrip('/').lower()
    record_object_id = hget(path_bucket, path)
    if record_object_id:
        record_object_id = just_get_record_id(record_object_id)
        record_object_id = record_object_id.lstrip('#')
    return record_object_id


def get_record_ids_by_paths(bucket, paths, ignore_marked_id=True):
    path_bucket = get_bucket_name_for_path(bucket)
    raw_result = hget_many(path_bucket, keys=paths)
    record_ids = []
    for path, record_id in raw_result:
        record_id = just_get_record_id(record_id)
        if record_id.startswith('#') and ignore_marked_id:
            continue
        else:
            record_id = record_id.lstrip('#')
        record_ids.append(record_id)
    return record_ids


def get_paths_and_ids_under(bucket, under="", max_limit=10000):
    path_bucket = get_bucket_name_for_path(bucket)
    under = under or ""
    path_under = under.lower().strip('/')  # prefix
    if not path_under:
        path_under_key_start = ''
        path_under_key_end = ''
    else:
        path_under_key_start = path_under + '/'
        path_under_key_end = path_under + '0'
    ids_and_paths = []
    raw_result = hscan(path_bucket, key_start=path_under_key_start, key_end=path_under_key_end, limit=max_limit)
    for path, record_id in raw_result:
        record_id = just_get_record_id(record_id)
        path = smart_unicode(path)
        ids_and_paths.append([path, record_id])
    return ids_and_paths


def get_bucket_markdown_record_ids(bucket, under='', max_limit=20000):
    record_ids = []
    paths_and_ids = get_paths_and_ids_under(bucket=bucket, under=under, max_limit=max_limit)
    for (path, record_id) in paths_and_ids:
        if is_a_markdown_file(path):
            record_ids.append(record_id)
    return record_ids



def get_paths_under(bucket, under='', max_limit=10000):
    paths_and_ids = get_paths_and_ids_under(bucket=bucket, under=under, max_limit=max_limit)
    paths = []
    for path, record_id in paths_and_ids:
        paths.append(path)
    return paths


############## basic ends ##########


def get_record_by_path(bucket, path, force_dict=False):
    if not bucket:
        return None
    if not path:
        return None
    if not isinstance(path, string_types):
        return None
    record_object_id = get_record_id_by_path(bucket, path)
    if record_object_id:
        record = hget(bucket, record_object_id, force_dict=force_dict)
        if isinstance(record, dict) and not record.get("_id"):
            record["_id"] = record_object_id
    else:
        record = None
    return record


def get_markdown_record_by_path_prefix(bucket, prefix):
    if not bucket:
        return
    for ext in MARKDOWN_EXTS:
        path = prefix.strip("/") + ext
        doc = get_record_by_path(bucket, path)
        if doc:
            return doc

def has_record_by_path(bucket, path):
    # 是否存在 path 对应的 record
    if not bucket:
        return False
    record_object_id = get_record_id_by_path(bucket, path)
    if record_object_id:
        return  hexists(bucket, record_object_id)
    else:
        return False

def has_markdown_record_by_path_prefix(bucket, prefix):
    if not bucket:
        return False
    for ext in MARKDOWN_EXTS:
        path = prefix.strip("/") + ext
        if has_record_by_path(bucket, path):
            return True
    return False




def get_raw_content_by_record(record):
    if not record or not isinstance(record, dict):
        return ""
    raw_content = record.get('raw_content')
    if not raw_content:
        return ''
    if record.get('_zipped'):
        try:
            raw_content = ungzip_content(raw_content, base64=True)
        except:
            pass
    return raw_content

def get_raw_content_by_path(bucket, path):
    # 只处理有 raw_content 这个字段的
    record = get_record_by_path(bucket, path)
    return get_raw_content_by_record(record)


def get_json_content_by_path(bucket, path, force_dict=False):
    raw_content = get_raw_content_by_path(bucket, path)
    if not raw_content:
        return {}
    try:
        result = json_loads(raw_content)
        if force_dict and not isinstance(result, dict):
            return {}
        return result
    except:
        return {}


def do_get_record_by_url(bucket, url_path):
    url_path = url_path.strip().lower()
    bucket_for_url = '%s_url' % bucket
    path_data_id = hget(bucket_for_url, url_path)
    if path_data_id:
        return get_record_by_path(bucket, path_data_id)

def get_record_by_url(bucket, url_path):
    if "://" in url_path: # abs url is not allowed
        return None
    cache_key = "cache_for_get_record_by_url"
    cached_in_g = get_context_value_from_request(cache_key, force_dict=True)
    if url_path in cached_in_g:
        return cached_in_g.get(url_path)
    doc = do_get_record_by_url(bucket, url_path)
    # post 开头的url，是系统默认提供的一般; 去掉这个前缀，继续尝试干净的 url_path
    if not doc and url_path and url_path.startswith('post/'):
        url_path = url_path.replace('post/', '', 1)
        doc = do_get_record_by_url(bucket, url_path=url_path)
    cached_in_g[url_path] = doc
    set_context_value_from_request(cache_key, cached_in_g)
    return doc


def get_record_by_url_or_path(bucket, key):
    if not isinstance(key, string_types):
        return None
    record = get_record_by_url(bucket, key) or get_record_by_path(bucket, key)
    return record


def get_records_by_paths(bucket, paths, ignore_marked_id=True, limit=None):
    record_ids = get_record_ids_by_paths(bucket, paths, ignore_marked_id=ignore_marked_id)
    if limit and isinstance(limit, int):
        record_ids = record_ids[:limit]
    records = get_records_by_ids(bucket, record_ids)
    return records


def get_next_record(bucket, current_record, reverse=True):
    if not current_record:
        return None
    data_type = current_record.get('_type') or 'post'
    current_path = current_record.get('path') or ''
    if not current_path:
        return None
    current_path = current_path.lower().strip('/')
    paths = get_paths_by_type(bucket, data_type=data_type, reverse=reverse, prefix_to_ignore='_')
    if current_path not in paths:
        return None
    current_index = paths.index(current_path)
    paths_to_hit = paths[current_index+1:current_index+1+5] # 准备 5 个做备选，如果有太多 draft 性质的，可能会找不到数据
    records_to_hit = get_records_by_paths(bucket=bucket, paths=paths_to_hit, ignore_marked_id=True, limit=1)
    if records_to_hit:
        return records_to_hit[0]
    else:
        return None


# 有 order 的，也就是缩进建立在 xxx_<type>_order 上的，也都是有 path 的
def get_paths_by_type(bucket, data_type, offset=0, limit=10000, reverse=False,
                      prefix_to_ignore=None, date_start=None, date_end=None):

    paths = []
    if not bucket:
        return []

    site_configs = get_bucket_site_configs(bucket)
    utc_offset = to_float(site_configs.get('utc_offset', 8), default_if_fail=8)

    if date_start:
        date_start = date_to_timestamp(to_date(date_start), utc_offset=utc_offset)
    if date_end:
        date_end = date_to_timestamp(to_date(date_end), utc_offset=utc_offset)
    should_hit_date = False
    if date_start or date_end:
        should_hit_date = True
    if should_hit_date and not prefix_to_ignore:
        prefix_to_ignore = '_'

    if prefix_to_ignore:
        prefix_to_ignore = smart_unicode(prefix_to_ignore)
    order_bucket = get_bucket_name_for_order(bucket, data_type)
    result = zrange(order_bucket, offset=offset, limit=limit, reverse=reverse)


    for path, order_value in result:
        if should_hit_date:
            order_value = to_float(order_value)
            if order_value < 10000000:
                continue
            if date_start and order_value<date_start:
                continue
            if date_end and order_value>date_end:
                continue
        path = smart_unicode(path)
        if prefix_to_ignore and path.startswith(prefix_to_ignore):
            continue
        paths.append(path)
    return paths


def get_records_by_type(bucket, data_type, offset=0, limit=100, reverse=False):
    paths = get_paths_by_type(bucket, data_type=data_type, offset=offset, limit=limit, reverse=reverse)
    records = get_records_by_paths(bucket, paths)
    return records


def excludes_paths(paths, excludes=None):
    if not excludes:
        return paths
    if not isinstance(excludes, (list, tuple)):
        return paths
    if not paths:
        return paths
    if '_' in excludes or '-' in excludes:
        excludes_tmp_paths = True # 不包含临时文件，比如_cover, _cache .etc
    else:
        excludes_tmp_paths = False
    filtered_paths = []
    for path in paths:
        if not path:
            continue
        if path in excludes:
            continue
        path_without_ext = os.path.splitext(path)[0]
        if path_without_ext in excludes: # 这个是文件名包含
            continue
        elif path_without_ext.split('/')[0] in excludes: # 这是是第一层目录包含
            continue
        if excludes_tmp_paths and (path.startswith('_') or '/_' in path): # _ 开头的作为tmp 逻辑
            continue
        filtered_paths.append(path)
    return filtered_paths
