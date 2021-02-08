# coding: utf8
from flask import abort
from farbox_bucket.utils.env import get_env
from farbox_bucket.server.web_app import app
from farbox_bucket.bucket.token.utils import get_logined_bucket
from farbox_bucket.clouds.wechat.bind_wechat import get_wechat_bind_code_for_bucket, get_wechat_user_docs_by_bucket
from farbox_bucket.server.template_system.api_template_render import render_api_template_as_response
from .wechat_handler import wechat_web_handler, WECHAT_TOKEN

# 公众号后台获得公众号二维码，解析后是一个 URL 的字符串
wechat_account_url = get_env("wechat_account_url") or ""
wechat_account_url2 = get_env("wechat_account_url2") or ""

@app.route("/__wechat_api", methods=["POST", "GET"])
def wechat_api_view():
    return wechat_web_handler()


@app.route("/__wechat_bind", methods=["POST", "GET"])
def wechat_bind_view():
    if not WECHAT_TOKEN or not wechat_account_url:
        abort(404, "Wechat is not valid in current service")
    else:
        logined_bucket = get_logined_bucket(check=True)
        if not logined_bucket:
            return abort(404, "not login")
        bind_code = get_wechat_bind_code_for_bucket(logined_bucket)
        wechat_user_docs = get_wechat_user_docs_by_bucket(logined_bucket, with_name=True)
        response = render_api_template_as_response("wechat_bind.jade",
                                               wechat_user_docs=wechat_user_docs,
                                               bind_code=bind_code,
                                               wechat_account_url=wechat_account_url,
                                               wechat_account_url2 = wechat_account_url2)
        return response


