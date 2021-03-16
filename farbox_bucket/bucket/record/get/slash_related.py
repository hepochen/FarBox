# coding: utf8
from __future__ import absolute_import
from farbox_bucket.utils.ssdb_utils import zscan

from farbox_bucket.bucket.utils import get_bucket_name_for_slash
from farbox_bucket.utils import smart_unicode

from .path_related import get_records_by_paths, filter_paths_under_path


def get_paths_by_slash_number(bucket, level_start, level_end='', under=''):
    bucket_for_slash = get_bucket_name_for_slash(bucket)
    paths = []
    raw_result = zscan(bucket_for_slash, score_start=level_start, score_end=level_end, limit=30000)
    for path, level_value in raw_result:
        paths.append(smart_unicode(path))
    paths = filter_paths_under_path(paths, under=under)
    return paths




def get_records_by_slash_number(bucket, level_start, level_end='', under=''):
    paths = get_paths_by_slash_number(bucket=bucket, level_start=level_start, level_end=level_end, under=under)
    records = get_records_by_paths(bucket=bucket, paths=paths)
    return records



