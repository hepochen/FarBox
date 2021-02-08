# coding: utf8
from farbox_bucket.utils import smart_unicode, to_int
from farbox_bucket.bucket.utils import get_bucket_files_info
from .path_related import get_records_by_paths
from .path_related import excludes_paths
from .mix import mix_get_record_paths



def get_folder_children_count(bucket, folder_path, field='posts', direct=False, files_info=None):
    # posts & images
    if not bucket and not files_info:
        return 0
    if folder_path is None:
        return 0
    folder_path = folder_path.strip('/').lower()
    if files_info is None:
        files_info = get_bucket_files_info(bucket) or {}
    if not isinstance(files_info, dict):
        files_info = {}
    folder_counts_info = files_info.get('lower_folders_count') or {}
    folder_matched_info = folder_counts_info.get(folder_path) or {}
    count_key = '%s_count' % field
    if direct:
        count_key = '_%s' % count_key
    num = folder_matched_info.get(count_key, 0)
    num = to_int(num, default_if_fail=0)
    return num




def get_folder_records(bucket, under=None, level_start=0, level_end=1, min_posts_count=0, min_images_count=0,
                       excludes=("_", "template", "configs", "licenses"), limit=300):
    paths = mix_get_record_paths(bucket=bucket, path=under, level_start=level_start, level_end=level_end,
                                 data_type='folder', data_type_reverse_sort=False)
    paths = excludes_paths(paths, excludes)
    if not min_images_count and not min_images_count:
        return paths
    files_info = get_bucket_files_info(bucket) or {}
    if min_posts_count:
        result = []
        for path in paths:
            num = get_folder_children_count(bucket=bucket, folder_path=path, field='posts', files_info=files_info)
            if num >= min_posts_count:
                result.append(path)
        paths = result
    if min_images_count:
        result = []
        for path in paths:
            num = get_folder_children_count(bucket=bucket, folder_path=path, field='images', files_info=files_info)
            if num >= min_images_count:
                result.append(path)
        paths = result
    records = get_records_by_paths(bucket, paths, limit=limit)
    return records

