# coding: utf8
from __future__ import absolute_import
from farbox_bucket.settings import ADMIN_DOMAIN_PASSWORD
from farbox_bucket.utils.ssdb_utils import hset, hexists, hdel, hget
from farbox_bucket.bucket import is_valid_bucket_name, has_bucket
from farbox_bucket.bucket.utils import get_admin_bucket
from farbox_bucket.bucket.domain.info import SYSTEM_DOMAINS, get_domain_basic_info, is_valid_domain, get_domain_text_record
from farbox_bucket.bucket.domain.utils import pull_domain_from_bucket, get_bucket_domains, push_domain_to_bucket
import time



def register_bucket_domain_from_system(bucket, domain, is_admin=False):
    # 注册系统提供的二级域名
    # 一个 bucket 只允许注册一个系统提供的二级域名
    # 返回 None or 错误信息
    domain = domain.strip().lower()
    if not is_valid_bucket_name(bucket):
        return 'invalid bucket'
    domain_info = get_domain_basic_info(domain, is_admin=is_admin)
    is_system_domain = domain_info.get('is_system_domain', False)
    is_allowed = domain_info.get('allowed', False)
    if is_system_domain and is_allowed:
        r_domain_info = hget('_rdomain', bucket) # 当前 bucket 是否已经域名绑定了
        parked_domain_info = hget('_domain', domain) # 这个域名是否已经被其它 bucket 绑定了

        if parked_domain_info:  # domain 已经注册过了
            if parked_domain_info.get('bucket') == bucket:
                return None
            return '%s is used by other bucket' % domain

        if r_domain_info:  # bucket 已经绑定过 domain 了
            master_old_domain = r_domain_info.get('domain')
            if master_old_domain == domain:
                return None
            else:
                # 一个 bucket 只能绑定一个系统的二级域名，就会删除之前的一个
                hdel('_rdomain', bucket)
                hdel('_domain', master_old_domain)
                pull_domain_from_bucket(bucket, master_old_domain) # 汇总 domains
        # 一个 _rdomain, 作为一个反向的对应, 一个 bucket 只能有一个系统级的域名 ?
        domain_doc = dict(
            bucket = bucket,
            domain = domain,
            created_at = time.time()
            )
        hset('_domain', domain, domain_doc)
        hset('_rdomain', bucket, domain_doc)
        push_domain_to_bucket(bucket, domain) # 汇总 domains
        return None

    else:
        return '%s is not allowed for bucket:%s' % (domain, bucket)


def register_bucket_independent_domain(bucket, domain):
    # 注册独立域名， 这个前提是域名已经 park 到当前节点，并且已经做了必要的校验
    # 返回 None or 错误信息
    domain = domain.strip().lower()
    if not is_valid_domain(domain):
        return 'domain format error or not supported'
    if not is_valid_bucket_name(bucket):
        return 'invalid bucket'
    if not has_bucket(bucket):
        return 'current node does not have bucket:%s'%bucket
    bucket = bucket.strip()
    old_domain_info = hget('_domain', domain) or {}
    old_matched_bucket = old_domain_info.get('bucket')
    if old_matched_bucket == bucket: # # 已经注册过了，不做处理
        return None
        #return 'registered already for this bucket, no need to change'
    if domain == "thisisadomainfortest.com": # for test only
        bucket_in_domain_text = bucket
    else:
        bucket_in_domain_text = get_domain_text_record(domain)
    if bucket_in_domain_text == bucket:
        # 比如 A 曾经注册过，后来 domain 是 B 的了，那么 B 修改了 TXT 记录，就可以重新注册了。
        # at last, create or modify
        hset('_domain', domain, dict(
            bucket = bucket,
            created_at = time.time(),
        ))
        push_domain_to_bucket(bucket, domain) # 汇总 domains
        return None # done
    else:
        if bucket_in_domain_text:
            if not is_valid_bucket_name(bucket_in_domain_text):
                return 'invalid bucket format in TXT record: %s' % bucket_in_domain_text
            else:
                return 'TXT record is not matched to %s' % bucket
        else:
            return 'should set TXT record for domain first'



def delete_bucket_domain(domain, bucket=None):
    # 删除 bucket 上的 domain， 支持独立域名以及系统二级域名
    # 这里未做是否有权限 unregister 的校验， 需要前置校验
    # 未指定 bucket，就会删除 domain 对应的唯一 bucket；指定了，则进行 bucket 一致性校验
    # 返回 None or 错误信息
    domain = domain.strip().lower()
    if bucket and not is_valid_bucket_name(bucket):
        return 'invalid bucket'
    domain_record = hget('_domain', domain)
    if domain_record:
        to_delete = False
        bucket_in_db = domain_record.get('bucket')
        if bucket and bucket_in_db==bucket:
            to_delete = True
        elif not bucket and bucket_in_db:
            to_delete = True
        if to_delete:
            hdel('_domain', domain)
            hdel('_rdomain', bucket_in_db)  # 尝试删除 rdomain 上的信息, 这样下次 bucket 还能再注册一个系统二级域名
            pull_domain_from_bucket(bucket_in_db, domain) # 汇总 domains
            return None
    return 'can not find the matched domain record to remove for %s' % domain



### shortcuts starts #######

def register_system_domain(domain, bucket):
    return register_bucket_domain_from_system(domain=domain, bucket=bucket)

def unregister_bucket_domain(domain, bucket=None):
    return delete_bucket_domain(domain=domain, bucket=bucket)


def register_bucket_domain(domain, bucket, admin_password=None):
    # 这里的调用，是注册系统提供的二级域名, 这个 domain 不需要校验， 但是，一个 bucket 只允许一个 domain
    # 此处调用的前提是， bucket 本身的权限进行了校验
    domain = domain.lower().strip()
    is_admin = False
    if admin_password and ADMIN_DOMAIN_PASSWORD==admin_password:
        is_admin = True
    if not is_admin:
        if bucket == get_admin_bucket():
            is_admin = True
    domain_basic_info = get_domain_basic_info(domain, is_admin=is_admin)
    is_allowed = domain_basic_info.get('allowed', False)
    is_system_domain = domain_basic_info.get('is_system_domain', False)
    if not is_allowed:
        return 'invalid domain or not allowed sub-domain'
    if is_system_domain:
        if not SYSTEM_DOMAINS:
            return 'current node has not system domains offer'
        error_info = register_bucket_domain_from_system(bucket=bucket, domain=domain, is_admin=is_admin)
        if error_info:
            return error_info
    else:
        error_info = register_bucket_independent_domain(bucket=bucket, domain=domain)
        if error_info:
            return error_info

### shortcuts ends #######