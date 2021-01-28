# coding: utf8
import os, time
from flask import request, abort, Response, g
from farbox_bucket.server.web_app import app
from farbox_bucket.server.dangerous.restart import try_to_reload_web_app
from farbox_bucket.utils import to_int
from farbox_bucket.bucket.token.utils import get_logined_admin_bucket, get_admin_bucket
from farbox_bucket.bucket.invite import get_invitations, create_invitations
from farbox_bucket.bucket.utils import has_bucket
from farbox_bucket.bucket.service.bucket_service_info import change_bucket_expired_date, get_bucket_service_info
from farbox_bucket.server.template_system.api_template_render import render_api_template, render_api_template_as_response
from farbox_bucket.utils.env import load_app_global_envs, set_app_global_envs
from farbox_bucket.bucket.usage.bucket_usage_utils import get_all_buckets_bandwidth, get_all_buckets_file_size, get_all_buckets_request




@app.route('/admin/invite', methods=['POST', 'GET'])
def invite():
    bucket = get_logined_admin_bucket()
    if not bucket:
        abort(404, "not admin")
    cursor = request.values.get("cursor", "")
    if request.values.get("action") == "create":
        # 创建 1 个邀请码
        invitations_number = to_int(request.values.get("number"), default_if_fail=1)
        create_invitations(limit=invitations_number)
    per_page = to_int(request.values.get("per_page"), default_if_fail=100)
    invitations = get_invitations(limit=per_page, start_code=cursor)
    return render_api_template_as_response('page_admin_invite.jade', invitations=invitations)


@app.route("/admin/bucket_date", methods=["POST", "GET"])
def change_bucket_date():
    if not get_logined_admin_bucket():
        abort(404, "not admin")
    info = ""
    bucket = request.values.get("bucket")
    date = request.values.get("date")
    if request.method == "POST":
        # change the expired date of bucket
        if not has_bucket(bucket):
            info = "no bucket found"
        elif not date:
            info = "no date to set"
        else:
            change_bucket_expired_date(bucket, date)
    service_info = get_bucket_service_info(bucket)
    html = render_api_template("page_admin_bucket_expired_date.jade", info=info, service_info=service_info)
    return Response(html)


@app.route("/admin/buckets_usage")
def show_all_buckets_usage():
    if not get_logined_admin_bucket():
        abort(404, "not admin")
    bandwith_start_at = request.values.get("bandwidth") or 0
    file_size_start_at = request.values.get("file_size") or 0
    bandwidth_usage = get_all_buckets_bandwidth(score_start=bandwith_start_at, per_page=100)
    store_usage = get_all_buckets_file_size(score_start=file_size_start_at, per_page=100)
    request_usage = get_all_buckets_request(score_start=file_size_start_at, per_page=100)
    return render_api_template_as_response("page_admin_buckets_usage.jade",
                                           bandwidth_usage = bandwidth_usage,
                                           store_usage = store_usage,
                                           request_usage = request_usage)



@app.route("/admin/system_setup", methods=["POST", "GET"])
def system_configs_setup():
    if not get_logined_admin_bucket():
        abort(404, "not admin")

    data_obj = load_app_global_envs()

    info = ""
    if request.method == "POST":
        configs = request.form.to_dict()
        set_app_global_envs(configs)

    if request.method == "POST":
        new_data_obj = load_app_global_envs()
        if new_data_obj != data_obj:
            # 尝试重启整个 Web App
            data_obj = new_data_obj  # update
            try_to_reload_web_app()

    html = render_api_template("page_admin_system_setup.jade", info=info, data_obj=data_obj)
    #print(time.time() - t1)
    return Response(html)

