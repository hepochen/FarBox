# coding: utf8
from __future__ import absolute_import
import json
import copy
from farbox_bucket.utils import string_types, to_int, smart_unicode
from farbox_bucket.server.utils.cache_for_function import cache_result
from farbox_bucket.server.utils.record_and_paginator.paginator import get_paginator as _get_paginator

from farbox_bucket.bucket.utils import get_bucket_configs, get_bucket_site_configs, get_bucket_in_request_context
from farbox_bucket.bucket.record.get.path_related import get_record_by_path, get_record_by_url,\
    get_json_content_by_path, has_record_by_path, get_raw_content_by_record
from farbox_bucket.bucket.record.get.tag_related import get_records_by_tag

from farbox_bucket.utils.functional import cached_property
from farbox_bucket.utils.data import make_tree as _make_tree

from farbox_bucket.server.utils.record_and_paginator.paginator import auto_pg, pg_with_keywords_search
from farbox_bucket.server.utils.doc_url import get_doc_url_for_template_api
from farbox_bucket.server.utils.request_context_vars import set_doc_in_request
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

    def get_force_graph_data(self, under=""):
        # todo, mix tag & refer
        pass

    @cached_property
    def bucket(self):
        bucket = get_bucket_in_request_context()
        return bucket

    @staticmethod
    @cache_result
    def get_data(type='post', limit=None, page=None, path=None, level=None, level_start=None, level_end=None, excludes=None,
                 status=None, with_page=True, pager_name=None, sort='desc', return_count=False,
                 date_start=None, date_end=None, ignore_marked_id=None, prefix_to_ignore=None, keywords=None, min_limit=0, **kwargs):

        # 对 Bitcron 的兼容, tag for get_data
        tag_to_match = kwargs.get("tags") or kwargs.get("tag")
        if tag_to_match:
            if isinstance(tag_to_match, (list, tuple)):
                tag_to_match = tag_to_match[0]
        if tag_to_match:
            tag_match_records= get_records_by_tag(get_bucket_in_request_context(), tag=tag_to_match,
                                      sort_by="-date" if sort=="desc" else "date")
            if return_count:
                return len(tag_match_records)
            return tag_match_records


        if isinstance(type, (list, tuple)) and type:
            type = type[0]

        if isinstance(type, string_types) and "+" in type: # 兼容旧的 Bitcron， 查询索引所限，只能单一 post
            type = type.split("+")[0].strip()

        if type == "all":
            type = None

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

        bucket = get_bucket_in_request_context()

        if type == "post" and path is None and bucket:
            # 尝试取得 posts_root，可以分离数据, 这是默认的情况， 即使指定了 path = ""， 也不走这个逻辑
            site_configs = get_bucket_site_configs(bucket)
            posts_root = smart_unicode(site_configs.get("posts_root", "")).strip()
            if posts_root:
                path = posts_root

        if keywords:
            obj_list = pg_with_keywords_search(
                bucket = bucket,
                keywords = keywords,
                limit = limit,
                with_page = with_page,
                page = page,
                pager_name = pager_name,
                path = path,
                excludes = excludes,
                status = status,
                sort_by = sort,
                return_total_count = return_count,
                date_start = date_start,
                date_end = date_end,
                min_limit = min_limit,
            )

        else:
            obj_list = auto_pg(
                bucket = bucket,
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

                min_limit = min_limit,
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

    def has(self, path=None):
        if not path:
            return False
        return has_record_by_path(self.bucket, path)



    def get_doc(self, path, **kwargs):
        path = path.lower().strip('/').strip()
        if "?" in path:
            path = path.split("?")[0]
        if "#" in path:
            path = path.split("#")[0]
        doc = self.get_doc_by_url(path) or self.get_doc_by_path(path) or {}
        if path == 'settings.json':
            doc['raw_content'] = json.dumps(get_bucket_site_configs(self.bucket), indent=4, ensure_ascii=False) #ensure_ascii
        if not doc:
            return

        if doc.get("_zipped"):
            doc["raw_content"] = get_raw_content_by_record(doc)

        doc_type = doc.get('_type') or doc.get('type')
        if kwargs.get('type') and kwargs.get('type')!=doc_type:
            return None
        as_context_doc = kwargs.get('as_context_doc')
        if as_context_doc and doc:
            set_doc_in_request(doc)
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


    def get_doc_url(self, doc, url_prefix, url_root=None, hit_url_path=False):
        # hit_url_path=True 的时候，post 上有 url_path， 但跟 post.url 直接调用的逻辑不亦一样
        # post.url 相当于有一个动态的 url_prefix
        return get_doc_url_for_template_api(doc, url_prefix=url_prefix, url_root=url_root, hit_url_path=hit_url_path)


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