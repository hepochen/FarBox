# coding: utf8
from farbox_bucket.utils.pay.alipay_api import AlipayAPI

def check_qrcode_alipay(app_id, private_key):
    alipay = AlipayAPI(app_id=app_id, private_key=private_key)
    info = alipay.pay(0.01, 'hello', 'world', qrcode=True)
    print(info)





