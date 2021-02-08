# coding: utf8
import os
import re
from farbox_bucket.utils import get_md5
from farbox_bucket.utils.functional import curry
from farbox_bucket.utils.convert.css import compile_css_with_timeout
from farbox_bucket.bucket.utils import get_bucket_in_request_context
from farbox_bucket.bucket.record.get.path_related import get_raw_content_by_path, has_record_by_path
from farbox_bucket.bucket.domain.web_utils import get_bucket_from_request
from farbox_bucket.server.static.static_render import get_static_raw_content
from farbox_bucket.server.helpers.file_manager import sync_file_by_server_side



scss_key_value_compiler = re.compile(r'(\$[a-z0-9_-]+)(:\s*)([\S]+)(\n|\r|$)', flags=re.I)

def get_vars_in_scss(scss_filepath='', raw_content=''):
    if not raw_content and scss_filepath:
        # 从某个文件里读取源代码
        if os.path.isfile(scss_filepath):
            with open(scss_filepath) as f:
                raw_content = f.read()
    if not raw_content:
        return {}
    records_found = scss_key_value_compiler.findall(raw_content)
    vars_in_scss = {}
    for record in records_found:
        key = record[0].lstrip('$').strip()
        if key.startswith('tmp_'): # 临时变量不做提取
            continue
        value = record[2].rstrip(';').strip()
        vars_in_scss[key] = value
    return vars_in_scss



def replace_var_in_scss_func(re_match, new_vars=None):
    new_vars = new_vars or {}
    if not isinstance(new_vars, dict):
        new_vars = {}
    record = list(re_match.groups())
    key = record[0].lstrip("$").strip()
    new_value = new_vars.get(key)
    if new_value:
        record[2] = "%s;"%new_value
        new_line = ''.join(record)
    else: # 没有变化
        new_line = re_match.group()
    return new_line


def replace_vars_in_scss(raw_content, new_vars, compile_scss=False):
    if not raw_content: # return nothing
        return ''
    new_content = scss_key_value_compiler.sub(curry(replace_var_in_scss_func, new_vars=new_vars), raw_content)
    if compile_scss: # 编译为普通的css内容
        new_content = compile_css_with_timeout(new_content)
        raw_version = get_md5(raw_content)
        new_content = '/*%s*/\n%s' % (raw_version, new_content) # compile 之后，保留原始内容的version，这样后续，可以进行对比，是否需要更新
    return new_content


def get_prefix_name_from_source_filepath(filepath):
    prefix_name = os.path.splitext(filepath)[0]
    prefix_name = prefix_name.replace('.', '_').strip('/')
    if prefix_name.startswith('template/'):
        prefix_name = prefix_name.replace('template/', '')
    prefix_name = prefix_name.replace('/', '_')
    return prefix_name


def do_get_smart_scss_url(scss_filepath, **kwargs):
    # 根据其内容内的变量名，进行替换处理;
    #  总是要读取源文件的，不然不知道是否要重新编译; 由于页面本身的缓存逻辑，性能影响有限
    # filename.scss -> filename-xxxxxxxxxxxx.css
    ext = os.path.splitext(scss_filepath)[-1]
    if ext not in [".less", ".scss"]:
        return  scss_filepath #ignore

    prefix_name = get_prefix_name_from_source_filepath(scss_filepath)
    filename = get_md5(get_md5(kwargs.keys()) + get_md5(kwargs.values())) + '.css'
    filepath = '/_cache/scss/%s-%s' % (prefix_name, filename)

    bucket = get_bucket_in_request_context() or get_bucket_from_request()
    if not bucket:
        return scss_filepath # ignore

    if has_record_by_path(bucket, path=filepath):
        # 缓存的文件已经存在了
        return filepath

    raw_content = ""
    if scss_filepath.startswith("/fb_static/"):
        raw_content = get_static_raw_content(scss_filepath)
    else:
        bucket = get_bucket_in_request_context()
        if bucket:
            raw_content = get_raw_content_by_path(bucket=bucket, path=scss_filepath)
    if not raw_content:
        return scss_filepath #ignore

    css_content = replace_vars_in_scss(raw_content=raw_content, new_vars=kwargs, compile_scss=True)
    sync_file_by_server_side(bucket=bucket, relative_path=filepath, content=css_content)

    return filepath


def get_smart_scss_url(scss_filepath, **kwargs):
    url = do_get_smart_scss_url(scss_filepath, **kwargs)
    if url.startswith("/fb_static/"):
        p1, ext = os.path.splitext(url)
        if ext in [".scss", ".less"]:
            return p1 + ".css"
    return url
