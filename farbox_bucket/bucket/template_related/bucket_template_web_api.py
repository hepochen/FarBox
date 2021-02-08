# coding: utf8
import time
import gevent
import requests
from flask import Response, request
from farbox_bucket.settings import server_secret_key
from farbox_bucket.utils.data import json_dumps
from farbox_bucket.utils import get_md5, to_int, string_types
from farbox_bucket.bucket.utils import has_bucket
from farbox_bucket.bucket.token.utils import get_logined_bucket
from farbox_bucket.bucket.utils import set_bucket_configs, get_bucket_pages_configs
from farbox_bucket.bucket.token.bucket_signature_and_check import get_signature_for_bucket, check_signature_for_bucket





def do_set_bucket_pages_configs_by_web_api(bucket, remote_url, timeout=3):
    if not has_bucket(bucket):
        return
    if not isinstance(remote_url, string_types):
        return
    if "://" not in remote_url:
        remote_url = "http://" + remote_url
    try:
        response = requests.get(remote_url, timeout=timeout)
        raw_pages_configs = response.json()
        if not isinstance(raw_pages_configs, dict):
            return
        if not raw_pages_configs.get("_route"):
            return
        raw_pages_configs["can_copy"] = False
        set_bucket_configs(bucket, raw_pages_configs, config_type="pages")
        return True
    except:
        pass


def set_bucket_pages_configs_by_web_api(bucket, remote_url, timeout=3):
    # True or False
    if not has_bucket(bucket):
        return  # ignore
    gevent_job = gevent.spawn(do_set_bucket_pages_configs_by_web_api, bucket, remote_url, timeout)
    try:
        result = gevent_job.get(block=True, timeout=timeout)
        return result
    except:
        gevent_job.kill(block=False)
        return False

def show_bucket_pages_configs_by_web_api(bucket):
    sign = request.values.get("sign")
    if not check_signature_for_bucket(bucket, sign):
        pages_config = {"error": "signature is not matched"}
    else:
        pages_config = get_bucket_pages_configs(bucket) or {}
        if not pages_config.get("can_copy", True):
            # 比如从别人那里 copy 过来的，是不允许再 copy 的
            pages_config = {"error": "copied from another bucket, not allowed to copy it again."}
    data = json_dumps(pages_config)
    response = Response(data, mimetype='application/json')
    return response





