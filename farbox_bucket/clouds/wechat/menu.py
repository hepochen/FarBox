#coding: utf8
from __future__ import absolute_import
from .auth import get_access_token, check_wechat_errors, get_oauth_jump_url
import requests
import ujson as json
from farbox_bucket.utils import string_types

API_PREFIX = 'https://api.weixin.qq.com/cgi-bin/'

def create_menus(menus):
    # wechat比较变态，menus需要是完整的json字符串
    url = API_PREFIX + 'menu/create'
    access_token = get_access_token()
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
        if json_data.get('errcode'):
            return False
        check_wechat_errors(json_data)
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



