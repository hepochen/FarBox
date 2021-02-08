#coding: utf8
import re
from flask import request
from farbox_bucket.settings import WEBSITE_DOMAINS, DEBUG, TMP_BUCKET_FOR_DEBUG
from farbox_bucket.bucket import is_valid_bucket_name
from farbox_bucket.bucket.utils import get_admin_bucket, get_buckets_size
from farbox_bucket.bucket.domain.utils import get_bucket_from_domain
from farbox_bucket.server.utils.request_path import get_bucket_from_url
from farbox_bucket.server.utils.cache_for_function import cache_result




@cache_result
def get_bucket_from_request(try_referrer=True):
    if DEBUG and TMP_BUCKET_FOR_DEBUG: # for debug
        return TMP_BUCKET_FOR_DEBUG
    domain = request.host
    if ':' in domain:
        domain = domain.split(':')[0]
    bucket = get_bucket_from_domain(domain)
    if not bucket and request.referrer:
        bucket_c = re.search(r'/bucket/([^/]+)/', request.referrer)
        if bucket_c:
            bucket_from_referrer = bucket_c.group(1)
            if is_valid_bucket_name(bucket_from_referrer):
                bucket = bucket_from_referrer
    if not bucket:
        # at last, check the ADMIN_BUCKET
        admin_bucket = get_admin_bucket()
        if admin_bucket:
            if domain in WEBSITE_DOMAINS: # the website for platform, return the ADMIN_BUCKET directly
                return admin_bucket
            elif domain in ['localhost'] or domain.startswith("192.168.100."): # for debug, domain should not be 127.0.0.1
                return admin_bucket
            elif get_buckets_size() == 1:
                # 当前只有一个 bucket
                return admin_bucket

    if try_referrer and not bucket and request.referrer and request.referrer.startswith(request.url_root):
        bucket = get_bucket_from_url(request.referrer)

    return bucket