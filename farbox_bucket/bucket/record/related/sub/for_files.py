# coding: utf8
import time, os
from farbox_markdown.util import is_a_markdown_file
from farbox_bucket.utils.mime import is_a_image_file
from farbox_bucket.utils.ssdb_utils import hscan
from farbox_bucket.utils import to_int
from farbox_bucket.bucket.utils import get_bucket_files_info, set_bucket_configs, get_bucket_name_for_path
from farbox_bucket.bucket.record.utils import get_path_from_record


# max files is 5000, max depth is 10
def get_files_info(bucket):
    data = {}
    path_bucket = get_bucket_name_for_path(bucket)
    data['files'] = {}
    data['folders'] = {}
    data['lower_files'] = {}
    data['lower_folders'] = []  # not a dict
    lower_folders = []
    lower_folders_count = {}
    records = hscan(path_bucket, key_start='', limit=5000)
    for filepath, filepath_data_string in records:
        if filepath.startswith('_'):
            continue
        lower_filepath = filepath.strip().lower()
        # prepare raw data starts
        raw_filepath_data = filepath_data_string.split(',')
        if len(raw_filepath_data) != 3:
            continue
        filepath_data_keys = ['record_id', 'size', 'version']
        filepath_data = dict(zip(filepath_data_keys, raw_filepath_data))
        filepath_data['size'] = to_int(filepath_data['size'], default_if_fail=0)
        if filepath_data.get('version') == 'folder':
            #is_dir = True
            is_image = False
            is_markdown = False
            data['folders'][filepath] = filepath_data
            if lower_filepath not in lower_folders:
                lower_folders.append(lower_filepath)
        else:
            #is_dir = False
            # prepare raw data ends
            is_image = is_a_image_file(filepath)
            is_markdown = is_a_markdown_file(filepath)
            data['files'][filepath] = filepath_data
            data['lower_files'][filepath.strip().lower()] = filepath_data
        lower_folder_path = os.path.split(filepath.strip().lower())[0]
        if lower_folder_path:
            parts = lower_folder_path.split('/')
            parts_length = len(parts)
            if parts_length > 10:
                continue
            for i in range(parts_length):
                one_lower_folder_path = '/'.join(parts[:i + 1])
                last_path_part = one_lower_folder_path.split('/')[-1]
                if last_path_part.startswith('_'):
                    continue
                if one_lower_folder_path not in lower_folders:
                    lower_folders.append(one_lower_folder_path)
                if one_lower_folder_path:
                    images_count_plus = 1 if is_image else 0
                    posts_count_plus = 1 if is_markdown else 0
                    _images_count_plus = 1 if images_count_plus and lower_folder_path == one_lower_folder_path else 0
                    _posts_count_plus = 1 if posts_count_plus and lower_folder_path == one_lower_folder_path else 0
                    matched_count = lower_folders_count.setdefault(one_lower_folder_path, {})
                    matched_count['images_count'] = matched_count.get('images_count', 0) + images_count_plus
                    matched_count['posts_count'] = matched_count.get('posts_count', 0) + posts_count_plus
                    matched_count['_images_count'] = matched_count.get('_images_count', 0) + _images_count_plus
                    matched_count['_posts_count'] = matched_count.get('_posts_count', 0) + _posts_count_plus
    data['lower_folders'] = lower_folders
    data['lower_folders_count'] = lower_folders_count

    data['date'] = time.time()
    return data



def update_bucket_files_info(bucket):
    files_info = get_files_info(bucket)
    set_bucket_configs(bucket, configs=files_info, config_type='files')


