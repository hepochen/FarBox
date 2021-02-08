#coding: utf8
import datetime
from farbox_bucket.utils import to_int, bytes2human
from farbox_bucket.utils.ssdb_utils import hincr, hlist, hget, hgetall, zincr, zget, zscan, zrscan
from farbox_bucket.bucket.record.utils import count_records_by_type_for_bucket
from farbox_bucket.bucket.record.get.get import  get_records_count




def increase_file_size_for_bucket(bucket, file_size):
    file_size = to_int(file_size, default_if_fail=0)
    if not file_size:
        return
    zincr("_bucket_usage_file_size", bucket, file_size)


def decrease_file_size_for_bucket(bucket, file_size):
    file_size = to_int(file_size, default_if_fail=0)
    if not file_size:
        return
    if file_size > 0:
        file_size = -file_size
    zincr("_bucket_usage_file_size", bucket, file_size)



def increase_bandwidth_for_bucket(bucket, bandwidth):
    # 带宽
    bandwidth = to_int(bandwidth, default_if_fail=0)
    if not bandwidth:
        return
    now = datetime.datetime.utcnow()
    key = now.strftime("%Y%m") + "b"
    zincr("_bucket_usage_bandwidth", bucket, bandwidth) # all buckets bandwidth
    hincr("_bucket_usage_%s"%bucket, key, bandwidth)


def increase_request_for_bucket(bucket, num=1):
    # 请求数
    num = to_int(num, default_if_fail=0)
    if not num:
        return
    now = datetime.datetime.utcnow()
    key = now.strftime("%Y%m") + "r"
    zincr("_bucket_usage_request", bucket, 1)
    hincr("_bucket_usage_%s"%bucket, key, num)



def get_bucket_file_size(bucket):
    file_size = zget("_bucket_usage_file_size", bucket)
    file_size = to_int(file_size, default_if_fail=0)
    return file_size



def get_all_buckets_file_size(score_start=0, per_page=1000):
    result = []
    raw_result = zrscan("_bucket_usage_file_size", score_start=score_start or "", limit=per_page)
    for bucket, value in raw_result:
        value = to_int(value, default_if_fail=0)
        result.append(dict(bucket=bucket, value=bytes2human(value)))
    return result


def get_all_buckets_bandwidth(score_start=0, per_page=1000):
    result = []
    raw_result = zrscan("_bucket_usage_bandwidth", score_start=score_start or "", limit=per_page)
    for bucket, value in raw_result:
        value = to_int(value, default_if_fail=0)
        result.append(dict(bucket=bucket, value=bytes2human(value)))
    return result

def get_all_buckets_request(score_start=0, per_page=1000):
    result = []
    raw_result = zrscan("_bucket_usage_request", score_start=score_start or "", limit=per_page)
    for bucket, value in raw_result:
        value = to_int(value, default_if_fail=0)
        result.append(dict(bucket=bucket, value=value))
    return result


def get_bucket_usage(bucket):
    name = "_bucket_usage_%s"%bucket
    raw_result = hgetall(name)
    usage = {
        "requests": [],
        "bandwidth": [],
        "file_size": "",
        "docs_count": 0
    }
    if not bucket:
        return usage
    usage["file_size"] = bytes2human(get_bucket_file_size(bucket))
    usage["docs_count"] = get_records_count(bucket)
    usage["posts_count"] = count_records_by_type_for_bucket(bucket, "post")
    usage["files_count"] = count_records_by_type_for_bucket(bucket, "file")
    usage["images_count"] = count_records_by_type_for_bucket(bucket, "image")
    usage["folders_count"] = count_records_by_type_for_bucket(bucket, "folder")
    raw_result.reverse()
    for k, v in raw_result:
        v = to_int(v, default_if_fail=0)
        if not v:
            continue
        if k.endswith("r"): # requests
            month = k[:-1]
            usage["requests"].append(dict(
                month = month,
                value = v,
            ))
        elif k.endswith("b"): # bandwidth
            month = k[:-1]
            usage["bandwidth"].append(dict(
                month = month,
                value = bytes2human(v),
            ))
    return usage


