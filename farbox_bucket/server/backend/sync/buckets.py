#coding: utf8
from __future__ import absolute_import

from farbox_bucket.utils.gevent_run import run_long_time

from farbox_bucket.bucket.sync.node import sync_buckets_from_remote_nodes_by_gevent
from farbox_bucket.bucket.sync.remote import sync_buckets_from_remote_marked_by_gevent



@run_long_time(wait=10, sleep_at_end=10*60, log='sync from remote nodes')
def sync_buckets_from_remote_nodes():
    sync_buckets_from_remote_nodes_by_gevent(pool_size=20)




@run_long_time(wait=10, sleep_at_end=60, log='sync buckets marked from remote')
def sync_buckets_from_remote_marked():
    sync_buckets_from_remote_marked_by_gevent(pool_size=30)





