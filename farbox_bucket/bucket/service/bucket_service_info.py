#coding: utf8
import datetime
from farbox_bucket.utils.ssdb_utils import hset, hget
from farbox_bucket.bucket.utils import is_valid_bucket_name
from farbox_bucket.utils.date import utc_date_parse
from farbox_bucket.utils.env import get_env
from farbox_bucket.utils import to_int



def get_bucket_service_info(bucket):
    if not bucket:
        return {}
    if not is_valid_bucket_name(bucket):
        return {}
    return hget("_bucket_info", bucket, force_dict=True)


def set_bucket_service_info(bucket, order_id=None, **kwargs):
    if not is_valid_bucket_name(bucket):
        return
    info = get_bucket_service_info(bucket)
    if not info.get("bucket"):
        info["bucket"] = bucket
    if order_id:
        order_id_list = info.get("order_id_list")
        if not isinstance(order_id_list, (list, tuple)):
            order_id_list = []
        if isinstance(order_id_list, tuple):
            order_id_list = list(order_id_list)
        if order_id not in order_id_list:
            order_id_list.append(order_id)
        info["order_id_list"] = order_id_list
    info.update(kwargs)
    hset("_bucket_info", bucket, info)



def get_bucket_expired_date(bucket):
    info = get_bucket_service_info(bucket)
    return info.get("expired_date")


def change_bucket_expired_date(bucket, expired_date=None, days=None, order_id=None, **kwargs):
    if expired_date is None and days is None:
        # by default, 30 days
        free_days = to_int(get_env("free_days"), default_if_fail=30) or 30
        expired_date = datetime.datetime.utcnow() + datetime.timedelta(days=free_days)
    elif isinstance(days, (int, float)):
        # 指定扩展的天数
        now = datetime.datetime.utcnow()
        current_expired_date = get_bucket_expired_date(bucket) or now
        if current_expired_date < now:
            current_expired_date = now
        expired_date = current_expired_date + datetime.timedelta(days=days)
    if not isinstance(expired_date, datetime.datetime):
        try:
            expired_date = utc_date_parse(expired_date)
        except:
            return
    set_bucket_service_info(bucket, expired_date=expired_date, order_id=order_id, **kwargs)


