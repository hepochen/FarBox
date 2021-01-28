#coding: utf8
from __future__ import absolute_import

# todo ....
from configs.clouds import WECHAT_APP_SECRET, WECHAT_APP_ID

import requests
import urllib
import ujson as json
from flask import request

from farbox_bucket.utils.url import join_url
from farbox_bucket.server.utils.cookie import set_cookie
from farbox_bucket.utils.functional import curry
from farbox_bucket.utils.env import get_env

from .utils.scan import save_scan_doc



# 一个微信的open id 看起来可能是这样的: oZ454jpVhF15nHxs3ig-uCq_gqss

API_PREFIX = 'https://api.weixin.qq.com/cgi-bin/'

# 每天最多 2000 次
def _get_access_token():
    url = API_PREFIX + 'token'
    params = {'grant_type': 'client_credential', 'appid': WECHAT_APP_ID, 'secret': WECHAT_APP_SECRET}
    response = requests.get(url,  params=params, verify=False)
    try:
        token = response.json().get('access_token')
    except:
        token = ''
    return token

def get_access_token(force_update=False):
    # 7200s的有效期
    return db.system.cache('wechat_token', _get_access_token, ttl=3600, force_update=force_update) # 一个小时更新一次


def check_wechat_errors(json_data):
    if not json_data:
        return # ignore
    error_code = json_data.get("errcode")
    if error_code == 40001: # access_token失效了
        get_access_token(force_update=True)



def _create_tmp_ticket(info):
    # 为FarBox上的一个account_id创建一个临时二维码, ticket可以对应一个二维码
    url = API_PREFIX + 'qrcode/create'
    scan_id = save_scan_doc(info) # scan_id按照微信的要求，比如是整数
    if not scan_id:
        return ''
    access_token = get_access_token()
    if not access_token:
        return ''
    params = dict(access_token=access_token) # set the token
    headers = {'content-type': 'application/json'}
    request_data = {"expire_seconds": 1800, "action_name": "QR_SCENE", "action_info": {"scene": {"scene_id": scan_id}}}
    response = requests.post(url,data=json.dumps(request_data), params=params, headers=headers, verify=False)
    try:
        json_data = response.json()
        check_wechat_errors(json_data)
        ticket = json_data.get('ticket')
    except:
        ticket = ''
    return ticket


def create_tmp_ticket(info, cache_key=None, collection=None):
    # todo 数据库的处理
    # 1800的有效期
    # cache_key + collection, 表示在某个表（collection）中对ticket做缓存，以cache_key作为doc的_id
    # 上面这个规则的设计，可以避免反复的创建ticket
    if cache_key and isinstance(cache_key, (str, unicode)) and collection:
        return collection.cache(cache_key, curry(_create_tmp_ticket, info), ttl=1200, value_field='wechat_qrcode')
    else:
        return _create_tmp_ticket(info)

def create_account_bind_ticket(account_id):
    # 为已经存在的账户，生成绑定微信的二维码
    info = dict(type='bind_wechat_account', account_id=account_id)
    return create_tmp_ticket(info, cache_key=account_id, collection=db.account)


def create_login_ticket(session_id):
    # 根据Cookie里特殊设定的session_id，生成登录、注册用的二维码
    # utils.scan用的是log_db.we_scan来存储场景的信息
    # 而tmp_db.we_scan则是临时性缓存一个session_id对应的qrcode信息，以避免多余的到微信API上的create_ticket请求
    info = dict(type='scan_login', session_id=session_id)
    return create_tmp_ticket(info, cache_key=session_id, collection=tmp_db.we_scan)



def get_wechat_qrcode_url(ticket):
    return 'https://mp.weixin.qq.com/cgi-bin/showqrcode?ticket=%s' % ticket



def get_oauth_jump_url(redirect_url, state='wechatCode'):
    base_url = 'https://open.weixin.qq.com/connect/oauth2/authorize'

    params = dict(appid = WECHAT_APP_ID,
        redirect_uri = redirect_url,
        response_type = 'code',
        scope = 'snsapi_base', # 静默状态，不会请求账户的额外信息
        state = state)

    params_order = ['appid', 'redirect_uri', 'response_type', 'scope', 'state']
    params_list = []
    for k in params_order:
        params_list.append( urllib.urlencode({k:params[k]}) )
    url = '%s?%s#wechat_redirect' % (base_url, '&'.join(params_list))

    return url


def get_wechat_id_by_code(code):
    url = join_url(
        'https://api.weixin.qq.com/sns/oauth2/access_token',
        appid = WECHAT_APP_ID,
        secret = WECHAT_APP_SECRET,
        code = code,
        grant_type = 'authorization_code',
    )
    response = requests.get(url, verify=False)
    json_data = response.json()
    check_wechat_errors(json_data)
    return json_data.get('openid')


def wechat_oauth_callback(callback_func=None):
    # wechat oauth 跳转的回调函数
    if request.args.get('code'):
        code = request.args.get('code')
        wechat_id = get_wechat_id_by_code(code)
        if callback_func:
            return callback_func(wechat_id)
        else:
            set_cookie('wechat_id', wechat_id)

