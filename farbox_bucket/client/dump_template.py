# coding: utf8
from __future__ import absolute_import
import os
from farbox_bucket.utils import smart_unicode, is_a_markdown_file
from farbox_bucket.utils.convert.coffee2js import compile_coffee
from farbox_bucket.utils.convert.css import compile_css
from farbox_bucket.utils.convert.jade2jinja import convert_jade_to_html
from farbox_bucket.utils.path import get_relative_path, is_real, is_a_hidden_path, get_all_sub_files
from farbox_markdown.compile_md import compile_markdown


template_resource_compilers = {
    'scss': ('css', compile_css),
    'less': ('css', compile_css),
    'coffee': ('js', compile_coffee),
    'jade': ('html', convert_jade_to_html)
}

allowed_exts = [
    'scss', 'css', 'less',
    'json', 'js', 'coffee',
    'html',  'htm', 'jade',
]

def get_templates_route_info(templates_info):
    route_info = {}
    for relative_path in templates_info:
        prefix, ext = os.path.splitext(relative_path)
        ext = ext.lower().strip('.')
        if ext not in ['html']:
            continue
        relative_name = os.path.splitext(relative_path)[0]  # 不包含后缀的
        path_parts = relative_name.split('/')
        route_paths = []  # 会产生的路由可能
        prefix = '/'.join(path_parts[:-1])  # 不算最尾部的前面算 prefix
        suffixes = path_parts[-1].split('+')  # 考虑用+链接起来的，需要 split 的
        for suffix in suffixes:
            route_path = (prefix + '/' + suffix).lstrip('/')
            route_paths.append(route_path)
            if route_path.endswith('/index'):
                route_paths.append(route_path[:-6])
        if relative_name.endswith('/index'):
            route_paths.append(relative_name[:-6])
        for route_path in route_paths:
            if route_path == 'index':
                route_path = ''  # 首页
            route_info[route_path] = relative_path  # 不保留后缀名的
    return route_info


def get_template_info(template_dir):
    info = {}
    template_dir = template_dir.strip().rstrip('/')
    if not os.path.isdir(template_dir):
        return info # ignore
    filepaths = get_all_sub_files(template_dir, accept_func=os.path.isfile, max_tried_times=1000)
    for filepath in filepaths:
        relative_path = get_relative_path(filepath, root=template_dir).lower()  # lower case
        if not os.path.isfile(filepath):
            continue
        if not is_real(filepath) or is_a_hidden_path(relative_path):
            continue
        if relative_path.startswith('readme.') and is_a_markdown_file(relative_path): # 模板 readme 上的信息
            with open(filepath, 'rb') as f:
                raw_markdown_content = smart_unicode(f.read())
            compiled_markdown_content = compile_markdown(raw_markdown_content)
            compiled_markdown_content_meta = compiled_markdown_content.metadata
            readme_info = dict(content=compiled_markdown_content, metadata=compiled_markdown_content_meta) # raw_content=raw_markdown_content,
            info['_readme'] = readme_info
        else:
            path_without_ext, ext = os.path.splitext(relative_path)
            ext = ext.strip('.').lower()
            if ext not in allowed_exts:
                continue
            with open(filepath, 'rb') as f:
                raw_content = f.read()
            raw_content = smart_unicode(raw_content) # to unicode
            info[relative_path] = raw_content
            matched_compiler = template_resource_compilers.get(ext)
            if matched_compiler:
                new_ext, compile_func = matched_compiler
                try:
                    compiled_content = compile_func(raw_content)
                    new_key = path_without_ext + '.' + new_ext.strip('.')
                    info[new_key] = compiled_content
                except Exception as e:
                    error_message = getattr(e, 'message', None)
                    if error_message:
                        try: print('%s error: %s' % (relative_path, error_message))
                        except: pass
    info['_route'] = get_templates_route_info(info)
    return info



def get_template_content_from_name(name_or_path, templates_info,):
    route_info = templates_info.get('_route') or {}
    name_or_path = name_or_path.lower().strip('/').strip() # 全小写
    if name_or_path in ['index', '/']:
        name_or_path = ''  # homepage
    path_parts = name_or_path.split('/')
    while path_parts:
        path = '/'.join(path_parts)
        if path in route_info:
            real_path = route_info[path]
            template_content = templates_info.get(real_path)
            if template_content:
                return template_content
        path_parts = path_parts[:-1]  # 必须要保证每次非 break 的要运行到，不然就是死循环了。
    # at last, fallback
    if not name_or_path:
        name_or_path = 'index'
    if '.' not in name_or_path:
        filename = '%s.html' % name_or_path
        return templates_info.get(filename)





