# coding: utf8
from flask import request, Response
from farbox_bucket.utils import string_types


# 把通过 request 中转的变量统一放在这里，避免四处调用时，未来再做调整，明晰一些
# request 和 g 很相似，采用 request 为了更自然一些
# 注意和 request 自带的一些变量，不要冲突


def get_context_value_from_request(key, force_dict=False, force_list=False, is_string=False):
    try: value = getattr(request, key, None)
    except: value = None
    if force_dict and not isinstance(value, dict):
        value = {}
    if force_list:
        if isinstance(value, tuple):
            value = list(value)
        elif not isinstance(value, list):
            value = []
    if is_string and not isinstance(value, string_types):
        value = None
    return value


def set_context_value_from_request(key, value):
    if not isinstance(key, string_types):
        return
    try: setattr(request, key, value)
    except: pass


def set_data_root_in_request(data_root):
    request.data_root = data_root

def get_data_root_in_request():
    return get_context_value_from_request("data_root", is_string=True)


def set_response_in_request(r):
    # 强制取代当前的 response 返回
    if isinstance(r, Response):
        request.response = r

def get_response_in_request():
    response = get_context_value_from_request("response")
    if isinstance(response, Response):
        return response

def set_error_description_in_request(error_description):
    # 404 的错误描述主要是
    request.error_description = error_description

def get_error_description_in_request():
    return get_context_value_from_request("error_description", is_string=True)

def set_response_content_type_in_request(response_content_type):
    request.response_content_type = response_content_type

def get_response_content_type_in_request():
    return get_context_value_from_request("response_content_type", is_string=True)

def set_response_code_in_request(response_code):
    request.response_code = response_code

def get_response_code_in_request():
    return get_context_value_from_request("response_code")



def set_url_prefix_in_request(prefix):
    request.url_prefix = prefix


def get_url_prefix_in_request():
    return get_context_value_from_request("url_prefix", is_string=True)


def set_not_cache_current_request():
    request.cache_strategy = "no"

def get_can_auto_cache_current_request():
    if getattr(request, "cache_strategy", None) == "no":
        return False
    else:
        return True



def get_i18n_data_from_request():
    i18n_data = getattr(request, 'i18n', {})
    if not isinstance(i18n_data, dict):
        i18n_data = {}
    return i18n_data


def set_i18n_data_to_request(key, value):
    i18n_data = getattr(request, "i18n", None)
    if not isinstance(i18n_data, dict):
        i18n_data = {}
        request.i18n = i18n_data
    request.i18n[key] = value


def is_in_request_context_list(key, value, auto_append=True):
    value_list = getattr(request, key, [])
    if not isinstance(value_list, list):
        value_list = []
    if value in value_list:
        return True
    else:
        if auto_append:
            value_list.append(value)
    if auto_append:
        setattr(request, key, value_list)
    return False


def is_resource_in_loads_in_page_already(resource):
    return is_in_request_context_list("loads_in_page", resource, auto_append=True)


def reset_loads_in_page_in_request():
    request.loads_in_page = []


def set_force_response_pre_handler(handler):
    request.force_response_pre_handler = handler


def pre_handle_force_response_in_context(content):
    force_response_pre_handler = getattr(request, 'force_response_pre_handler', None)
    if force_response_pre_handler and hasattr(force_response_pre_handler, '__call__'):
        try: content = force_response_pre_handler(content)
        except: pass
    return content


def set_logined_bucket_in_request(bucket, checked=False):
    request.logined_bucket = bucket
    if checked:
        set_logined_bucket_checked_in_request(checked=True)

def get_logined_bucket_in_request():
    return getattr(request, "logined_bucket", None)

def set_logined_bucket_checked_in_request(checked):
    # 表示 logined_bucket 在赋予的时候，校验过了
    request.logined_bucket_checked = checked

def get_logined_bucket_checked_in_request():
    return getattr(request, "logined_bucket_checked", False)


# pending_bucket 主要是通过 token 校验 bucket 的时候，token 内不带 bucket，可以从这里提取
def set_pending_bucket_bucket_in_request(bucket):
    request.pending_bucket = bucket

def get_pending_bucket_bucket_in_request():
    return getattr(request, "pending_bucket", None)


def set_site_in_request(bucket_configs):
    # 把 bucket_configs 作为 site 对象存在 request 里
    set_context_value_from_request("site", bucket_configs)

def get_site_in_request():
    return get_context_value_from_request("site", force_dict=True)



def set_no_html_inject_in_request(should=True):
    # 渲染 html 后续插入头尾的片段就不插入了
    request.no_html_inject = should

def get_no_html_inject_in_request():
    return get_context_value_from_request("no_html_inject")


def set_page_is_cached(is_cached=True):
    request.is_cached = is_cached

def get_page_is_cached():
    return getattr(request, 'is_cached', False)


def set_page_cache_key_in_request(cache_key):
    # for response
    if isinstance(cache_key, string_types):
        request.cache_key = cache_key


def get_page_cache_key_in_request():
    cache_key = getattr(request, "cache_key", None)
    if not isinstance(cache_key, string_types):
        cache_key = ""
    return cache_key


def set_doc_type_in_request(doc_type):
    if isinstance(doc_type, dict):
        doc_type = doc_type.get("_type") or doc_type.get("type")
    if isinstance(doc_type, string_types):
        request.doc_type = doc_type

def get_doc_type_in_request():
    return getattr(request, "doc_type", None)


def set_doc_path_in_request(doc_path):
    if isinstance(doc_path, dict):
        doc_path = doc_path.get("path")
    if isinstance(doc_path, string_types):
        request.doc_path = doc_path

def get_doc_path_in_request():
    return getattr(request, "doc_path", None)



def get_doc_in_request():
    doc = getattr(request, "doc", None)
    if not isinstance(doc, dict):
        doc = None
    return doc

def set_doc_in_request(doc):
    if doc and isinstance(doc, dict):
        request.doc = doc


def set_doc_type_and_path_in_request_by_context_doc(data_to_update=None):
    doc = get_doc_in_request()
    if not doc:
        return
    doc_type = doc.get('_type')
    doc_path = doc.get("path")
    set_doc_type_in_request(doc_type)
    set_doc_path_in_request(doc_path)
    if data_to_update and isinstance(data_to_update, dict):
        data_to_update["doc_type"] = doc_type
        data_to_update["doc_path"] = doc_path
