#coding: utf8
import os, re, time
import datetime
from farbox_bucket.utils import smart_str
from farbox_bucket.utils.path import join, same_slash



MARKDOWN_EXTS = ['.txt', '.md', '.markdown', '.mk']

def _is_a_markdown_file(path):
    if not path:
        return False
    ext = os.path.splitext(path)[1].lower()
    return ext in MARKDOWN_EXTS



def make_sure_archive_folder(filepath):
    # 根据某一个文件路径，创建其对应的.Archive目录，主要是用来处理版本管理的
    folder_path = same_slash(os.path.dirname(filepath))
    archive_path = join(folder_path, '.Archive')
    if not os.path.isdir(archive_path):
        os.makedirs(archive_path)
    return archive_path


def get_file_versions_folder(filepath):
    filepath = same_slash(filepath)
    if not os.path.isfile(filepath): # 源文件不存在，则不处理
        return # ignore
    archive_path = make_sure_archive_folder(filepath) # 确保.Archive目录存在
    filename = os.path.split(filepath)[-1]
    versions_folder = join(archive_path, filename)
    return versions_folder


def create_file_version(filepath, force=False, min_time_diff=60, history_max_versions=150):
    # force 表示强制version
    # 将一个file_path进行拷贝到特定目录的读写操作，进而形成version的概念
    filepath = same_slash(filepath)

    # for Markdown file only
    if not _is_a_markdown_file(filepath):
        return

    if not os.path.exists(filepath):
        return # ignore

    if os.path.isdir(filepath):
        return

    with open(filepath, 'rb') as f:
        raw_content = f.read()
        if not raw_content:
            return # blank content, ignore

    raw_content = smart_str(raw_content)

    now = datetime.datetime.now()
    now_str = now.strftime('%Y-%m-%d %H-%M-%S')

    version_folder = get_file_versions_folder(filepath)
    if not version_folder:
        return # ignore

    version_file_path = join(version_folder, now_str+os.path.splitext(filepath)[1])

    if not os.path.isdir(version_folder):
        os.makedirs(version_folder)

    versions_file_names = os.listdir(version_folder)
    versions_file_names = [name for name in versions_file_names if re.search('\d{4}-\d{1,2}-\d{1,2}',name)]
    versions_file_names.sort()
    versions_file_names.reverse() # 倒序之后，就是最新的排最前面

    file_size = os.path.getsize(filepath)
    now = time.time()

    if versions_file_names and file_size<30*1024: # 对30k以下的文章，做version进一步的判断
        last_version = versions_file_names[0]
        last_path = join(version_folder, last_version)
        last_mtime = os.path.getmtime(last_path)
        with open(last_path) as f:
            last_content = f.read()
        if last_content == raw_content: # 内容没有变化，ignore
            return

        length_diff = abs(len(last_content)-len(raw_content))
        if length_diff < 30 or 0< (now-last_mtime) < min_time_diff and not force:
            # 内容长度变化小余30，或者最后修改时间1分钟内的，忽略掉
            return # ignore
    elif versions_file_names:
        # 1 分钟内, 才会尝试创建一个 version
        last_version = versions_file_names[0]
        last_path = join(version_folder, last_version)
        last_mtime = os.path.getmtime(last_path)
        if 0< (now-last_mtime) < min_time_diff and not force:
            return # ignore



    if file_size < 10*1024: # 10k以下
        max_versions = history_max_versions
        if max_versions < 0: max_versions = 0
    elif file_size < 100*1024: # 100k
        max_versions = 80
    elif file_size < 500*1024:
        max_versions = 50
    else:
        max_versions = 20

    if not max_versions: # ignore, versions is not allowed
        return

    for version_name_to_delete in versions_file_names[max_versions:]: # 删除过多的版本文件
        file_path_to_delete = join(version_folder, version_name_to_delete)
        try:
            os.remove(file_path_to_delete)
        except IOError:
            pass

    try:
        with open(version_file_path, 'wb') as new_f:
            new_f.write(raw_content)
    except IOError: # 失败
        return

