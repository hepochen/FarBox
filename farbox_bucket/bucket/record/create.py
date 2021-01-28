# coding: utf8
from __future__ import absolute_import
from farbox_bucket.bucket.storage.default import storage
from farbox_bucket.utils import to_md5, smart_unicode
from farbox_bucket.utils.objectid import ObjectId, is_object_id
from farbox_bucket.utils.ssdb_utils import hset, ssdb_data_to_py_data, py_data_to_ssdb_data

from farbox_bucket.utils.data import json_loads
from farbox_bucket.bucket.utils import  has_bucket, set_bucket_into_buckets, get_bucket_max_id, set_bucket_configs
from farbox_bucket.bucket.record.utils import  allowed_to_create_record_in_bucket, update_bucket_last_record_md5, get_record_data_error_info

from .related.for_deleted import auto_clean_record_before_handle_path_related_record
from .related.for_all import after_record_created, update_path_related_when_record_changed

#!!!!!!! 所有的 record 必须是一个 {} 的数据结构

# 主要是 web 端 API 构建的
def create_record(bucket, record_data, avoid_repeated=True, auto_id=True, file_content=None, return_record=False):
    # make sure the bucket is correct before create record
    # 如果返回数据，就是 error_info
    # avoid_repeated 就是避免跟最后一条数据 body 是一样的
    error_info = get_record_data_error_info(record_data)
    if error_info:
        return error_info

    py_record_data = ssdb_data_to_py_data(record_data)
    byte_record_data = py_data_to_ssdb_data(record_data)

    if auto_id:
        object_id = str(ObjectId())
        if '_id' not in py_record_data and isinstance(py_record_data, dict): # record data 如有必要自动填充 _id
            py_record_data['_id'] = object_id
    else:
        object_id = py_record_data.get('_id') or py_record_data.get('id')
        avoid_repeated = False # 指定的 id 的，不做 repeated 的校验
        if not object_id:
            return 'auto_id disabled, should pass id in the record data'

    if avoid_repeated: # 避免最后一条记录的重复
        record_md5 = to_md5(byte_record_data)
        if not allowed_to_create_record_in_bucket(bucket, record_md5):
            error_info = 'current data is repeated to latest record @%s' % bucket
            if isinstance(py_record_data, dict):
                path_in_record = py_record_data.get('path')
                if path_in_record:
                    error_info += smart_unicode(', the path is %s'%path_in_record)
            return error_info
        else:
            update_bucket_last_record_md5(bucket, record_md5)

    # '_auto_clean_bucket' in record_data and is `True`
    # 如果是 delete 的直接删除 （break），反之则是完全的 update，相当于新的 record 代替 旧的  record
    auto_clean_status = auto_clean_record_before_handle_path_related_record(bucket, py_record_data)
    if auto_clean_status == 'break':
        return

    # store pre_object_id
    # 获得上一个对象的 id， 将当前的 data 转为 dict （如果是），存储 _pre_id 这个字段
    pre_object_id = get_bucket_max_id(bucket)
    if pre_object_id:
        if isinstance(py_record_data, dict):
            py_record_data['_pre_id'] = pre_object_id

    # 存储 record， 并且更新 bucket 上 max_id 的信息
    # 由于 record_id 是随机生成，本质上不会重复，故 ignore_if_exists=False, 避免一次校验的过程
    hset(bucket, object_id, py_record_data, ignore_if_exists=False)

    after_record_created(bucket, py_record_data, object_id=object_id, should_update_bucket_max_id=True)

    # 更新 buckets 的信息，表示当前 bucket 刚刚被更新过了
    set_bucket_into_buckets(bucket)

    if file_content and not py_record_data.get("raw_content"):
        # 指定了要存储的 file content，并且 record 中并没有 raw_content 这个字段，进行文件的存储
        storage.accept_upload_file_from_client(bucket, py_record_data, get_raw_content_func=file_content)

    if py_record_data.get("path") == "settings.json" and py_record_data.get("raw_content"):
        try:
            site_settings = json_loads(py_record_data.get("raw_content"))
            if isinstance(site_settings, dict):
                set_bucket_configs(bucket, site_settings, config_type="site")
        except:
            pass

    if return_record:
        return py_record_data


# 通过 node 之间同步创建的 record 信息
# record 必然是 dict 类型
# 如果 record_id 在本地已经存在的，就以本地的为准
def create_record_by_sync(bucket, record, check_bucket=False):
    if not isinstance(record, dict):
        return 'record is not a dict'
    record_id = record.pop('_id', None)
    if not record_id:
        return 'record_id is missing'
    if not is_object_id(record_id):
        return 'record_id is not a valid ObjectID'
    error_info = get_record_data_error_info(record)
    if error_info:
        return error_info
    if check_bucket: # current node has the bucket or not
        if not has_bucket(bucket):
            return 'no bucket matched'

    py_record_data = ssdb_data_to_py_data(record)

    saved = hset(bucket, record_id, py_record_data, ignore_if_exists=True)
    if saved:
        after_record_created(bucket, py_record_data, object_id=record_id, )
