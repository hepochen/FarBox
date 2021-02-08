# coding: utf8
import time
from farbox_bucket.settings import server_secret_key
from farbox_bucket.utils import get_md5, string_types, to_int



def get_signature_for_bucket(bucket, timestamp=None, salt=None):
    # <timestamp>-<signature>
    timestamp = timestamp or int(time.time())
    value_to_hash = "%s-%s-%s" % (timestamp, bucket, server_secret_key)
    if salt:
        value_to_hash = "%s-%s" % (value_to_hash, salt)
    signature_body = get_md5(value_to_hash)
    signature = "%s-%s" % (timestamp, signature_body)
    return signature



def check_signature_for_bucket(bucket, signature, salt=None, hours=24):
    if not isinstance(signature, string_types):
        return False
    if signature.count("-") != 1:
        return False
    signature_timestamp, signature_body = signature.split("-", 1)
    signature_timestamp = to_int(signature_timestamp, default_if_fail=0)
    if not signature_timestamp:
        return False
    timestamp = int(time.time())
    diff = timestamp - signature_timestamp
    if diff > hours*60*60: # 1 day by default
        return False
    signature_should_be = get_signature_for_bucket(bucket, signature_timestamp, salt=salt)
    if signature == signature_should_be:
        return True
    return False