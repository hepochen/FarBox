#coding: utf8
from __future__ import absolute_import
import requests
import time
import os
import ujson as json
import logging
import re
from farbox_bucket.utils import string_types, get_md5
from farbox_bucket.utils.encrypt.key_encrypt import sign_by_private_key, get_public_key_from_private_key
from farbox_bucket.utils.gzip_content import gzip_content
from farbox_bucket.bucket import get_bucket_by_private_key
from .project import get_project_config



def get_node_url(node, route='farbox_bucket_message_api'):
    node = node or ''
    if '://' in node:
        node = node.split('://')[-1]
    node = node.strip().strip('/').strip()
    if not node:
        node = os.environ.get('DEFAULT_NODE') or '127.0.0.1:7788'
    node_url = 'http://%s/%s' % (node, route.lstrip('/'))
    return node_url



def get_data_to_post(node, private_key, message='', action='record'):
    message = message or ''
    node_url = get_node_url(node)
    # #return logging.error('bucket or private_key can not be found')
    bucket = get_bucket_by_private_key(private_key)
    if not bucket or not private_key:
        return None, None
    public_key = get_public_key_from_private_key(private_key)
    if not public_key: # private key is error?
        return None, None
    if not isinstance(message, string_types):
        message = json.dumps(message) # no indent

    data_to_post = dict(
        bucket = bucket,
        action = action,
        timestamp = int(time.time()),
        data = message,
    )


    if action in ['create_bucket', 'check'] or action.startswith('config'): # create bucket, should put public_key in data
        data_to_post['public_key'] = public_key
    signature = sign_by_private_key(private_key, content=data_to_post)
    data_to_post['signature'] = signature

    # 给 server 端一个 private_key 的 md5 值，做一些敏感字段的弱加密、解密用的
    clean_private_key = re.sub('\s', '', private_key, flags=re.M)
    private_key_md5 = get_md5(clean_private_key)
    data_to_post['private_key_md5'] = private_key_md5

    # data 压缩一下
    if isinstance(message, string_types):
        data_to_post['data'] = gzip_content(message, base64=True)

    return node_url, data_to_post



def send_message(node, private_key, message='', action='record', file_to_post=None, timeout=60, return_response=False):
    node_url, data_to_post = get_data_to_post(node=node, private_key=private_key, message=message, action=action)
    if not node_url and not data_to_post:
        logging.error('bucket or private_key can not be found or error')
        result = {'message': 'no node_url or no data_to_post', 'code': 410}
        return result
    files = None
    if file_to_post:
        files = {'file': file_to_post}
    timeout = timeout or 60
    if timeout < 2:
        timeout = 60
    try:
        response = requests.post(
            node_url,
            data = data_to_post,
            timeout = timeout,
            files = files,
        )
        if return_response:
            return response
    except:
        if return_response:
            return None
        result = {'message': 'request failed', 'code': 410}
        return result
    try:
        # like {u'message': u'ok', u'code': 200}
        response_result = response.json()
        return response_result
    except:
        result = {'message': 'json error', 'code': 404, 'content': response.content, "response_code": response.status_code}
        return result
    #response_code = response_result.get('code')
    #response_message = response_result.get("message")
    #if response_code != 200:
    #    print('error: %s' % response_message)




############# for project starts ########

def send_message_for_project(project, message='', action='record', node=None):
    node_to_post = node
    node, bucket, private_key, public_key = get_project_config(project, as_list=True, auto_create=True)
    if node_to_post:
        node = node_to_post # node_to_post 优先
    result = send_message(node=node, private_key=private_key, message=message, action=action)
    return result

############# for project ends ########

