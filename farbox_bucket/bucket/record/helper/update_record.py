# coding: utf8
from farbox_bucket.bucket.utils import has_bucket
from farbox_bucket.bucket.record.create import create_record, update_path_related_when_record_changed





def update_record_directly(bucket, record):
    # 通过 record 来更新 record，不需要额外的编译
    # 如果有 path 路径，不要去更改它
    if not isinstance(record, dict):
        return False
    if not has_bucket(bucket):
        return False
    record['_auto_clean_bucket'] = True

    # 创建新的 record
    create_record(bucket, record)

    object_id = record.get("_id")
    if object_id:
        update_path_related_when_record_changed(bucket, object_id, record)

    return True
