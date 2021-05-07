#coding: utf8
from __future__ import absolute_import
import os
import time
import re
import json
import hashlib
from farbox_bucket.utils import smart_unicode, smart_str, string_types

def is_real(path):
    # 主要是判断是否真实的文档，还是软链，或者软链下的目录内
    if not os.path.exists(path):
        return False
    parts = path.split('/')
    for i in range(len(parts)):
        if i:
            _path = '/'.join(parts[:-i])
        else:
            _path = path
        if os.path.islink(_path):
            return False
    return True


def is_a_hidden_path(path):
    if re.search('(^|/)(\.|~$)', path):
        return True
    elif re.search(r'~\.[^.]+$', path):
        return True
    elif re.search(r"/@eaDir/", path, flags=re.I): # 群晖
        return True
    elif re.search(r"@SynoEAStream$", path, flags=re.I): # 群晖
        return True
    elif path.endswith('~'):
        return True
    else:
        return False



def get_just_name(filepath, for_folder=False):
    if not filepath:
        return ""
    if not isinstance(filepath, string_types):
        return ""
    folder, filename = os.path.split(filepath)
    if for_folder:
        return filename
    just_name, ext = os.path.splitext(filename)
    return just_name


def split_path_by_name(name, length=7, hash_name=True):
    name = name.strip()
    if hash_name:
        name_string = hashlib.md5(smart_str(name)).hexdigest()
    else:
        name_string = name
    head = name_string[:length-1]
    tail = name_string[length-1:]
    path_parts = list(head) + [tail]
    path = '/'.join(path_parts)
    return path



def make_sure_path(path, is_file=False, is_dir=False):
    # 保证path是有效的，特别是写入一个文件的时候，避免没有父目录，而写入失败
    # 如果返回False，表示有问题...
    # is_file 表示会新建一个文件，里面用当前的时间戳作为正文内容
    if not is_dir: # 非 dir，只保证其父目录的存在
        folder, name = os.path.split(path)
    else:
        folder = path
    if not os.path.isdir(folder):
        try:
            os.makedirs(folder)
        except:
            return False
    if is_file: # like touch in linux
        try:
            with open(path, 'w') as f:
                f.write("%s" % time.time())
        except:
            pass
    return True



def get_file_list(root_path, split=False):
    # 遍历folder
    file_paths = []
    just_files = []
    just_folders = []
    if not os.path.isdir(root_path): # 根目录不存在，不处理
        pass
    else:
        for parent, folders, files in os.walk(root_path):
            if is_a_hidden_path(parent):
                continue
            elif not is_real(parent): # link类型的不处理
                continue

            for filename in files:
                file_path = os.path.join(parent, filename)
                if not is_a_hidden_path(file_path) and is_real(file_path):
                    #relative_path = file_path.replace(root_path, '').strip('/')
                    file_paths.append(file_path)
                    just_files.append(file_path)

            for filename in folders:
                file_path = os.path.join(parent, filename)
                if not is_a_hidden_path(file_path) and is_real(file_path):
                    #relative_path = file_path.replace(root_path, '').strip('/')
                    file_paths.append(file_path)
                    just_folders.append(file_path)
    if not split:
        return file_paths
    else:
        return just_folders, just_files



def get_all_sub_files(root, accept_func=None, max_tried_times=None):
    # ignore_folders 里的文件，不处理； accept_func可以处理当前的 path 是否支持
    root = same_slash(root)
    result = []
    tried = 0
    if not os.path.isdir(root): # 目录不存在
        return result
    to_break = False
    for parent, folders, files in os.walk(root):
        #if is_a_hidden_path(parent):
            #continue
        parent_relative_path = get_relative_path(parent, root)
        if is_a_hidden_path(parent_relative_path):
            continue
        if not is_real(parent): # link类型的不处理
            continue
        for filename in files:
            tried += 1
            filepath = join(parent, filename)
            if accept_func:
                accepted = accept_func(filepath)
            else:
                accepted = True
            if accepted:
                result.append(filepath)
            if max_tried_times and tried >= max_tried_times:
                to_break = True
                break
        if to_break:
            break
    return result


def get_relative_path(filepath, root, return_name_if_fail=True):
    filepath = same_slash(filepath)
    root = same_slash(root)
    if filepath and root and filepath.startswith(root+'/'):
        return filepath.replace(root, '').strip('/')
    elif filepath == root:
        return ''
    else:
        if return_name_if_fail:
            return os.path.split(filepath)[-1]
        else:
            return filepath



_join = os.path.join

def join(*args, **kwargs):
    args = [smart_unicode(arg) for arg in args]
    path = _join(*args, **kwargs)
    return same_slash(path)



def same_slash(path):
    path = path.replace('\\', '/')
    path = path.rstrip('/')
    path = smart_unicode(path)
    return path

def is_same_path(p1, p2):
    p1 = p1 or ''
    p2 = p2 or ''
    p1 = smart_unicode(p1.strip('/').lower())
    p2 = smart_unicode(p2.strip('/').lower())
    return p1 == p2


def is_sub_path(filepath, parent_path, direct=False):
    if not parent_path: # ignore
        return False
    if not filepath:
        return False
    parent_path = same_slash(parent_path).lower()
    filepath = same_slash(filepath).lower()
    is_under_parent = filepath.startswith(parent_path+'/')
    if is_under_parent and direct:
        # 必须是直接的根目录, 如果是子目录之下的, 则忽略
        relative_path = filepath.replace(parent_path, '', 1).strip('/')
        if '/' in relative_path:
            return False
    return is_under_parent




def write_file(filepath, content):
    make_sure_path(filepath)
    if isinstance(content, unicode):
        content = content.encode('utf8')
    with open(filepath, 'wb') as f:
        f.write(content)


def read_file(filepath):
    if not os.path.isfile(filepath):
        return ''
    else:
        with open(filepath, 'rb') as f:
            raw_content = f.read()
        return raw_content


def delete_file(file_path):
    if not os.path.exists(file_path):
        return # ignore
    if os.path.isfile(file_path):
        try:
            os.remove(file_path)
        except:
            pass


def load_json_file(filepath):
    raw_content = read_file(filepath)
    if not raw_content:
        return {}
    try:
        raw_content = smart_unicode(raw_content)
        return json.loads(raw_content)
    except:
        return {}

def dump_json_file(filepath, data):
    json_data = json.dumps(data, indent=4)
    write_file(filepath, json_data)
