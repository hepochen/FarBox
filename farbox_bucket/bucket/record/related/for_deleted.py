# coding: utf8
import os
from farbox_bucket.bucket.storage.default import storage
from farbox_bucket.utils.ssdb_utils import hset, hget, hdel, zset, zdel, hincr, py_data_to_ssdb_data
from farbox_bucket.bucket.record.get.path_related import get_record_id_by_path, get_record_by_path
from farbox_bucket.bucket.utils import get_bucket_name_for_url, get_bucket_name_for_path, get_bucket_name_for_slash
from farbox_bucket.bucket.record.utils import get_path_from_record, get_data_type, get_url_path, get_bucket_name_for_order_by_record
from .sub.utils import update_tags_info_for_posts

# 一般未必是 record 被删除
# 很可能只是 is_deleted 的标记

def after_path_related_record_deleted(bucket, record_data):
    path = get_path_from_record(record_data)
    if not path:
        return

    bucket_name_for_id = get_bucket_name_for_path(bucket)
    bucket_name_for_url = get_bucket_name_for_url(bucket)
    bucket_name_for_slash = get_bucket_name_for_slash(bucket)
    bucket_name_for_order = get_bucket_name_for_order_by_record(bucket, record_data)

    #bucket_name_for_order_file_type = "%s_file_order" % bucket

    # path 上清掉
    hdel(bucket_name_for_id, path)

    # 数据类型，对应的排序
    if bucket_name_for_order:
        zdel(bucket_name_for_order, path)

    #if bucket_name_for_order != bucket_name_for_order_file_type:
    #    zdel(bucket_name_for_order_file_type, path)

    # slash 上清掉
    zdel(bucket_name_for_slash, path)

    # url 上两个进行删除
    url_path = get_url_path(record_data) or hget(bucket_name_for_url, path)
    if url_path:
        hdel(bucket_name_for_url, url_path)
    hdel(bucket_name_for_url, path)


    # 删除文件, 使用 storage 来处理这里的逻辑
    storage.when_record_deleted(bucket, record_data)



def delete_path_related_record_by_path(bucket, path, record_data=None, continue_to_create_record=False):
    record_id = None
    record_data_in_db = get_record_by_path(bucket, path) or {}
    if record_data_in_db and isinstance(record_data_in_db, dict):
        record_data_in_db["is_deleted"] = True
    if record_data is None:
        record_data = record_data_in_db
        record_id = record_data.get('_id')
    if not record_id:
        record_id = get_record_id_by_path(bucket, path)
    if record_id:
        hdel(bucket, record_id)

    if not record_data:
        return

    after_path_related_record_deleted(bucket, record_data_in_db or record_data) # 关联的数据删除

    if not continue_to_create_record:
        # 后面如果是继续创建 record，还是会调用到 update_files_and_tags 的逻辑
        update_tags_info_for_posts(bucket=bucket, record_data=record_data)  # files and posts info





def auto_clean_record_before_handle_path_related_record(bucket, record_data):
    # 有 path 的情况，并且 client 过来的数据要求 _auto_clean_bucket 的，则进行如此处理
    # 删除的性质，便不会增加一个冗余的 record，而直接删除掉旧的 record 以及相关数据了； 同时 break，不进行后续的操作了
    # 如果是 update 的性质，则会删除前一个同 path 的 record
    if not isinstance(record_data, dict):
        return # ignore
    is_deleted = record_data.get('is_deleted')
    path = get_path_from_record(record_data)
    auto_clean_bucket = record_data.get('_auto_clean_bucket', False)
    if not auto_clean_bucket:
        return
    if not path:
        return
    if is_deleted:
        delete_path_related_record_by_path(bucket, path, record_data)
        return 'break' # 后面不运行了
    else:
        # 已经存在的，先删除， 后面有的，后面再自行 update
        delete_path_related_record_by_path(bucket, path, continue_to_create_record=True)