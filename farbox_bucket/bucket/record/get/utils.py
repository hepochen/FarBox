# coding: utf8
from farbox_bucket.utils import string_types, get_value_from_data, to_md5, smart_unicode
from farbox_bucket.utils.ssdb_utils import hset, hexists, hscan, hkeys, zset, hget, ssdb_data_to_py_data, zrange
from farbox_bucket.bucket.defaults import zero_ids


def to_py_records_from_raw_ssdb_records(records, ignore_zero_ids=False):
    # 直接从 ssdb 过来的数据， 第一个是 record_id
    # record 必须是一个 dict 类型, 并且看是否必要不显示 zero_ids
    records_to_return = []
    for record_id, raw_record in records:
        if ignore_zero_ids:
            if record_id in zero_ids:
                continue
        record = ssdb_data_to_py_data(raw_record)
        if not record:
            continue
        if  not isinstance(record, dict):
            continue
        record['_id'] = record_id
        records_to_return.append(record)
    return records_to_return



def filter_records_for_bucket(records, fields):
    fields_to_show = fields
    if not fields_to_show or not isinstance(fields_to_show, (list, tuple)):
        fields_to_show = []
    records_to_return = []
    for record_id, raw_record in records:
        if record_id in zero_ids:
            continue
        record = ssdb_data_to_py_data(raw_record)
        if not record:
            continue
        if not isinstance(record, dict):
            record = dict(data=record)
        record['_id'] = record_id
        if fields_to_show:
            f_record = {'_id': record_id}
            for field in fields_to_show:
                v = get_value_from_data(record, field)
                if v is not None:
                    f_record[field] = v
            record = f_record
        records_to_return.append(record)
    return records_to_return


