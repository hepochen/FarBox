# coding: utf8
import uuid
from farbox_bucket.utils import smart_str
from farbox_bucket.server.utils.cookie import set_cookies, get_cookie, set_cookie
from flask import g

one_year_seconds = 365 * 24 * 60 * 60

def default_response_handler(response):
    # 如果有g.response, 则 g.response 是最优先处理的
    g_response = getattr(g, 'response', None)
    response = g_response or response

    # 确保有 vid 这个 cookie
    visitor_id = get_cookie('vid')
    if not visitor_id:
        visitor_id = uuid.uuid1().hex
        set_cookie('vid', visitor_id, max_age=5 * one_year_seconds)

    # getattr(g, 'user_response_headers', {})
    more_headers = getattr(g, 'more_headers', None) or {}
    for k, v in more_headers.items():
        if isinstance(k, (str, unicode)) and isinstance(v, (str, unicode)) and k not in response.headers:
            k = smart_str(k)
            v = smart_str(v)
            response.headers[k] = v

    # 用户通过模板 API 设定的 headers
    user_response_headers = getattr(g, 'user_response_headers', {})
    for k, v in user_response_headers.items():
        if isinstance(k, (str, unicode)) and isinstance(v, (str, unicode)) and k not in response.headers:
            k = smart_str(k)
            v = smart_str(v)
            response.headers[k] = v


    if getattr(g, 'response_code', None):
        response.status_code = g.response_code

    if getattr(g, 'response_content_type', None):
        response.content_type = g.response_content_type

    cache_key = getattr(g, 'cache_key', None)
    if cache_key:
        response.headers['x-cache-key'] = smart_str(cache_key)

    if response.status_code > 400:
        return response

    ## 尝试缓存
    #cache_response_into_memcache(response)

    # 最后再处理 cookies，一些行为（比如统计）可能会产生新的 cookie
    set_cookies(response)

    return response