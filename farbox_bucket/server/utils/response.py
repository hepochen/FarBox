# coding: utf8
import os, re
import ujson as json
from flask import request, redirect, Response, abort, send_file, make_response
from farbox_bucket.settings import DEBUG
from farbox_bucket.utils import smart_str, smart_unicode, string_types, get_md5, is_str
from farbox_bucket.utils.data import json_dumps
from farbox_bucket.utils.mime import guess_type
from farbox_bucket.utils.url import join_url, get_get_var
from farbox_bucket.server.utils.request_context_vars import pre_handle_force_response_in_context
from farbox_bucket.utils.convert.jade2jinja import jade_to_template


def _handle_redirect_url(url, keep_site_id=True):
    if url.startswith('?'):
        url = request.path + url
    protocol = request.environ.get('HTTP_X_PROTOCOL') or 'http'
    if protocol == 'https':
        if not url.startswith('http://') and not url.startswith('https://'):
            # 相对路径
            url = 'https://%s/%s' % (request.host, url.lstrip('/'))
        elif url.startswith('http://'):
            # 绝对路径
            url = url.replace('http://', 'https://', 1)

    if keep_site_id:
        # 保留 site_id
        if request.args.get('site_id'):
            if 'site_id=' not in url:
                url = join_url(url, site_id=request.args.get('site_id'))
        elif request.referrer:
            site_id_in_referrer = get_get_var(request.referrer, 'site_id')
            if site_id_in_referrer:
                if 'site_id=' not in url:
                    url = join_url(url, site_id=site_id_in_referrer)

    return url



def jsonify(data):
    try:
        data = json_dumps(data)
    except:
        data = json.dumps(dict(error='json_error'))
    response = Response(data, mimetype='application/json')
    return response


def send_plain_text(text):
    response = Response(text, mimetype='text/plain')
    return response


def p_redirect(url, *args, **kwargs):
    # 保证从https的url中跳转也是https的
    url = _handle_redirect_url(url)
    return redirect(url, *args, **kwargs)


def force_redirect(url, *args, **kwargs):
    if not isinstance(url, string_types):
        return ''
    keep_site_id = kwargs.pop('keep_site_id', True)
    url = _handle_redirect_url(url, keep_site_id)
    # 通过error 410的跳转来实现
    if not args and not kwargs: # just url
        abort(410, url)
    redirect_s = json.dumps(dict(url=url, args=args, kwargs=kwargs))
    abort(410, redirect_s)


def force_response(content, mime_type='text/html'):
    # 相当于一个断点，直接拦截当前的 response 进行新的返回
    if isinstance(content, Response): # 已经是 response 了
        abort(422, content)
    if isinstance(content, (dict, list, tuple)):
        try:
            content = json.dumps(content)
            if not mime_type or mime_type == 'text/html':
                mime_type = 'application/json'
        except:
            content = smart_unicode(content)
    else:
        content = smart_unicode(content)
        content = pre_handle_force_response_in_context(content)
    if isinstance(content, string_types):
        content = make_response(content)
    if isinstance(content, Response) and isinstance(mime_type, string_types):
        content.content_type = mime_type
    abort(422, content)


def force_redirect_error_handler_callback(error):  # 做跳转使用
    # 410 状态, 永久性不可用
    if isinstance(error.description, string_types):
        url = error.description
        if url.startswith('{'):
            try:
                redirect_data = json.loads(url)
                url = redirect_data.get('url') or '/'
                args = redirect_data.get('args') or ()
                kwargs = redirect_data.get('kwargs') or {}
                return p_redirect(url, *args, **kwargs)
            except:
                pass
        # at last if not redirect correctly
        return p_redirect(url)
    else:
        return error.description


ERROR_MESSAGES = {
    503: 'Wait for a Moment, and Try Again.',
    400: 'Bad Request',
    401: 'You Need to Login Now.',
    404: 'Page not Found or this Request is not Allowed',
}

def json_if_error(code, message=''):
    message = message or ERROR_MESSAGES.get(code, '')
    result = dict(error_code=code, message=message)
    response = make_response(jsonify(result))
    response.status_code = code
    return response



def is_doc_modified(doc, date_field='date'):
    if not doc:
        return True
    #if request.environ.get('HTTP_PRAGMA') in ['no-cache']:
    #    return True
    if request.environ.get('HTTP_CACHE_CONTROL') in ['no-cache']:
        return True
    if date_field in doc:
        date = smart_str(doc[date_field])
        date_in_request = request.environ.get('HTTP_IF_MODIFIED_SINCE')
        if date_in_request:
            if smart_str(date_in_request)== date: # and request.cache_control.max_age
                return False
    return True


def get_304_response():
    # 仅仅给出一个空 response
    response = make_response('')
    response.status_code = 304
    return response


def get_status_response(error_info='', status_code=404):
    error_info = error_info or 'not found'
    response = Response(error_info)
    response.status_code = status_code
    return response

def set_304_response_for_doc(doc, response, date_field='date', etag=None):
    if date_field in doc:
        date = smart_str(doc[date_field])
        response.headers['Last-Modified'] = date
        if etag:
            response.set_etag(etag)
    return response


def is_filepath_modified(filepath):
    try:
        mtime = int(os.path.getmtime(filepath))
        if request.environ.get('HTTP_CACHE_CONTROL') in ['no-cache']:
            return True
        date_in_request = request.environ.get('HTTP_IF_MODIFIED_SINCE')
        try:
            date_in_request = int(date_in_request)
            if date_in_request == mtime:
                return False
        except:
            pass
    except:
        pass
    # at last
    return True



def send_file_with_304(filepath, mimetype=None):
    if not os.path.isfile(filepath):
        return # ignore
    if not is_filepath_modified(filepath):
        return get_304_response()
    else:
        mimetype = mimetype or guess_type(filepath, 'application/octet-stream')
        response = send_file(filepath, mimetype=mimetype)
        try:
            mtime = int(os.path.getmtime(filepath))
            response.headers['Last-Modified'] = smart_str(mtime)
        except:
            pass
        return response


def add_response_header(k, v):
    if not hasattr(request, 'more_headers'):
        request.more_headers = {}
    request.more_headers[k] = v



def set_more_headers_for_response(response):
    more_headers = getattr(request, 'more_headers', None) or {}
    if not isinstance(more_headers, dict):
        return
    for k, v in more_headers.items():
        if isinstance(k, string_types) and isinstance(v, string_types) and k not in response.headers:
            k = smart_str(k)
            v = smart_str(v)
            response.headers[k] = v



def get_user_response_headers():
    headers = getattr(request, 'user_response_headers', {})
    if not isinstance(headers, dict):
        headers = {}
    return headers

def set_user_response_headers(user_headers=None):
    # 直接赋值的情况
    if user_headers and isinstance(user_headers, dict):
        request.user_response_headers = user_headers



def set_user_headers_for_response(response):
    # 用户通过模板 API 设定的 headers, 给出到 response
    user_response_headers = getattr(request, 'user_response_headers', {})
    if not isinstance(user_response_headers, dict):
        return
    for k, v in user_response_headers.items():
        if isinstance(k, string_types) and isinstance(v, string_types) and k not in response.headers:
            k = smart_str(k)
            v = smart_str(v)
            response.headers[k] = v


def set_user_header_for_response(key, value):
    # 这是设定的逻辑，主要是 template api 中调用
    if isinstance(key, string_types) and len(key) < 50 and re.match('^[a-z0-9-_]+$', key, flags=re.I):
        value = smart_unicode(value)
        if not isinstance(getattr(request, 'user_response_headers', None), dict):
            request.user_response_headers = {}
        request.user_response_headers[key] = value
        return True
    else:
        return False





local_jade_templates = {}
def render_jade_template(template_filepath, after_render_func=None, *args, **kwargs):
    from farbox_bucket.server.template_system.env import farbox_bucket_env
    # 主要渲染本地的模板文件，可以传入一个env，这样可以确定模板的root
    global local_jade_templates

    env = kwargs.pop('env', None) or farbox_bucket_env

    if template_filepath in local_jade_templates and not DEBUG:
        template = local_jade_templates.get(template_filepath)
    else:
        if not os.path.isfile(template_filepath):
            return # 模板文件不存在, ignore
        with open(template_filepath) as f:
            source = f.read()

        template = None

        if DEBUG:
            template_md5 = get_md5(source)
            if template_md5 in local_jade_templates: # 文件实际上是缓存了的
                template = local_jade_templates.get(template_md5)

        template = template or jade_to_template(source, env=env)

        #if DEBUG:
            #print template.source

        local_jade_templates[template_filepath] = template

        if DEBUG:
            template_md5 = get_md5(source)
            local_jade_templates[template_md5] = template

    return_html = kwargs.pop('return_html', False)
    html_source = template.render(*args, **kwargs)
    if after_render_func:
        html_source = after_render_func(html_source)
    if return_html:
        return '\n'+html_source
    else:
        response = make_response(html_source)
        return response




default_jade_source_cache_space = {}
def render_jade_source(source, cache_key=None, cache_space=None, env=None, **kwargs):
    # 返回的是 html 源码, 指定一个 source，直接进行 compile
    # env 是当前的环境
    # cache_key 是缓存 key，如果没有指定，则是源码的 md5 值
    # cache_space 是缓存的存储空间
    if not cache_key:
        cache_key = get_md5(source)
    if cache_space is None or not isinstance(cache_space, dict):
        cache_space  = default_jade_source_cache_space

    if cache_key in cache_space:
        template = cache_space[cache_key]
    else:
        template = jade_to_template(source, env=env)
        cache_space[cache_key] = template
    html = template.render(**kwargs)
    return html