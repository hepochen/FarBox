# coding: utf8
from flask import request
from farbox_bucket.settings import BUCKET_PRICE, BUCKET_PRICE2
from farbox_bucket.utils.data import json_dumps
from farbox_bucket.utils.memcache import get_cache_client
from farbox_bucket.utils.pay.alipay import alipay
from farbox_bucket.bucket.utils import is_valid_bucket_name
from farbox_bucket.server.utils.response import force_redirect, force_response
from farbox_bucket.server.utils.request_context_vars import set_response_in_request
from farbox_bucket.bucket.service.bucket_service_info import change_bucket_expired_date, get_bucket_service_info


def extend_bucket_expired_date_yearly_by_alipay(bucket, try_price2=False):
    title = "FarBox"
    if bucket:
        title = "FarBox-%s" % bucket
    price = BUCKET_PRICE
    if try_price2:
        price = BUCKET_PRICE2
    if price <= 0 :
        price = 128
    if request.method == 'POST':
        # # notify 过来的，要告诉 alipay 已经成功了
        cache_client = get_cache_client()
        cache_client.set('alipay_notify', json_dumps(alipay.payment_doc), zipped=True, expiration=24*60*60)
        set_response_in_request(alipay.success_response)
    current_url = request.url.split('?')[0]  # 不处理 GET 参数
    if bucket and not is_valid_bucket_name(bucket):
        return 'not a valid bucket name'
    payment_doc = alipay.payment_doc
    if not payment_doc:
        alipay_url_to_redirect = alipay.pay(
            price = price,
            title = title,
            content = bucket,
            notify_url = current_url,
            callback_url = current_url,
        )
        force_redirect(alipay_url_to_redirect)
    else:
        # bucket 增加了一年的有效期
        bucket = payment_doc.get('body') or bucket
        bucket_service_info = get_bucket_service_info(bucket)
        order_id = payment_doc.get("order_id")
        price = payment_doc.get("total_fee")
        to_handle = True
        order_id_for_db = None
        if order_id:
            order_ids_for_db = bucket_service_info.get("order_id_list")
            order_id_for_db = "%s-%s" % (order_id, price)
            if isinstance(order_ids_for_db, (list, tuple)) and order_id_for_db in order_ids_for_db:
                # 已经处理过了
                to_handle = False
        if to_handle:
            change_bucket_expired_date(bucket, days=367, order_id=order_id_for_db,)

        if request.method == "POST":
            return force_response(alipay.success_response)

        return to_handle
