# coding: utf8
import datetime
from farbox_bucket.utils import smart_unicode
from farbox_bucket.utils.ssdb_utils import hset, hget, hsize, hdel, hscan_for_dict_docs
from farbox_bucket.bucket.utils import has_bucket, string_types
from farbox_bucket.bucket.token.bucket_signature_and_check import get_signature_for_bucket, check_signature_for_bucket
from farbox_bucket.bucket.domain.utils import get_bucket_domains


def get_wechat_bind_code_for_bucket(bucket):
    if not has_bucket(bucket):
        return ""
    signature = get_signature_for_bucket(bucket, salt="wechat")
    code = "%s-%s" % (bucket, signature)
    return code


def check_wechat_bind_code(bind_code):
    # 校验成功后，比较偷懒，返回的不是 True，而是 bucket
    if not isinstance(bind_code, string_types):
        return False
    if "-" not in bind_code:
        return False
    bucket, signature = bind_code.strip().split("-", 1)
    if not check_signature_for_bucket(bucket, signature=signature, hours=1, salt="wechat"): # 1 小时有效期
        return False
    else:
        if not has_bucket(bucket):
            return False
        else:
            return bucket


def get_bucket_namespace_for_wechat(bucket):
    namespace = "%s_%s" % (bucket, "wechat")
    return namespace


def get_bucket_by_wechat_user_id(wechat_user_id):
    if not isinstance(wechat_user_id, string_types):
        return None
    return hget("wechat_accounts", wechat_user_id)


def get_name_by_wechat_user_id(wechat_user_id):
    if not isinstance(wechat_user_id, string_types):
        return None
    return hget("wechat_names", wechat_user_id)


def set_name_by_wechat_user_id(wechat_user_id, name):
    if not isinstance(wechat_user_id, string_types) or not isinstance(name, string_types):
        return
    name = smart_unicode(name)
    if not name:
        return
    return hset("wechat_names", wechat_user_id, name)


def get_wechat_user_docs_by_bucket(bucket, with_name=False):
    if not isinstance(bucket, string_types):
        return []
    docs = hscan_for_dict_docs(get_bucket_namespace_for_wechat(bucket))
    if with_name:
        for doc in docs:
            doc["name"] = get_name_by_wechat_user_id(doc.get("uid"))
    return docs

def get_bound_wechat_accounts_count(bucket):
    namespace = get_bucket_namespace_for_wechat(bucket)
    return hsize(namespace)

################################################################################################



def get_bucket_bind_status_reply(bucket):
    if not bucket:
        reply = u"尚未绑定任何 Bucket"
    else:
        name = bucket
        domains = get_bucket_domains(bucket)
        if domains:
            name = domains[0]
        reply = u"已绑定至 %s\n\n协作人数: %s" % (name, get_bound_wechat_accounts_count(bucket))
    return reply


def get_wechat_account_bind_status_reply(wechat_user_id):
    bucket = get_bucket_by_wechat_user_id(wechat_user_id)
    return get_bucket_bind_status_reply(bucket)


def bind_bucket_by_wechat(wechat_user_id, bind_code):
    bucket = check_wechat_bind_code(bind_code)
    if not bucket:
        return u'绑定信息有误或者已经超过1小时有效期'

    # 绑定到当前的 bucket 下， 一个 bucket 下可以有多个 wechat account
    doc = dict(
        name = "",
        uid = wechat_user_id,
        date = datetime.datetime.utcnow(),
    )
    hset(get_bucket_namespace_for_wechat(bucket), wechat_user_id, doc)  # list

    # 一个 wechat_user 只能对应一个 bucket
    hset("wechat_accounts", wechat_user_id, bucket)

    return get_bucket_bind_status_reply(bucket)



def unbind_wechat_account(wechat_user_id):
    bucket = get_bucket_by_wechat_user_id(wechat_user_id)
    if bucket:
        hdel("wechat_accounts", wechat_user_id)
        hdel(get_bucket_namespace_for_wechat(bucket), wechat_user_id)
        return True
    else:
        return False



def remove_wechat_accounts_for_bucket(bucket):
    wechat_user_docs = get_wechat_user_docs_by_bucket(bucket)
    for doc in wechat_user_docs:
        wechat_user_id = doc.get("uid")
        if not wechat_user_id:
            continue
        hdel("wechat_accounts", wechat_user_id)
        hdel(get_bucket_namespace_for_wechat(bucket), wechat_user_id)

    # hclear(get_bucket_namespace_for_wechat(bucket))
