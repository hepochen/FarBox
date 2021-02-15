# coding: utf8
from farbox_bucket.utils.ssdb_utils import hset, just_hget
from farbox_bucket.bucket.utils import is_valid_bucket_name, has_bucket
import shortuuid



def get_a_random_api_token(length = 8):
    token = shortuuid.uuid()[:length]
    return token


def get_bucket_api_token(bucket, db_name="_bucket_api_token",  auto_create=True):
    """
    :param bucket: 需要
    :param db_name: 提供了默认值
    :return: api_token
    """
    token = just_hget(db_name, bucket) or ''
    if not token and auto_create:
        token = set_bucket_api_token(bucket, db_name=db_name)
    return token

def set_bucket_api_token(bucket, db_name="_bucket_api_token"):
    """
    :param bucket: 需要
    :param db_name: 提供了默认值
    :return: new_api_token
    """
    if not is_valid_bucket_name(bucket):
        return ""
    if not has_bucket(bucket):
        return ""
    new_token = get_a_random_api_token()
    hset(db_name, bucket, new_token)
    return new_token

def check_bucket_api_token(bucket, token, db_name="_bucket_api_token"):
    """
    :param bucket: 需要
    :param token: 需要被校验的 token
    :param db_name: 提供了默认值
    :return:
    """
    token_in_db = get_bucket_api_token(bucket, db_name, auto_create=False)
    if token_in_db and token == token_in_db:
        return True
    else:
        return False



def get_bucket_login_token(bucket):
    return get_bucket_api_token(bucket, db_name="_bucket_login_token")

def set_bucket_login_token(bucket):
    return set_bucket_api_token(bucket, db_name="_bucket_login_token")

def check_bucket_login_token(bucket, token):
    return check_bucket_api_token(bucket, token, db_name="_bucket_login_token")


