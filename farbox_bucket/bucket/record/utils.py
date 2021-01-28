# coding: utf8
from __future__ import absolute_import
from farbox_bucket.utils import to_unicode, string_types, are_letters
from farbox_bucket.utils.data import json_dumps
from farbox_bucket.bucket.defaults import BUCKET_RECORD_SORT_TYPES
from farbox_bucket.utils.ssdb_utils import hset, hget
from farbox_bucket.settings import sentry_client


def get_record_data_error_info(data):
    # record_data 必须是可以 dumps 的 dict 或者 字符串
    if isinstance(data, dict):
        try:
            data = json_dumps(data)
        except:
            if sentry_client:
                sentry_client.captureException()
            return 'py-data format error'
    if not isinstance(data, string_types):
        return 'data format error'


def update_bucket_last_record_md5(bucket, record_md5):
    hset('_bucket_max_md5', bucket, record_md5)


def allowed_to_create_record_in_bucket(bucket, record_md5):
    last_md5 = hget('_bucket_max_md5', bucket)
    if last_md5 and last_md5==record_md5:
        return False
    else:
        return True


def get_file_id_from_record(record):
    if not isinstance(record, dict):
        return
    file_id = record.get('_ipfs') or record.get('version')
    if not isinstance(file_id, string_types):
        return
    return file_id




def get_bucket_name_for_order_by_record(bucket, record_data):
    data_type = get_data_type(record_data)
    should_set_order = data_type in BUCKET_RECORD_SORT_TYPES
    if should_set_order:
        bucket_name_for_order = '%s_%s_order' % (bucket, data_type)
    else:
        bucket_name_for_order = None
    return bucket_name_for_order


def get_data_type(record_data):
    data_type = record_data.get('_type') or record_data.get('type')
    if data_type and isinstance(data_type, string_types):
        if not are_letters(data_type):
            data_type = None
        else:
            data_type = to_unicode(data_type).strip().lower()
    return data_type

def get_url_path(record_data):
    url_path = record_data.get('url_path')
    if url_path and not isinstance(url_path, string_types):
        url_path = to_unicode(url_path)
    if not isinstance(url_path, string_types):
        url_path = None
    if not url_path and 'url' in record_data:
        _url = record_data.get('url')
        if isinstance(_url, string_types) and '://' not in _url:
            url_path = to_unicode(_url).lstrip('/')
    return url_path

def get_path_from_record(record_data, is_lower=True):
    # 默认全小写处理
    path = (record_data.get('path') or '').strip()
    if is_lower:
        path = path.lower()
    if not isinstance(path, string_types):
        return
    path = to_unicode(path)
    if not path:
        return
    #### 从某种角度来说， path 相当于是一个 db 中的唯一 id
    return path


