#coding: utf8
from __future__ import absolute_import
from flask import request
from farbox_bucket.settings import signer
from itsdangerous import BadTimeSignature, BadSignature
import time, re
from farbox_bucket.settings import sentry_client


# 这里处理的 cookie 都是用 signer 加密、解谜的，如果只是普通的 cookie，直接response.set_cookie 就可以了



def save_cookie(k, v, max_age=10*60): # 一般10分钟过期(客户端的)
    raw_max_age = max_age
    if not hasattr(request, 'safe_cookies_to_set'):
        request.safe_cookies_to_set = {}
    if isinstance(raw_max_age, (str, unicode)):
        int_c = re.search(r'\d+', raw_max_age)
        if int_c:
            value = int_c.group()
            max_age = int(value)
            if re.search(r'days?', raw_max_age):
                max_age *= 24*3600
            elif re.search(r'months?', raw_max_age):
                max_age *= 24*3600*30
            elif re.search(r'years?', raw_max_age):
                max_age *= 24*3600*365
    if max_age:
        try:
            max_age = int(max_age)
        except:
            max_age = 10*60
    else:
        max_age = None
    request.safe_cookies_to_set[k] = dict(value=signer.dumps(v), max_age=max_age)


def set_cookie(k, v, max_age=10*60):
    return save_cookie(k, v, max_age)


def get_cookie(k, max_age=None, is_pure=False): # 这里的max_age是服务端的判定
    try:
        raw_value = request.cookies.get(k)
        if is_pure: # 纯 cookie
            return raw_value
    except RuntimeError: # 基本上是因为request不能调用，因为当前不是web请求
        return ''
    if raw_value:
        try:
            return signer.loads(raw_value, max_age=max_age)
        except (BadTimeSignature, BadSignature):
            return
        except Exception:
            if sentry_client:
                sentry_client.captureException()
            return

def delete_cookies(*keys):
    if not hasattr(request, 'cookies_to_delete'):
        request.cookies_to_delete = []
    for key in keys:
        request.cookies_to_delete.append(key)


def set_cookies(response):
    # the value must dumps by singer
    # 在website.core中调用，after_request，可以处理安全性cookie的读写删除
    cookies_to_set = getattr(request, 'safe_cookies_to_set', {})
    for k, data in cookies_to_set.items():
        # 用expires, 而非max_age，这样可以重复set_cookie, 即使nano在proxy的情况下
        if 'max_age' in data and data['max_age'] is None: # 浏览器关闭时，失效
            response.set_cookie(k, data.get('value'))
        else:
            response.set_cookie(k, data.get('value'), expires=time.time()+data.get('max_age', 10*60))

    # delete the cookies
    cookies_to_delete = getattr(request, 'cookies_to_delete', [])
    for key in cookies_to_delete:
        if key not in cookies_to_set and key in request.cookies:
            response.delete_cookie(key)





