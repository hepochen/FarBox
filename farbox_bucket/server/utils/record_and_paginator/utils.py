# coding: utf8
import os
from farbox_bucket.utils import string_types, to_int, smart_unicode

default_excludes = ["_", "template", "configs", "licenses"]



def should_exclude_record(record, excludes):
    should = False
    path = record.get('path')
    path_without_ext = os.path.splitext(path)[0]
    if '_' in excludes or '-' in excludes:
        excludes_tmp = True # 不包含临时文件，比如_cover, _cache .etc
        if path in ['_nav']:
            excludes_tmp = False
    else:
        excludes_tmp = False
    if not path:
        should  = True
    elif path in excludes:
        should = True
    elif path_without_ext in excludes: # 这个是文件名包含
        should = True
    elif path_without_ext.split('/')[0] in excludes: # 这是是第一层目录包含
        should = True
    if excludes_tmp and (path.startswith('_') or '/_' in path):  # _ 开头的作为tmp 逻辑
        should = True
    return should



def does_hit_level(record, level, path_prefix):
    path = record.get('path')
    base_slash_number = path_prefix.strip('/').count('/') if path_prefix else -1
    current_slash_number =  path.strip('/').count('/') if path else -1
    current_level = current_slash_number - base_slash_number
    if type(level) in [list, tuple] and len(level) == 2 and level[1] > level[0]:
        if level[1] >= current_level >= level[0]:
            return True
    elif type(level) == int:  # 指定一个层级的目录
        if current_level == level:
            return True
    elif isinstance(level, string_types):
        int_level = to_int(level.strip('<>'), None)
        if int_level:
            if level.startswith('>') and current_level>int_level:
                return True
            elif level.startswith('<') and current_level<int_level:
                return  True
    return False # at last


def does_hit_status(record, status):
    if status == "all":
        return True
    record_status = record.get('status', 'public')
    if status == record_status:
        return True
    else:
        return False


def does_hit_type(record, data_type):
    record_type = record.get('_type') or record.get('type')
    if record_type == data_type:
        return True
    else:
        return False



def filter_records(records, path_prefix='', status=None, excludes=None, data_type=None):
    # 主要是获取list数据类型的， 然后最最终的结果进行一次过滤
    if excludes is None and data_type in ["folder"]:
        excludes = default_excludes
    if isinstance(excludes, string_types):
        excludes = [smart_unicode(excludes)]
    if not isinstance(excludes, (list, tuple)):
        excludes = []
    filtered_records = []
    for record in records:
        if excludes and should_exclude_record(record, excludes):
            continue
        if status and not does_hit_status(record, status):
            continue
        if data_type and not does_hit_type(record, data_type):
            continue
        # at last
        filtered_records.append(record)
    return filtered_records