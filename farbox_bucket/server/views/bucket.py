#coding: utf8
import re
import ujson as json
from flask import abort, request, Response, redirect

from farbox_bucket.server.web_app import app
from farbox_bucket.utils.env import get_env
from farbox_bucket.utils.ssdb_utils import hscan
from farbox_bucket.utils.web_utils.response import jsonify
from farbox_bucket.utils.web_utils.request import to_per_page

from farbox_bucket.bucket import get_bucket_full_info, is_valid_bucket_name
from farbox_bucket.bucket.token.utils import get_logined_bucket_by_token, get_logined_bucket
from farbox_bucket.bucket.helper.files_related import auto_update_bucket_and_get_files_info

from farbox_bucket.bucket.utils import get_bucket_configs, get_bucket_name_for_path, get_buckets_size, get_bucket_site_configs
from farbox_bucket.bucket.private_configs import get_bucket_private_config
from farbox_bucket.bucket.template_related.bucket_template_web_api import show_bucket_pages_configs_by_web_api
from farbox_bucket.bucket.domain.web_utils import get_bucket_from_request

from farbox_bucket.server.static.static_render import send_static_frontend_resource
from farbox_bucket.server.bucket_render.render import render_bucket
from farbox_bucket.server.backend.status.server_status import get_server_status_bucket
from farbox_bucket.server.helpers.bucket import show_bucket_records_for_web_request
from farbox_bucket.server.utils.response import p_redirect
from farbox_bucket.server.utils.request_context_vars import set_pending_bucket_bucket_in_request, set_site_in_request




def allowed_to_display_some_bucket_info(bucket=None):
    if bucket:
        set_pending_bucket_bucket_in_request(bucket) # 校验用的
    logined_bucket = get_logined_bucket_by_token()
    if not logined_bucket:
        raw_token = request.values.get("api_token") or request.values.get("token") or ""
        if raw_token:
            endpoint_password = get_env("endpoint_password")
            if endpoint_password and endpoint_password == raw_token:
                return True
    if not logined_bucket:
        logined_bucket = get_logined_bucket()  # try again, by cookie
    if logined_bucket and logined_bucket == bucket:
        return True
    return False


@app.route('/__theme', methods=['POST', 'GET'])
def show_bucket_theme():
    bucket = request.values.get("bucket") or get_bucket_from_request()
    return show_bucket_pages_configs_by_web_api(bucket)


@app.route('/bucket/<bucket>/configs_for_<configs_type>')
def show_bucket_configs(bucket, configs_type):
    if configs_type in ["order", "sort", "sorts"]:
        configs_type = "orders"
    if not allowed_to_display_some_bucket_info(bucket):
        return abort(404, "token not valid")
    if configs_type == "files":
        configs = auto_update_bucket_and_get_files_info(bucket)
    else:
        configs = get_bucket_configs(bucket, configs_type) or {}
    return jsonify(configs)



@app.route('/bucket/<bucket>/paths', methods=['POST', 'GET'])
def list_bucket_paths(bucket):
    if not allowed_to_display_some_bucket_info(bucket):
        return abort(404, "token not valid")
    path_bucket = get_bucket_name_for_path(bucket)
    pre_record_id = request.values.get('cursor')
    per_page = to_per_page(200, request.values.get('per_page'), max_per_page=1000)
    records = hscan(path_bucket, key_start=pre_record_id, limit=per_page)
    return jsonify(records)



@app.route('/bucket/<bucket>/info')
def show_bucket_info(bucket):
    if not is_valid_bucket_name(bucket):
        abort(404, 'no bucket found')
    bucket_info = get_bucket_full_info(bucket)

    # 过滤掉一些敏感信息
    bucket_configs = bucket_info.get('configs')
    if bucket_configs:
        bucket_configs.pop('public_key', None)
    bucket_user_configs = bucket_info.get('user_configs')
    if bucket_user_configs:
        for k in list(bucket_user_configs.keys()):
            if k.endswith('password'):
                bucket_user_configs.pop(k, None)

    data = json.dumps(bucket_info, indent=4)

    response = Response(data, mimetype='text/plain')

    return response



# 需要 API TOKEN 的校验
default_records_per_page = 100
@app.route('/bucket/<bucket>/list', methods=['POST', 'GET'])
def list_bucket(bucket):
    set_pending_bucket_bucket_in_request(bucket) # 校验用的
    return show_bucket_records_for_web_request(default_records_per_page=default_records_per_page, includes_zero_ids=True)


################# for web pages starts ##########


@app.route('/_the_server_status')
def show_server_stats_bucket():
    status_bucket = get_server_status_bucket()
    if not status_bucket:
        abort(404, 'server_status not found')
    else:
        return p_redirect('/bucket/%s/web/' % status_bucket)


@app.route('/bucket/<bucket>/web/', methods=['POST', 'GET'])
@app.route('/bucket/<bucket>/web/<path:web_path>', methods=['POST', 'GET'])
def bucket_web(bucket, web_path=''):
    return render_bucket(bucket, web_path)



@app.route('/', methods=['POST', 'GET'])
@app.route('/<path:web_path>', methods=['POST', 'GET'])
def bucket_web_for_independent_domain(web_path=''):
    # 跟 bucket web 一样， 但是呈现的是独立域名， 放到最后被 app.route 添加，以避免影响其它 view 的逻辑
    # 系统自带的前端资源
    if re.match("/(_system|admin|service|bucket)/", request.path):
        abort(404, "custom url is not allowed to startswith (_system|admin|service|bucket)")
    frontend_response = send_static_frontend_resource()
    if frontend_response:
        return frontend_response
    if not web_path and not get_buckets_size():
        # 还没有 bucket 的时候，允许用户进行安装的操作
        return p_redirect("/__create_bucket?code=admin")
    bucket = get_bucket_from_request()
    if bucket:
        if request.path in ['/robot.txt', '/robots.txt']:
            if not get_bucket_private_config(bucket, "enable_web_robots", default=True):
                # 禁用爬虫
                robot_content = 'User-agent: *\nDisallow: /'
                return Response(robot_content, mimetype='text/plain')
        if request.url.startswith("http://") and get_bucket_private_config(bucket, "enable_https_force_redirect", default=False):
            # 强制跳转 https， 不用永久 301 code，避免用户自己切换后不成功
            return redirect(request.url.replace('http://', 'https://', 1), code=302)
        set_site_in_request(get_bucket_site_configs(bucket))
        return render_bucket(bucket, web_path)
    else:
        abort(404, 'no bucket found')


################# for web pages ends ##########