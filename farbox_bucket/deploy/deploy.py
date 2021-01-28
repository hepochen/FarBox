# coding: utf8
import os
import json
import re
import sys
import base64
from farbox_bucket import version
from farbox_bucket.utils import string_types, get_kwargs_from_console
from farbox_bucket.deploy.run.files import files_data as raw_files_data


def run_cmd(cmd):
    c_f = os.popen(cmd)
    try:
        return c_f.read().strip()
    except:
        return None


def update_deploy_farbox_bucket():
    from xserver.helper.package_utils import deploy_project_dir
    last_arv = sys.argv[-1].strip()
    if '.' not in last_arv and '/' not in last_arv:
        project_name = last_arv
    else:
        project_name = 'farbox_bucket'
    files_data = json.loads(raw_files_data)
    files_data.pop('memcached.conf', None) # memcached 的设置不修改
    files_data_for_deploy = json.dumps(files_data)
    deploy_project_dir(
        files_data = files_data_for_deploy,
        project_name = project_name,
    )



def deploy_farbox_bucket(memcache='2G', project_name='farbox_bucket',
                         sync_from_remote_node=None, start_project=True):
    print('deploy_farbox_bucket')
    print(json.dumps(locals(), indent=4))
    run_cmd('pip install xserver') # install xserver first
    from xserver.helper.package_utils import deploy_project_dir
    #files_data = json.loads(raw_files_data)
    #files_data_for_deploy = json.dumps(files_data)
    files_data_for_deploy = raw_files_data
    memcache = str(memcache).strip().lower().replace('b', '')
    if memcache.endswith('g'):
        memcache = memcache.replace('g', '').strip()
        memcache = str(int(memcache)*1024)
    memcache = '%smb' % re.search('\d+', memcache).group() # to MB


    deploy_project_dir(
        files_data = files_data_for_deploy,
        project_name = project_name,
        memcache = memcache,
    )

    if sync_from_remote_node:
        # 表示从 remote_node 进行持续的同步，相当于当前是远程节点的备份
        run_cmd('echo "%s" > /home/run/%s/configs/backup_from_ips.txt' % (sync_from_remote_node, project_name))


    if start_project:
        try:
            from xserver.server.project import run_project
            run_project(project_name)
        except:
            print('failed to start the project, should install xserver first')



# deploy_farbox_bucket memcache=5g project=farbox_bucket remote_node=xxx.com start_project=true
# deploy_farbox_bucket memcache=2g project=farbox_bucket start_project=true
def deploy_from_console():
    last_arv = sys.argv[-1].strip()
    action = None
    if last_arv.startswith('-'):
        action = last_arv.strip('-')
    elif len(sys.argv) == 2:
        action = last_arv
    if action == 'version':
        print('farbox_bucket %s' % version)
        return
    elif len(sys.argv) == 1:
        print('version:%s' % version)
        print('deploy_farbox_bucket memcache=5g project=farbox_bucket remote_node=xxx.com start_project=true')
        return

    kwargs = get_kwargs_from_console()
    memcache = kwargs.get('memcache') or kwargs.get('mem') or '2G'
    project_name = kwargs.get('project') or kwargs.get('project_name') or 'farbox_bucket'
    remote_node = kwargs.get('sync_from') or kwargs.get('remote_node') or kwargs.get('remote')
    should_start_project = True
    if kwargs.get('start_project') == 'false':
        should_start_project = False

    deploy_farbox_bucket(
        memcache = memcache,
        sync_from_remote_node = remote_node,
        start_project = should_start_project,
        project_name = project_name,
    )



def upgrade_farbox_bucket():
    last_arv = sys.argv[-1]
    if '.' in last_arv:
        print(run_cmd('pip install farbox_bucket==%s'%last_arv))
    else:
        print(run_cmd('pip install farbox_bucket -U'))
    print(run_cmd('kill -HUP `cat /tmp/web_server.pid`'))
    print(run_cmd('supervisorctl status'))


def restart_farbox_bucket_cache():
    print(run_cmd('service memcached restart'))
    print(run_cmd('service memcached status'))



def update_farbox_bucket_web():
    print(run_cmd('kill -HUP `cat /tmp/web_server.pid`'))
    print(run_cmd('supervisorctl status'))