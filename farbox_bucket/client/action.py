#coding: utf8
from __future__ import absolute_import
import os
import json
from farbox_bucket.utils import smart_unicode, string_types
from farbox_bucket.bucket import get_bucket_by_private_key
from farbox_bucket.bucket.utils import encrypt_configs_for_bucket
from farbox_bucket.client.dump_template import get_template_info
from farbox_bucket.utils.encrypt.key_encrypt import get_md5_for_key

from .message import send_message_for_project, send_message


def get_pages_data(pages_dir):
    data = get_template_info(pages_dir) or {}
    return data




############# project starts ##########
# project 是指本地设备上固定保存的 project， 而后面的 utils
def update_bucket_configs_for_project(project, configs, config_type='site', node=None):
    # config_type in site, user, pages
    # configs = {'nodes':[x, y]}
    send_message_for_project(project, action='config_%s' % config_type, message=configs, node=node)


def dump_pages_for_project(project, pages_dir, node=None):
    pages_data = get_pages_data(pages_dir)
    if not pages_data:
        print('no pages data')
        return
    update_bucket_configs_for_project(project, pages_data, config_type='pages', node=node)


def create_bucket_for_project(project, token=''):
    send_message_for_project(project, action='create', message=token)


def create_record_for_project(project, message):
    send_message_for_project(project, message=message)


def register_domain_for_bucket_for_project(project, domain, node=None):
    message = dict(
        domain = domain,
    )
    send_message_for_project(project, action='register', message=message, node=node)

############# project ends ##########




############## utils starts ############

def update_bucket_configs(node, private_key, configs, config_type='site'):
    config_type = smart_unicode(config_type).strip()
    if config_type in ['sorts', 'sort', 'order']:
        config_type = 'orders'
    if not configs:
        return
    if config_type in ['secret', 'user']: # 数据需要加密
        configs = encrypt_configs_for_bucket(configs, private_key_md5=get_md5_for_key(private_key))

    action = 'config_%s' % config_type.strip()

    response_result = send_message(
        node = node,
        private_key = private_key,
        action = action,
        message = configs,
    )
    return response_result


def dump_pages(node, private_key, pages_dir, old_pages_data=None):
    pages_data = get_pages_data(pages_dir)
    if not pages_data:
        print('no pages data')
        return

    if old_pages_data:
        changed_filepaths = []
        for k, v in pages_data.items():
            if not isinstance(v, string_types):
                continue
            if not isinstance(k, string_types):
                continue
            if '.' not in k:
                continue
            old_value = old_pages_data.get(k) or ''
            old_value = smart_unicode(old_value)
            if v != old_value:
                changed_filepaths.append(k)
        if changed_filepaths:
            pages_data['__changed_filepaths'] = changed_filepaths
    return update_bucket_configs(node=node, private_key=private_key, configs=pages_data, config_type='pages')



def update_sorts(node, private_key, sorts_config_filepath):
    if not os.path.isfile(sorts_config_filepath):
        return
    with open(sorts_config_filepath, 'rb') as f:
        try:
            data = json.loads(f.read())
            if '__positions' in data:
                data = data['__positions']
            update_bucket_configs(node=node, private_key=private_key, configs=data, config_type='orders')
            return
        except:
            pass


def create_bucket(node, private_key, token=''):
    result = send_message(
        node = node,
        private_key = private_key,
        action = 'create_bucket',
        message = token,
    )
    if result and result.get('code') == 200:
        bucket = get_bucket_by_private_key(private_key)
    else:
        error_code = result.get('code')
        message = result.get('message', None)
        info = 'code:%s, message:%s' % (error_code, message)
        print(info)
        bucket = None
    return bucket


def quick_set_bucket_theme(node, private_key, theme_key):
    result = send_message(
        node=node,
        private_key=private_key,
        action='set_bucket_theme',
        message=dict(theme_key=theme_key),
    )
    if result and result.get('code') == 200:
        return True
    else:
        return False


def create_record(node, private_key, message):
    return send_message(node=node, private_key=private_key,  action='record', message=message)


def register_domain(node, private_key, domain, admin_password=None):
    message = dict(
        domain = domain,
    )
    if admin_password:
        message['admin_password'] = smart_unicode(admin_password)
    return send_message(node=node, private_key=private_key, action='register_domain', message=message)


def unregister_domain(node, private_key, domain):
    message = dict(
        domain = domain,
    )
    return send_message(node=node, private_key=private_key, action='unregister_domain', message=message)

############## utils ends ############
