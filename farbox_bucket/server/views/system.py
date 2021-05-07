# coding: utf8
from flask import request, abort, Response
from farbox_bucket.server.web_app import app
from farbox_bucket.utils.ssdb_utils import hlist, zrscan, hscan, zscan
from farbox_bucket.utils.system_status_recorder import get_system_timed_records
from farbox_bucket.utils.cache import cached
from farbox_bucket.bucket.utils import is_valid_bucket_name
from farbox_bucket.bucket.status import get_current_node_status
from farbox_bucket.utils.web_utils.response import jsonify
from farbox_bucket.utils.web_utils.request import to_per_page
from farbox_bucket.bucket.domain.utils import not_allowed_for_parked_domain
from farbox_bucket.bucket.sync.remote import get_buckets_to_sync_from_remote
from farbox_bucket.bucket.token.utils import get_logined_admin_bucket
from farbox_bucket.settings import WEBSITE_DOMAINS


@app.route('/_system/status/action_seconds')
@cached(10)
def action_seconds():
    records = get_system_timed_records()
    records_content = '\n'.join(records)
    response = Response(records_content, mimetype='text/plain')
    return response


@app.route('/_system/status/db_status')
def show_node_status():
    node_status = get_current_node_status()
    return jsonify(node_status)






@app.route('/_system/namespaces', methods=['POST', 'GET'])
@not_allowed_for_parked_domain
def show_namespaces(): # also bucket names
    # just bucket names, cursor 是上一个 bucket name
    per_page = to_per_page(1000, request.values.get('per_page'), max_per_page=10000)
    cursor = request.values.get('cursor') or ''
    bucket_names = hlist(name_start=cursor, limit=per_page)
    bucket_names = [name for name in bucket_names if is_valid_bucket_name(name)]

    return jsonify(bucket_names)



@app.route('/_system/buckets', methods=['POST', 'GET'])
@not_allowed_for_parked_domain
def show_buckets():
    # cursor 是 bucket 的最后更新时间
    # 在 record 创建的过程中， 会更新 bucket， 从而让 buckets 按照最后更新时间，进行排序
    per_page = to_per_page(1000, request.values.get('per_page'), max_per_page=10000)
    try:
        cursor = int(request.values.get('cursor') or '')
    except:
        cursor = ''
    buckets_result = zscan('buckets', score_start=cursor, limit=per_page)
    return jsonify(buckets_result)

@app.route('/_system/domains', methods=['POST', 'GET'])
@not_allowed_for_parked_domain
def show_domains():
    if not get_logined_admin_bucket():
        abort(404)
    per_page = to_per_page(1000, request.values.get('per_page'), max_per_page=10000)
    cursor = request.values.get('cursor') or ''
    domain_docs = hscan('_domain', key_start=cursor, limit=per_page)
    return jsonify(domain_docs)


@app.route('/_system/buckets_will_sync_from_remote', methods=['POST', 'GET'])
@not_allowed_for_parked_domain
def show_buckets_should_be_synced():
    # 需要从 remote 同步过来的 buckets
    buckets_data = get_buckets_to_sync_from_remote()
    return jsonify(buckets_data)



def check_current_request_under_system_domains():
    domain = request.host.lower()
    if domain not in WEBSITE_DOMAINS and not domain.startswith('localhost:'):
        abort(404, 'not allowed, on system main domains only')







