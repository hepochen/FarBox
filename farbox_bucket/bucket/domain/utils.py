#coding: utf8
from __future__ import absolute_import
import datetime
from flask import request, abort
from farbox_bucket.utils import smart_unicode, string_types
from farbox_bucket.utils.ssdb_utils import hget, hset, hdel
from farbox_bucket.utils.cache import cached
from farbox_bucket.settings import ADMIN_BUCKET, WEBSITE_DOMAINS



def get_bucket_domains(bucket):
    if not bucket:
        return []
    domains = hget("_domains", bucket, force_dict=False)
    if not isinstance(domains, (list, tuple)):
        return []
    else:
        return domains


def push_domain_to_bucket(bucket, domain, old_domain=None):
    if not isinstance(domain, string_types): return
    if old_domain:
        # 需要先移除旧的域名
        pull_domain_from_bucket(bucket, old_domain)
    domain = domain.lower().strip()
    domains = get_bucket_domains(bucket)
    if domain not in domains:
        domains.append(domain)
    hset("_domains", bucket, domains)


def pull_domain_from_bucket(bucket, domain):
    if not isinstance(domain, string_types): return
    domain = domain.lower().strip()
    domains = get_bucket_domains(bucket)
    if domain in domains:
        domains.remove(domain)
        hset("_domains", bucket, domains)


def get_bucket_from_domain(domain):
    if not domain:
        return
    domain = smart_unicode(domain)
    domain = domain.strip().lower()
    if ADMIN_BUCKET and domain in WEBSITE_DOMAINS:
        return ADMIN_BUCKET
    maybe_domains = [domain]
    if domain.startswith('www.'):
        maybe_domains.append(domain.replace('www.', '', 1))
    else:
        maybe_domains.append('www.%s'%domain)
    for d in maybe_domains:
        db_domain_info = hget('_domain', d)
        if db_domain_info and isinstance(db_domain_info, dict):
            return db_domain_info.get('bucket')


def get_system_domain_from_bucket(bucket):
    # 获得的是系统提供的二级域名，
    domain_doc = hget('_rdomain', bucket)
    if domain_doc and isinstance(domain_doc, dict):
        return domain_doc.get('domain')
    else:
        return None


@cached(10)
def get_bucket_from_domain_and_cached(domain):
    return get_bucket_from_domain(domain)




def not_allowed_for_parked_domain(func):
    def _curried(*args, **kwargs):
        domain = request.host
        if ':' in domain:
            domain = domain.split(':')[0]
        if domain in WEBSITE_DOMAINS:
            allowed = True
        else:
            bucket_bound_to_domain = get_bucket_from_domain_and_cached(domain)
            allowed = False if bucket_bound_to_domain else True
        if not allowed:
            return abort(404, 'page not found, and this url is for system')
        return func(*args, **kwargs)
    _curried.__name__ = func.__name__
    _curried.func_name = func.func_name
    _curried.original_func = func
    return _curried




