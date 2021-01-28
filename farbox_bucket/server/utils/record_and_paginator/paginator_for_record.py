#coding: utf8
from __future__ import absolute_import
import urllib
from math import ceil
from flask import request, abort
from farbox_bucket.utils.functional import cached_property
from farbox_bucket.utils import smart_unicode, to_int
from farbox_bucket.utils.ssdb_utils import zsize
from farbox_bucket.bucket.utils import get_order_bucket_name, get_bucket_configs, get_bucket_name_for_path
from farbox_bucket.bucket.record.get.mix import mix_get_record_paths
from farbox_bucket.bucket.record.get.path_related import get_records_by_paths, get_record_by_path

def compute_auto_pages(pages, current_page=1, max_count=10):
    # 1 ...... n
    if max_count < 6:
        max_count = 6
    if pages <= max_count:
        return range(1, pages+1)

    just_head = range(1, max_count-1) + [0, pages]
    just_foot = [1, 0] + range(pages-max_count+1, pages+1)

    if current_page in just_head and current_page!=pages:
        if current_page < max_count/2:
            return just_head
    if current_page in just_foot and current_page!=1:
        if current_page > pages-max_count/2:
            return just_foot

    auto_fix_count = (max_count - 2*2)/2
    head = [1, 2]
    foot = [pages-1, pages]
    _middle_list = range(current_page-auto_fix_count+1, current_page+auto_fix_count)
    middle_list = []
    for i in _middle_list:
        if 1<i<pages and i not in head and i not in foot:
            middle_list.append(i)
    result =  head
    if result[-1]+1 not in middle_list:
        result.append(0) # head fill
    result += middle_list
    if result[-1] and result[-1]+1 not in foot:
        result.append(0)
    result += foot
    return result



# 只针对 zrange，不然无法获取
class SortedRecordsPaginator(object):
    def __init__(self, bucket, data_type, per_page=3, page=1, path=None,
                 level_start=None, level_end=None, sort_by=None,
                 ignore_marked_id=False, prefix_to_ignore=None, date_start=None, date_end=None,):
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

    def __getitem__(self, item):
        # 主要是做 for 循环用的
        if hasattr(self.list_object, '__getitem__'):
            return self.list_object.__getitem__(item)

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
    def pre_page(self):
        return self.previous_page

    @cached_property
    def total_count(self):
        # count = zsize(self.z_bucket) or 0
        #if self.path or self.date_start or self.date_end:
        count = len(self._all_matched_paths)
        return count

    @cached_property
    def has_previous(self):
        return self.page > 1

    @cached_property
    def has_pre(self):
        return self.has_previous

    @cached_property
    def has_next(self):
        return self.page < self.total_pages


    @staticmethod
    def get_page_url(page_number):
        if '/page/' in request.url:
            base = request.path.split('/page/',1)[0]
        else:
            base = request.path
        if page_number != 1:
            url = ('%s/page/%s'%(base, page_number)).replace('//','/')
        else:
            url = base.replace('//','/') or '/'
        if request.query_string:
            query_string = request.query_string
            if '%' in query_string:
                query_string = urllib.unquote(query_string)
            url += '?%s'%smart_unicode(query_string)
        url = url.replace('"', '%22').replace("'", '%27') # 避免被跨站
        return url

    @cached_property
    def previous_page_url(self):
        if self.has_previous:
            return self.get_page_url(self.previous_page)
        else:
            return '#'

    @cached_property
    def pre_page_url(self):
        return self.previous_page_url

    @cached_property
    def pre_url(self):
        return self.pre_page_url

    @cached_property
    def next_page_url(self):
        if self.has_next:
            return self.get_page_url(self.next_page)
        else:
            return '#'

    @cached_property
    def next_url(self):
        return self.next_page_url



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


    @cached_property
    def page_numbers(self):
        return self.get_page_numbers()

    def set_default_max_page_numbers(self, numbers):
        # 设定 auto_pages 计算时，最大的长度跨度
        numbers = to_int(numbers)
        if isinstance(numbers, int) and 50>numbers>3:
            self.default_max_page_numbers = numbers
        return ''


    def get_page_numbers(self, max_count=None):
        if not max_count:
            max_count = self.default_max_page_numbers
        return compute_auto_pages(self.total_pages, current_page=self.page, max_count=max_count)

