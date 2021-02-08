#coding: utf8
from __future__ import absolute_import
from flask import request
from farbox_bucket.utils.memcache import cache_client
from farbox_bucket.bucket.utils import is_valid_bucket_name
from farbox_bucket.settings import MAX_RECORD_SIZE, MAX_RECORD_SIZE_FOR_CONFIG, ADMIN_BUCKET
from farbox_bucket.bucket import get_public_key_from_bucket
from farbox_bucket.utils.encrypt.key_encrypt import verify_by_public_key
from farbox_bucket.utils.gzip_content import ungzip_content
import time



def allowed_empty_data_for_action(action):
    if action in ['create_bucket', 'check', 'reset']:
        return True
    if '_' in action and action.split('_')[0] in ['show', 'config', 'check']:
        return True
    return False


def get_verified_message_from_web_request(raw_data=None):
    # return dict, if done
    # else return a response for webview
    raw_data = raw_data or request.values
    bucket = raw_data.get('bucket')
    timestamp = raw_data.get('timestamp')
    signature = raw_data.get('signature') # sign all data in request
    action = raw_data.get('action') # record & config
    data = raw_data.get('data') # if action==create, data is None
    try: data = ungzip_content(data, base64=True)
    except: pass
    try:
        timestamp = int(timestamp)
    except:
        return 'timestamp is error'

    if not bucket or not timestamp or not signature:
        return 'fields not filled, bucket is %s, timestamp is %s, signature is %s' % (bucket, timestamp, signature)
    if not data and not allowed_empty_data_for_action(action):
        # show_xxx, config_xxx, create_bucket, the data can be {}, []
        return 'fields not filled, action is %s, has data:%s' % (action, bool(data))

    current_timestamp = time.time()
    if abs(current_timestamp - timestamp) > 60*60:
        return 'compared to now, the offset is more than one hour'

    max_size = MAX_RECORD_SIZE
    if action.startswith('config_'):
        max_size = MAX_RECORD_SIZE_FOR_CONFIG # `设置`类型的限制

    if data:
        data_size = len(data)
        if data_size > max_size:
            return 'data should be less than %sk per record, current is %sk' % (max_size/1024., data_size/1024.)

    public_key = get_public_key_from_bucket(bucket)
    if not public_key:
        return 'bucket is not on current node now or no public_key in bucket'

    if not public_key:
        return 'bucket lost public key, error!'

    # verify the message
    content_to_verify = dict(
        bucket = bucket,
        timestamp = timestamp,
    )
    if data:
        content_to_verify['data'] = data
    if action:
        content_to_verify['action'] = action

    public_key_in_request = request.values.get("public_key")
    if public_key_in_request:
        content_to_verify['public_key'] = public_key_in_request

    verified = verify_by_public_key(public_key, signature, content_to_verify)
    if not verified:
        return 'verify failed'

    if not action:
        action = 'record' # default action

    message = dict(
        bucket = bucket,
        action = action,
        data = data, # string
        public_key = public_key,
    )

    # patch by helper?
    helper_bucket = cache_client.get("system_assistant_bucket", zipped=False)
    if helper_bucket and bucket == helper_bucket:
        helper_bucket_for_user = cache_client.get("system_assistant_bucket_for_user", zipped=False)
        if helper_bucket_for_user and is_valid_bucket_name(helper_bucket_for_user):
            user_public_key = get_public_key_from_bucket(helper_bucket_for_user)
            if user_public_key:
                message["bucket"] = bucket
                message["public_key"] = user_public_key

    return message



