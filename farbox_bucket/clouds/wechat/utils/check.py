# coding: utf8
from flask import request, abort
from farbox_bucket.utils import get_sha1, to_int
import time


def _is_from_wechat(token, ttl=120):
    # 这里的 token，实际上实在 wechat 的后台自己设置的
    rv = request.values
    nonce = rv.get('nonce')
    timestamp = rv.get('timestamp')
    if not nonce or not timestamp:
        return False
    values_to_sign = [token, nonce, timestamp]
    values_to_sign.sort()
    to_sign = ''.join(values_to_sign)
    signature = get_sha1(to_sign)
    if rv.get('signature') != signature:
        return False

    if ttl:
        timestamp = to_int(timestamp)
        now = time.time()
        if (now-timestamp) > ttl:# （默认）超过2分钟前就算请求过期了，校验失败
            return False

    return True # at last



def check_is_from_wechat(token, ttl=120, raise_error=True):
    status = _is_from_wechat(token, ttl=ttl)
    if raise_error and not status:
        # 需要触发错误，并且 status==False 的情况下，直接400扔出
        abort(400, 'not allowed or expired')
        return False
    else:
        return status