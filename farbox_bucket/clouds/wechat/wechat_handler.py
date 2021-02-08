# coding: utf8
import xmltodict
from flask import request
from farbox_bucket.settings import DEBUG
from farbox_bucket.utils import smart_unicode
from farbox_bucket.utils.env import get_env
from farbox_bucket.utils.memcache_block import is_blocked
from farbox_bucket.clouds.wechat.utils.check import check_is_from_wechat
from farbox_bucket.clouds.wechat.utils.message import send_wechat_message
from .wechat_text_image_sync_worker import wechat_text_image_handler
from .bind_wechat import unbind_wechat_account, get_wechat_account_bind_status_reply, bind_bucket_by_wechat, \
    get_bucket_by_wechat_user_id


WECHAT_TOKEN = (get_env("wechat_token") or "").strip()

is_wechat_server_valid = True if WECHAT_TOKEN else False


def compile_for_wechat(raw_data):
    if isinstance(raw_data, dict):
        xml_data = raw_data
    else:
        xml_data = xmltodict.parse(raw_data)["xml"]

    wechat_user_id = xml_data.get("FromUserName")
    msg_type = xml_data.get("MsgType")
    event_name = (xml_data.get("Event") or "").lower()
    event_key = (xml_data.get("EventKey") or "").lower()

    #with open("/tmp/test.json", "w") as f:
        #f.write(json_dumps(xml))

    if event_name: # 事件类型，如果没有 reply， 默认不进行回应
        if event_name == "click":
            if event_key == "unbind":
                done = unbind_wechat_account(wechat_user_id)
                if done:
                    return u"已经解除网站的绑定"
                else:
                    return u"尚未绑定，无需解绑。:)"
            elif event_key == "bind_status":
                return get_wechat_account_bind_status_reply(wechat_user_id)
        elif event_name == "scancode_waitmsg":
            scan_info = xml_data.get("ScanCodeInfo") or {}
            if not isinstance(scan_info, dict):
                return ""
            scan_result = smart_unicode(scan_info.get("ScanResult") or "")
            if event_key == "bind":
                # 绑定网站
                return bind_bucket_by_wechat(wechat_user_id, scan_result)
        return ""


    bucket = get_bucket_by_wechat_user_id(wechat_user_id)

    if not bucket:
        return u"请先绑定一个 Bucket，才能使用此功能。 :)"

    if msg_type not in ["text", "image", "voice"]: # link
        return u"尚不支持的消息类型"

    msg_id = xml_data.get("MsgId")

    # 看是否 block 了, 可以避免数据重复处理
    block_id = "w-%s" % msg_id
    if (msg_id and not DEBUG) and is_blocked(block_id, ttl=60*10): # 10 分钟内已经处理过了的，不重复处理了
        return ""

    return wechat_text_image_handler(wechat_user_id=wechat_user_id, bucket=bucket, xml_data=xml_data)



def wechat_web_handler():
    if request.method == "GET": # 微信端过来的验证行为，其它时候，都是 POST 数据过来
        return request.args.get("echostr") or ""
    if not WECHAT_TOKEN:
        return ""
    if not check_is_from_wechat(WECHAT_TOKEN):
        return ""
    xml_data = xmltodict.parse(request.data)["xml"]
    reply = compile_for_wechat(xml_data)
    if not reply:
        return ""
    else:
        from_user_name = xml_data.get("FromUserName") or ""
        to_user_name = xml_data.get("ToUserName") or ""
        return send_wechat_message(reply, from_user_name, to_user_name)
