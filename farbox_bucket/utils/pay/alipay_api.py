# coding: utf8
from __future__ import absolute_import
from OpenSSL import crypto
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA
import requests
import datetime
import base64
import ujson as json
import uuid
import re
from flask import request
from urllib import urlencode

from farbox_bucket.utils import to_float, smart_str, smart_unicode, get_md5
from farbox_bucket.utils.cache import LimitedSizeDict
from farbox_bucket.bucket.utils import get_bucket_in_request_context


# alipay_partner_public_key = 'MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCnxj/9qwVfgoUh/y2W89L6BkRAFljhNhgPdyPuBV64bfQNN1PjbCzkIM6qRdKBoLPXmKKMiFYnkd6rAoprih3/PrQEB/VsW8OoM8fxn67UDYuyBTqA23MML9q1+ilIZwBC2AQ2UBVOrFXfFl75p6/B5KsiNG9zpgmLCUYuLkxpLQIDAQAB'
# alipay_partner_public_key = RSA.importKey("-----BEGIN PUBLIC KEY-----\n%s\n-----END PUBLIC KEY-----"%alipay_partner_public_key)
# partner_verifier = PKCS1_v1_5.new(alipay_partner_public_key)



certs_cache = LimitedSizeDict(max=1000)
def get_cert(private_key):
    # 避免重复 load_privatekey 产生性能问题
    if isinstance(private_key, crypto.PKey):
        return private_key
    private_key = private_key.strip()
    private_key = private_key.replace('\r', '')
    if '-BEGIN PRIVATE KEY-' not in private_key:
        private_key = "-----BEGIN PRIVATE KEY-----\n"+private_key+"\n-----END PRIVATE KEY-----"
    if private_key in certs_cache:
        return certs_cache[private_key]
    cert = crypto.load_privatekey(crypto.FILETYPE_PEM, private_key)
    certs_cache[private_key] = cert
    return cert

verifier_cache = LimitedSizeDict(max=1000)
def get_verifier(public_key):
    if not public_key:
        return None
    public_key = public_key.strip()
    cache_key = get_md5(public_key)
    if cache_key in verifier_cache:
        return verifier_cache[cache_key]
    if not '-BEGIN PUBLIC KEY-' in public_key:
        public_key = "-----BEGIN PUBLIC KEY-----\n%s\n-----END PUBLIC KEY-----"%public_key
    public_key = RSA.importKey(public_key)
    verifier = PKCS1_v1_5.new(public_key)
    verifier_cache[cache_key] = verifier
    return verifier


# partner 主要是直接支付，需要用到的, 公开的, 支付宝提供的
alipay_platform_public_key = 'MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDDI6d306Q8fIfCOaTXyiUeJHkrIvYISRcc73s3vF1ZT7XN8RNPwJxo8pWaJMmvyTn9N4HQ632qJBVHf8sxHi/fEsraprwCtzvzQETrNRwVxLO5jVmRGi60j8Ue1efIlzPXV9je9mkjzOmdssymZkh2QhUrCmZYI/FCEa3/cNMW0QIDAQAB'
platform_verifier = get_verifier(alipay_platform_public_key)




def get_cn_timestamp(t_format='%Y-%m-%d %H:%M:%S'):
    # 考虑服务器本身的时间戳问题，使用 utcnow + 8来处理
    utc_now = datetime.datetime.utcnow()
    cn_now = utc_now + datetime.timedelta(hours=8)
    timestamp = cn_now.strftime(t_format)
    return timestamp




class BaseAlipay(object):
    def __init__(self, private_key, public_key=None):
        try: self.cert = get_cert(private_key)
        except: self.cert = None
        try: self.verifier = get_verifier(public_key)
        except: self.verifier = None


    def get_out_trade_no(self, prefix=''): # 64位最长
        # 商户网站唯一订单号
        prefix = smart_unicode(prefix)[:10] # 最多10位
        now = get_cn_timestamp('%Y%m%d%H%M%S') # 14位了已经
        uid = uuid.uuid1().hex[:8]
        no = '%s%s%s' % (prefix, now, uid)
        try:
            bucket = get_bucket_in_request_context()
            if bucket: # site_id hashed 长度为 32， 总长度为 14+8+1+32=55 < 64
                hashed_bucket_id = get_md5(bucket) # 主要用作校验，避免跨站的交易被验证成功
                no = '%s-%s' % (no, hashed_bucket_id)
        except:
            pass

        return no

    def is_trade_under_this_site(self):
        # 校验当前回调的交易，是不是从当前网站发出去的
        out_trade_no = request.values.get('out_trade_no') or ''
        if '-' not in  out_trade_no:
            # 没有在trade_no 中增加site的信息，ignore掉, return True
            return True
        bucket = get_bucket_in_request_context()
        if bucket: # site_id hashed 长度为 32， 总长度为 14+8+1+32=55 < 64
            hashed_bucket_id = get_md5(bucket) # 主要用作校验，避免跨站的交易被验证成功
            if out_trade_no and out_trade_no.endswith('-%s' % hashed_bucket_id):
                return True
        return False



    def compile_response(self, r):
        if r.status_code in [301, 302]: # url 跳转
            return r.headers.get('location')
        try:
            return json.loads(r.text)
        except Exception, e:
            if r.status_code in [200]:
                s = re.search('<div class=["\']Todo["\']>(.*?)</div>', r.text, flags=re.I)
                if s:
                    error_info = re.search('<div class="Todo">(.*?)</div>', r.text).groups()[0]
                    return error_info
            return


    def get_pay_request_data(self, price, title, content, notify_url='', return_url='', out_trade_no='', note=''):
        price = to_float(price)
        if not price:
            return # ignore
        price = '%.2f' % price

        out_trade_no = smart_unicode(out_trade_no)
        if len(out_trade_no) < 10: # 作为前缀，自动生成
            out_trade_no = self.get_out_trade_no(prefix=out_trade_no)

        # 不限制 subject、 body， 反正太长了自己会出错
        data = dict(
            total_amount = price,
            subject = smart_unicode(title), # max length 256
            body = smart_unicode(content), # max length 128
            out_trade_no = out_trade_no,
        )

        if note:
            data['passback_params'] = note

        if notify_url: # alipay 会进行通知
            data['notify_url'] = notify_url
        if return_url: # url 跳转回来，成功支付后
            data['return_url'] = return_url

        return data


    def verify_request(self):
        # 校验支付宝通知请求的合法性
        if request.method == 'POST':
            request_doc = request.form.to_dict() or request.args.to_dict()
        else:
            request_doc = request.args.to_dict()
        return self.verify_request_doc(request_doc)

    def verify_request_doc(self, request_doc):
        sign = request_doc.pop('sign', None)
        sign_type = request_doc.pop('sign_type', None)

        if not sign:
            return False
        try:
            sign = base64.b64decode(sign)
        except:
            return False

        # 检验签名的时候，需要去除 sign、sign_type
        # 先尝试用 partner， 再用 platform 公钥
        sign_content = self._get_sign_s(request_doc, excludes=['sign', 'sign_type'])
        sha_sign_content = SHA.new(sign_content)
        verified = False
        if self.verifier:
            verified = self.verifier.verify(sha_sign_content, sign)
        if not verified:
            verified = platform_verifier.verify(sha_sign_content, sign)
        return verified


    def _get_sign_s(self, post_data, excludes=None):
        #post_data = post_data.copy()
        #post_data.pop('sign_type', None)
        excludes = excludes or []  # ['sign', 'sign_type']
        post_data = {
            k: v
            for k, v in post_data.items()
            if len(smart_str(v)) and k not in excludes
        }
        # 按照 alipay 的规则，key 的升序排列形成 content
        post_data_s = '&'.join('%s=%s'%(k, v) for k, v in sorted(post_data.items()))
        post_data_s = smart_str(post_data_s)
        return post_data_s

    def _sign(self, post_data, excludes=None):
        post_data_s = self._get_sign_s(post_data, excludes=excludes)
        signature = crypto.sign(self.cert, post_data_s, 'sha1')
        return base64.standard_b64encode(signature).decode()





class AlipayAPI(BaseAlipay):
    def __init__(self, private_key, public_key=None, pid=None, app_id=None, api_url='',):
        # private_key 是 str 类型
        # product api: 'https://openapi.alipay.com/gateway.do'
        # sandbox api: 'https://openapi.alipaydev.com/gateway.do'
        # 即时到账的网关： https://mapi.alipay.com/gateway.do
        BaseAlipay.__init__(self, private_key, public_key=public_key)
        self.api_url = api_url or 'https://openapi.alipay.com/gateway.do'
        self.app_id = smart_unicode(app_id or '').strip()
        self.default_request = {
            'charset': 'utf-8',
            'sign_type': 'RSA',
            'version': '1.0',
            'app_id': self.app_id
        }
        self.pid = smart_unicode(pid or '').strip()  # 有pid的话，可以使用直接支付的逻辑，不用指定app_id
        self.direct_alipay = DirectAlipay(self.pid, private_key)

    # methods
    def query(self, trade_no, is_alipay_id=True):
        data = dict(trade_no=trade_no)
        if not is_alipay_id:
            data = dict(out_trade_no=trade_no)
        return self._send_request('alipay.trade.query', data)['alipay_trade_query_response']


    def pay(self, price, title, content, notify_url='', return_url='', out_trade_no='', note='', qrcode=False):
        if self.pid and not qrcode:
            # 使用直接付款的 api
            return self.direct_alipay.pay(price, title, content, notify_url, return_url, out_trade_no, note)
        else:
            pay_request_data = self.get_pay_request_data(price, title, content, notify_url, return_url, out_trade_no, note)
            redirect_url = self._send_request('alipay.trade.wap.pay', pay_request_data)
            return redirect_url


    def refund(self, trade_no, amount, reason=''):
        # 退款
        data = {
            'trade_no': smart_str(trade_no),
            'refund_amount': smart_str(amount),
        }
        if reason:
            data['refund_reason'] = smart_unicode(reason)[80]

        return self._send_request('alipay.trade.refund', data)



    # utils

    def is_paid_by_remote(self, trade_no, is_alipay_id=True):
        # 交易状态：WAIT_BUYER_PAY（交易创建，等待买家付款）
        # TRADE_CLOSED（未付款交易超时关闭，或支付完成后全额退款）
        # TRADE_SUCCESS（交易支付成功）
        # TRADE_FINISHED（交易结束，不可退款）
        payment_status = self.query(trade_no, is_alipay_id)
        trade_status = payment_status.get('trade_status')
        if trade_status in ['TRADE_SUCCESS']: # 'TRADE_FINISHED',
            return True
        else:
            return False

    def is_paid(self, payment_doc):
        if isinstance(payment_doc, dict):
            trade_status = payment_doc.get('trade_status')
            if trade_status in ['TRADE_SUCCESS']: # 'TRADE_FINISHED',
                return True
        return False


    # 基本的请求信息 starts

    def _send_request(self, method, data):
        if not self.cert:
            return # ignore
        # 发送请求信息 # data is a dict
        data = {key:smart_str(value) for key, value in data.items()} # value 全部转为 utf8 编码
        biz_content = json.dumps(data)
        post_data = dict(
            self.default_request,
            method = method,
            timestamp = get_cn_timestamp(),
            biz_content = biz_content,
        )
        sign = self._sign(post_data) # 进行签名
        post_data['sign'] = sign

        r = requests.post(self.api_url, data=post_data, allow_redirects=False)

        return self.compile_response(r)

    # 基本的请求信息 ends


class DirectAlipay(BaseAlipay):
    def __init__(self, pid, private_key):
        # pid == partner id
        BaseAlipay.__init__(self, private_key)
        self.api_url = 'https://mapi.alipay.com/gateway.do'
        self.pid = pid
        self.default_request = {
            '_input_charset': 'UTF-8',
            'sign_type': 'RSA',
            'service': 'create_direct_pay_by_user',
            'partner': self.pid,
            'seller_id': self.pid,
        }


    def _send_request(self, data):
        if not self.cert:
            return # ignore
        # 发送请求信息 # data is a dict
        post_data = self.default_request.copy()
        post_data.update(data)
        post_data = {key:smart_str(value) for key, value in post_data.items()} # value 全部转为 utf8 编码
        sign = self._sign(post_data, excludes=['sign', 'sign_type']) # 进行签名
        post_data['sign'] = sign

        params_s = urlencode(post_data)
        # 直接 POST 的话，中文会有问题....
        r = requests.post(self.api_url+"?"+params_s, allow_redirects=False)

        return self.compile_response(r)


    def pay(self, price, title, content, notify_url='', return_url='', out_trade_no='', note=''):
        pay_request_data = self.get_pay_request_data(price, title, content, notify_url, return_url, out_trade_no, note=note)
        pay_request_data['total_fee'] = pay_request_data.pop('total_amount')
        pay_request_data['payment_type'] = 1

        redirect_url = self._send_request(pay_request_data)
        return redirect_url

