# coding: utf8
from farbox_bucket.utils.client_sync.sync_utils import clear_sync_meta_data
from farbox_bucket.utils.path import load_json_file, dump_json_file
from farbox_bucket.utils.encrypt.key_encrypt import create_private_key
from farbox_bucket.bucket.utils import get_bucket_by_private_key
from farbox_bucket.client.action import create_bucket
from farbox_bucket.client.sync.site import sync_site_folder_simply
import os


def get_private_key_for_site_folder(site_folder):
    home_dir = os.environ.get('HOME')
    if home_dir and os.path.isdir(home_dir):
        config_root = home_dir
    else:
        config_root = '/tmp'
    config_filepath = os.path.join(config_root, '.farbox_bucket_debug_site_private_keys.json')
    site_folder_key = site_folder.strip().lower()
    private_keys = load_json_file(config_filepath) or {}
    if site_folder_key in private_keys:
        private_key = private_keys[site_folder_key]
    else:
        private_key = create_private_key()
        private_keys[site_folder_key] = private_key
        dump_json_file(config_filepath, private_keys)
    return private_key



def sync_site_for_debug(site_folder, web_port=7788, clear_first=False):
    node = 'localhost:%s' % web_port
    private_key = get_private_key_for_site_folder(site_folder)
    bucket = get_bucket_by_private_key(private_key)
    web_url = 'http://localhost:%s/bucket/%s/web' % (web_port, bucket)

    if clear_first:
        clear_sync_meta_data(site_folder, app_name='debug_site')

    # create bucket first
    create_bucket(node=node, private_key=private_key, token='')

    sync_site_folder_simply(
        node = node,
        root = site_folder,
        app_name_for_sync='debug_site',
        should_encrypt_file=False,
        private_key=private_key,
    )

    # exit now
    print(web_url)


