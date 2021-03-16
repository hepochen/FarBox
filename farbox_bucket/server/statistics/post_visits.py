# coding: utf8
import time
from gevent import spawn
from flask import request
from farbox_bucket.utils import to_float, to_int, string_types, is_a_markdown_file
from farbox_bucket.utils.data import dump_csv
from farbox_bucket.utils.ssdb_utils import hincr, hclear, hget, hset, hgetall, hsize
from farbox_bucket.bucket.utils import get_bucket_in_request_context, get_bucket_updated_at_diff_to_now
from farbox_bucket.server.utils.request_context_vars import get_doc_in_request, get_doc_type_in_request, get_doc_path_in_request
from farbox_bucket.server.helpers.file_manager import sync_file_by_server_side


one_year_seconds = 365 * 24 * 60 * 60


def get_visits_db_name_for_bucket(bucket):
    name = '_visits_%s' % bucket
    return name

def get_visits_key(doc_path, field='visits'):
    doc_path = doc_path.strip().strip('/').lower()
    visits_key = '%s/%s' % (field, doc_path)
    return visits_key


def update_post_visits_for_response(response):
    doc = get_doc_in_request()
    if doc:
        doc_type = doc.get('_type')
        doc_path = doc.get('path')
    else:
        doc_type = get_doc_type_in_request()
        doc_path = get_doc_path_in_request()
    bucket = get_bucket_in_request_context()
    if bucket and doc_type=='post' and doc_path:
        pass
    else:
        return

    visits_key = get_visits_key(doc_path, field='visits')
    visitors_key = get_visits_key(doc_path, field='visitors')

    now = time.time()
    # 直接在这里处理cookie
    # set cookie to know it's not a new visitor
    response.set_cookie('last_visited_at', str(now), max_age=one_year_seconds)


    last_visited_at = to_float(request.cookies.get('last_visited_at', 0)) or 0

    diff = now - last_visited_at
    if diff > 24 * 60 * 60:  # 24小时内的，认为是同一个visitor
        is_visitor = True
    else:
        is_visitor = False

    # 异步更新到数据库
    spawn(async_update_visits, bucket, visits_key, visitors_key, is_visitor=is_visitor)


def async_update_visits(bucket, visits_key, visitors_key, is_visitor=False):
    visits_db_name = get_visits_db_name_for_bucket(bucket)
    hincr(visits_db_name, visits_key, 1)  # pv 始终是记录的
    if is_visitor:
        hincr(visits_db_name, visitors_key, 1)  # uv 要做次判断，

    diff = get_bucket_updated_at_diff_to_now(bucket)
    if diff > 3 * 24 * 60 * 60: # 每隔 3 天的间隙，把访问数的统计路径进行一次 dump
        visits_csv_raw_content = export_all_posts_visits_as_csv(bucket)
        if not visits_csv_raw_content:
            return
        sync_file_by_server_side(bucket, relative_path="_data/visits.csv", content=visits_csv_raw_content)


def get_post_visits_count(doc, field='visits'):
    # field is in ['visits', 'visitors']
    bucket = get_bucket_in_request_context()
    if not bucket:
        return 0
    visits_db_name = get_visits_db_name_for_bucket(bucket)
    doc_path = doc.get('path')
    if not doc_path:
        return 0
    key = get_visits_key(doc_path, field=field)
    count = hget(visits_db_name, key) or 0
    count = to_int(count, default_if_fail=0)
    return count



def load_all_posts_visits_from_csv(bucket, csv_file_record):
    visits_db_name = get_visits_db_name_for_bucket(bucket)
    current_visits_size = hsize(visits_db_name)
    if current_visits_size > 5000: # 如果超过了 5k 的数量，先clear，避免过度冗余
        hclear(visits_db_name)
    raw_objects = csv_file_record.get('objects') or []
    if not raw_objects:
        return
    if not isinstance(raw_objects, (list, tuple)):
        return
    for data_obj in raw_objects[:3000]:
        # 最多处理 3k 条记录，避免一个 bucket 过于庞大，出现性能问题
        if not isinstance(data_obj, dict):
            continue
        path = data_obj.get('path')
        if not path or not isinstance(path, string_types):
            continue
        path = path.strip('/').lower()
        if not is_a_markdown_file(path):
            continue
        visits = to_int(data_obj.get('visits'), default_if_fail=0)
        visitors = to_int(data_obj.get('visitors'), default_if_fail=0)
        visits_key = get_visits_key(path, field='visits')
        visitors_key = get_visits_key(path, field='visitors')
        hset(visits_db_name, visits_key, visits)
        hset(visits_db_name, visitors_key, visitors)


def get_all_posts_visits(bucket):
    visits_db_name = get_visits_db_name_for_bucket(bucket)
    raw_result = hgetall(visits_db_name)
    visits_data = {}
    for k, v in raw_result:
        if '/' not in k:
            continue
        prefix, path = k.split('/', 1)
        path = path.strip('/').lower()
        visits_data.setdefault(path, {})[prefix] = to_int(v, default_if_fail=0)
    return visits_data


def export_all_posts_visits_as_csv(bucket):
    visits_data = get_all_posts_visits(bucket)
    if not visits_data:
        return  ''# ignore
    csv_records = [['Path', 'Visits', 'Visitors']]
    for path, path_matched_data in visits_data.items():
        visits = path_matched_data.get('visits') or 0
        visitors = path_matched_data.get('visitors') or 0
        record = [path, visits, visitors]
        csv_records.append(record)
    csv_content = dump_csv(csv_records, lines=True)
    return csv_content

