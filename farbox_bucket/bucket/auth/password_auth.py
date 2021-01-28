#coding: utf8
from __future__ import absolute_import
from farbox_bucket.utils import hash_password
from farbox_bucket.utils.web_utils.flask_httpauth import HTTPBasicAuth
from farbox_bucket.bucket import get_bucket_user_configs, is_valid_bucket_name
from flask import g, request

def verify_password_callback(username, password):
    # password, must be a hashed password here
    bucket = request.view_args.get('bucket')
    if not is_valid_bucket_name(bucket):
        return True

    username = username or request.values.get('user') or ''
    password = password or request.values.get('password') or ''

    bucket_user_configs = get_bucket_user_configs(bucket)
    if bucket_user_configs:
        user_username = bucket_user_configs.get('username')
        user_password = bucket_user_configs.get('password')
        if user_password: # 有密码限定
            if user_username and username!=user_username:
                return False
            if user_password!=password:
                return False
            else:
                return True
    return True # at last

bucket_http_auth = HTTPBasicAuth()
bucket_http_auth.verify_password_callback = verify_password_callback