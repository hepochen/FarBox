# coding: utf8
import time
from farbox_bucket.utils.ssdb_utils import ssdb_cache_get, ssdb_cache_set
from farbox_bucket.utils.encrypt.key_encrypt import create_private_public_keys
from farbox_bucket.bucket.utils import get_bucket_by_public_key


def get_bucket_cache_key(bucket):
    cache_key = '%s_keys' % bucket
    return cache_key


def create_private_key_on_server_side():
    private_key, public_key = create_private_public_keys()
    """bucket = get_bucket_by_public_key(public_key)
    cache_key = get_bucket_cache_key(bucket)
    ssdb_cache_set(
        key = cache_key,
        value = dict(
            bucket = bucket,
            private_key = private_key,
            public_key = public_key,
            time = time.time(),
        ),
        ttl = 10 * 24 * 60 * 60, # 24 hours * 10 days
    )"""
    return private_key


def get_private_key_on_server_side(bucket):
    cache_key = get_bucket_cache_key(bucket)
    cached_value = ssdb_cache_get(cache_key)
    if cached_value and isinstance(cached_value, dict):
        return cached_value.get('private_key')


def get_public_key_on_server_side(bucket):
    cache_key = get_bucket_cache_key(bucket)
    cached_value = ssdb_cache_get(cache_key)
    if cached_value and isinstance(cached_value, dict):
        return cached_value.get('public_key')



