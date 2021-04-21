#coding: utf8
from __future__ import absolute_import
from functools import partial
import requests


from farbox_bucket.bucket import set_buckets_cursor_for_remote_node, get_buckets_cursor_for_remote_node
from farbox_bucket.bucket.node import get_node_url, get_remote_nodes_to_sync_from
from farbox_bucket.utils.env import get_env
from farbox_bucket.utils.gevent_run import do_by_gevent_pool


from farbox_bucket.bucket.sync.sync_api import sync_bucket_from_remote_node





def get_buckets_to_sync_from_remote_node(remote_node):
    # 从一个 node 上获得需要同步到本地的 buckets 列表
    # 本地本身也是一个在线的节点
    # 数据库内会有对应 node 的 cursor 记录状态，以确保，只获得最新需要同步的 buckets
    # todo 多个bucket，其修改时间一样， cursor hit 到的，会不会 ignore 掉某些 buckets？
    buckets = []
    cursor = get_buckets_cursor_for_remote_node(remote_node)
    url = get_node_url(remote_node, '_system/buckets')
    data = {}
    if cursor:
        try:
            cursor = int(cursor)
        except:
            cursor = ''
    if cursor:
        data['cursor'] = cursor+1
    try:
        response = requests.post(url,  data=data, timeout=180)
        raw_result = response.json()
    except:
        return []
    bucket_cursor = None
    for bucket, bucket_cursor in raw_result:
        buckets.append(bucket)
    if bucket_cursor: # last one
        set_buckets_cursor_for_remote_node(remote_node, bucket_cursor)
    return buckets




def sync_from_remote_node(remote_node):
    # 从 remote node 上完全同步所有 buckets 的时候， 每次任务实际上是每次 1000 个 buckets
    # 在下次 cronjob 触发的时候，会在上次 cursor 保存的状态后，进行后面 1000 个同步，如此周而复始
    buckets = get_buckets_to_sync_from_remote_node(remote_node)
    if not buckets:
        return
    server_sync_token = get_env("server_sync_token")
    if not server_sync_token:
        return
    job_func = partial(sync_bucket_from_remote_node, remote_node=remote_node, server_sync_token=server_sync_token)
    do_by_gevent_pool(pool_size=100, job_func=job_func, loop_items=buckets, timeout=30*60)




def sync_buckets_from_remote_nodes_by_gevent(pool_size=20):
    #
    remote_nodes = get_remote_nodes_to_sync_from()
    if not remote_nodes:
        return
    do_by_gevent_pool(pool_size=pool_size, job_func=sync_from_remote_node, loop_items=remote_nodes, timeout=60*60)




