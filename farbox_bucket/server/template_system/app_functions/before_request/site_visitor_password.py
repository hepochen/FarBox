# coding: utf8
import re
from flask import request, redirect, abort

from farbox_bucket.utils import get_value_from_data, string_types
from farbox_bucket.utils.mime import guess_type
from farbox_bucket.bucket.private_configs import get_bucket_private_configs_by_keys
from farbox_bucket.bucket.domain.web_utils import get_bucket_from_request
from farbox_bucket.server.template_system.api_template_render import render_api_template_as_response
from farbox_bucket.server.utils.cookie import save_cookie, get_cookie
from farbox_bucket.server.utils.request_context_vars import set_not_cache_current_request



def check_site_visitor_password_allowed():
    bucket = get_bucket_from_request()
    if not bucket:
        return True
    private_configs = get_bucket_private_configs_by_keys(bucket, ["enable_visit_passwords", "visit_passwords"])
    if not private_configs.get("enable_visit_passwords"):
        return True
    visit_passwords = private_configs.get("visit_passwords")
    if not visit_passwords or not isinstance(visit_passwords, (list, tuple)):
        return True
    # 开始校验了
    if request.method == 'POST': # 页面 POST 请求
        password_to_check = request.form.get('password', '')
    else:
        password_to_check = get_cookie("visitor_password")
    request_path_lower = request.path.lower()
    for visit_password_data in visit_passwords:
        if not isinstance(visit_password_data, dict):
            continue
        path = visit_password_data.get("path")
        password = visit_password_data.get("password")
        if isinstance(path, string_types) and isinstance(path, string_types):
            path = path.strip("/").lower()
            if request_path_lower.startswith("/%s" % path):
                # 命中了，需要匹配密码
                if password_to_check == password:
                    return True
                else:
                    return False
    return True





def site_visitor_password_before_request():
    if request.path.startswith("/__"):
        return
    if re.match("/(_system|admin|service|bucket)/", request.path):
        return
    if request.path.strip("/") in ["login", "admin", "logout"]:
        return
    if guess_type(request.path) in ['text/css', 'text/scss', 'text/sass', 'text/less', 'application/json',
                                    'application/javascript']:
        return

    # 授权校验
    if request.method == 'POST' and request.args.get("before_request_check_type") == "site_visitor_password":
        if check_site_visitor_password_allowed():
            # 保存到 cookie, 30天有效期
            password_from_request = request.form.get('password', '')
            save_cookie('visitor_password', password_from_request, max_age=30 * 24 * 60 * 60)
            redirect_url = '%s?by=visitor_password' % request.path
            return redirect(redirect_url)

    if not check_site_visitor_password_allowed():
        set_not_cache_current_request()
        try:
            response = render_api_template_as_response("site_visitor_password.jade")
            if response:
                return response
        except:
            pass
        abort(404)




