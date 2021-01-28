# coding: utf8
from flask import g
from farbox_bucket.utils.data import json_dumps
from farbox_bucket.utils import is_email_address, string_types
from farbox_bucket.utils.ssdb_utils import  hset, hget
from farbox_bucket.bucket.utils import has_bucket


def get_bucket_private_configs(bucket):
    # 只允许在服务端中获取，不允许返回给 client 查看
    cache_key = "%s_private_configs" % bucket
    try: cached_value = getattr(g, cache_key, None)
    except: cached_value = None
    if cached_value is not None:
        return cached_value
    configs = hget("_bucket_private_configs", bucket)
    if not isinstance(configs, dict):
        configs = {}
    try:
        setattr(g, cache_key, configs)
    except:
        pass
    return configs


def set_bucket_private_configs(bucket, configs):
    if not isinstance(configs, dict):
        return
    if not has_bucket(bucket):
        return
    configs_data = json_dumps(configs)
    if len(configs_data) > 500*1024: # 不能大于 500k
        return
    else:
        hset("_bucket_private_configs", bucket, configs_data)
        return True



def update_bucket_private_configs(bucket, **kwargs):
    if not bucket:
        return
    if not kwargs:
        return
    configs = get_bucket_private_configs(bucket)
    configs.update(kwargs)
    set_bucket_private_configs(bucket, configs)



def get_bucket_private_config(bucket, key, default=None):
    configs = get_bucket_private_configs(bucket)
    return configs.get(key, default)


def set_owner_email_to_bucket(bucket, email):
    email = email.strip().lower()
    if email and not is_email_address(email):
        return
    else:
        update_bucket_private_configs(bucket, email=email)


def get_bucket_owner_email(bucket):
    if not bucket:
        return ""
    email = get_bucket_private_config(bucket, "email") or ""
    if not isinstance(email, string_types):
        email = ""
    return email