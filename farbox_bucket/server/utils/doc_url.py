# coding: utf8
from farbox_bucket.utils import string_types, smart_unicode
from farbox_bucket.bucket.record.utils import get_path_from_record
from farbox_bucket.server.utils.site_resource import get_site_config
from farbox_bucket.server.utils.request_path import auto_bucket_url_path
from farbox_bucket.utils.path import get_relative_path
from farbox_bucket.utils.url import get_url_without_prefix



def get_doc_url(doc):
    if not isinstance(doc, dict):
        return ''
    if not doc:
        return ''
    url = ''
    # 主要处理日志的 url 这个属性
    if 'url_path' in doc and doc.get('_type')=='post':
        hide_post_prefix = get_site_config('hide_post_prefix', default_value=False)
        if hide_post_prefix:
            url = '/' + doc['url_path']
        else:
            url = '/post/' + doc['url_path']
    elif doc.get('_type') in ['file', 'image'] and doc.get('path'):
        url = '/' + doc['path']
    if not url: # last
        url = doc.get('url') or ''
    if url:
        url = auto_bucket_url_path(url)
    return url


def get_post_url_with_url_path(doc, url_prefix=None, url_root=None, hit_url_path=False):
    # 如果没有 url_prefix 的前提下，& hit_url_path = True 的时候，走系统逻辑的 post.url 的逻辑
    # 相当于  get_doc_url &  get_doc_url_for_template_api 的混合
    if not doc or not isinstance(doc, dict):
        return ""
    doc_url_path = doc.get("url_path")
    if not hit_url_path or not doc_url_path or not isinstance(doc_url_path, string_types):
        return get_doc_url_for_template_api(doc, url_prefix=url_prefix, url_root=url_root, hit_url_path=False)
    else:
        url_prefix = smart_unicode(url_prefix or "")
        if url_prefix:
            post_url = "/%s/%s"%(url_prefix.strip("/"), doc_url_path.strip("/"))
        else:
            post_url = get_doc_url(doc)
        return post_url



def get_doc_url_for_template_api(doc, url_prefix, url_root=None, hit_url_path=False):
    # hit_url_path=True 的时候，post 上有 url_path， 但跟 post.url 直接调用的逻辑不亦一样
    # post.url 相当于有一个动态的 url_prefix
    if not doc or not isinstance(doc, dict):
        return ""
    if not isinstance(url_prefix, string_types):
        return ""
    if url_root and not isinstance(url_root, string_types):
        return ""
    url_prefix = url_prefix.strip("/")
    doc_path = get_path_from_record(doc)
    if not doc_path:
        return ""
    url_path = ""
    if hit_url_path:
        url_path = smart_unicode(doc.get("url_path") or "").strip("/")
    if url_path:
        return "/%s/%s" % (url_prefix, url_path)
    if not url_root or not isinstance(url_root, string_types):
        return "/%s/%s" % (url_prefix, doc_path)
    else:
        relative_path = get_relative_path(doc_path.lower(), url_root.lower(), return_name_if_fail=False)
        if not relative_path:
            return "/%s/%s" % (url_prefix, doc_path)
        else:
            return "/%s/%s" % (url_prefix, relative_path)