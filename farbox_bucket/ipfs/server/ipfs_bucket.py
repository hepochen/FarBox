# coding: utf8
from __future__ import absolute_import
from farbox_bucket.bucket.utils import  basic_mark_bucket_to_sync, basic_get_buckets_to_sync, basic_remove_mark_bucket_to_sync




###### 对单个 bucket 上 ipfs files 的 sync #########
def mark_bucket_to_sync_ipfs(bucket):
    # 只有更新 files 这个 config 的时候， 才会更新
    basic_mark_bucket_to_sync(namespace='bucket_to_sync_ipfs', bucket=bucket)


def remove_mark_a_bucket_to_sync_ipfs(bucket):
    basic_remove_mark_bucket_to_sync(namespace='bucket_to_sync_ipfs', bucket=bucket)


def get_buckets_to_sync_ipfs():
    return basic_get_buckets_to_sync(namespace='bucket_to_sync_ipfs')


###### 对单个 bucket ipfs files 的 sync  ends #########