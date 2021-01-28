# coding: utf8
from __future__ import absolute_import
from farbox_bucket.utils.cache import cached
from farbox_bucket.utils.system_status_recorder import record_system_timed_status
from farbox_bucket.bucket import get_bucket_files_info
from farbox_bucket.utils.memcache import get_cache_client
import os
try:
    from cPickle import loads as py_loads, dumps as py_dumps
except:
    from pickle import loads as py_loads, dumps as py_dumps
import time

# bucket 上的信息应该是 public 的状态的，不然也无法校验是否 ok
ipfs_pin_list_cache_filepath = '/tmp/ipfs_pin_list.data'


from .config import get_ipfs_api_client

# 每 5 分钟计算一次
@cached(60*5)
def get_local_ipfs_hashes():
    now = time.time()
    if os.path.isfile(ipfs_pin_list_cache_filepath):
        ipfs_pin_list_cache_filepath_m_time = os.path.getmtime(ipfs_pin_list_cache_filepath)
        if now - ipfs_pin_list_cache_filepath_m_time < 60: # 60s 内，只执行一次，避免影响到性能
            try: # hit the file cache
                with open(ipfs_pin_list_cache_filepath, 'rb') as f:
                    raw_content = f.read()
                ipfs_hashes = py_loads(raw_content)
                if isinstance(ipfs_hashes, set):
                    return ipfs_hashes
            except:
                pass
    ipfs_hashes = get_local_ipfs_hashes_without_cache()
    try:
        ipfs_hashes_content = py_dumps(ipfs_hashes)
        with open(ipfs_pin_list_cache_filepath, 'wb') as f:
            f.write(ipfs_hashes_content)
    except:
        pass
    return ipfs_hashes




@record_system_timed_status('get_ipfs_local_pin_list')
def get_local_ipfs_hashes_without_cache():
    ipfs_client = get_ipfs_api_client()
    if not ipfs_client:
        return set()
    try:
        raw_pin_list_result = ipfs_client.pin_ls()['Keys']
        pin_list = raw_pin_list_result.keys()
    except:
        pin_list = []
    ipfs_hashes = set(pin_list)
    return ipfs_hashes


def temp_add_ipfs_hash_to_local_refs(ipfs_hash):
    cache_client = get_cache_client()
    cache_key = 'ipfs_pinned_%s' % ipfs_hash
    cache_client.set(cache_key, '1', expiration=60*60) # 60分钟


def is_ipfs_hash_in_local(ipfs_hash, local_ipfs_hashes=None):
    if local_ipfs_hashes is None:
        local_ipfs_hashes = get_local_ipfs_hashes()
    if ipfs_hash in local_ipfs_hashes:
        is_in_local = True
    else:
        cache_client = get_cache_client()
        cache_key = 'ipfs_pinned_%s' % ipfs_hash
        if cache_client.get(cache_key):
            is_in_local = True
        else:
            is_in_local = False
    if is_in_local:
        # todo 进步一校验吗？
        pass
    return is_in_local


def get_bucket_ipfs_files_sync_status(bucket, only_failed=True):
    if not bucket:
        return {}
    files_info = get_bucket_files_info(bucket)
    files_sync_status = {}
    if not files_info or not isinstance(files_info, dict) or not 'files' in files_info:
        return files_sync_status
    files_info = files_info['files'] # files & folders 组成了这个 bucket 上原始的 files_info
    if not files_info or not isinstance(files_info, dict):
        return files_sync_status
    # start
    synced_count = 0
    local_ipfs_hashes = get_local_ipfs_hashes()
    for relative_path, file_info in files_info.items():
        if not isinstance(file_info, dict):
            files_sync_status[relative_path] = dict(ok=False, size=0)
            continue
        ipfs_hash = file_info.get('hash')
        if not ipfs_hash:
            files_sync_status[relative_path] = dict(ok=False, size=0)
            continue
        ok = is_ipfs_hash_in_local(ipfs_hash, local_ipfs_hashes=local_ipfs_hashes)
        if ok:
            synced_count += 1
        size = file_info.get('size') or 0
        if only_failed and ok:
            continue
        files_sync_status[relative_path] = dict(ok=ok, size=size, hash=ipfs_hash)

    info = dict(
        data = files_sync_status,
        synced_files = synced_count
    )

    return info



