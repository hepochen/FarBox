# coding: utf8
from __future__ import absolute_import
from farbox_bucket.utils import smart_str, smart_unicode
from farbox_bucket.utils.functional import cached_property
from dateutil.parser import parse as date_parse
from flask import request
import json
import base64
import datetime
import re
import csv
from io import BytesIO

class UTCDateJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime.datetime):
            v = {'$date_string': o.isoformat()}
            return v
        return json.JSONEncoder.default(self, o)



def json_object_hook(dct):
    if '$date_string' in dct:
        value = dct['$date_string']
        try: value = date_parse(value)
        except: pass
        return value
    return dct


def json_dumps(obj, indent=None):
    # 主要是 mongodb 上的一些 obj
    if isinstance(obj, dict) and '_id' in obj:
        obj['_id'] = smart_str(obj['_id'])
    return json.dumps(obj, cls=UTCDateJSONEncoder, indent=indent)


def json_loads(raw_content):
    # 主要是 mongodb 上的一些 obj
    return json.loads(raw_content, object_hook=json_object_hook)



def csv_to_list(raw_content, max_rows=None, max_columns=None, return_max_length=False, auto_fill=False):
    # auto_fill 表示会自动补充缺失的空 cell
    file_io = BytesIO(smart_str(raw_content))
    csv_reader = csv.reader(file_io)
    result = []
    i = 0
    max_length = 0
    if max_rows is None:
        max_rows = 9999
    for row in csv_reader:
        row = [smart_unicode(s).strip().replace('\\n', '\n') for s in row]
        if max_columns: # 一行最多允许多少列数据
            row = row[:max_columns]
        if len(row) > max_length:
            max_length = len(row)
        result.append(row)
        if i >= max_rows:
            break
        i += 1
    if auto_fill: # 自动补全
        result = [row+['']*(max_length-len(row)) for row in result]
    if return_max_length:
        return result, max_length
    else:
        return result


def list_to_csv(data_list, max_rows=None):
    content_list = []
    i = 0
    for row in data_list:
        if isinstance(row, (tuple, list)):
            content_list.append(','.join(row))
        if i >= max_rows:
            break
        i += 1
    content = '\n'.join(content_list)
    return smart_unicode(content)


def dump_csv(list_obj, lines=True):
    f = BytesIO()
    wr = csv.writer(f, quoting=csv.QUOTE_ALL)
    if lines: # 多行，list_obj 内的元素，本身自成一行
        for sub_list in list_obj:
            sub_list = [smart_str(e) for e in sub_list]
            wr.writerow(sub_list)
    else:
        list_obj = [smart_str(e) for e in list_obj]
        wr.writerow(list_obj)
    return f.getvalue()



def csv_list_to_dict(data_list):
    # 用第一行，作为 key，形成一个 obj list，每个 obj 是一个 dict 对象
    result = []
    if not data_list or not isinstance(data_list, (list, tuple)):
        return result
    if len(data_list) <= 1: # 必须保证有2行以及以上的元素，才能生成dict
        return result
    keys = data_list[0]

    # 校验 keys 是否符合规则
    for key in keys:
        if '.' in key:
            return []
        key = key.strip()
        if not re.match(r'[a-z0-9_]+$', key, flags=re.I):
            return []
        if len(key) >= 20:
            return []

    for obj_list in data_list[1:]:
        obj = {}
        for i, key in enumerate(keys):
            # 并不是所有key都会构建成dict中的一部分，可能有部分key会被ignore掉，以防冲突
            # 也可能对应的value上的index不存在数据
            key = key.strip().lower() # 全部小写化处理
            if key and '.' not in key and len(key)<20: # key中不能包含 dot 符 & key的长度不能超过20
                try:
                    value = obj_list[i]
                    #if key == 'date' and value:
                    #    try: value = date_parse(value, utc_offset=utc_offset)
                    #    except: pass
                    if value:
                        obj[key] = value
                except IndexError:
                    break
        if obj:
            result.append(obj)
    return result


def csv_data_to_objects(data):
    # csv_data 本身是一个list组成的list，要转化为dict组成的list
    if  isinstance(data, (tuple, list)) and len(data)>=2:
        objects = csv_list_to_dict(data)
    else:
        objects = []
    return objects


def csv_records_to_object(keys, *records):
    # 多个records，对应的keys，组成的object
    data = [keys] + list(records)
    objects = csv_list_to_dict(data)
    if objects:
        return objects[0]
    return {}


def json_b64_loads(raw_content):
    try:
        raw_content = base64.b64decode(raw_content)
    except:
        pass
    try:
        data = json_loads(raw_content)
    except:
        data = {}
    return data


def json_b64_dumps(obj):
    json_data = json_dumps(obj)
    return base64.b64encode(json_data)


class DataWorker(object):
    def __init__(self, keys, origin):
        self.keys = keys
        self.origin = origin or {}
        self.origin.pop('_id', None) # 可能是数据库的主键，会导致新旧数据不一致

    @cached_property
    def new_obj(self):
        """获取从request中得到的新数据"""
        obj = {}
        for key in self.keys:
            value = (request.values.get(key) or '')[:2000] # 最多不能超过2k字
            old_value = self.origin.get(key)
            if old_value is not None and not isinstance(old_value, (str, unicode)):
                try:
                    value = type(old_value)(value)
                except:
                    pass
            obj[key] = value
        return obj


    @cached_property
    def changed_properties(self):
        changed_keys = []
        for key in self.keys:
            if self.origin.get(key)!=self.new_obj.get(key):
                changed_keys.append(key)
        return changed_keys

    @cached_property
    def changed(self):
        return self.changed_properties

    @cached_property
    def new(self):
        return self.new_obj

    @cached_property
    def old(self):
        return self.origin


    def get_obj_with_processors(self, processors):
        # processors是key/v形式的，确定new_obj是否合适作为存储的对象
        # 比如email修改了，但是email是不会存储的
        new_obj = self.new_obj
        for key in self.changed_properties:
            if key in processors:
                processor = processors[key]
                if hasattr(processor, '__call__'):
                    new_value = processor(self.new_obj.get(key), self.origin.get(key))
                else:
                    new_value = processor
                if new_value is None: # reset to old_value
                    new_obj[key] = self.origin.get(key)
                else: # update
                    new_obj[key] = new_value
        return new_obj






def make_tree(docs, kept_fields=None):
    if not docs:
        return docs

    #('title', 'position', '_images_count', 'images_count', 'posts_count', '_posts_count', 'real_path')
    if kept_fields and isinstance(kept_fields, (list, tuple)): # 为避免产生的 tree 包含太多数据，如果指定了 kept_fields
        kept_fields = set(list(kept_fields) + ['slash_number', 'path'])
        _docs = []
        for doc in docs:
            doc = {field:doc.get(field) for field in kept_fields}
            _docs.append(doc)
        docs = _docs

    leveled_docs = {}
    for doc in docs:
        slash_number = doc.get('slash_number') # 肯定是整数
        if slash_number is None:
            continue
        leveled_docs.setdefault(slash_number, []).append(doc)

    levels = leveled_docs.keys()
    if not levels:
        return docs

    min_level = min(levels)
    max_level = max(levels)

    level1_docs = leveled_docs.pop(min_level) # 先得到第一级的
    if min_level == max_level: # 没有多层结构
        return level1_docs

    parent_level_docs = level1_docs
    for level in range(min_level+1, max_level+1): # 得到后续的 level
        current_level_docs = leveled_docs.pop(level, [])
        if not current_level_docs:
            break
        parent_match_dict = {doc['path'].lower():doc for doc in parent_level_docs}
        for doc in current_level_docs:
            parent_path = doc['path'].lower().rsplit('/', 1)[0]
            parent_doc = parent_match_dict.get(parent_path)
            if parent_doc and isinstance(parent_doc, dict):
                children = parent_doc.setdefault('children', [])
                if doc not in children:
                    children.append(doc)
                #parent_doc.setdefault('children', []).append(doc)
        parent_level_docs = current_level_docs
    return level1_docs