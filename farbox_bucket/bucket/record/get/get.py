# coding: utf8
from __future__ import absolute_import
from farbox_bucket.bucket.defaults import zero_ids
from farbox_bucket.utils.ssdb_utils import hget_many, hscan, hkeys, hget, hexists, hsize

from .utils import to_py_records_from_raw_ssdb_records


def get_records_count(bucket):
    return hsize(bucket)


def get_record(bucket, record_id, zero_ids_allowed=False, force_dict=False):
    if not zero_ids_allowed and record_id in zero_ids:
        return None
    if not bucket:
        return {}
    record = hget(bucket, record_id, force_dict=force_dict)
    return record

def has_record(bucket, record_id):
    return hexists(bucket, record_id)

def get_all_record_ids(bucket, ignore_zero_ids=False):
    keys = []
    key_start = ''
    while True:
        loop_keys = hkeys(bucket, key_start, limit=1000) or []
        keys += loop_keys
        if not loop_keys or len(loop_keys) !=1000:
            break
        key_start = loop_keys[-1]
    if ignore_zero_ids:
        return filter(lambda x: x not in zero_ids, keys)
    return keys



def get_records_for_bucket(bucket, start_record_id=None, end_record_id=None, limit=1000,
                           includes_start_record_id=False, reverse_scan=False, raw=False):
    # start_record_id means start here but does not include itself
    # 在两个地方用到： url 中 list bucket 的 & 模板引擎中调用 records 的
    # 模板引擎中调用的话，一般都会指定 start_record_id，避免一些 zero_ids 在实际呈现无意义的数据被显示出来
    # 一般是不 includes_start_record_id， 上一次获得的 list 的最后一个 record 的 id 会作为 cursor (start_id)，
    #   也就是说 start_id 不应该在当前获取的 list 内
    records = hscan(bucket, key_start=start_record_id, key_end=end_record_id, limit=limit, reverse_scan=reverse_scan)
    if includes_start_record_id and start_record_id:
        start_record = hget(bucket, start_record_id)
        if start_record:
            records.insert(0, [start_record_id, start_record])
    if not raw:
        records = to_py_records_from_raw_ssdb_records(records)
    return records



def loop_records_for_bucket(bucket, callback_func, limit=1000, start_record_id=None):
    records = get_records_for_bucket(bucket, start_record_id=start_record_id, limit=limit, includes_start_record_id=False)
    for record in records:
        record_id = record.get("_id")
        if record_id in zero_ids:
            continue
        callback_func(record)
    if records:
        last_record = records[-1]
        last_record_id = last_record.get("_id")
        if last_record_id:
            loop_records_for_bucket(bucket, callback_func, limit=limit, start_record_id=last_record_id)




def get_records_by_ids(bucket, record_ids):
    records = hget_many(bucket, keys=record_ids, force_dict=True, return_raw=False)
    return records

