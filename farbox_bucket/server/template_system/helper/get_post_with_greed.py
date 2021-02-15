# coding: utf8
import re, os
from farbox_bucket.utils import is_a_markdown_file, smart_unicode
from farbox_bucket.bucket.record.utils import get_path_from_record
from farbox_bucket.utils.url import get_get_var
from farbox_bucket.server.es.es_search import get_one_post_by_es
from farbox_bucket.bucket.utils import get_bucket_site_configs, get_bucket_in_request_context
from farbox_bucket.utils.path import get_just_name
from farbox_bucket.server.utils.request_context_vars import get_data_root_in_request, get_doc_in_request
from farbox_bucket.server.utils.cache_for_function import cache_result
from farbox_bucket.server.template_system.namespace.data import data as get_data_namespace


@cache_result
def get_current_data_root():
    bucket = get_bucket_in_request_context()
    if not bucket:
        return ""
    data_root = get_data_root_in_request()
    if data_root:
        return data_root
    site_configs = get_bucket_site_configs(bucket)
    if site_configs:
        data_root = smart_unicode(site_configs.get("posts_root") or "").strip().strip("/")
        return data_root
    else:
        return ""




# todo 在 post 编译后 更新 bucket 的时候，是否也要进行 greedy 的匹配呢？
@cache_result
def get_post_with_greed(url_body, parent_doc=None):
    pure_url_body = re.split("[?#]", url_body)[0]
    post_url = pure_url_body
    d = get_data_namespace()
    post_doc = d.get_doc(post_url)
    current_data_root = get_current_data_root()
    parent_doc = parent_doc or get_doc_in_request()
    if not post_doc and is_a_markdown_file(post_url) and parent_doc and isinstance(parent_doc, dict):
        filename = post_url
        if "/post/" in filename:
            filename = filename.split("/post/", 1)[-1]
        parent_post_doc_path = get_path_from_record(parent_doc)
        if parent_post_doc_path:
            post_doc_parent = os.path.split(parent_post_doc_path)[0]
            if post_doc_parent:
                abs_path = "%s/%s" % (post_doc_parent.strip("/"), filename.strip("/"))
                post_doc = d.get_doc_by_path(abs_path)

        if current_data_root and not post_doc:  # 增加 wiki_root 作为前缀，再尝试匹配
            abs_path = "%s/%s" % (current_data_root, filename.strip("/"))
            post_doc = d.get_doc_by_path(abs_path)

    if not post_doc:  # 尝试 hit keyword 的方式进行搜索匹配
        bucket = get_bucket_in_request_context()
        post_name = (get_get_var(url_body, "name") or "").strip()
        if post_name:
            if "." in post_name:
                post_name = os.path.splitext(post_name)[0]
            post_doc = get_one_post_by_es(bucket, keywords=post_name, under=current_data_root)
        if not post_doc and is_a_markdown_file(post_url): # 直接搜索 filename
            just_post_file_name = get_just_name(post_url)
            if just_post_file_name != post_name:
                post_doc = get_one_post_by_es(bucket, keywords=just_post_file_name, under=current_data_root)
    return post_doc

