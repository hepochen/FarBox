#coding: utf8
from __future__ import absolute_import

def apply_middleware(app, middleware):
    # 处理中间件 & before_request & after_request
    app.wsgi_app = middleware(app.wsgi_app)
    before_request = getattr(middleware, 'before_request',None)
    after_request = getattr(middleware, 'after_request',None)
    if before_request:
        app.before_request_funcs.setdefault(None,[]).append(before_request)
    if after_request:
        app.after_request_funcs.setdefault(None, []).append(after_request)



def apply_before_request(app, func):
    app.before_request_funcs.setdefault(None,[]).append(func)

def apply_after_request(app, func):
    app.after_request_funcs.setdefault(None,[]).append(func)