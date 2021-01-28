#coding: utf8
from __future__ import absolute_import
import re, os
from farbox_bucket.settings import SYSTEM_DOMAINS
from farbox_bucket.utils import string_types
from farbox_bucket.utils.cache import cached
from dns.resolver import Resolver, NoAnswer
from dns import rdatatype

domain_re = re.compile(r'^([a-z0-9\-_][a-z0-9-_]+[a-z0-9]\.|[a-z0-9]+\.)+([a-z]{2,3}\.)?[a-z]{2,9}$', flags=re.I)


_kept_sub_names = [
    'beta', 'www', 'wwww','blog', 'theme', 'themes', 'template', 'templates',
    'service', 'status', 'park', 'mail', 'app', 'apps','sync', 'dns', 'api', 'doc', 'docs', 'help', 'dig',
    'bbs', 'wiki', 'resource', 'pay', 'payment', 'hello', 'bill', 'status', 'wait', 'system', 'account', 'email',
    'prefix', 'admin', 'administrator', 'hostmaster', 'postmaster', 'webmaster',
    'demo', 'demos', 'pro', 'senior', 'standard', 'promo', 'daily', 'biz', 'auto', 'no-reply', 'noreply'
    'ns', 'ns1', 'ns2', 'ns3', 'ns4', 'ns5', 'ns6', 'ipfs', 'farbox',
]
kept_sub_names = set(_kept_sub_names)


def is_valid_domain(domain):
    domain = domain.strip().lower()
    if domain_re.match(domain):
        return True
    else:
        return False

def get_is_system_domain(domain):
    if not isinstance(domain, string_types):
        return False
    domain = domain.lower().strip()
    for system_domain in SYSTEM_DOMAINS:
        if domain.endswith("."+system_domain):
            return True
    return False


def get_domain_basic_info(domain, is_admin=False):
    domain = domain.strip().lower()
    info = dict(domain=domain, allowed=True)
    if not domain_re.match(domain):
        info['allowed'] = False
        return info
    #from_system = is_a_system_domain()
    allowed = True
    is_system_domain = False
    for system_domain in SYSTEM_DOMAINS:
        if domain.endswith("."+system_domain):
            is_system_domain = True
            sub_domain = domain[:-len(system_domain)].strip().strip('.')
            if '.' in sub_domain:
                # 系统的二级域名, 不允许再产生 3 级 & 以上的子域名, 不便验证
                allowed = False
            elif not is_admin:
                if sub_domain in kept_sub_names:
                    # 被保留的二级域名
                    allowed = False
            if allowed and len(sub_domain)<=2: # 两位以内的子域名保留
                allowed = False
            break
    info['allowed'] = allowed
    info['is_allowed'] = allowed
    info['is_system_domain'] = is_system_domain
    return info


dns_resolver = Resolver()
dns_resolver.nameservers = ['8.8.8.8', '8.8.4.4']
@cached(1*60) # 结果, 缓存 1 分钟
def get_domain_text_record(domain):
    domain = domain.strip().lower()
    if not domain_re.match(domain):
        return ''
    else:
        try:
            result = dns_resolver.query(domain, rdatatype.TXT)
            answer = result.response.answer[0]
            text_value = answer[0].to_text()
            text_value = text_value.strip().strip('"').strip("'").strip()
            return text_value
        except NoAnswer:
            return ''
        except:
            return ''
