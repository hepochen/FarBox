# coding: utf8
from flask import request, abort
from farbox_bucket.server.web_app import app
from farbox_bucket.bucket.utils import set_bucket_in_request_context, get_bucket_in_request_context
from farbox_bucket.bucket.token.utils import is_bucket_login
from farbox_bucket.bucket.domain.web_utils import get_bucket_from_request
from farbox_bucket.server.template_system.api_template_render import render_api_template_as_response
from farbox_bucket.server.helpers.file_manager import sync_file_by_web_request, \
    check_should_sync_files_by_web_request
from farbox_bucket.server.helpers.bucket import sync_download_file_by_web_request, show_bucket_records_for_web_request




######### 简单的 client 的对应 starts #########

@app.route('/__file_manager_check_api', methods=['POST', 'GET'])
def file_manager_check_api():
    return check_should_sync_files_by_web_request()

@app.route('/__file_manager_api', methods=['POST', 'GET'])
def file_manager_api():
    return sync_file_by_web_request()

@app.route('/__file_manager_list_api', methods=['POST', 'GET'])
def file_manager_list_api():
    return show_bucket_records_for_web_request(includes_zero_ids=False)

@app.route('/__file_manager_download_api', methods=['POST', 'GET'])
def file_manager_download_api():
    record_id = request.values.get("record") or request.values.get("record_id")
    return sync_download_file_by_web_request(record_id)

######### 简单的 client 的对应 ends #########



def get_bucket_for_file_manager():
    bucket = get_bucket_in_request_context() or request.values.get('bucket')
    if not bucket:
        bucket = get_bucket_from_request()
    if not is_bucket_login(bucket=bucket):
        abort(401)
    if not bucket:
        abort(404)
    return bucket

# web-file-manager 上对应的一些模板文件
@app.route('/__file_<subname>', methods=['POST', 'GET'])
@app.route('/__file_<subname>/<path:path>', methods=['POST', 'GET'])
def show_file_manager_related_page(subname, path=''):
    set_bucket_in_request_context(get_bucket_for_file_manager())
    template_name = 'page_file_%s.jade' % subname
    return render_api_template_as_response(template_name)



@app.route("/__web_editor", methods=["POST", "GET"])
def show_web_editor():
    set_bucket_in_request_context(get_bucket_for_file_manager())
    return render_api_template_as_response("page_web_editor.jade")



@app.route("/__web_editor_posts", methods=["POST", "GET"])
def show_web_editor_posts():
    set_bucket_in_request_context(get_bucket_for_file_manager())
    return render_api_template_as_response("page_web_editor_posts.jade")



