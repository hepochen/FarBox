# coding: utf8
from __future__ import absolute_import
from farbox_bucket.utils.ssdb_utils import hincr, py_data_to_ssdb_data
from farbox_bucket.bucket.utils import  update_bucket_max_id
from farbox_bucket.bucket.record.utils import get_path_from_record, get_data_type

from .for_created import after_path_related_record_created
from .for_deleted import after_path_related_record_deleted



def update_path_related_when_record_changed(bucket, record_id, record_data):
    # 注意:!!!! 凡是 record 中有指定 path 段的，都是可以被更新的；如果不希望这个 record 被 删除，就不要赋予这个字段
    if not isinstance(record_data, dict):
        return
    if not bucket or not record_id:
        return
    is_deleted = record_data.get('is_deleted', False)


    # path 相关的逻辑
    path = get_path_from_record(record_data)
    if not path:
        return
    if is_deleted:
        # delete the record, 实际上都是增量，只是一个 action=delete 的标识而已; 但也有直接把 record 删除掉的
        after_path_related_record_deleted(bucket, record_data=record_data)
    else: # create or update
        after_path_related_record_created(bucket, record_id, record_data)



def after_record_created(bucket, py_record_data, object_id, should_update_bucket_max_id=False):
    if should_update_bucket_max_id and object_id:
        # 由 API 构建的， 会产生一个新的 object_id
        update_bucket_max_id(bucket, object_id)

    byte_record_data = py_data_to_ssdb_data(py_record_data) # must be string_types

    hincr('_bucket_usage', bucket, len(byte_record_data))  # 容量增加
    hincr('_records_count', 'all', num=1)  # 如果系统中 bucket 被删除，这个增量是不会减少的
    hincr('_records_count', bucket, num=1)

    update_path_related_when_record_changed(bucket, object_id, py_record_data)