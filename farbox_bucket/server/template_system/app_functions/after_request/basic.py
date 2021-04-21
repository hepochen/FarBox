# coding: utf8
from flask import request
import uuid
from farbox_bucket.utils import smart_str
from farbox_bucket.server.utils.cookie import set_cookies, get_cookie, set_cookie
from farbox_bucket.server.utils.response import set_more_headers_for_response, set_user_headers_for_response
from farbox_bucket.server.utils.request_context_vars import get_page_cache_key_in_request,\
    get_response_code_in_request, get_response_content_type_in_request, get_response_in_request

one_year_seconds = 365 * 24 * 60 * 60

def default_response_handler(response):
    # request.response 是最优先处理的
    response_in_request = get_response_in_request()
    response = response_in_request or response

    # 确保有 vid 这个 cookie
    visitor_id = get_cookie('vid')
    if not visitor_id:
        visitor_id = uuid.uuid1().hex
        set_cookie('vid', visitor_id, max_age=5 * one_year_seconds)

    # 系统中调用产生的 header
    set_more_headers_for_response(response)

    # 用户通过模板 API 设定的 headers
    set_user_headers_for_response(response)


    r_code = get_response_code_in_request()
    if r_code:
        response.status_code = r_code

    r_type = get_response_content_type_in_request()
    if r_type:
        response.content_type = r_type

    cache_key = get_page_cache_key_in_request()
    if cache_key:
        response.headers['x-cache-key'] = smart_str(cache_key)

    emails_sent_info = getattr(request, "emails_sent_info", None)
    if emails_sent_info:
        response.headers['x-emails-sent'] = smart_str(emails_sent_info)

    if response.status_code > 400:
        return response

    ## 尝试缓存
    #cache_response_into_memcache(response)

    # 最后再处理 cookies，一些行为（比如统计）可能会产生新的 cookie
    set_cookies(response)

    return response