#coding: utf8
from __future__ import absolute_import
from flask import Flask
from farbox_bucket.settings import sentry_client
from raven.contrib.flask import Sentry
from farbox_bucket.utils import smart_str, is_str
from farbox_bucket.server.utils.response import get_status_response
from farbox_bucket.server.template_system.app_functions.before_and_after_request.time_cost import time_cost_handler
from farbox_bucket.server.template_system.app_functions.utils import apply_after_request, apply_before_request
from farbox_bucket.server.template_system.app_functions.after_request.basic import default_response_handler
from farbox_bucket.server.template_system.app_functions.after_request.cache_page import cache_response_into_memcache
from farbox_bucket.server.template_system.app_functions.before_request.basic import basic_before_request
from farbox_bucket.server.statistics.after_request import after_request_func_for_statistics
from farbox_bucket.server.template_system.app_functions.before_request.site_visitor_password import site_visitor_password_before_request
from farbox_bucket.server.utils.request_context_vars import get_context_value_from_request

# patch context resolver
from farbox_bucket.server.template_system.template_system_patch import patch_context; patch_context()

try:
    from gunicorn.http.wsgi import InvalidHeader
except:
    class InvalidHeader(Exception):
        pass


class FarBoxBucketFlask(Flask):
    def get_send_file_max_age(self, name):
        if get_context_value_from_request("is_template_resource"): # template static resource, 10 minutes
            return 10*60
        if get_context_value_from_request("is_static_file"): # 3 hours
            return 3 * 60 * 60
        if get_context_value_from_request("is_system_static_file"): # 10 days
            return 10 * 24 * 60 * 60
        return 60
        #return Flask.get_send_file_max_age(self, name)

    def send_static_file(self, filename): # static file 保证使用纯英文状态的
        filename = smart_str(filename)
        if not is_str(filename): #  fb_static 下会有路径, 别人渗透 password 的
            not_found_response = get_status_response(status_code=404)
            return not_found_response
        return Flask.send_static_file(self, filename)


    def wsgi_app(self, environ, start_response):
        try:
            return Flask.wsgi_app(self, environ, start_response)
        except InvalidHeader:
            response = get_status_response('InvalidHeader', status_code=500)
            return response(environ, start_response)
        except:
            sentry_client.captureException()
            response = get_status_response('unknown request error', status_code=500)
            return response(environ, start_response)

app = FarBoxBucketFlask(__name__, static_url_path='/___flask_static')

if sentry_client:
    sentry = Sentry(app, sentry_client)

apply_before_request(app, basic_before_request)
apply_before_request(app, site_visitor_password_before_request)
apply_before_request(app, time_cost_handler)
apply_after_request(app, time_cost_handler)
apply_after_request(app, cache_response_into_memcache)

apply_after_request(app, default_response_handler)

apply_after_request(app, after_request_func_for_statistics)

# handle 500 errors
from farbox_bucket.server.template_system.errors import *

# load my_farbox_bucket views first
try:
    from my_farbox_bucket import *
except:
    pass


# load views
## system views
from farbox_bucket.server.views.system import *
from farbox_bucket.server.views.install_ssl import *
## other views
from farbox_bucket.server.views.api import *
from farbox_bucket.server.views.for_admin import *
from farbox_bucket.server.views.my import *
from farbox_bucket.server.views.file_manager import *

# 3rd clouds
from farbox_bucket.clouds.wechat.views import *

from farbox_bucket.server.views.wiki_link_fallback import *

# last one
from farbox_bucket.server.views.bucket import *

from farbox_bucket.server.utils.verification_code import show_verification_code_by_url
from farbox_bucket.server.comments.add import add_new_comment_web_view