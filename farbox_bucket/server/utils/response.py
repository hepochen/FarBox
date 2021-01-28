# coding: utf8
import os
import ujson as json
from farbox_bucket.utils import smart_str, smart_unicode, get_md5, is_str
from flask import request, g, redirect, Response, abort, send_file, make_response
from farbox_bucket.utils.data import json_dumps
from farbox_bucket.utils.mime import guess_type
from farbox_bucket.utils.url import join_url, get_get_var


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
    if not isinstance(url, (str, unicode)):
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
        force_response_pre_handler = getattr(g, 'force_response_pre_handler', None)
        if force_response_pre_handler and hasattr(force_response_pre_handler, '__call__'):
            content = force_response_pre_handler(content)
    if isinstance(content, (str, unicode)):
        content = make_response(content)
    if isinstance(content, Response) and isinstance(mime_type, (str, unicode)):
        content.content_type = mime_type
    abort(422, content)


def force_redirect_error_handler_callback(error):  # 做跳转使用
    # 410 状态, 永久性不可用
    if isinstance(error.description, (str, unicode)):
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
    if not hasattr(g, 'more_headers'):
        g.more_headers = {}
    g.more_headers[k] = v

