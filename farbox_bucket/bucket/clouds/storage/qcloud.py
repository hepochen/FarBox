# coding: utf8
from farbox_bucket.utils.env import get_env
from farbox_bucket.clouds.qcloud import upload_file_obj_to_qcloud, delete_file_on_qcloud,\
    has_file_on_qcloud, get_file_content_from_qcloud


raw_qcloud_config = get_env('qcloud')
QCLOUD_REGION = get_env("qcloud_region") or 'ap-shanghai'
QCLOUD_BUCKET = get_env("qcloud_bucket")
QCLOUD_SECRET_ID = get_env("qcloud_secret_id")
QCLOUD_SECRET_KEY = get_env("qcloud_secret_key")

if QCLOUD_BUCKET and  QCLOUD_SECRET_ID and  QCLOUD_SECRET_KEY:
    qcloud_is_valid = True
else:
    qcloud_is_valid = False
QCLOUD_URL = (get_env("qcloud_url") or "").rstrip("/")

QCLOUD_CDN_TOKEN = (get_env("qcloud_cdn_token") or "").strip()


def upload_file_to_qcloud_for_bucket(bucket, relative_path, file_obj, content_type="", **headers):
    if not qcloud_is_valid:
        return False # ignore
    relative_path = relative_path.strip('/')
    url_path = '%s/%s' % (bucket, relative_path)
    uploaded = upload_file_obj_to_qcloud(
        file_obj = file_obj,
        url_path = url_path,
        secret_id=QCLOUD_SECRET_ID,
        secret_key=QCLOUD_SECRET_KEY,
        bucket= QCLOUD_BUCKET,
        region=QCLOUD_REGION,
        content_type = content_type,
        **headers
    )
    return uploaded


def delete_file_on_qcloud_for_bucket(bucket, relative_path):
    if not qcloud_is_valid:
        return False # ignore
    relative_path = relative_path.strip('/')
    url_path = '%s/%s' % (bucket, relative_path)
    deleted = delete_file_on_qcloud(
        url_path = url_path,
        secret_id=QCLOUD_SECRET_ID,
        secret_key=QCLOUD_SECRET_KEY,
        bucket=QCLOUD_BUCKET,
        region=QCLOUD_REGION,
    )
    return deleted


def has_file_on_qcloud_for_bucket(bucket, relative_path):
    if not qcloud_is_valid:
        return False # ignore
    relative_path = relative_path.strip('/')
    url_path = '%s/%s' % (bucket, relative_path)
    has_file = has_file_on_qcloud(url_path = url_path,
        secret_id=QCLOUD_SECRET_ID,
        secret_key=QCLOUD_SECRET_KEY,
        bucket=QCLOUD_BUCKET,
        region=QCLOUD_REGION)
    return has_file


def get_file_on_qcloud_for_bucket(bucket, relative_path):
    if not qcloud_is_valid:
        return None
    relative_path = relative_path.strip('/')
    url_path = '%s/%s' % (bucket, relative_path)
    try:
        raw_content = get_file_content_from_qcloud(url_path, secret_id=QCLOUD_SECRET_ID,
        secret_key=QCLOUD_SECRET_KEY,
        bucket=QCLOUD_BUCKET,
        region=QCLOUD_REGION)
        return raw_content
    except:
        return None