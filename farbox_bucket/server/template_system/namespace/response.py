# coding: utf8
from __future__ import absolute_import
from flask import request, g, abort, Response as FlaskResponse, send_file
import io
import re

from farbox_bucket.utils import smart_str, smart_unicode, to_int
from farbox_bucket.server.utils.cache_for_function import cache_result

from farbox_bucket.server.utils.response import force_redirect, force_response



class Response(object):
    def __init__(self):
        self.set_property_allowed = True


    def __setattr__(self, key, value):
        if key in ['type', 'content_type', 'mime_type', 'mimetype']:
            self.set_content_type(value)
        elif key in ['status_code', 'code', 'status']:
            self.set_status_code(value)
        # anyway
        self.__dict__[key] = value


    def __getattr__(self, item):
        if item in ['type', 'content_type', 'mime_type', 'mimetype']:
            return self.__dict__.get('type') or 'text/html'
        elif item in ['code', 'status', 'status_code']:
            return self.__dict__.get('code') or 200

    def set_content_type(self, content_type):
        if isinstance(content_type, basestring):
            content_type = smart_str(content_type)
            g.response_content_type = content_type
            self.__dict__['type'] = content_type
        return ''

    def set_type(self, content_type):
        return self.set_content_type(content_type)

    def set_status_code(self, code):
        code = to_int(code) or 200
        if code in [
            200, 201, 202, 203, 204, 205, 206,
            300, 301, 302, 303, 304, 305, 306, 307,
            400, 401, 402, 403, 404, 405, 406, 408, 409, 410]:
            g.response_code = code
            self.__dict__['code'] = code
        return ''

    @staticmethod
    def redirect(url, code=302, keep_site_id=True):
        force_redirect(url, code=code, keep_site_id=keep_site_id)


    @staticmethod
    def raise_404(description=''):
        if getattr(g, 'response', None):
            return 'not allowed because for other response existing'
        # 触发错误，由 render 这个函数处理错误，从而实现404页面
        if description:
            description = smart_unicode(description)
            g.error_description = description
        g.response_code = 404
        abort(404, description)

    @classmethod
    def raise404(cls, description=''):
        return cls.raise_404(description)

    def set_header(self, key, value):
        if isinstance(key, (str, unicode)) and len(key) < 50 and re.match('^[a-z0-9-_]+$', key, flags=re.I):
            value = smart_unicode(value)
            if not isinstance(getattr(g, 'user_response_headers', None), dict):
                g.user_response_headers = {}
            g.user_response_headers[key] = value
            return ''
        else:
            return 'this key is not allowed'

    def response(self, content, mime_type='text/html', as_file=False, **kwargs):
        # 相当于一个断点，直接拦截当前的 response 进行新的返回
        if as_file: # 作为附件发出
            file_response = send_file(io.BytesIO(content), mimetype=mime_type, **kwargs)
            content = file_response
        return force_response(content, mime_type)





@cache_result
def response():
    return Response()