# coding: utf8
from farbox_bucket.utils.data import json_dumps, json_loads
from .get.get import get_record
from .get.path_related import get_record_id_by_path
from farbox_bucket.utils.ssdb_utils import hset, ssdb_data_to_py_data, py_data_to_ssdb_data


# 如非特殊，不要对一个 record 进行 update

fields_not_allowed_to_update = ['_id', '_pre_id', 'id', 'path']

def update_record(bucket, record_id, **kwargs):
    if not record_id:
        return False
    if isinstance(record_id, dict):
        record_id = record_id.get("_id")
    record = get_record(bucket, record_id, force_dict=True)
    if not record:
        return False
    for field in fields_not_allowed_to_update: # 不允许更改的字段
        kwargs.pop(field, None)
    if not kwargs:
        return False
    record.update(kwargs) # update
    hset(bucket, record_id, record)
    return True



def update_record_by_path(bucket, path, **kwargs):
    record_id = get_record_id_by_path(bucket, path)
    if record_id:
        return update_record(bucket, record_id, **kwargs)
    else:
        return False







