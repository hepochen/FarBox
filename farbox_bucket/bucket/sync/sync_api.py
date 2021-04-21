# coding: utf8
from __future__ import absolute_import
import requests
import time
import gc

from farbox_bucket.utils.logger import get_file_logger

from farbox_bucket.bucket.record.create import create_record_by_sync


from farbox_bucket.bucket import get_bucket_max_id, get_bucket_delta_id, update_bucket_delta_id, is_valid_bucket_name, set_bucket_into_buckets
from farbox_bucket.bucket.node import get_node_url, get_current_node_id





# todo 要处理 remote_node 是否存活的判断
def should_sync_remote_node(remote_node):
    # 如果 remote_node 也是 当前 node 自己， 就不同步了
    remote_uri = '/_system/status/node_status'
    remote_url = get_node_url(remote_node, remote_uri)
    try:
        response = requests.get(remote_url)
        remote_node_status = response.json()
        remote_node_id = remote_node_status.get('id')
        if remote_node_id:
            current_node_id = get_current_node_id()
            if current_node_id == remote_node_id:
                return  False
    except:
        pass
    return True






def sync_bucket_from_remote_node(bucket, remote_node, api_token='', cursor=None, per_page=1000,
                                 loop=True, check_should_or_not=True, print_log=False, server_sync_token=None):
    # 本质上，一个 node 的 sync，都是对这个函数的调用
    # bucket 上的记录，是多次调用这个 API，利用 cursor 来保持连接；如果一次调用失败，下次继续调用的时候， 并不影响
    logger = get_file_logger('sync_bucket')
    bucket = bucket.strip()
    if not is_valid_bucket_name(bucket):
        logger.info('%s is not a valid bucket' % bucket)
        return

    if check_should_or_not and not should_sync_remote_node(remote_node):
        # 不需要同步这个 node
        logger.info('no need to sync from remote_node %s, self or not live' % remote_node)
        return

    if not api_token and not server_sync_token:
        logger.info("set api token of the bucket first")
        return

    t1 = time.time()
    remote_uri = 'bucket/%s/list' % bucket
    remote_url = get_node_url(remote_node, remote_uri)
    cursor = cursor or get_bucket_delta_id(bucket) or get_bucket_max_id(bucket)
    data_to_post = {'per_page': per_page}
    if cursor:
        data_to_post['cursor'] = cursor
    if api_token:
        data_to_post['api_token'] = api_token
    if server_sync_token:
        data_to_post["server_sync_token"] = server_sync_token
    try:
        if print_log:
            print('will get data from %s?cursor=%s   per_page is %s' % (remote_url, cursor or '', per_page))
        response = requests.post(remote_url, data=data_to_post, timeout=180)
    except:
        info = '%s@%s is not valid or timeout' % (bucket, remote_node)
        logger.info(info)
        if print_log:
            print(info)
        return # ignore
    try:
        records = response.json()
    except:
        logger.info('%s@%s is not valid json data' % (bucket, remote_node))
        return # ignore
    if not isinstance(records, (list, tuple)):
        logger.info('records from remote bucket %s is not list' % bucket)
        return

    if not records: # 没有记录的情况，已经是最后的一条了
        logger.info('records from remote bucket %s is empty, cursor is %s' % (bucket, cursor or ''))
        return

    if print_log:
        print('got %s records, will to sync to local database...' % len(records))

    last_record = records[-1]
    last_record_id = last_record['_id']
    for record in records:
        create_record_by_sync(bucket, record, check_bucket=False)

    if print_log:
        print('create records by sync to database now')

    update_bucket_delta_id(bucket, last_record_id)
    set_bucket_into_buckets(bucket)
    if print_log:
        print('bucket delta_id is updated to %s, and current bucket is into recently updated buckets list' % last_record_id)

    records_length = len(records)
    seconds_used = time.time() - t1

    info = 'got %s records from %s at remote node %s, costs %s seconds' % (records_length, bucket, remote_node, seconds_used)
    logger.info(info)
    if print_log:
        print(info)


     # 节省内存, 进行一次回收
    del records, response
    gc.collect()

    # continue to loop
    if loop:
        if records_length == per_page:
            # 当前 结果数 和 per_page 的设定一样的时候，认为是有下一页的
            sync_bucket_from_remote_node(bucket, remote_node,
                                         api_token=api_token,
                                         cursor=last_record_id, per_page=per_page,
                                         loop=True, check_should_or_not=False, print_log=print_log,
                                         server_sync_token = server_sync_token,)
        else:
            if print_log:
                print('sync records from %s is done.\n' % bucket)



