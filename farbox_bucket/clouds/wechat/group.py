#coding: utf8
from __future__ import absolute_import
from .auth import get_access_token
import requests
import ujson as json

API_PREFIX = 'https://api.weixin.qq.com/cgi-bin/'


def get_groups():
    url = API_PREFIX + 'groups/get'
    params = dict(access_token=get_access_token())
    response = requests.get(url, params=params, verify=False)
    print response.json()


def get_group_id(wechat_id, access_token=None):
    access_token = access_token or get_access_token()
    url = API_PREFIX + 'groups/getid'
    params = dict(access_token=access_token)
    response = requests.post(url, data=json.dumps(dict(openid=wechat_id)), params=params, verify=False)
    if response.status_code == 200:
        return response.json().get('groupid')
    else:
        return None

def set_group(wechat_id, group_id):
    access_token = get_access_token()
    old_group_id = get_group_id(wechat_id, access_token=access_token)
    if old_group_id == group_id:
        return False
    url = API_PREFIX + 'groups/members/update'
    params = dict(access_token=access_token)
    data = dict(openid=wechat_id, to_groupid=group_id)
    response = requests.post(url, params=params, data=json.dumps(data, ensure_ascii=False), verify=False)
    return response