# coding: utf8
from math import ceil
from flask import request
from farbox_bucket.utils import to_int, string_types
from .paginator_for_record import SortedRecordsPaginator as Paginator
from farbox_bucket.server.utils.lazy import LazyDict
from farbox_bucket.server.utils.site_resource import get_site_config
from farbox_bucket.server.utils.record_and_paginator.utils import filter_records
from farbox_bucket.server.es.es_search import search_posts
from farbox_bucket.server.utils.record_and_paginator.base_paginator import BasePaginator
from farbox_bucket.server.utils.request_context_vars import get_context_value_from_request

MAX_PER_PAGE = 1000


def pg_with_keywords_search(bucket, keywords, limit=None, page=None, pager_name=None, with_page=True,
            path=None, status=None,  sort_by=None,excludes=None,
            min_limit=0, return_total_count=False, date_start=None, date_end=None):
    if limit is None:
        limit = get_site_config(['post_per_page', 'posts_per_page', 'per_page'], type_required=int)
    limit = limit or 5
    if min_limit and limit < min_limit:
        limit = min_limit
    if limit > MAX_PER_PAGE:
        limit = MAX_PER_PAGE

    if not with_page and not page:
        page = 1
    else:
        page = page or get_context_value_from_request("page") or 1

    search_result = search_posts(bucket=bucket, keywords=keywords, limit=limit, page=page,
                                 path=path, status=status, sort=sort_by, date_start=date_start, date_end=date_end,
                                 return_count=return_total_count)
    if return_total_count:
        return search_result

    total, current_page_posts = search_result

    total_pages = int(ceil(total / float(limit)))

    paginator =  BasePaginator(page=page, total_pages=total_pages, list_object=current_page_posts)

    if with_page: # 启用分页
        if not hasattr(request, 'paginators'):
            request.paginators = []
        if not hasattr(request, 'paginators_dict'):
            request.paginators_dict = {}
        request.paginators.append(paginator)
        if pager_name:
            request.paginators_dict[pager_name] = paginator

    records = paginator.list_object  # objects list

    if path and path.startswith('_'):
        pass
    else:
        records = filter_records(records, path_prefix=path, status=status, data_type="post", excludes=excludes)
    return records



def auto_pg(bucket, data_type, limit=None, page=None, pager_name=None, with_page=True,
            path=None, status=None, level_start=None, level_end=None, excludes=None,
            sort_by=None, ignore_marked_id=False, prefix_to_ignore=None,
            min_limit=0, return_total_count=False, date_start=None, date_end=None):
    """
    如果函数是获取列表式的，那么第一个函数可以使用g.pg来获得分页信息。
    data_type 指定的时候效率比较高， 如果有 level_start & level_end， 需要找到对应 level，然后再过滤 path
    """
    not_matched = False
    if not isinstance(bucket, string_types):
        not_matched = True
    if not bucket: #  or not data_type
        not_matched = True
    if not data_type and level_end is None and level_start is None:
        not_matched = True
    if not_matched:
        if return_total_count:
            return 0
        else:
            return []

    if limit is None:
        limit = get_site_config(['%s_per_page'%data_type, '%ss_per_page'%data_type, 'per_page'], type_required=int)

    # default per page is 5
    limit = to_int(limit, 5, max_value=MAX_PER_PAGE) #不能超过 1000

    if min_limit and limit < min_limit:
        limit = min_limit
    if limit > MAX_PER_PAGE:
        limit = MAX_PER_PAGE

    if not with_page and not page:
        page = 1
    else:
        page = page or get_context_value_from_request("page") or 1

    paginator = Paginator(bucket=bucket, data_type=data_type, per_page=limit, page=page,
                          path=path, sort_by=sort_by, level_start=level_start, level_end=level_end,
                          ignore_marked_id=ignore_marked_id,  prefix_to_ignore=prefix_to_ignore,
                          date_start=date_start, date_end=date_end,)

    if return_total_count:
        return paginator.total_count

    if with_page: # 启用分页
        if not hasattr(request, 'paginators'):
            request.paginators = []
        if not hasattr(request, 'paginators_dict'):
            request.paginators_dict = {}
        request.paginators.append(paginator)
        if pager_name:
            request.paginators_dict[pager_name] = paginator

    records = paginator.list_object  # objects list

    if path and path.startswith('_'):
        pass
    else:
        records = filter_records(records, path_prefix=path, status=status, data_type=data_type, excludes=excludes)

    return records



def get_paginator(index_or_name=0, match_name=False):
    paginators  = list(getattr(request, 'paginators', []))
    paginators_dict = getattr(request, 'paginators_dict', {})
    if paginators and isinstance(index_or_name, int):
        try:
            return paginators[index_or_name]
        except:
            return paginators[0]
    elif paginators_dict and isinstance(index_or_name, string_types):
        # 必然有paginators
        if match_name:
            return paginators_dict.get(index_or_name) or LazyDict()
        else:
            return paginators_dict.get(index_or_name, paginators[0])
    else:
        return LazyDict()