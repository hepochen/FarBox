#coding: utf8
import time
import datetime
import gevent
from farbox_bucket.server.dangerous.restart import try_to_reload_web_app
from farbox_bucket.utils.ssdb_utils import hset, ssdb_set
from farbox_bucket.utils.data import json_dumps
from farbox_bucket.bucket.utils import has_bucket, set_bucket_into_buckets
from farbox_bucket.bucket.token.utils import mark_bucket_login_by_private_key
from farbox_bucket.bucket.defaults import zero_id
from farbox_bucket.utils.encrypt.key_encrypt import get_public_key_from_private_key
from farbox_bucket.bucket.utils import get_bucket_by_public_key, get_bucket_by_private_key, is_valid_bucket_name, get_buckets_size
from farbox_bucket.bucket.invite import can_use_invitation, check_invitation_by_web_request, use_invitation
from farbox_bucket.bucket.service.bucket_service_info import change_bucket_expired_date
#from farbox_bucket.server.template_system.exceptions import TemplateDebugException


from flask import request


def create_bucket_by_public_key(public_key, init_configs=None, force_to_create=False):
    # 本质上是创建一个 创世configs
    if not force_to_create:
        # todo 需要校验邀请码？
        # 非强制需要创建的，需要被邀请才能创建 bucket
        return False
    bucket = get_bucket_by_public_key(public_key)
    if not bucket:
        return False
    if has_bucket(bucket): # 已经存在了，不允许重新创建, 认为已经创建成功了
        return True
    now = int(time.time())
    now_date = datetime.datetime.utcfromtimestamp(now)
    now_date_string = now_date.strftime('%Y-%m-%d %H:%M:%S UTC')
    bucket_info = dict(
        public_key = public_key,
        created_at = now,
        created_date = now_date_string,
    )
    if init_configs and isinstance(init_configs, dict):
        allowed_to_update = True
        init_configs_bytes = json_dumps(init_configs)
        if len(init_configs_bytes) > 10*1024:
            allowed_to_update = False
        if allowed_to_update:
            init_configs.update(bucket_info)
            bucket_info = init_configs

    # 创建 init config, 这是不可修改的
    hset(bucket, zero_id, bucket_info, ignore_if_exists=True)

    # 创建的时候，也进行这个操作，方便知道 buckets 的总数相关数据
    set_bucket_into_buckets(bucket)

    # 创建的时候，给 30 days 的有效期
    change_bucket_expired_date(bucket)

    return True
    #if not done:
    #    return False
    #else:
    #    return True



def create_bucket_by_web_request(invitation_code=None):
    # return None or error_info
    # token, bucket(check by private_key), private_key, domain,
    if not request.method == 'POST':
        return 'invalid request Method'
    private_key = request.values.get('private_key', '').strip()
    try:
        bucket = get_bucket_by_private_key(private_key)
    except:
        bucket = None
    if not bucket:
        return 'invalid private key'
    public_key = get_public_key_from_private_key(private_key)
    is_first_bucket = False
    if not has_bucket(bucket): # bucket 如果已经创建了，不走这个流程
        if get_buckets_size() == 0:
            is_first_bucket = True
        else: # 需要邀请码的
            if not can_use_invitation(invitation_code):
                # 错误或者已经使用了的邀请码
                return "invitation code used or invalid"

        created = create_bucket_by_public_key(public_key=public_key, force_to_create=True)
        if not created:
            return 'unknown error'
        else:
            bucket = get_bucket_by_public_key(public_key)
            if is_first_bucket: # 向系统写入 first bucket
                ssdb_set("first_bucket", bucket)
                gevent.spawn_later(1, try_to_reload_web_app)  # try to restart web server
            elif invitation_code: # 保存已经使用的邀请码信息
                use_invitation(invitation_code, bucket)

    # at last, login bucket
    mark_bucket_login_by_private_key(private_key)
    #else:
    #    return "exists already"




