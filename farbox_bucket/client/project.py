#coding: utf8
from __future__ import absolute_import
from farbox_bucket.utils import to_unicode
from farbox_bucket.utils.encrypt.key_encrypt import get_public_key_from_private_key, create_private_public_keys
from farbox_bucket.bucket import get_bucket_by_public_key
import ujson as json
import os


def get_home_path():
    home_path = ''
    if os.environ.get('HOME'):
        home_path = to_unicode(os.environ['HOME'])
        if not os.path.exists(home_path):
            home_path = ''
    if not home_path:
        home_path = '/var'
    return  home_path



def get_projects_config_filepath():
    home_path = get_home_path()
    config_filepath = os.path.join(home_path, '.farbox_bucket_projects.json')
    return config_filepath



def get_projects_config():
    config_filepath = get_projects_config_filepath()
    if not os.path.isfile(config_filepath):
        projects_config = {}
    else:
        with open(config_filepath, 'rb') as f:
            projects_config_content = f.read()
        try:
            projects_config = json.loads(projects_config_content)
            if not isinstance(projects_config, dict):
                projects_config = {}
        except:
            projects_config = {}
    return projects_config



def write_projects_config(projects_config):
    projects_config_data = json.dumps(projects_config, indent=4)
    config_filepath = get_projects_config_filepath()
    with open(config_filepath, 'wb') as f:
        f.write(projects_config_data)



def save_project_config(project, private_key, public_key=None, node=None):
    if not private_key:
        return
    if not public_key:
        public_key = get_public_key_from_private_key(private_key, is_clean=False)
    if not private_key or not public_key:
        print('no private_key or no public_key, save project config failed')
        return #ignore
    bucket = get_bucket_by_public_key(public_key)
    projects_config = get_projects_config()
    current_project_config = dict(
        bucket = bucket,
        private_key = private_key,
        public_key = public_key,
        node = node,
    )
    project = project.strip()
    projects_config[project] = current_project_config

    write_projects_config(projects_config)

    return current_project_config


def update_project_config(project, k, v):
    # 主要是更新 node 信息的
    project_config = get_project_config(project)
    if not project_config or not project_config.get('private_key'):
        # 确保 project 的存在
        create_project(project)
    projects_config = get_projects_config()
    project_config = projects_config.get(project) or {}
    if not isinstance(project_config, dict):
        project_config = {}
    project_config[k] = v
    projects_config[project] = project_config
    write_projects_config(projects_config)




def get_project_config(project, as_list=False, auto_create=False):
    project = project.strip()
    projects_config = get_projects_config()
    project_config = projects_config.get(project) or {}
    if not project_config and auto_create: # 自动创建一个 project, 也就是产生一个随机的 private_key
        project_config = create_project(project)
    if not isinstance(project_config, dict):
        project_config = {}
    if as_list:
        bucket = project_config.get('bucket')
        private_key = project_config.get('private_key')
        public_key = project_config.get('public_key')
        node = project_config.get('node')
        return node, bucket, private_key, public_key
    else:
        return project_config


def get_project_private_key(project):
    project_config = get_project_config(project, auto_create=True)
    return project_config.get('private_key')


def get_project_public_key(project):
    project_config = get_project_config(project, auto_create=True)
    return project_config.get('public_key')

def get_project_bucket(project):
    project_config = get_project_config(project)
    return project_config.get('bucket')




def create_project(project, node=None):
    private_key, public_key = create_private_public_keys(is_clean=False)
    project_config = save_project_config(project, private_key, public_key=public_key, node=node)
    return project_config



def load_project(project, private_key, node=None):
    # 根据提供的 private_key, 将 project 的设置保存到本地
    project_config = save_project_config(project, private_key=private_key, node=node)
    return project_config



def set_project_node(project, node):
    if '://' in node:
        node = node.split('://')[-1]
    update_project_config(project, 'node', node)




def show_project(project):
    # 显示 project 的信息
    node, bucket, private_key, public_key = get_project_config(project, as_list=True)
    print('node: %s\nbucket:%s\n\n'%(node, bucket))
    print(private_key)
    print('\n'*3)
    print(public_key)



def show_projects():
    projects_config = get_projects_config()
    for project_name, project_config in projects_config.items():
        bucket = project_config.get('bucket')
        node = project_config.get('node') or ''
        print('%s\nbucket: %s\nnode: %s\n\n' % (project_name, bucket, node))



