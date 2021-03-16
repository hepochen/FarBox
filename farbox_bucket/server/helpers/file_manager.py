# coding: utf8
import time
import ujson as json
from flask import request
from farbox_bucket.settings import MAX_FILE_SIZE
from farbox_bucket.bucket.storage.default import storage
from farbox_bucket.client.sync.compiler_worker import get_compiler_data_directly
from farbox_bucket.bucket.utils import set_bucket_configs
from farbox_bucket.bucket.record.create import create_record
from farbox_bucket.bucket.record.get.path_related import get_record_by_path, get_paths_under
from farbox_bucket.bucket.token.utils import is_bucket_login, get_logined_bucket, get_logined_bucket_by_token
from farbox_bucket.server.utils.response import jsonify, json_if_error
from farbox_bucket.server.utils.request import get_file_content_in_request
from farbox_bucket.utils import smart_unicode, to_int, string_types, get_md5, is_a_markdown_file


def sync_file_by_server_side(bucket, relative_path, content=None, is_dir=False, is_deleted=False, return_record=False, real_relative_path=None):
    data = get_compiler_data_directly(relative_path, content=content, is_dir=is_dir, is_deleted=is_deleted, real_relative_path=real_relative_path)
    if content:
        data["size"] = len(content)
        if not data["version"]:
            data["version"] = get_md5(content)
    file_version = data.get("version")
    if file_version:
        old_record = get_record_by_path(bucket=bucket, path=relative_path, force_dict=True)
        if old_record:
            old_file_version = old_record.get("version")
            if file_version == old_file_version:
                # 路径 & 内容一致，不做处理
                return
    if not data:
        result  = 'no data to create a record'
    else:
        result = create_record(bucket=bucket, record_data=data, file_content=content, return_record=return_record)
    # error_info/ None / record_data(dict)
    if return_record and not isinstance(result, dict):
        return None
    else:
        return result




def sync_file_by_web_request():
    relative_path = (request.values.get('path') or request.values.get('relative_path') or '').strip()
    relative_path = relative_path.lstrip('/')
    real_relative_path = request.values.get("real_path", "").strip().lstrip("/")
    content = get_file_content_in_request() or request.values.get('raw_content') or request.values.get('content')
    is_dir = request.values.get('is_dir')=='true'
    is_deleted = request.values.get('is_deleted')=='true'
    bucket = get_logined_bucket()
    should_check_login = True
    if not bucket:
        bucket = get_logined_bucket_by_token() # by api token
        if bucket and request.values.get("action")=="check": # 仅仅是校验当前的 token 是否正确了
            return jsonify(dict(status='ok'))
        should_check_login = False
    if not relative_path:
        error_info = 'set path first'
    elif not bucket:
        error_info = 'no bucket matched'
    elif should_check_login and not is_bucket_login(bucket=bucket):
        error_info  = 'bucket is not login'
    elif is_deleted and is_dir and get_paths_under(bucket=bucket, under=relative_path):
        error_info = 'a non-empty folder is not allowed to delete on web file manager'
    elif content and len(content) > MAX_FILE_SIZE:
        error_info = "max file size is %s" % MAX_FILE_SIZE
    else:
        # 处理 .configs/sorts.json -> orders
        content_handled = False
        error_info = ""
        if relative_path in [".configs/sorts.json", "configs/sorts.json"]:
            try:
                raw_sorts_data = json.loads(content)
                if isinstance(raw_sorts_data, dict) and "__positions" in raw_sorts_data:
                    sorts_data = raw_sorts_data.get("__positions")
                    if isinstance(sorts_data, dict):
                        set_bucket_configs(bucket, configs=sorts_data, config_type="orders")
                        content_handled = True
            except:
                pass
        if not content_handled:
            error_info = sync_file_by_server_side(bucket=bucket, relative_path=relative_path, content=content,
                                                  is_dir=is_dir, is_deleted=is_deleted, real_relative_path=real_relative_path)
    if not error_info:
        return jsonify(dict(status='ok'))
    else:
        return json_if_error(400, dict(status='failed', message=error_info))


def check_should_sync_files_by_web_request():
    bucket = get_logined_bucket() or get_logined_bucket_by_token()
    if not bucket:
        return jsonify([])
    raw_json_data = request.values.get("json")
    if raw_json_data:
        try:
            json_data = json.loads(raw_json_data)
        except:
            json_data = {}
    else:
        json_data = request.json or {}
    to_return = [] # 需要上传的 paths 集合
    if isinstance(json_data, dict):
        tried_times = 0
        for path, version in json_data.items():
            tried_times += 1
            if tried_times >= 1000: break
            if not isinstance(path, string_types) or not isinstance(version, string_types):
                continue
            if path in to_return: continue
            matched_record = get_record_by_path(bucket, path, force_dict=True)
            if not matched_record:
                to_return.append(path)
            else:
                raw_content = matched_record.get('raw_content') or matched_record.get('content') or ''
                if not raw_content and storage.should_upload_file_by_client(bucket, matched_record):
                    # 服务器上还没有，需要上传的
                    to_return.append(path)
                    continue
                matched_version = matched_record.get("version")
                if matched_version and matched_version == version:
                    continue
                else:
                    to_return.append(path)
    return jsonify(to_return)





# record.get('raw_content') or record.get('content') or ''

def append_to_markdown_record(bucket, relative_path, content_to_append, lines_to_append=1,
                              more_line_when_seconds_passed=0, position='tail'):
    record = get_record_by_path(bucket, path=relative_path) or {}
    record_type = record.get('_type') or record.get('type')
    if record_type != 'post':
        return 'ignore' # ignore
    if not is_a_markdown_file(relative_path):
        return 'ignore'
    old_content = record.get('raw_content') or record.get('content') or ''
    old_content = smart_unicode(old_content)
    now = time.time()
    old_timestamp = record.get('timestamp')

    if more_line_when_seconds_passed and old_timestamp and isinstance(old_timestamp, (int, float)):
        # 超过多少 seconds 之后，就会自动空一行，相当于产生了一个『段落』的逻辑
        diff = now - old_timestamp
        if diff > more_line_when_seconds_passed:
            lines_to_append += 1

    interval_empty_lines = '\r\n' * abs(to_int(lines_to_append, max_value=10))  # 间隔换行

    content_to_append = smart_unicode(content_to_append).strip()

    if old_content.endswith('\n' + content_to_append) or old_content == content_to_append:
        return 'ignore' # ignore, 重复的内容不处理

    if position == 'tail': # 默认插入尾巴
        new_content = '%s%s' % (interval_empty_lines, content_to_append)
        content = '%s%s' % (old_content, new_content)
    else:
        new_content = '%s%s' % (content_to_append, interval_empty_lines)
        content = '%s%s' % (new_content, old_content)
    error_info = sync_file_by_server_side(bucket=bucket, relative_path=relative_path, content=content)
    return error_info








