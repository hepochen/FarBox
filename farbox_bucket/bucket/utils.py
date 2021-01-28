#coding: utf8
from __future__ import absolute_import
from farbox_bucket.utils import to_md5, to_sha1
import time
from farbox_bucket.utils import hash_password, string_types
from farbox_bucket.utils.ssdb_utils import hset, hget, hexists, hsize, hscan, zset, zdel, hdel, hclear, zclear, zget, zsize, ssdb_get
from farbox_bucket.utils.encrypt.key_encrypt import is_valid_public_key, to_clean_key, get_public_key_from_private_key, get_md5_for_key
from farbox_bucket.bucket.defaults import bucket_config_doc_id_names, zero_id, config_names_not_allowed_set_by_user, \
    zero_id_for_files, BUCKET_RECORD_SORT_TYPES
from farbox_bucket.bucket.token.simple_encrypt_token import get_normal_data_by_simple_token
from farbox_bucket.utils.data import json_dumps
from farbox_bucket.utils.encrypt.simple import simple_encrypt
from flask import g
import ujson as json


def is_valid_bucket_name(bucket):
    if not bucket:
        return False
    if not isinstance(bucket, string_types):
        return False
    bucket = bucket.strip()
    if len(bucket)!=40:
        return False
    else:
        return True


def get_bucket_by_public_key(public_key, verify=True):
    # the bucket is from public key, client & server 端都会用到的
    if not public_key:
        return None
    if verify and not is_valid_public_key(public_key):
        return None
    public_key = to_clean_key(public_key)
    public_key_id = to_sha1(public_key)
    bucket = public_key_id
    return bucket


def get_bucket_by_private_key(private_key):
    if not private_key:
        return None
    public_key = get_public_key_from_private_key(private_key)
    bucket = get_bucket_by_public_key(public_key, verify=False)
    return bucket




def get_bucket_configs(bucket, config_type='init'):
    # 'init', 'user', 'pages'
    if not bucket:
        return {}

    config_doc_id = bucket_config_doc_id_names.get(config_type)
    if not config_doc_id:
        return {}
    g_var_name = 'bucket_%s_cached_%s_value' % (bucket, config_type)
    if hasattr(g, g_var_name):
        return getattr(g, g_var_name)
    info  = hget(bucket, config_doc_id)
    if not info or not isinstance(info, dict):
        info = {}
    if config_type in ['user', 'secret'] and info:
        # 需要解密的数据类型
        raw_data = info.get('data')
        real_info = get_normal_data_by_simple_token(bucket, raw_data, force_py_data=True)
        if not isinstance(real_info, dict):
            real_info = {}
        info = real_info

    if config_type == "site" and has_bucket(bucket):
        # site 默认给的 settings
        site_configs = default_site_configs.copy()
        site_configs.update(info)
        info = site_configs

    try:
        setattr(g, g_var_name, info)
    except:
        pass
    return info


def get_bucket_init_configs(bucket):
    return get_bucket_configs(bucket, 'init')


def get_bucket_user_configs(bucket):
    # # username, password, fields=[x, x, x, x]
    return get_bucket_configs(bucket, 'user')


def get_bucket_pages_configs(bucket):
    return get_bucket_configs(bucket, 'pages')

def get_bucket_orders_configs(bucket):
    return get_bucket_configs(bucket, 'orders')

def get_bucket_site_configs(bucket=None):
    if bucket is None:
        bucket = getattr(g, 'bucket', None)
    return get_bucket_configs(bucket, 'site')


def get_bucket_secret_site_configs(bucket=None):
    if bucket is None:
        bucket = getattr(g, 'bucket', None)
    return get_bucket_configs(bucket, 'secret')


def get_bucket_files_info(bucket):
    return get_bucket_configs(bucket, 'files')

def get_bucket_posts_info(bucket):
    return get_bucket_configs(bucket, 'posts')

def get_bucket_files_configs(bucket):
    return get_bucket_files_info(bucket)



def get_public_key_from_bucket(bucket):
    bucket_configs = get_bucket_init_configs(bucket)
    public_key = bucket_configs.get('public_key') or ''
    return public_key


def has_bucket(bucket):
    if not bucket:
        return False
    if not isinstance(bucket, string_types):
        return False
    bucket = bucket.strip()
    return hexists(bucket, zero_id)

def get_buckets_size():
    # zset for "buckets" 会存储一些 bucket 的信息，可以认为它的存在，粗略代表了 bucket 的数量
    return zsize('buckets')



cached_admin_bucket = None
def get_admin_bucket():
    global  cached_admin_bucket
    from farbox_bucket.settings import ADMIN_BUCKET
    if cached_admin_bucket is not None:
        return cached_admin_bucket
    admin_bucket = ADMIN_BUCKET
    if not admin_bucket:
        admin_bucket = get_first_bucket()
    admin_bucket = admin_bucket or ""
    cached_admin_bucket = admin_bucket
    return admin_bucket


def get_first_bucket():
    return ssdb_get("first_bucket") or ""


def re_configs_for_user(configs):
    # 将 user 上其 key 以 password 结尾的，进行处理，避免明文密码
    for k, v in list(configs.items()):
        if k.endswith('password') and v:
            hashed_v = hash_password(v)
            configs[k] = hashed_v


default_site_configs = {
    "utc_offset": 8,
    "image_max_height": "",
    "title": "",
    "image_max_width": "1560",
    "sub_title": "",
    "image_max_type": "webp-jpg",
    "post_per_page": 3,
    "mathjax": False,
    "echarts": False,
    "mermaid": False,
    "anti_theft_chain": True,
}

def set_bucket_configs(bucket, configs, config_type='site', by_system=False):
    # config_type in site, user, files, pages,
    if not configs or not isinstance(configs, dict):
        return False # ignore
    if not has_bucket(bucket):
        return False

    if not by_system and config_type in config_names_not_allowed_set_by_user:
        # 不是系统处理的，而且 config 类型不是用户可以修改的， ignore
        return False

    if config_type == 'user': # hash the password
        re_configs_for_user(configs)

    if config_type in ['site'] and isinstance(configs, dict) and not configs.get('date'):
        configs['date'] = int(time.time())

    # 设定 mtime
    if config_type in ['pages', 'site']:
        configs['mtime'] = time.time()

    configs['_config_type'] = config_type

    config_doc_id = bucket_config_doc_id_names.get(config_type)
    if not config_doc_id:
        return False

    if config_doc_id:
        hset(bucket, config_doc_id, configs)

        # todo 变动 id 上的数据变化，这个怎么进行同步呢？按照固定区域查询？
        set_bucket_into_buckets(bucket)

        return True
    else:
        return False



def update_bucket_max_id(bucket, max_id):
    # 只有在完全新的记录生成时才会处置
    # 如果只是 node 之间的同步， 并不会增加其 max_id
    hset('_bucket_max_id', bucket, max_id)

def update_bucket_delta_id(bucket, delta_id):
    # 这个是同步时候用的
    hset('_bucket_delta_id', bucket, delta_id)




def get_bucket_max_id(bucket):
    max_id = hget('_bucket_max_id', bucket) or ''
    return max_id

def get_bucket_delta_id(bucket):
    delta_id = hget('_bucket_delta_id', bucket) or ''
    return delta_id


def get_bucket_meta_info(bucket):
    meta_info = dict(
        max_id = get_bucket_max_id(bucket),
        delta_id = get_bucket_delta_id(bucket)
    )
    return meta_info


def set_bucket_into_buckets(bucket):
    # 记录到当前的 buckets 信息中, 主要表示当前什么时间，某个 bucket 被更新了
    # 更新 configs 的字段，也会更新
    # create record 会更新
    zset('buckets', bucket, int(time.time()*1000))


def remove_bucket_from_buckets(bucket):
    zdel("buckets", bucket)


def get_bucket_last_updated_at(bucket):
    last_updated_at = zget('buckets', bucket) or ''
    return last_updated_at


def set_buckets_cursor_for_remote_node(node, cursor):
    hset('_remote_buckets_cursor', node, cursor)


def get_buckets_cursor_for_remote_node(node):
    cursor = hget('_remote_buckets_cursor', node) or ''
    return cursor


def get_bucket_full_info(bucket):
    info = {}
    configs = get_bucket_init_configs(bucket)
    user_configs = get_bucket_user_configs(bucket)
    info['configs'] = configs
    info['user_configs'] = user_configs
    info['size'] = hsize(bucket)
    meta_info = get_bucket_meta_info(bucket)
    info.update(meta_info)
    return info




########################################################################################################################



# 在某个 namespace 上，增加记录，表示后续需要同步的；同步了，则进行删除
# 考虑到系统保留的性质，namespace 必须以 _ 开头
# 除了 _bucket_to_sync，还有 _bucket_to_sync_ipfs 两个 namespace
def basic_mark_bucket_to_sync(namespace, bucket, **kwargs):
    if not bucket:
        return
    if not is_valid_bucket_name(bucket):
        return
    if not has_bucket(bucket):
        return
    if not namespace.startswith('_'):
        namespace = '_' + namespace
    data = dict(
        bucket = bucket,
        date = time.time(),
    )
    if kwargs:
        data.update(kwargs)
    hset(namespace, bucket, data, ignore_if_exists=True)


def basic_remove_mark_bucket_to_sync(namespace, bucket):
    if not bucket:
        return
    if not namespace.startswith('_'):
        namespace = '_' + namespace
    hdel(namespace, bucket)


def basic_get_buckets_to_sync(namespace, limit=1000):
    if not namespace.startswith('_'):
        namespace = '_' + namespace
    result = hscan(namespace, limit=limit) or []
    if result:
        buckets_data = []
        for bucket, bucket_data in result:
            try:
                bucket_data = json.loads(bucket_data)
            except:
                continue
            buckets_data.append(bucket_data)
        return buckets_data
    else:
        return []






def get_bucket_name_for_path(bucket):
    # path 从某种角度来说是 id
    bucket_name = '%s_id' % bucket
    return bucket_name

def get_bucket_name_for_url(bucket):
    bucket_name = '%s_url' % bucket
    return bucket_name

def get_bucket_name_for_slash(bucket):
    bucket_name = '%s_slash' % bucket
    return bucket_name


def get_bucket_name_for_order(bucket, data_type):
    bucket_name = '%s_%s_order' % (bucket, data_type)
    return bucket_name


def get_order_bucket_name(bucket, sort_data_type):
    sort_bucket_name = '%s_%s_order' % (bucket, sort_data_type)
    return sort_bucket_name

def get_related_bucket_names(bucket, includes_self=False):
    related_bucket_names = []
    for sort_data_type in BUCKET_RECORD_SORT_TYPES: # zset
        sort_bucket_name = get_order_bucket_name(bucket, sort_data_type)
        related_bucket_names.append(sort_bucket_name)
    extra_set_suffixes = ['url', 'id', 'slash']
    for extra_set_suffix in extra_set_suffixes:
        extra_bucket = '%s_%s' % (bucket, extra_set_suffix)
        related_bucket_names.append(extra_bucket)
    if includes_self:
        related_bucket_names.append(bucket)
    return related_bucket_names



def clear_related_buckets(bucket):
    related_buckets = get_related_bucket_names(bucket, includes_self=True)
    for related_bucket in related_buckets:
        if related_bucket.endswith('_order') or related_bucket.endswith('_slash'):
            zclear(related_bucket)
        else:
            hclear(related_bucket)




# for user and secret config_type
def encrypt_configs_for_bucket(configs, private_key_md5):
    configs = dict(
        data=simple_encrypt(json_dumps(configs), password=private_key_md5)
    )
    return configs


