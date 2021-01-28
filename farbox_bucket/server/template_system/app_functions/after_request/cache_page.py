# coding: utf8
import datetime
import pickle
import re
from flask import g, request, Response
from farbox_bucket.server.utils.request import get_language
from farbox_bucket.utils import get_value_from_data, get_md5
from farbox_bucket.bucket.utils import get_bucket_last_updated_at, get_bucket_site_configs
from farbox_bucket.utils.memcache import get_cache_client


def get_cache_key_for_page():
    bucket = getattr(g, 'bucket', None)
    if not bucket:
        return
    bucket_last_updated_at = get_bucket_last_updated_at(bucket)
    if not bucket_last_updated_at:
        return
    url = request.url
    raw_cache_key = '%s-%s-%s' % (bucket, bucket_last_updated_at, url)
    lang = get_language()
    if lang:
        raw_cache_key += "-%s"%lang
    cache_key = "page-%s" % get_md5(raw_cache_key)
    return cache_key



def should_hit_cache_in_site():
    if request.method != 'GET':
        return False
    if request.path.startswith("/__") and not request.path.startswith("/__page/"):
        return False
    cache_strategy = getattr(g, 'cache_strategy', 'yes')
    if cache_strategy in ['no']:
        return False
    return True # at last


def response_to_render_data(response):
    # 获得的 render_data 主要是为了缓存的作用

    # 先处理一些不用缓存的情况
    if getattr(g, 'is_cached', False): # 本身就是缓存逻辑
        return
    if response.status_code not in [200]:
        # 不在缓存的范围内
        return
    if not should_hit_cache_in_site():
        return

    if response.is_streamed:
        return

    render_data = dict(
        content = response.data, # str 类型的数据
    )

    doc = getattr(g, 'doc', None) # 当前的上下文文档
    if doc and isinstance(doc, dict):
        g.doc_type = render_data['doc_type'] = doc.get('_type')
        g.doc_path = render_data['doc_path'] = doc.get('path')


    if request.path == '/feed': # /feed是application/xml
        content_type = 'application/xml'
    else:
        content_type = response.mimetype or response.default_mimetype

    render_data['content_type'] = content_type
    render_data['url'] = request.url

    render_data['user_response_headers'] = getattr(g, 'user_response_headers', {})


    return render_data


def cache_response_into_memcache(response):
    from farbox_bucket.server.web_app import sentry_client
    cache_client = get_cache_client()
    if not cache_client:
        return response
    bucket = getattr(g, 'bucket', None)
    if not bucket:
        return response

    render_data = response_to_render_data(response)
    if render_data:  # 尝试缓存到 memcache 里
        cache_expiration_time = 2 * 3600 # 2小时的缓存期
        cache_key = get_cache_key_for_page()  # 得到缓存的 key 值
        if not cache_key:
            return response
        to_cache = pickle.dumps(render_data)
        cache_client.set(cache_key, to_cache, zipped=True, expiration=cache_expiration_time)

        if sentry_client: # for debug
            cached_data = cache_client.get(cache_key, zipped=True)
            try:
                if cached_data and isinstance(cached_data, (str, unicode)) and re.match(r'^\d$', cached_data):
                    raise TypeError("meme cache error?")
            except:
                sentry_client.captureException()
    return response


def get_response_from_memcache():
    # 从 memcache 中直接获得 response
    from farbox_bucket.server.web_app import sentry_client
    should_hit_cache = should_hit_cache_in_site()
    if not should_hit_cache:
        return
    cache_client = get_cache_client()
    if not cache_client:
        return
    cache_key = get_cache_key_for_page()
    if cache_key:
        cached_data = cache_client.get(cache_key, zipped=True)
        if cached_data:
            try:
                render_data = pickle.loads(cached_data)
                g.user_response_headers = render_data.get('user_response_headers') or getattr(g, 'user_response_headers', {})
                # 校验一次，保证url一致，避免缓存串了（万一）
                cached_url = render_data.pop('url', None)
                if cached_url != request.url:
                    return
                g.cache_key = cache_key
                g.doc_type = render_data.get('doc_type')
                g.doc_path = render_data.get('doc_path')
                response = Response(render_data.pop('content', None), mimetype=render_data.pop('content_type', None))
                for k, v in render_data.items():
                    setattr(g, k, v)
                g.is_cached = True
                return response
            except Exception as e:
                if sentry_client:
                    sentry_client.captureException()