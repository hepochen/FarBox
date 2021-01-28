# coding: utf8
import time, os
from farbox_bucket.bucket.utils import get_bucket_by_public_key, set_bucket_configs, has_bucket
from farbox_bucket.bucket.create import create_bucket_by_public_key
from farbox_bucket.bucket.record.create import create_record
from farbox_bucket.utils.env import get_env
from farbox_bucket.utils.encrypt.key_encrypt import create_private_key, create_private_public_keys
from farbox_bucket.utils.gevent_run import run_long_time
from farbox_bucket.utils.path import load_json_file, write_file
from farbox_bucket.utils.data import json_dumps
from xserver.server_status.status.status import get_system_status

from .bucket_web_template import bucket_web_template

config_folder = '/mt/web/configs'
server_status_bucket = None
server_status_bucket_configs = None

def get_server_status_bucket_configs():
    global server_status_bucket_configs
    if not server_status_bucket_configs:
        config_filepath = os.path.join(config_folder, 'server_status.json')
        if not os.path.isfile(config_filepath):
            private_key, public_key = create_private_public_keys()
            bucket = get_bucket_by_public_key(public_key)
            configs = dict(bucket=bucket, private_key=private_key, public_key=public_key, created_at=time.time())
            write_file(config_filepath, json_dumps(configs, indent=4))
        else:
            configs = load_json_file(config_filepath)
        server_status_bucket_configs = configs
    return server_status_bucket_configs



def get_server_status_bucket():
    global server_status_bucket
    if not server_status_bucket:
        configs = get_server_status_bucket_configs()
        server_status_bucket = configs.get('bucket')
    return server_status_bucket


def init_server_status_bucket():
    if 'utc_offset' not in os.environ:
        # 统计系统信息时候，可读性使用的 utc_offset
        utc_offset = get_env('utc_offset')
        if utc_offset is None:
            utc_offset = 8
        try:
            utc_offset = str(utc_offset)
        except:
            utc_offset = '8'
        os.environ['utc_offset'] = utc_offset


    configs = get_server_status_bucket_configs()
    bucket = configs['bucket']
    public_key = configs['public_key']
    if has_bucket(bucket):
        return

    create_bucket_by_public_key(public_key)
    set_bucket_configs(bucket, config_type='pages', configs=bucket_web_template)



def update_server_status_bucket_template():
    bucket = get_server_status_bucket()
    if bucket and has_bucket(bucket):
        set_bucket_configs(bucket, config_type='pages', configs=bucket_web_template)



# per 2 minutes report once
@run_long_time(wait=10, sleep_at_end=2*60, log='report server status')
def report_server_status():
    init_server_status_bucket()
    configs = get_server_status_bucket_configs()
    bucket = configs.get('bucket')
    if not bucket:
        return
    system_status=  get_system_status(includes_processes=True, mini=True, extra_disk_path='/mt/web/data')
    create_record(bucket, record_data=system_status)

