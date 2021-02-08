# coding: utf8
import os, time
from farbox_bucket.utils.objectid import ObjectId
from farbox_bucket.utils import to_float, to_unicode
from farbox_bucket.utils.ssdb_utils import hset, hget, hdel, zset, zdel, hincr, py_data_to_ssdb_data
from farbox_bucket.bucket.defaults import BUCKET_RECORD_SLASH_TYPES
from farbox_bucket.bucket.utils import get_bucket_name_for_url, get_bucket_name_for_path, get_bucket_name_for_slash, is_valid_bucket_name
from farbox_bucket.bucket.record.utils import get_path_from_record, get_data_type, get_url_path, get_bucket_name_for_order_by_record
from farbox_bucket.bucket.record.get.path_related import has_record_by_path
from .sub.utils import update_files_and_tags



def create_record_for_a_folder(bucket="", folder_path=""):
    if not is_valid_bucket_name(bucket):
        return
    folder_path = folder_path.strip("/")
    if not folder_path:
        return
    if has_record_by_path(bucket, folder_path):
        # 再校验一次 folder 是否存在
        return
    folder_record_data = dict(
        path = folder_path,
        relative_path = folder_path,
        is_dir = True,
        slash_number = folder_path.count("/"),
        type = "folder",
        _type = "folder",
        _order = int(time.time()),
        title = os.path.split(folder_path)[-1],

    )
    object_id = str(ObjectId())
    folder_record_data["_id"] = object_id
    hset(bucket, object_id, folder_record_data, ignore_if_exists=False)

    after_path_related_record_created(bucket, object_id, folder_record_data)

    #parent_path = os.path.split(folder_path)[0].strip("/")
    #if parent_path and not has_record_by_path(bucket, parent_path):
        # 继续往上找 parent
    #    create_record_for_a_folder(bucket=bucket, folder_path=parent_path)



def update_record_order_value_to_related_db(bucket, record_data):
    # 设定排序, 如果没有排序逻辑的，实际上根据 get_data(type) 的逻辑是无法取出内容的
    path = get_path_from_record(record_data)
    if not path:
        return
    path = path.strip('/')
    if not path:
        return
    bucket_name_for_order = get_bucket_name_for_order_by_record(bucket, record_data)
    data_type = get_data_type(record_data)
    data_order = record_data.get("_order") or record_data.get("order")
    if not data_order and data_type in ["file", "post", "folder"]:  # 不应该出现的情况
        data_order = time.time()
    if data_order is not None:
        data_order = to_float(data_order, default_if_fail=None)
    if data_order is not None and bucket_name_for_order:
        zset(bucket_name_for_order, path, data_order)

def after_path_related_record_created(bucket, record_id, record_data):
    path = get_path_from_record(record_data)
    if not path:
        return
    path = path.strip('/')
    if not path:
        return
    #original_path = to_unicode(record_data.get('path').strip('/'))

    # 如果 parent 不存在，也需要创建一个
    parent_path = os.path.split(path)[0].strip("/")
    if parent_path and not has_record_by_path(bucket, parent_path):
        # 如果 parent 如果不存在，也需要创建一个, 并且递归往上走，所有的 parents 都创建
        real_path = get_path_from_record(record_data, is_lower=False)
        real_parent_path = os.path.split(real_path)[0].strip("/") # 保留了大小写
        create_record_for_a_folder(bucket, real_parent_path)

    slash_number = path.count('/')
    bucket_name_for_path = get_bucket_name_for_path(bucket)
    bucket_name_for_url = get_bucket_name_for_url(bucket)
    bucket_name_for_slash = get_bucket_name_for_slash(bucket)
    bucket_name_for_order = get_bucket_name_for_order_by_record(bucket, record_data)

    to_mark_object_id = False
    data_type = get_data_type(record_data)
    if data_type == 'post' and record_data.get('status', 'public')!='public':
        # post 类型的，标记 object_id，前面加 #
        to_mark_object_id = True


    # url 匹配用的索引
    url_path = get_url_path(record_data)
    # 两两对应的映射关系, 除了通过 url 找path，还可以 通过 path 找 url，因为删除一个 record 的时候，只有 path，没有 url_path
    if url_path:
        hset(bucket_name_for_url, url_path, path)
        if path != url_path:
            hset(bucket_name_for_url, path, url_path)

    # 建立 path 与 object_id 的关系
    if to_mark_object_id:
        # 在普通 list 的时候，不会出现；单独路径查找，又能找到
        value = '#%s'%record_id
    else:
        value = record_id

    # 同时记录 version & size:  record_id,size,version
    size = record_data.get('size') or 0
    version = record_data.get('version') or ''
    if record_data.get('is_dir'):
        version = 'folder'
    value = '%s,%s,%s' % (value, size, version)

    hset(bucket_name_for_path, path, value)

    # 设定排序, 如果没有排序逻辑的，实际上根据 get_data(type) 的逻辑是无法取出内容的
    update_record_order_value_to_related_db(bucket, record_data)

    # slash number 绑定到 path
    # 指定的类型才能处理 slash
    if data_type in BUCKET_RECORD_SLASH_TYPES:
        zset(bucket_name_for_slash, path, score=slash_number)


    update_files_and_tags(bucket=bucket, record_data=record_data) # files and posts info

