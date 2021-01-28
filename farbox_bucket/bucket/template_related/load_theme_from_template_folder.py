# coding: utf8
import os
from farbox_bucket.utils.functional import curry
from farbox_bucket.utils import smart_unicode, get_md5
from farbox_bucket.bucket.utils import set_bucket_configs, has_bucket
from farbox_bucket.bucket.record.get.path_related import get_paths_under, get_raw_content_by_path
from farbox_bucket.client.dump_template import get_templates_route_info, allowed_exts
from farbox_bucket.utils.convert.css import compile_css_with_timeout
from farbox_bucket.utils.convert.jade2jinja import convert_jade_to_html
from farbox_bucket.utils.memcache import get_cache_client


def compile_css(content):
    hash_key = get_md5(content)
    return compile_css_with_timeout(content, timeout=2, hash_key=hash_key, cache_client=get_cache_client())

def compile_jade(content):
    hash_key = get_md5(content)
    return convert_jade_to_html(content, hash_key=hash_key, cache_client=get_cache_client())



server_side_template_resource_compilers = {
    'scss': ('css', compile_css),
    'less': ('css', compile_css),
    'jade': ('html', compile_jade)
}


def load_theme_from_template_folder_for_bucket(bucket, prefix="template"):
    if not has_bucket(bucket):
        return
    info = {}
    prefix = prefix.strip().strip("/")
    template_paths = get_paths_under(bucket, under=prefix)
    for _relative_path in template_paths:
        relative_path = _relative_path.replace("%s/"%prefix, "", 1)
        raw_content = get_raw_content_by_path(bucket, _relative_path)
        if not raw_content:
            continue
        path_without_ext, ext = os.path.splitext(relative_path)
        ext = ext.lower().strip('.')
        if ext not in allowed_exts:
            continue
        raw_content = smart_unicode(raw_content)  # to unicode
        info[relative_path] = raw_content
        matched_compiler = server_side_template_resource_compilers.get(ext)
        if matched_compiler:
            new_ext, compile_func = matched_compiler
            try:
                compiled_content = compile_func(raw_content)
                new_key = path_without_ext + '.' + new_ext.strip('.')
                info[new_key] = compiled_content
            except Exception as e:
                pass
    info["_route"] = get_templates_route_info(info)

    set_bucket_configs(bucket, info, config_type='pages')

    return info


