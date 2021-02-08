#coding: utf8
import requests
from farbox_bucket.utils.ssdb_utils import auto_cache_by_ssdb
from farbox_bucket.utils.env import get_env

WECHAT_APP_ID = get_env("wechat_app_id")
WECHAT_APP_SECRET = get_env("wechat_app_secret")


# 一个微信的open id 看起来可能是这样的: oZ454jpVhF15nHxs3ig-uCq_gqss

API_PREFIX = 'https://api.weixin.qq.com/cgi-bin/'

# 每天最多 2000 次
def _get_access_token():
    if not WECHAT_APP_ID or not WECHAT_APP_SECRET:
        return ""
    url = API_PREFIX + 'token'
    params = {'grant_type': 'client_credential', 'appid': WECHAT_APP_ID, 'secret': WECHAT_APP_SECRET}
    response = requests.get(url,  params=params, verify=False)
    try:
        token = response.json().get('access_token')
    except:
        try: print(response.json().get("errmsg"))
        except: pass
        token = ""
    return token

def get_access_token(force_update=False):
    # 7200s的有效期
    # # 一个小时更新一次
    return auto_cache_by_ssdb("wechat_token", value_func=_get_access_token, ttl=3600, force_update=force_update)


def check_wechat_errors_and_update_token(json_data):
    if not json_data:
        return # ignore
    error_code = json_data.get("errcode")
    if error_code == 40001: # access_token失效了
        get_access_token(force_update=True)
