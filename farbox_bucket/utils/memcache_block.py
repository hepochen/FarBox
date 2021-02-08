#coding: utf8
from farbox_bucket.utils.memcache import cache_client



def is_blocked(block_id, ttl=60):
    cache_key = "mblock_%s" % block_id
    if cache_client.get(cache_key):
        return True
    else:
        cache_client.set(cache_key, "y", expiration=ttl)
