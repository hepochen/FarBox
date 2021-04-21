#coding: utf8
from __future__ import absolute_import
from farbox_bucket.server.utils.cache_for_function import cache_result
from .data import data, paginator, get_data
from .request import request
from .html import html, Html
from .post import posts, post
from .site import site
from .response import response
from .bucket import bucket

namespace_functions = {
    'd': data,
    'data': data,
    'request': request,
    'html': html,
    'h': html,
    'paginator': paginator,
    'post': post,
    'posts': posts,
    'p': posts,
    'site': site,
    'response': response,
    'bucket': bucket,
    'b': bucket,
}



# shortcuts


@cache_result
def i18n(key, *args): # i18n 专用函数名
    return Html.i18n(key, *args)


namespace_shortcuts = {
    "_": i18n,
    "i18n": i18n,
    "get_data": get_data,
    "load": Html.load

}
