# coding: utf8
import datetime
from farbox_bucket.utils.ssdb_utils import hset, hdel, hget
from farbox_bucket.bucket.domain.utils import get_bucket_from_domain
from farbox_bucket.utils.ssl_related import load_key_content, load_cert_content, load_cert_contents




def get_ssl_cert_for_domain(domain):
    domain = domain.strip().lower()
    doc = hget('_domain_ssl', domain) or {}
    if not doc and domain.startswith("www."):
        domain = domain.replace("www.", "", 1)
        doc = hget('_domain_ssl', domain) or {}
    if not isinstance(doc, dict):
        doc = {}
    return doc

def set_ssl_cert_for_domain(domain, ssl_key, ssl_cert, by_user=False, bucket=None):
    domain = domain.strip().lower()
    doc = dict(
        ssl_key = ssl_key,
        ssl_cert = ssl_cert,
        created_at = datetime.datetime.utcnow(),
        by_user = by_user,
        bucket = bucket,
    )
    hset('_domain_ssl', domain, doc)


def del_ssl_cert_for_domain(domain):
    domain = domain.strip().lower()
    hdel('_domain_ssl', domain)



def set_ssl_cert_for_domain_by_user(domain, ssl_key, ssl_cert):
    # return None or error_info
    # 需要确定 domain 对应到 bucket
    bucket = get_bucket_from_domain(domain)
    if not bucket:
        return "the domain can not match bucket"
    if not ssl_key:
        return 'SSL Certificate Key is error'
    try:
        load_key_content(ssl_key)
    except:
        return 'SSL Certificate Key is error'
    if not ssl_cert:
        return 'SSL Certificate is error'
    try:
        load_cert_contents(ssl_cert)
    except:
        return 'SSL Certificate is error'
    set_ssl_cert_for_domain(domain, ssl_key, ssl_cert, by_user=True, bucket=bucket)
