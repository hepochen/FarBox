# coding: utf8
from __future__ import absolute_import
import json
from flask import g
import copy
from farbox_bucket.utils import string_types, to_date, to_int
from farbox_bucket.server.utils.cache_for_function import cache_result
from farbox_bucket.server.utils.record_and_paginator.paginator import get_paginator as _get_paginator

from farbox_bucket.bucket.utils import get_bucket_configs, get_bucket_site_configs
from farbox_bucket.bucket.record.get.path_related import get_record_by_path, get_record_by_url, get_json_content_by_path

from farbox_bucket.utils.functional import cached_property
from farbox_bucket.server.utils.record_and_paginator.paginator import auto_pg
from farbox_bucket.utils.data import make_tree as _make_tree

from farbox_bucket.server.helpers.file_manager import sync_file_by_server_side


def level_to_level_start_and_end(level, path):
    if not level:
        return None, None
    level_start, level_end = None, None
    base_slash_number = path.strip('/').count('/') if path else -1  # 根目录的当做-1处理
    if type(level) in [list, tuple] and len(level)==2 and level[1] > level[0]:
        level_start = base_slash_number+level[0]
        level_end = base_slash_number+level[1]
    elif type(level)==int: # 指定一个层级的目录
        level_start = level_end = base_slash_number+level
    elif isinstance(level, string_types):
        current = base_slash_number + to_int(level.strip('<>'), 0)
        if level.startswith('>'):
            level_start = current + 1
        elif level.startswith('<'): # <1 相当于0
            level_end = current
    return level_start, level_end




class Data(object):
    @staticmethod
    @cache_result
    def make_tree(docs, kept_fields=None):
        docs = [copy.copy(doc) for doc in docs] # 复制一份，因为很多 record 是 cache 性质的，不能直接修改
        return _make_tree(docs, kept_fields)

    @cached_property
    def bucket(self):
        bucket = getattr(g, 'bucket', None)
        return bucket

    def get_data(self, type='post', limit=None, page=None, path='', level=None, level_start=None, level_end=None, excludes=None,
                 status=None, with_page=True, pager_name=None, sort='desc', return_count=False,
                 date_start=None, date_end=None, ignore_marked_id=None, prefix_to_ignore=None, **kwargs):
        if isinstance(type, (list, tuple)) and type:
            type = type[0]

        if level is not None and level_start is None and level_end is None:
            # 重新计算 level，如果给 level，是相当于 path 的相对路径
            level_start, level_end = level_to_level_start_and_end(level=level, path=path)

        if prefix_to_ignore is None:
            if type in ['post']:
                prefix_to_ignore = '_'

        if ignore_marked_id is None:
            if type in ['post']:
                ignore_marked_id = True
                if status == "all":
                    ignore_marked_id = False
            else:
                ignore_marked_id = False

        obj_list = auto_pg(
            bucket = self.bucket,
            data_type = type,
            limit = limit,
            with_page = with_page,
            page = page,
            pager_name = pager_name,
            path = path,
            level_start = level_start,
            level_end = level_end,
            excludes = excludes,
            status = status,
            sort_by = sort, # for position 才特殊处理
            return_total_count = return_count,
            date_start = date_start,
            date_end = date_end,

            ignore_marked_id = ignore_marked_id,
            prefix_to_ignore = prefix_to_ignore,
        )

        fields = kwargs.get('fields')
        if fields and isinstance(fields, (list, tuple)) and obj_list and isinstance(obj_list, (list, tuple)):
            obj_list = [{key:value for key,value in obj.items() if key in fields} for obj in obj_list if isinstance(obj, dict)]
        return obj_list


    def get_record_by_url(self, url=''):
        if not self.bucket or not url:
            return None
        return get_record_by_url(self.bucket, url)


    def get_record_by_path(self, path=''):
        if not self.bucket or not path:
            return None
        return get_record_by_path(self.bucket, path)

    def get_doc_by_url(self, url=''):
        return self.get_record_by_url(url)

    def get_doc_by_path(self, path=''):
        return self.get_record_by_path(path)


    def get_doc(self, path, **kwargs):
        path = path.lower().strip('/').strip()
        doc = self.get_doc_by_url(path) or self.get_doc_by_path(path) or {}
        if path == 'settings.json':
            doc['raw_content'] = json.dumps(get_bucket_site_configs(self.bucket), indent=4, ensure_ascii=False) #ensure_ascii
        if not doc:
            return
        doc_type = doc.get('_type') or doc.get('type')
        if kwargs.get('type') and kwargs.get('type')!=doc_type:
            return None
        as_context_doc = kwargs.get('as_context_doc')
        if as_context_doc and doc:
            g.doc = doc
        return doc


    def sort_by_position(self, records, reverse=False):
        if not records:
            return records
        if not isinstance(records, (list, tuple)):
            return records
        orders_configs = get_bucket_configs(self.bucket, 'orders') or {}
        if not orders_configs:
            return records
        sorted_records_with_order_value = []
        for record in records:
            path = record.get('path')
            if not isinstance(path, string_types):
                continue
            path = path.lower()
            order_value = orders_configs.get(path, -1)
            sorted_records_with_order_value.append([order_value, record])
        sorted_records_with_order_value.sort()
        if reverse:
            sorted_records_with_order_value.reverse()
        sorted_records = [row[1] for row in sorted_records_with_order_value]
        return sorted_records

    @staticmethod
    @cache_result
    def get_paginator(index_or_name=0):
        return _get_paginator(index_or_name)


    def update_json(self, path, **kwargs):
        # 更新一个 json 文件，用 simple_sync 的调用
        # 注意，调用这个函数的时候，并不需要管理员权限，所以，要慎重处理!!!!
        if not path.lower().endswith('.json'):
            return 'must be a json file'
        json_data = get_json_content_by_path(self.bucket, path)
        if not isinstance(json_data, dict):
            return 'update_json failed, not a dict obj'
        to_update = False
        for key, value in kwargs.items():
            old_value = json_data.get(key)
            if value != old_value:
                to_update = True
                break
        if to_update:
            json_data.update(kwargs)
            new_content = json.dumps(json_data, indent=4)
            sync_file_by_server_side(bucket=self.bucket, relative_path=path, content=new_content, is_dir=False, is_deleted=False)
        return ''



@cache_result
def data():
    return Data()

@cache_result
def d():
    return data()

@cache_result
def paginator():
    return _get_paginator()



def get_data(type='post', limit=None, page=None, path='', level=None, level_start=None, level_end=None, excludes=None,
                 status=None, with_page=False, pager_name=None, sort='desc', return_count=False, **kwargs):
    d = data()
    result = d.get_data(type=type, limit=limit, page=page, path=path, level=level, level_start=level_start,
                        level_end=level_end, excludes=excludes, status=status, with_page=with_page,
                        pager_name=pager_name, sort=sort, return_count=return_count, **kwargs)
    return result