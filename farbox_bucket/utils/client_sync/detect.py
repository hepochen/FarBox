# coding: utf8
from __future__ import absolute_import
import os
import json
from farbox_bucket.utils import md5_for_file
from farbox_bucket.utils.path import same_slash, join, is_real, is_a_hidden_path, get_relative_path


from .sync_utils import get_sync_data, get_sync_data_folder



def should_sync(filepath, root, app_name, check_md5=True, extra_should_sync_func=None):
    if not os.path.exists(filepath):
        return False
    elif is_a_hidden_path(filepath):
        return False
    elif not is_real(filepath):
        return False


    if check_md5:
        sync_data = get_sync_data(filepath, root, app_name)
        if sync_data:
            if sync_data.get('md5') == md5_for_file(filepath): # has been synced
                return False


    # 比如 Bitcron, 不允许超过 100 mb 的文件上传
    # elif os.path.getsize(filepath) > 100*1024*1024: # 100Mb+ is not supported
    #return False
    if extra_should_sync_func:
        try:
            result = extra_should_sync_func(filepath, root)
            if isinstance(result, bool):
                return result
        except:
            try:
                relative_path = get_relative_path(filepath, root=root)
                result = extra_should_sync_func(relative_path)
                if isinstance(result, bool):
                    return result
            except:
                pass


    return True



def sync_loop_local_filesystem(root_path, app_name, check_md5=True, extra_should_sync_func=None):
    root_path = same_slash(root_path)
    if not os.path.isdir(root_path): # 根目录不存在，不处理
        return []
    file_paths = []
    for parent, folders, files in os.walk(root_path):
        if is_a_hidden_path(parent):
            continue
        elif not is_real(parent): # link类型的不处理
            continue
        for fs in [files, folders]:
            for filename in fs:
                filepath = join(parent, filename)
                # 看是否已经在本地数据库了
                if not should_sync(filepath, root_path, app_name, check_md5, extra_should_sync_func=extra_should_sync_func):
                    continue
                file_paths.append(filepath)
    return file_paths

    #for filepath in file_paths:
    #    sync_a_filer_or_folder(filepath)



def sync_find_files_to_delete(root_path, app_name, as_dict=False):
    sync_data_folder = get_sync_data_folder(root_path, app_name)
    if not os.path.isdir(sync_data_folder): # never synced before
        return []
    files = sync_loop_local_filesystem(root_path, app_name=app_name, check_md5=False) # same_path already
    data_filenames = os.listdir(sync_data_folder)
    old_file_paths = []
    old_dir_paths = set()
    for data_filename in data_filenames:
        data_filepath = join(sync_data_folder, data_filename)
        try:
            with open(data_filepath) as f:
                data = json.loads(f.read())
                filepath = data.get('filepath')
                is_dir = data.get('is_dir', False)
                if data.get('is_relative'):
                    filepath = join(root_path, filepath)
                if filepath:
                    filepath = same_slash(filepath)
                    old_file_paths.append(filepath)
                    if is_dir:
                        old_dir_paths.add(filepath)

        except:
            pass
    _filepaths_to_delete = list(set(old_file_paths) - set(files))

    # 让 folder 类型的排在最后
    filepaths_to_delete = []
    dirs_to_delete = []
    for path in _filepaths_to_delete:
        # todo 尝试判断是不是在 iCloud 上
        is_dir = filepath in old_dir_paths
        if not is_dir:
            filepaths_to_delete.append(path)
        else:
            dirs_to_delete.append(path)
    filepaths_to_delete += dirs_to_delete


    if as_dict:
        filepaths_to_delete_as_dict = []
        for filepath in filepaths_to_delete:
            is_dir= filepath in old_dir_paths
            filepaths_to_delete_as_dict.append(dict(
                path = filepath,
                filepath = filepath,
                is_dir = is_dir
            ))
        return filepaths_to_delete_as_dict

    else:
        return filepaths_to_delete


