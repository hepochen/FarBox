#coding: utf8
from flask import request
from farbox_bucket.settings import WEBSITE_DOMAINS
from farbox_bucket.utils import to_sha1
#from farbox_bucket.utils.encrypt.key_encrypt import get_md5_for_key
from farbox_bucket.bucket.utils import get_bucket_by_private_key, has_bucket, get_admin_bucket
from farbox_bucket.bucket.domain.web_utils import get_bucket_from_request
from farbox_bucket.server.utils.cookie import set_cookie, get_cookie, delete_cookies
from .bucket_api_token import check_bucket_api_token, check_bucket_login_token, get_bucket_login_token,\
    set_bucket_api_token, set_bucket_login_token, get_bucket_api_token

from farbox_bucket.server.utils.request_context_vars import get_logined_bucket_in_request, \
    set_logined_bucket_in_request, get_logined_bucket_checked_in_request, get_pending_bucket_bucket_in_request



def get_bucket_login_key(bucket):
    bucket_login_token = get_bucket_login_token(bucket)
    raw_value = '%s-%s-%s' % (bucket, 'login_key', bucket_login_token)
    login_key = to_sha1(raw_value)
    return login_key


def mark_bucket_login_by_private_key(private_key):
    if not private_key:
        return False
    bucket = get_bucket_by_private_key(private_key)
    if not bucket:
        return False
    if not has_bucket(bucket):
        return False
    login_key = get_bucket_login_key(bucket)
    utoken_for_cookie = '%s-%s' % (bucket, login_key)
    set_cookie('utoken', utoken_for_cookie, max_age=120*24*60*60) # 120 days
    set_logined_bucket_in_request(bucket, checked=True)
    return True

def mark_bucket_logout():
    delete_cookies('utoken')

def refresh_bucket_login_key(bucket):
    set_bucket_login_token(bucket)
    mark_bucket_logout()


def is_bucket_login(bucket=None):
    # 会进行校验
    utoken = get_cookie('utoken') or ''
    if '-' not in utoken:
        return False
    bucket_in_cookie, login_key_in_cookie = utoken.split('-', 1)
    if bucket and bucket!=bucket_in_cookie:
        # 传入的参数，bucket 相当于二次比对吧
        return False
    login_key = get_bucket_login_key(bucket_in_cookie)
    if login_key != login_key_in_cookie:
        return False
    return True # at last

def get_logined_bucket(check=True):
    logined_bucket_checked = get_logined_bucket_checked_in_request()
    if logined_bucket_checked:
        logined_bucket_in_g = get_logined_bucket_in_request()
        if logined_bucket_in_g:
            return logined_bucket_in_g
    utoken = get_cookie('utoken') or ''
    if '-' not in utoken:
        return None
    bucket_in_cookie, login_key_in_cookie = utoken.split('-', 1)
    if check: # 要校验数据库里的 login token
        if not is_bucket_login(bucket_in_cookie):
            return None

    # 增加一个限制，只有 bucket 对应的 domain 下才允许登录，避免使用者混淆了
    if check and request.host not in WEBSITE_DOMAINS:
        bucket_from_domain = get_bucket_from_request()
        if bucket_from_domain and bucket_from_domain != bucket_in_cookie:
            admin_bucket = get_admin_bucket()
            if admin_bucket == bucket_in_cookie:
                return bucket_in_cookie
            else:
                return None
    return bucket_in_cookie


def get_logined_admin_bucket():
    # 获得 login 并且是管理员的 bucket
    logined_bucket = get_logined_bucket(check=True)
    if logined_bucket:
        admin_bucket = get_admin_bucket()
        if admin_bucket == logined_bucket:
            return admin_bucket


def refresh_bucket_client_api_token(bucket):
    """
    更新并返回新的 client_api_token
    :param bucket:
    :return: 新的 client_api_token
    """
    set_bucket_api_token(bucket)
    return get_bucket_client_api_token(bucket)


def get_bucket_client_api_token(bucket):
    api_token = get_bucket_api_token(bucket)
    if api_token:
        return "%s-%s" % (bucket, api_token)
    else:
        return ""

def get_logined_bucket_by_token():
    # 目前 Metion 就使用传入 api_token 的方式进行数据的同步
    raw_token = request.values.get("api_token") or request.values.get("token") or ""
    if "-" not in raw_token:
        # 默认给的 token 都是自带 bucket 信息的，这里应该是单独输入的
        bucket = get_pending_bucket_bucket_in_request()
        if bucket and check_bucket_api_token(bucket, token=raw_token):
            return bucket
        return None
    bucket, token = raw_token.split("-", 1)
    if check_bucket_api_token(bucket, token=token):
        return bucket
    else:
        return None
