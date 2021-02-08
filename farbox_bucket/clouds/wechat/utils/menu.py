#coding: utf8
import requests
import ujson as json
from farbox_bucket.utils import string_types
from .token import get_access_token, check_wechat_errors_and_update_token

API_PREFIX = 'https://api.weixin.qq.com/cgi-bin/'

def create_menus(menus):
    # wechat比较变态，menus需要是完整的json字符串
    url = API_PREFIX + 'menu/create'
    access_token = get_access_token(force_update=True)
    params = dict(access_token=access_token)
    #headers = {'content-type': 'application/json'}
    if isinstance(menus, string_types):
        data = menus
    else:
        data = json.dumps(menus, ensure_ascii=False)
    response = requests.post(url, data=data, params=params, verify=False)
    print response.json()
    try:
        json_data = response.json()
        check_wechat_errors_and_update_token(json_data)
        if json_data.get('errcode'):
            return False
        else:
            return True
    except:
        return False


def get_menus():
    url = API_PREFIX + 'menu/get'
    access_token = get_access_token()
    params = dict(access_token=access_token)
    response = requests.get(url, params=params, verify=False)
    return response.json()


def delete_menus():
    url = API_PREFIX + 'menu/delete'
    access_token = get_access_token()
    params = dict(access_token=access_token)
    response = requests.get(url, params=params, verify=False)
    return response.json()



