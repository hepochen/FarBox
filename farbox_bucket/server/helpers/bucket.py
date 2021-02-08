#coding: utf8
from __future__ import absolute_import
from flask import request, abort, Response
from farbox_bucket.utils.web_utils.response import jsonify
from farbox_bucket.utils.web_utils.request import to_per_page
from farbox_bucket.bucket.defaults import zero_id_for_finder
from farbox_bucket.bucket.utils import set_bucket_in_request_context
from farbox_bucket.bucket.record.get.get import get_record, get_records_for_bucket
from farbox_bucket.bucket.storage.default import storage
from farbox_bucket.bucket.token.utils import get_logined_bucket_by_token


def sync_download_file_by_web_request(record_id):
    # return response or abort error
    bucket = get_logined_bucket_by_token()  # by api token
    if not bucket:
        error_info = 'no bucket matched'
    else:
        error_info = ""
    record = get_record(bucket=bucket, zero_ids_allowed=False, record_id=record_id, force_dict=True)
    if not record:
        error_info = "no record found"
    if record.get("is_dir"):
        error_info = "is dir, can not download"
    elif record.get("is_deleted"):
        error_info = "is deleted, can not download"
    if not error_info:
        file_version = record.get("version")
        version_from_client = request.values.get("version")
        if file_version == version_from_client:
            # 内容跟客户端一致，不需要下载回去
            return Response("")
        response = storage.get_download_response_for_record(bucket, record) or Response("")
        return response
    else:
        abort(404, error_info)



def show_bucket_records_for_web_request(bucket=None, default_records_per_page=100, includes_zero_ids=True):
    # return response or abort error
    bucket = bucket or get_logined_bucket_by_token()  # by api token
    if not bucket:
        abort(404, "no bucket matched")
    set_bucket_in_request_context(bucket)
    pre_record_id = request.values.get('cursor')
    if not includes_zero_ids and not pre_record_id: # 不包括 zero ids 相当于
        pre_record_id = zero_id_for_finder
    per_page = to_per_page(default_records_per_page, request.values.get('per_page'), max_per_page=1000)
    records = get_records_for_bucket(bucket, start_record_id=pre_record_id, limit=per_page)
    return jsonify(records)


