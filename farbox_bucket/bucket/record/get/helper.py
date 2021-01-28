# coding: utf8
from .get import get_records_for_bucket



def loop_records_for_bucket(bucket, func_for_record, limit=100, raw=False):
    start_record_id = None
    while True:
        records = get_records_for_bucket(
            bucket = bucket,
            start_record_id = start_record_id,
            limit = limit,
            includes_start_record_id = False,
            raw = raw,
        )
        for record in records:
            func_for_record(record)
        if not records or len(records) != limit:
            break
        last_record = records[-1]
        if isinstance(last_record, dict):
            start_record_id = last_record['_id']
        else:
            start_record_id = last_record[0]