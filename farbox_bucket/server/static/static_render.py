# coding: utf8
import os
import glob
from flask import abort
from farbox_bucket.utils.path import get_relative_path, make_sure_path
from farbox_bucket.server.utils.response import send_file_with_304
from farbox_bucket.server.utils.request_path import get_request_path_for_bucket, set_context_value_from_request

static_folder_path = os.path.dirname(os.path.abspath(__file__))


def get_static_resources_map():
    static_resources_map = {}
    raw_filepaths = glob.glob('%s/*'%static_folder_path) + glob.glob('%s/*/*'%static_folder_path) + \
                    glob.glob('%s/*/*/*'%static_folder_path) + glob.glob('%s/*/*/*/*'%static_folder_path)
    for filepath in raw_filepaths:
        if os.path.isdir(filepath):
            continue
        ext = os.path.splitext(filepath)[-1].lower()
        if ext in ['.py', '.jade', '.coffee', '.scss', '.less', 'jpg', 'gif', 'png']:
            continue
        filename = os.path.split(filepath)[-1].lower()
        just_name = os.path.splitext(filename)[0]
        relative_path = get_relative_path(filepath, static_folder_path)
        names = [filename, just_name, relative_path]
        if just_name.startswith('jquery.'):
            names.append(just_name.replace('jquery.', '', 1))
        for name in names:
            static_resources_map[name] = filepath
    return static_resources_map



def send_static_file(path):
    # todo 对于后缀有限制
    abs_filepath = os.path.join(static_folder_path, path.strip('/'))
    if os.path.isfile(abs_filepath):
        set_context_value_from_request("is_system_static_file", True)
        return send_file_with_304(abs_filepath)


web_static_resources_map = get_static_resources_map() # 0.02s，性能没有问题


def get_static_raw_content(path):
    path = path.strip("/")
    if path.startswith("fb_static/"):
        path = path.replace("fb_static/", "", 1)
    abs_filepath = os.path.join(static_folder_path, path.strip('/'))
    if os.path.isfile(abs_filepath):
        try:
            with open(abs_filepath, "rb") as f:
                return f.read()
        except:
            pass
    return "" # by default



def send_static_frontend_resource(try_direct_path=False):
    # 泛路径的，以 __ 开头，如果 try_direct_path = True， 则会忽略这个规则
    path = get_request_path_for_bucket()
    if path.startswith('/fb_static/'): # old style for Farbox and Bitcron
        r_response = send_static_file(path.replace('/fb_static/', ''))
        if r_response:
            return r_response
        else:
            abort(404, 'static file under /fb_static/ can not be found')
    if not try_direct_path and not path.startswith('/__'):
        return
    frontend_name = path.replace('/__', '', 1).strip('/')
    if frontend_name not in web_static_resources_map:
        return
    abs_filepath = web_static_resources_map[frontend_name]
    set_context_value_from_request("is_system_static_file", True)
    return send_file_with_304(abs_filepath)

