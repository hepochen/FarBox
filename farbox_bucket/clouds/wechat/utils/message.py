# coding: utf8
import time
from jinja2 import Template
from ._message_template import SEND_MESSAGE_WECHAT_TEMPLATE

wechat_message_template = None
def get_wechat_message_template():
    global wechat_message_template
    if wechat_message_template is not None:
        return wechat_message_template
    wechat_message_template = Template(SEND_MESSAGE_WECHAT_TEMPLATE)
    return wechat_message_template


def send_wechat_message(message, from_user_name="", to_user_name=""):
    # xml.FromUserName, xml.ToUserName
    # 被动地发送文本信息，即响应微信API的请求
    # set_content_type('application/xml')
    timestamp = str(int(time.time()))
    xml_content = SEND_MESSAGE_WECHAT_TEMPLATE % (from_user_name, to_user_name, timestamp, message)
    return xml_content
