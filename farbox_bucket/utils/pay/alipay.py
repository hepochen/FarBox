# coding: utf8
import re
from flask import request, Response
from farbox_bucket.utils import to_float
from farbox_bucket.utils.functional import cached_property
from farbox_bucket.utils.env import get_env
from .alipay_api import AlipayAPI


ALIPAY_PID = get_env('ALIPAY_PID')
ALIPAY_APP_ID = get_env('ALIPAY_APP_ID')
ALIPAY_PRIVATE_KEY = get_env('ALIPAY_PRIVATE_KEY')
ALIPAY_PUBLIC_KEY = get_env('ALIPAY_PUBLIC_KEY')



class AliPay(object):
    def __init__(self, private_key=None, public_key=None, pid=None, app_id=None):
        self.alipay_public_key = public_key or ALIPAY_PUBLIC_KEY
        self.alipay_private_key = private_key or ALIPAY_PRIVATE_KEY
        self.alipay_pid = pid or ALIPAY_PID
        self.alipay_app_id = app_id or ALIPAY_APP_ID


    @cached_property
    def alipay_api(self):
        if self.alipay_pid and self.alipay_private_key: # and self.alipay_public_key
            alipay_api = AlipayAPI(private_key=self.alipay_private_key, public_key=self.alipay_public_key,
                                   pid=self.alipay_pid, app_id=self.alipay_app_id)
            if alipay_api.cert:
                # 必须保证私钥正确
                return alipay_api

    @property
    def raw_alipay_payment(self):
        # body, body_list, total_fee, order_id 是固有的属性
        # 从当前请求中获得 payment_doc & 已经校验过是来自 alipay 的
        if not self.alipay_api:
            return {}

        payment_doc = request.values.to_dict()
        payment_body = payment_doc.get('body') or ''
        payment_body = payment_body.replace('%2C', ',').strip()
        payment_note = payment_doc.get('passback_params') or ''
        payment_doc['service'] = 'alipay'
        payment_doc['body'] = payment_body
        payment_doc['body_list'] = payment_body.split(',')
        payment_doc['payment_note'] = payment_note
        payment_id = payment_doc.get('trade_no') # 订单号
        payment_status = payment_doc.get('trade_status')
        is_paid = self.alipay_api.is_paid(payment_doc)
        if not is_paid: # 未支付状态，不处理
            return {}
        if payment_status and payment_id and self.alipay_api.verify_request(): # 请求校验，以保证这是从支付宝里过来的请求
            payment_doc['total_fee'] = payment_doc.get('total_fee') or payment_doc.get('total_amount') or payment_doc.get('price') or 0
            payment_doc['order_id'] = payment_doc.get('order_id') or payment_doc.get('trade_no')
            return payment_doc
        else:
            return {}

    @property
    def payment(self):
        # 只有支付成功的，才会返回一个数据对象
        raw_payment = self.raw_alipay_payment or {}
        return raw_payment

    @property
    def payment_doc(self):
        return self.payment

    @property
    def success_response(self):
        # 告诉支付宝，处理成功了
        return Response('success')


    def pay(self, price, title, content, callback_url='', notify_url='', return_url='', order_id='', note=''):
        if not self.alipay_api:
            return
        notify_url = notify_url or callback_url
        return_url = return_url or callback_url
        price = to_float(price)
        if not price or price < 0.01:
            price = 0.01
        redirect_url = self.alipay_api.pay(price, title, content,
                                           notify_url=notify_url, return_url=return_url,
                                           out_trade_no = order_id, note=note,
                                           )
        return redirect_url



alipay = AliPay()