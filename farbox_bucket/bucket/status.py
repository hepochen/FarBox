# coding: utf8
from farbox_bucket.utils import bytes2human
from farbox_bucket.utils.ssdb_utils import hsize, zsize, zget, zget_max, zget_min, hget, get_db_system_status, hset, \
    hclear, get_hlist_and_count
from farbox_bucket.bucket.node import get_current_node_id
from farbox_bucket.utils.objectid import ObjectID, is_object_id
from farbox_bucket.utils.cache import cached

import datetime


def db_timestamp_to_date_string(db_timestamp):
    if not db_timestamp:
        return ''
    timestamp = db_timestamp / 1000.
    try:
        utc_date = datetime.datetime.utcfromtimestamp(timestamp)
    except ValueError:
        return str(db_timestamp)
    date_string = utc_date.strftime('%Y-%m-%d %H:%M:%S UTC')
    return date_string


def record_id_to_date_string(record_id):
    if not record_id:
        return ''
    if not is_object_id(record_id):
        return ''
    record_id = ObjectID(record_id)
    date = record_id.generation_time
    date_string = date.strftime('%Y-%m-%d %H:%M:%S UTC')
    return date_string




def get_bucket_size(bucket):
    # count records of bucket
    size = hsize(bucket) or 0
    return size

def get_bucket_usage(bucket, for_human=False):
    try:
        usage = int(hget('_bucket_usage', bucket))
    except:
        usage = 0
    if for_human:
        usage = bytes2human(usage)
    return usage


def get_bucket_status(bucket):
    status_info = {}
    size = get_bucket_size(bucket)
    status_info['size'] = size
    last_updated_at = zget('buckets', bucket)
    if last_updated_at:
        status_info['date'] = db_timestamp_to_date_string(last_updated_at)
    max_record_id = hget('_bucket_max_id', bucket)
    delta_record_id = hget('_bucket_delta_id', bucket)
    status_info['max_record_id'] = max_record_id
    status_info['delta_record_id'] = delta_record_id
    status_info['max_record_date'] = record_id_to_date_string(max_record_id)
    status_info['delta_record_date'] = record_id_to_date_string(delta_record_id)
    try:
        usage = int(hget('_bucket_usage', bucket) or 0)
    except:
        usage = 0
    status_info['usage'] = usage
    status_info['usage_for_human'] = bytes2human(usage)
    if usage and size:
        usage_per_record = round(usage/float(size), 2)
        status_info['usage_per_record'] = usage_per_record
        status_info['usage_per_record_for_human'] = bytes2human(usage_per_record)
    return status_info


@cached(20)
def get_current_node_status():
    node_id = get_current_node_id() or '?'
    status_info = dict(
        id = node_id,
        node_id = node_id,
        buckets_size = zsize('buckets')
    )
    # todo 提供 first_bucket & last_bucket，会不会造成潜在的隐私泄露？
    first_bucket_timestamp = zget_min('buckets')
    if first_bucket_timestamp:
        first_bucket, first_bucket_timestamp = first_bucket_timestamp
        status_info['first_bucket'] = first_bucket
        status_info['first_bucket_date'] = db_timestamp_to_date_string(first_bucket_timestamp)
    last_bucket_timestamp = zget_max('buckets')
    if last_bucket_timestamp:
        last_bucket, last_bucket_timestamp = last_bucket_timestamp
        status_info['last_bucket'] = last_bucket
        status_info['last_bucket_date'] = db_timestamp_to_date_string(last_bucket_timestamp)

    records_count = hget('_records_count', 'all') or 0
    try:
        records_count = int(records_count)
    except:
        pass
    status_info['records_count'] = records_count

    status_info['db'] = get_db_system_status()
    now = datetime.datetime.utcnow()
    status_info['date'] = now.strftime('%Y-%m-%d %H:%M:%S UTC')

    return status_info





def fix_records_count():
    # 从数据库中，重新构建 _records_count 上的数据
    #hclear('_records_count')
    hlist_count = get_hlist_and_count()
    total_count = 0
    for name, count in hlist_count.items():
        if len(name) < 32:
            continue
        total_count += count
        hset('_records_count', name, count)
    hset('_records_count', 'all', total_count)


