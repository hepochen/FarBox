# coding: utf8
from __future__ import absolute_import

from farbox_bucket.utils.gevent_run import do_by_gevent_pool
from farbox_bucket.bucket.utils import basic_mark_bucket_to_sync, basic_remove_mark_bucket_to_sync, basic_get_buckets_to_sync
from farbox_bucket.bucket.sync.sync_api import sync_bucket_from_remote_node




###### 对单个 bucket 的 sync, 主要考虑单 bucket 的迁移问题 #########
def mark_bucket_to_sync_from_remote(bucket, remote_node, domain=None):
    # 表示要从一个 remote node 上同步一个 bucket 过来
    if not bucket or not remote_node:
        return
    basic_mark_bucket_to_sync(namespace='bucket_to_sync', bucket=bucket, remote_node=remote_node, domain=domain)


def remove_mark_bucket_to_sync_from_remote(bucket):
    basic_remove_mark_bucket_to_sync(namespace='bucket_to_sync', bucket=bucket)


def get_buckets_to_sync_from_remote():
    # 获得 buckets 的 list， 表示需要从 remote 同步数据回来的 bucket
    return basic_get_buckets_to_sync(namespace='bucket_to_sync')

###### 对单个 bucket 的 sync  ends #########



def do_sync_bucket_from_remote_marked(bucket_sync_info):
    if not isinstance(bucket_sync_info, dict):
        return
    bucket = bucket_sync_info.get('bucket')
    remote_node = bucket_sync_info.get('remote_node')
    if not bucket or not remote_node:
        remove_mark_bucket_to_sync_from_remote(bucket)
        return
    try:
        sync_bucket_from_remote_node(bucket, remote_node)
    finally:
        remove_mark_bucket_to_sync_from_remote(bucket)



########## 从 remote 同步所有需要更新的 buckets ###########
# 这是一个持续行为，所以，不求一次完全同步
# 默认是每次 （最多）1000 buckets 的同步
# 如果要 mark 一个 bucket 同步回来，需要有对应的 bucket 创建， 并且由私钥校对的数据发送过来，才能进行处理；


def sync_buckets_from_remote_marked_by_gevent(pool_size=30):
    buckets_info_list = get_buckets_to_sync_from_remote()
    if buckets_info_list:
        do_by_gevent_pool(pool_size=pool_size, job_func=do_sync_bucket_from_remote_marked, loop_items=buckets_info_list)



def sync_buckets_from_remote_marked_directly():
    buckets_info_list = get_buckets_to_sync_from_remote()
    for bucket_info in buckets_info_list:
        do_sync_bucket_from_remote_marked(bucket_sync_info=bucket_info)




