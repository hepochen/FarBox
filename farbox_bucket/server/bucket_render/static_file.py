# coding: utf8
from __future__ import absolute_import
import os, io
from flask import send_file, request, abort
from farbox_bucket.utils import to_bytes, string_types, get_md5
from farbox_bucket.utils.mime import guess_type
from farbox_bucket.utils.url import get_host_from_url
from farbox_bucket.bucket.storage.default import storage
from farbox_bucket.bucket.utils import get_bucket_site_configs, get_bucket_in_request_context
from farbox_bucket.bucket.record.utils import get_path_from_record
from farbox_bucket.bucket.record.get.path_related import get_record_by_path
from farbox_bucket.bucket.token.utils import is_bucket_login

from farbox_bucket.server.utils.site_resource import get_pages_configs, get_template_static_resource_content
from farbox_bucket.server.utils.response import set_304_response_for_doc, get_304_response, is_doc_modified, p_redirect
from farbox_bucket.server.utils.request_context_vars import set_context_value_from_request




def render_as_static_resource_in_pages_for_farbox_bucket(template_filename):
    ext = os.path.splitext(template_filename)[-1].lower()
    if ext not in ['.html', '.htm', '.js', '.css', '.json', '.jpg', '.png', '.scss', '.less', '.coffee']:
        return
    mime_type = ''
    raw_content = ''
    pages_configs = get_pages_configs()
    if not is_doc_modified(doc=pages_configs, date_field='mtime'):
        return get_304_response()
    if ext in ['.scss', '.less']:
        raw_content = get_template_static_resource_content('.'.join([template_filename.rsplit('.')[0], 'css']))
        mime_type = 'text/css'
    elif ext in ['.coffee']:
        raw_content = get_template_static_resource_content('.'.join([template_filename.rsplit('.')[0], 'js']))
        mime_type = 'application/javascript'
    if not raw_content:
        raw_content = get_template_static_resource_content(template_filename)
    if raw_content:
        raw_content = to_bytes(raw_content)
        mime_type = mime_type or guess_type(template_filename) or 'application/octet-stream'
        set_context_value_from_request("is_template_resource", True)
        file_response = send_file(io.BytesIO(raw_content), mimetype=mime_type)
        bucket = get_bucket_in_request_context()
        if bucket:
            set_304_response_for_doc(response=file_response, doc=pages_configs, date_field='mtime')
        return file_response



def render_as_static_file_for_farbox_bucket(path):
    if not path or path == "/":
        path = "index.html"
    bucket = get_bucket_in_request_context()
    if not bucket:
        return
    record = get_record_by_path(bucket, path)
    if path == "favicon.ico" and not record:
        record = get_record_by_path(bucket, "_direct/favicon.ico") # 兼容 Bitcron
    if not record:
        return
    record_path = get_path_from_record(record)
    if record_path and record_path.startswith("/_data/"):
        ext = os.path.splitext(record_path)[-1].strip(".").lower()
        if ext in ["csv"] and not is_bucket_login(bucket):
            return abort(404, "csv under /_data is not allowed to download directly")
    set_context_value_from_request("is_static_file", True)
    if record.get('compiled_type') and record.get('compiled_content'):
        raw_content = record.get('compiled_content')
        content_type = record.get('compiled_type')
        raw_content = to_bytes(raw_content)
        mimetype = content_type or guess_type(path) or 'application/octet-stream'
        compiled_file_response = send_file(io.BytesIO(to_bytes(raw_content)), mimetype=mimetype)
        return compiled_file_response
    else:
        # 先对应是否防盗链的逻辑
        site_configs = get_bucket_site_configs(bucket)
        anti_theft_chain = site_configs.get("anti_theft_chain", True)
        if anti_theft_chain and request.path.strip('/') in ['favicon.ico']:
            anti_theft_chain = False
        if anti_theft_chain and request.referrer:
            refer_host = get_host_from_url(request.referrer)
            if refer_host != request.host and "." in request.path:
                return abort(404, "this url is not allowed for outside")

        return storage.get_download_response_for_record(bucket=bucket, record_data=record, try_resized_image=True)