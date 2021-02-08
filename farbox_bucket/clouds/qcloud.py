#coding:utf8
#import re
import time
import logging
from qcloud_cos import CosConfig
from qcloud_cos import CosS3Client
from farbox_bucket.settings import server_secret_key
from farbox_bucket.utils import smart_unicode, get_md5
from farbox_bucket.utils.url import get_url_path, join_url


logger = logging.getLogger("qcloud_cos.cos_client")
logger.level = logging.ERROR

# 不要混淆，这里的 bucket 是 cos 上的 bucket，不是 FarBox 上的
# https://github.com/tencentyun/cos-python-sdk-v5/blob/master/demo/tce_demo.py

# Bucket由bucketname-appid组成  -> 原来还要分成 appid 的逻辑，要多蠢就有多蠢


cos_cached_clients = {}
def get_cos_client(secret_id, secret_key, region):
    region = smart_unicode(region.strip())
    secret_id = smart_unicode(secret_id.strip())
    secret_key = smart_unicode(secret_key.strip())
    cache_key = "%s-%s-%s" % (secret_id, secret_key, region)
    cached_client = cos_cached_clients.get(cache_key)
    if cached_client:
        return cached_client
    config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key, Token=None)  # 获取配置对象
    cos_client = CosS3Client(config)
    cos_cached_clients[cache_key] = cos_client
    return cos_client


########################################################################################################################################



def delete_file_on_qcloud(url_path, secret_id, secret_key, bucket, region):
    cos_client = get_cos_client(secret_id=secret_id, secret_key=secret_key, region=region)
    url_path = smart_unicode(url_path)
    if not url_path.startswith('/'):
        url_path = '/%s' % url_path
    try:
        result = cos_client.delete_object(Bucket=bucket, Key=url_path)
        if result.get("message") == "SUCCESS":
            return True
        else:
            return False
    except:
        return False



def has_file_on_qcloud(url_path, secret_id, secret_key, bucket, region):
    cos_client = get_cos_client(secret_id=secret_id, secret_key=secret_key, region=region)
    return cos_client.object_exists(Bucket=bucket, Key=url_path)


def get_file_meta_on_qcloud(url_path, secret_id, secret_key, bucket, region):
    cos_client = get_cos_client(secret_id=secret_id, secret_key=secret_key, region=region)
    return cos_client.head_object(Bucket=bucket, Key=url_path)



def upload_file_obj_to_qcloud(file_obj, url_path, secret_id, secret_key, bucket, region, content_type="", **headers):
    cos_client = get_cos_client(secret_id=secret_id, secret_key=secret_key, region=region)
    if hasattr(file_obj, 'read'):
        data = file_obj.read()
        try: file_obj.close()
        except: pass
    else:
        # 直接传入了原始的内容
        data = file_obj
    if not url_path.startswith('/'):
        url_path = '/%s' % url_path

    if content_type:
        headers["ContentType"] = content_type
    try:
        result = cos_client.put_object(Bucket=bucket, Key=url_path, Body=data, **headers)
        #result = {'Content-Length': '0', 'ETag': '"5b5465143c9f974f69fec8c38c449c44"', 'Date': 'Tue, 05 Jan 2021 13:23:05 GMT',
        # 'x-cos-hash-crc64ecma': '6187869793946143935', 'x-cos-request-id': 'NWZmNDY4MzlfN2EzZjIyMDlfY2M5NV8zMjQ4Yzk3',
        # 'Connection': 'keep-alive', 'Server': 'tencent-cos'}
        return True
    except Exception as e:
        return False




def get_file_content_from_qcloud(url_path, secret_id, secret_key, bucket, region):
    cos_client = get_cos_client(secret_id=secret_id, secret_key=secret_key, region=region)
    response = cos_client.get_object(Bucket=bucket, Key=url_path)
    body = response['Body']
    file_content = b""
    while True:
        chunk = body.read(1024*1024, auto_decompress=False)
        if not chunk:
            break
        file_content += chunk
    return file_content



def sign_qcloud_url(qcloud_url, qcloud_token, url_path=None, more=None, zero_steps=4):
    # 默认10000秒的容差, about 3 hours, 相当于 3 个小时左右的跳转 URL 是固定的，方便缓存的逻辑
    if url_path is None:
        url_path = get_url_path(qcloud_url)
        full_url = qcloud_url
    else:
        full_url = "%s/%s" % (qcloud_url.rstrip("/"), url_path.lstrip("/"))
    if not url_path.startswith("/"):
        url_path = "/%s" % url_path
    timestamp = str(int(time.time()))[:-zero_steps] + "0"*zero_steps
    rand = get_md5("%s-%s-%s" % (url_path, timestamp, server_secret_key))
    string_to_hash = "%s-%s-%s-0-%s" % (url_path, timestamp, rand, qcloud_token)
    hash_md5 = get_md5(string_to_hash)
    sign = "%s-%s-0-%s" % (timestamp, rand, hash_md5)
    if "?" in full_url:
        url = join_url(full_url, sign=sign)
    else:
        url = "%s?sign=%s" % (full_url, sign)
    if more:
        url = "%s&%s" % (url, more)
    return url
