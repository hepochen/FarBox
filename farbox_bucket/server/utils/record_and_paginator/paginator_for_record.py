#coding: utf8
from math import ceil
from flask import abort
from farbox_bucket.utils.functional import cached_property
from farbox_bucket.utils import to_int
from farbox_bucket.bucket.utils import get_order_bucket_name, get_bucket_configs, get_bucket_name_for_path
from farbox_bucket.bucket.record.get.mix import mix_get_record_paths
from farbox_bucket.bucket.record.get.path_related import get_records_by_paths
from farbox_bucket.server.utils.record_and_paginator.base_paginator import BasePaginator



# 只针对 zrange，不然无法获取
class SortedRecordsPaginator(BasePaginator):
    def __init__(self, bucket, data_type, per_page=3, page=1, path=None,
                 level_start=None, level_end=None, sort_by=None,
                 ignore_marked_id=False, prefix_to_ignore=None, date_start=None, date_end=None,):
        BasePaginator.__init__(self)
        z_bucket = get_order_bucket_name(bucket, data_type)
        self.data_type = data_type
        self.bucket = bucket # record bucket
        self.z_bucket = z_bucket  # for order
        self.path_bucket = get_bucket_name_for_path(bucket)
        self.level_start = level_start
        self.level_end = level_end
        self.sort_by = sort_by
        self.date_start = date_start
        self.date_end = date_end
        self.prefix_to_ignore = prefix_to_ignore

        page = to_int(page, 1, 10000) # 最多不超过10k页
        per_page = to_int(per_page, 3, 1000) # 单页不超过1k条记录
        if page * per_page > 100000: # 数据总数不能超过10w条
            abort(404)

        path = path or ''
        self.path = path.lower().strip('/')  # prefix

        self.per_page = per_page
        self.total_pages = int(ceil(float(self.total_count) / per_page))
        self.pages = self.total_pages # 总页码数
        self.page = page
        self.next_page = page + 1
        self.previous_page = page - 1

        self.default_max_page_numbers = 10

        self.ignore_marked_id = ignore_marked_id


    @cached_property
    def _all_matched_paths(self):
        if self.sort_by in ['-date','desc']:
            data_type_reverse_sort = True
        else:
            data_type_reverse_sort = False
        paths = mix_get_record_paths(bucket=self.bucket,
                                     path=self.path,
                                     level_start = self.level_start,
                                     level_end = self.level_end,
                                     data_type = self.data_type,
                                     data_type_reverse_sort = data_type_reverse_sort,
                                     date_start = self.date_start,
                                     date_end = self.date_end,
                                     prefix_to_ignore = self.prefix_to_ignore
                                     )
        return paths


    @cached_property
    def total_count(self):
        # count = zsize(self.z_bucket) or 0
        #if self.path or self.date_start or self.date_end:
        count = len(self._all_matched_paths)
        return count


    @cached_property
    def bucket_orders_configs(self):
        orders_configs = get_bucket_configs(self.bucket, 'orders') or {}
        return orders_configs

    @cached_property
    def list_object(self):
        if self.page > self.total_pages or self.page < 1:
            return []
        start_at = (self.page - 1) * self.per_page
        paths = self._all_matched_paths[start_at:start_at+self.per_page]
        ignore_marked_id = self.ignore_marked_id
        #ignore_marked_id = False if self.path.startswith('_') else True
        records = get_records_by_paths(bucket=self.bucket, paths=paths, ignore_marked_id=ignore_marked_id)
        return records


