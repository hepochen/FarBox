# coding: utf8
import os
import json
import time
from farbox_bucket.utils import get_md5_for_file, get_md5
from farbox_bucket.utils.data import json_dumps
from farbox_bucket.utils.path import join, load_json_file, dump_json_file, make_sure_path
from farbox_bucket.utils.encrypt.key_encrypt import is_valid_private_key
from farbox_bucket.utils.client_sync.sync_utils import clear_sync_meta_data
from farbox_bucket.bucket.utils import get_bucket_by_private_key
from farbox_bucket.client.action import update_bucket_configs, dump_pages, get_pages_data
from .sync import sync_folder_simply

allowed_bucket_config_types = ['sorts', 'site']

def get_path_with_dot_allowed(root, *keywords):
    possible_paths = []
    for keyword in keywords:
        possible_paths.append(join(root, '.%s' % keyword))
        possible_paths.append(join(root, keyword))
    path = None # by default
    for path in  possible_paths:
        if os.path.exists(path):
            return path
    return path



def sync_bucket_config(site_folder_status, root, node, private_key, config_type='site', print_log=True):
    if config_type not in allowed_bucket_config_types:
        return # not allowed
    filename = '%s.json' % config_type
    md5_key = '%s_md5' % config_type
    config_file_keywords = ['configs/%s'%filename, 'config/%s'%filename]
    config_filepath = get_path_with_dot_allowed(root, *config_file_keywords)

    if not config_filepath or not os.path.isfile(config_filepath):
        return

    old_md5 = site_folder_status.get(md5_key)
    current_md5 = get_md5_for_file(config_filepath)
    if old_md5 != current_md5:
        configs = load_json_file(config_filepath) or {}
        if not isinstance(configs, dict):
            configs = {}
        if config_type in ['sorts'] and '__positions' in configs: # for MarkEditor & Markdown.app
            configs = configs['__positions']
        sync_status = update_bucket_configs(
            node=node,
            private_key=private_key,
            config_type=config_type,
            configs=configs,
        )
        if not sync_status:
            return
        sync_status_code = sync_status.get('code')
        if sync_status_code != 200:
            if print_log:
                print(sync_status.get('message'))
            return
        site_folder_status[md5_key] = current_md5  # update the site_folder_status
        if print_log:
            print('update %s' % filename)


def sync_site_folder_simply(node, root, private_key, should_encrypt_file=False,
                            app_name_for_sync=None, print_log=True, exclude_rpath_func=None,):
    if not node or not root or not private_key:
        return # ignore
    if not os.path.isdir(root):
        return # ignore
    if not is_valid_private_key(private_key):
        return # ignore
    now = time.time()
    app_name_for_sync = app_name_for_sync or 'farbox_bucket'
    site_folder_status_config_filepath = join(root, '.%s_site_folder_status.json' % app_name_for_sync)
    site_folder_status = load_json_file(site_folder_status_config_filepath) or {}
    bucket = get_bucket_by_private_key(private_key)
    old_bucket = site_folder_status.get('bucket')
    old_node = site_folder_status.get('node')
    if bucket!=old_bucket or node!=old_node:
        # bucket or node changed, reset the sync
        clear_sync_meta_data(root=root, app_name=app_name_for_sync)
        site_folder_status['bucket'] = bucket
        site_folder_status['node'] = node
        # configs 的逻辑也调整下
        for key in site_folder_status:
            if key.endswith('_md5'):
                site_folder_status.pop('key', None)

    # dump_template first
    template_folder = get_path_with_dot_allowed(root, 'template')
    if os.path.isdir(template_folder):
        pages_data = get_pages_data(template_folder)
        current_pages_md5 = get_md5(json_dumps(pages_data, indent=4))
        old_pages_md5 = site_folder_status.get('pages_md5')
        if current_pages_md5 != old_pages_md5: # 模板发生变化
            old_pages_data = site_folder_status.get('pages') or {}
            sync_status = dump_pages(
                node=node,
                private_key=private_key,
                pages_dir=template_folder,
                old_pages_data = old_pages_data,
            )
            sync_status_code = sync_status.get('code')
            if sync_status_code != 200:
                if print_log:
                    print(sync_status.get('message'))
                return
            else:
                # update pages_md5
                site_folder_status['pages_md5'] = current_pages_md5
                site_folder_status['pages'] = pages_data
                if print_log:
                    print('template is changed and synced')

    # update files first
    files_changed = sync_folder_simply(node=node, root=root, private_key=private_key,
                       should_encrypt_file=should_encrypt_file,
                       app_name_for_sync=app_name_for_sync, exclude_rpath_func=exclude_rpath_func)

    # update configs
    for config_type in allowed_bucket_config_types:
        sync_bucket_config(site_folder_status, root=root, node=node, private_key=private_key,
                       config_type=config_type, print_log=print_log)

    # store the site_folder_status
    dump_json_file(filepath=site_folder_status_config_filepath, data=site_folder_status)