#coding: utf8
# 登录和注册的逻辑
from flask import request, abort, redirect
from farbox_bucket.settings import SYSTEM_DOMAINS, BUCKET_PRICE, BUCKET_PRICE2
from farbox_bucket.server.web_app import app
from farbox_bucket.utils import is_email_address, auto_type
from farbox_bucket.utils.env import get_env
from farbox_bucket.utils.data import json_dumps
from farbox_bucket.utils.ip.utils import get_current_ip
from farbox_bucket.server.utils.response import p_redirect
from farbox_bucket.server.utils.cookie import delete_cookies
from farbox_bucket.server.template_system.api_template_render import render_api_template_as_response
from farbox_bucket.server.utils.request_context_vars import set_not_cache_current_request
from farbox_bucket.server.template_system.namespace.utils.form_utils import get_data_obj_from_POST
from farbox_bucket.server.template_system.app_functions.after_request.cache_page import get_response_from_memcache
from farbox_bucket.server.helpers.file_manager import sync_file_by_server_side

from farbox_bucket.bucket.utils import set_bucket_in_request_context
from farbox_bucket.bucket.record.get.path_related import get_markdown_record_by_path_prefix
from farbox_bucket.bucket.helper import get_private_key_on_server_side
from farbox_bucket.bucket.create import create_bucket_by_web_request
from farbox_bucket.bucket.invite import check_invitation_by_web_request
from farbox_bucket.bucket.token.utils import get_logined_bucket
from farbox_bucket.bucket.domain.utils import get_bucket_from_domain
from farbox_bucket.bucket.domain.ssl_utils import set_ssl_cert_for_domain_by_user, get_ssl_cert_for_domain
from farbox_bucket.bucket.service.bucket_service_info import get_bucket_service_info
from farbox_bucket.bucket.service.yearly_bucket_by_alipay import extend_bucket_expired_date_yearly_by_alipay
from farbox_bucket.bucket.record.get.path_related import get_record_by_path, get_json_content_by_path
from farbox_bucket.bucket.private_configs import get_bucket_owner_email, set_owner_email_to_bucket
from farbox_bucket.bucket.usage.bucket_usage_utils import get_bucket_usage
from farbox_bucket.bucket.domain.web_utils import get_bucket_from_request

from farbox_bucket.clouds.wechat.wechat_handler import is_wechat_server_valid



@app.route("/logout")
def logout():
    delete_cookies("utoken", "visitor_password")
    return redirect("/")

@app.route("/login", methods=["POST","GET"])
@app.route("/admin", methods=["POST","GET"])
def login():
    set_not_cache_current_request()
    bucket = get_logined_bucket(check=True)
    if bucket:
        email = get_bucket_owner_email(bucket)
    else:
        email = ""
    show_donation = auto_type(get_env("show_donation"))
    response = render_api_template_as_response("page_user_admin.jade",
                                           email=email,
                                           show_donation=show_donation,
                                           is_wechat_server_valid=is_wechat_server_valid)
    return response



@app.route("/__site_settings", methods=["POST", "GET"])
def setting_settings_view():
    bucket = get_logined_bucket(check=True)
    if not bucket:
        return abort(410)
    data_obj = get_json_content_by_path(bucket, 'settings.json') or {}
    if request.method == "POST":
        keys = request.values.keys()
        data_obj = get_data_obj_from_POST(keys)
        sync_file_by_server_side(bucket, "settings.json", content=json_dumps(data_obj, indent=4))

    return render_api_template_as_response("page_user_site_settings.jade", data_obj=data_obj)


@app.route("/__site_json_settings", methods=["POST", "GET"])
def site_json_settings_view():
    bucket = get_logined_bucket(check=True)
    if not bucket:
        return abort(410)
    set_bucket_in_request_context(bucket)
    return render_api_template_as_response("page_user_json_settings_ui.jade")


@app.route("/__bucket_usage")
def show_bucket_usage():
    bucket = get_logined_bucket(check=True)
    if not bucket:
        return abort(410)
    usage = get_bucket_usage(bucket)
    return render_api_template_as_response("page_user_usage.jade", usage=usage)



@app.route("/__apply_theme", methods=["POST", "GET"])
def apply_theme():
    return render_api_template_as_response("page_user_template.jade")


@app.route("/__register", methods=["POST", "GET"])
def create_new_bucket_for_user_step_1():
    register_note = get_env("register_note") or ""
    info = ""
    invitation_code = request.values.get("invitation_code")
    if invitation_code:
        if not check_invitation_by_web_request():
            info = "invalid invitation code or used"
        else: # 跳转到创建 bucket 的逻辑
            return p_redirect("__create_bucket?invitation_code=%s" % invitation_code)
    return render_api_template_as_response("page_user_register.jade", info=info, register_note=register_note)

# g.cache_strategy = 'no'

@app.route("/__create_bucket", methods=["POST", "GET"])
def create_new_bucket_for_user_step_2():
    # 这个也负责初次的安装，还没有 bucket 的时候
    register_note = get_env("register_note") or ""
    private_key = request.values.get("private_key") or get_private_key_on_server_side()
    info = ""
    invitation_code = request.values.get("invitation_code") or request.values.get("code")
    if request.method == "POST":
        info = create_bucket_by_web_request(invitation_code)
        if not info: # 创建成功了
            return p_redirect("/admin")
    else: # GET
        if invitation_code != "admin" and not check_invitation_by_web_request():
            info = "invalid invitation code"
    return render_api_template_as_response("page_user_create_bucket.jade", private_key=private_key, info=info,
                                           register_note=register_note)



@app.route("/__bind_domain", methods=["POST","GET"])
def bind_domain_for_bucket():
    ip = get_current_ip()
    main_domain = SYSTEM_DOMAINS[0] if SYSTEM_DOMAINS else None
    return render_api_template_as_response("page_user_bind_domain.jade", ip=ip, main_domain=main_domain)


@app.route("/__set_bucket_email", methods=["POST", "GET"])
def set_bucket_email():
    bucket = get_logined_bucket()
    if not bucket:
        return abort(404, "need login first")
    info = ""
    if request.method == "POST":
        email = request.values.get("email", "").strip()
        if email and not is_email_address(email):
            info = "email format is error"
        else:
            set_owner_email_to_bucket(bucket, email)
            return p_redirect("/admin")
    else:
        email = get_bucket_owner_email(bucket)
    return render_api_template_as_response("page_user_set_bucket_email.jade", info=info, email=email)


@app.route("/__install_ssl_for_bucket_domain", methods=["POST", "GET"])
def install_ssl_for_bucket_domain():
    domain = request.values.get("domain")
    if not domain:
        return abort(404, "no domain set to install SSL")
    bucket = get_logined_bucket()
    if not bucket:
        return abort(404, "need login first")
    domain_bucket = get_bucket_from_domain(domain)
    if bucket != domain_bucket:
        return abort(404, "logined bucket is not matched to this domain")
    cert_doc = get_ssl_cert_for_domain(domain)
    ssl_key = request.values.get("ssl_key")
    ssl_cert = request.values.get("ssl_cert")
    if cert_doc.get("by_user"):
        ssl_key = ssl_key or cert_doc.get("ssl_key") or ""
        ssl_cert = ssl_cert or cert_doc.get("ssl_cert") or ""
    data_obj = dict(
        ssl_key = ssl_key,
        ssl_cert = ssl_cert
    )
    info = ""
    if request.method == "POST":
        info = set_ssl_cert_for_domain_by_user(domain=domain, ssl_key=ssl_key, ssl_cert=ssl_cert)
        if not info: #  ssl 安装成功了
            return p_redirect("/admin")
    return render_api_template_as_response("page_user_install_ssl.jade", info=info, data_obj=data_obj)


@app.route("/__extend_bucket", methods=["POST", "GET"])
def extend_bucket_yearly():
    # 考虑到 alipay 的回调，这里不限制 bucket 是否处于登录的状态
    bucket = get_logined_bucket(check=True)

    service_info = get_bucket_service_info(bucket)
    order_ids = service_info.get("order_id_list") or []
    if not isinstance(order_ids, (list, tuple)): order_ids = []

    price = BUCKET_PRICE
    price2 = BUCKET_PRICE2
    price_note = get_env("bucket_price_note") or ""


    if request.method == "GET" and not request.values.get("trade_no") and request.values.get("action") != "do":
        # 不需要处理，直接呈现页面
        return render_api_template_as_response("page_user_extend_bucket.jade", order_ids=order_ids,
                                               service_info=service_info, price=price, price2=price2, price_note=price_note)

    try_price2 = request.values.get("try_price2") in ["yes", "true"]
    to_handle = extend_bucket_expired_date_yearly_by_alipay(bucket, try_price2=try_price2)
    if to_handle:
        # 更新一次
        service_info = get_bucket_service_info(bucket)
        order_ids = service_info.get("order_id_list") or []
        if not isinstance(order_ids, (list, tuple)): order_ids = []

    return render_api_template_as_response("page_user_extend_bucket.jade", order_ids=order_ids,
                                           service_info=service_info, price=price, price2=price2, price_note=price_note)


@app.route("/__donate")
def donate_to_farbox():
    return render_api_template_as_response("page_donate.jade")

@app.route("/__page/<path:path>")
def render_markdown_page(path=""):
    # cache it
    bucket = get_bucket_from_request()
    set_bucket_in_request_context(bucket)
    try: # memcache 的获取，也可能会出错, 概率很低
        cached_response = get_response_from_memcache()
        if cached_response:
            return cached_response
    except:
        pass

    if path in ["about", "links"]:
        md_doc = get_markdown_record_by_path_prefix(bucket, path)
        show_site_nav = True
    else:
        md_doc = None
        show_site_nav = False

    return render_api_template_as_response("page_user_markdown_page.jade", md_doc=md_doc, show_site_nav=show_site_nav)