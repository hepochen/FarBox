# coding: utf8
from flask import g
from farbox_bucket.utils import to_int, string_types
from .paginator_for_record import SortedRecordsPaginator as Paginator
from farbox_bucket.server.utils.lazy import LazyDict
from farbox_bucket.server.utils.site_resource import get_site_config
from farbox_bucket.server.utils.record_and_paginator.utils import filter_records
MAX_PER_PAGE = 1000

def auto_pg(bucket, data_type, limit=None, page=None, pager_name=None, with_page=True,
            path=None, status=None, level_start=None, level_end=None, excludes=None,
            sort_by=None, ignore_marked_id=False, prefix_to_ignore=None,
            min_limit=0, return_total_count=False, date_start=None, date_end=None):
    """
    如果函数是获取列表式的，那么第一个函数可以使用g.pg来获得分页信息。
    """
    not_matched = False
    if not isinstance(bucket, string_types):
        not_matched = True
    if not bucket or not data_type:
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
        page = page or getattr(g, 'page', 1)

    paginator = Paginator(bucket=bucket, data_type=data_type, per_page=limit, page=page,
                          path=path, sort_by=sort_by, level_start=level_start, level_end=level_end,
                          ignore_marked_id=ignore_marked_id,  prefix_to_ignore=prefix_to_ignore,
                          date_start=date_start, date_end=date_end,)

    if return_total_count:
        return paginator.total_count

    if with_page: # 启用分页
        if not hasattr(g, 'paginators'):
            g.paginators = []
        if not hasattr(g, 'paginators_dict'):
            g.paginators_dict = {}
        g.paginators.append(paginator)
        if pager_name:
            g.paginators_dict[pager_name] = paginator

    records = paginator.list_object  # objects list

    if path and path.startswith('_'):
        pass
    else:
        records = filter_records(records, path_prefix=path, status=status, data_type=data_type, excludes=excludes)

    return records



def get_paginator(index_or_name=0, match_name=False):
    paginators  = list(getattr(g, 'paginators', []))
    paginators_dict = getattr(g, 'paginators_dict', {})
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