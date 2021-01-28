# coding: utf8
from .get import get_records_by_ids
from .path_related import  get_paths_by_type, get_paths_under, get_records_by_paths, filter_paths_under_path
from .slash_related import get_paths_by_slash_number

# bucket_id, bucket_slash, bucket_xxx_order
def mix_get_record_paths(bucket, path=None, level_start=None, level_end=None, data_type=None,
                         data_type_reverse_sort=True, prefix_to_ignore=None, date_start=None, date_end=None):
    # path means prefix
    if prefix_to_ignore and path and path.startswith(prefix_to_ignore):
        prefix_to_ignore = None
    if not bucket:
        return []
    must_in_list_set = []
    if data_type:
        # 这个带了排序的逻辑
        data_type_paths = get_paths_by_type(bucket=bucket, data_type=data_type, offset=0, limit=10000,
                                            prefix_to_ignore=prefix_to_ignore, date_start=date_start, date_end=date_end)
        if not data_type_paths:
            return []
        if path:
            data_type_paths = filter_paths_under_path(data_type_paths, under=path)
        if data_type_reverse_sort: # 大约等于默认是日期的倒序
            data_type_paths.reverse()
        must_in_list_set.append(data_type_paths)
    if level_start is not None and not isinstance(level_start, int):
        level_start = None
    if level_end is not None and not isinstance(level_end, int):
        level_end = None
    if level_start is not None and level_end is not None:
        level_paths = get_paths_by_slash_number(bucket=bucket, level_start=level_start, level_end=level_end, under=path)
        if not level_paths:
            return []
        must_in_list_set.append(level_paths)
    # the default
    if not must_in_list_set:
        must_in_list_set.append(get_paths_under(bucket=bucket, under=path))
    base_paths = must_in_list_set[0]
    left_paths_set = [set(l) for l in must_in_list_set[1:]]
    if not left_paths_set:
        return base_paths
    paths = []
    for p in base_paths:
        should_append_path = True
        for left_paths in left_paths_set:
            if p not in left_paths:
                should_append_path = False
                continue
        if should_append_path:
            paths.append(p)
    return paths



def mix_get_records(bucket, path=None, level_start=None, level_end=None, data_type=None, data_type_reverse_sort=True, ignore_marked_id=True):
    paths = mix_get_record_paths(bucket=bucket, path=path, level_start=level_start,
                                 level_end=level_end, data_type=data_type, data_type_reverse_sort=data_type_reverse_sort)
    records = get_records_by_paths(bucket=bucket, paths=paths, ignore_marked_id=ignore_marked_id)
    return records

