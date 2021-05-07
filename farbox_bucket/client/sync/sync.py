#coding: utf8
import os
import datetime
from farbox_bucket import settings
from farbox_bucket.utils.data import json_dumps
from farbox_bucket.utils import get_value_from_data, to_unicode, to_bytes, get_md5_for_file
from farbox_bucket.utils.functional import curry
from farbox_bucket.utils.path import get_relative_path,  make_sure_path, join, load_json_file, write_file, is_a_hidden_path
from farbox_bucket.client.message import send_message
from farbox_bucket.utils.client_sync.detect import sync_loop_local_filesystem, sync_find_files_to_delete, should_sync as detect_should_sync
from farbox_bucket.utils.client_sync.sync_utils import after_synced, after_sync_deleted, get_sync_data_filepath
from farbox_bucket.utils.ipfs_utils import add_filepath_to_ipfs, remove_hash_from_ipfs, encrypt_file

from farbox_bucket.utils.mime import guess_type

from farbox_bucket.client.sync.compiler_worker import FarBoxSyncCompilerWorker


FILE_TYPE_FILENAMES = ['robots.txt', 'robot.txt']

VISITS_FILEPATHS = ['_data/visits.csv']


def is_a_image_file(filepath):
    mimetype = guess_type(filepath) or ''
    if mimetype.startswith('image/'):
        return True
    else:
        return False



class FarBoxBucketSyncWorker(object):
    # # files_info_filepath 如果没有指定，则在根目录中，为 .files_info.json，
    # # 这个数据很重要，可以判断哪个 ipfs_hash 需要从 ipfs 系统中移除
    def __init__(self, server_node, root, private_key=None, should_encrypt_file=True, files_info_filepath=None,
                app_name_for_sync='farbox_bucket', should_sync_file_func=None, auto_clean_bucket=True):
        self.server_node = server_node
        self.root = root
        self.private_key = private_key
        self.should_encrypt_file = should_encrypt_file
        self.auto_clean_bucket = auto_clean_bucket

        self.files_info_filepath = files_info_filepath or join(root, '.files_info.json')
        files_info = load_json_file(self.files_info_filepath)
        if not isinstance(files_info, dict):
            files_info = {}
        ipfs_files = files_info.setdefault('files', {})
        if not isinstance(ipfs_files, dict):
            ipfs_files = {}
            files_info['files'] = ipfs_files

        self.ipfs_files = ipfs_files
        self.files_info = files_info

        self.app_name_for_sync = app_name_for_sync or 'farbox_bucket'

        self.files_info_on_server = {}  # the files' info from remote server side

        # pass relative-path to this func, return True/False to sync or not
        self.should_sync_file_func = should_sync_file_func


    def do_record_sync_log(self, log):
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log = to_bytes('%s %s\n\n' % (now, log))
        sync_log_filepath = join(self.root, '.sync/%s_sync.log' % self.app_name_for_sync)
        try:
            make_sure_path(sync_log_filepath)
            with open(sync_log_filepath, 'a') as f:
                f.write(log)
        except:
            pass

    def record_sync_log(self, filepath, is_deleted, sync_status):
        log = '%s, is_deleted=%s' % (filepath, is_deleted)
        if isinstance(sync_status, dict):
            status_code = sync_status.get('code') or ''
            status_message = sync_status.get('message') or ''
            log = '%s, status: %s, message: %s' % (log, status_code, status_message)
        elif not sync_status:
            log = '%s, status: None, maybe not allowed' % log
        self.do_record_sync_log(log)



    def add_file_to_ipfs(self, filepath):
        ipfs_key = add_filepath_to_ipfs(filepath)
        return ipfs_key

    def remove_file_from_ipfs(self, ipfs_key):
        # 提供的不是路径！！
        if not ipfs_key:
            return
        remove_hash_from_ipfs(ipfs_key)


    def sync_for_updated_files(self):
        files_info_on_server = send_message(
            node=self.server_node,
            private_key=self.private_key,
            action='show_files',
            message=''
        )
        self.files_info_on_server = files_info_on_server
        lower_files_info_on_server = get_value_from_data(files_info_on_server, 'message.lower_files') or {}
        lower_folders_info_on_server = get_value_from_data(files_info_on_server, 'message.lower_folders') or {}
        if not isinstance(lower_files_info_on_server, dict):
            lower_files_info_on_server = {}
        if not isinstance(lower_folders_info_on_server, (list, tuple)):
            lower_folders_info_on_server = []
        synced = False
        filepaths = sync_loop_local_filesystem(self.root, app_name=self.app_name_for_sync, extra_should_sync_func=self.should_sync_file_func)
        for filepath in filepaths:
            one_file_is_synced = self.sync_one_file(filepath,
                                                    lower_files_info_on_server=lower_files_info_on_server,
                                                    lower_folders_info_on_server=lower_folders_info_on_server,
                                                    )
            if one_file_is_synced:
                synced = True

        return synced


    def sync_one_file(self, filepath, lower_files_info_on_server=None, lower_folders_info_on_server=None,
                      re_check=False, should_store_files_info=False):
        if re_check:
            should_sync = detect_should_sync(filepath=filepath, root=self.root,
                                             app_name=self.app_name_for_sync, check_md5=True,
                                             extra_should_sync_func=self.should_sync_file_func)
            if not should_sync:
                return False
        synced = False
        lower_files_info_on_server = lower_files_info_on_server or {}
        lower_folders_info_on_server = lower_folders_info_on_server or []
        is_file = os.path.isfile(filepath)
        relative_path = get_relative_path(filepath, root=self.root)
        file_size = os.path.getsize(filepath)
        file_real_size = file_size
        if self.should_encrypt_file and self.private_key and is_file:
            # encrypted_filepath 是一个临时文件
            encrypted_filepath = encrypt_file(filepath, encrypt_key=self.private_key)
            if not encrypted_filepath:
                return
            file_real_size = os.path.getsize(encrypted_filepath)
            ipfs_key = self.add_file_to_ipfs(encrypted_filepath)
            try:
                os.remove(encrypted_filepath)
            except:
                pass
        elif is_file:
            ipfs_key = self.add_file_to_ipfs(filepath)
        else:
            ipfs_key = None

        file_version = ipfs_key
        if not ipfs_key and os.path.isfile(filepath):
            # 兼容没有 ipfs 的时候，用文件的 md5 值来代替
            file_version = get_md5_for_file(filepath)

        # 跟服务端上的 files 的 lower_files 上的信息进行比对，如果文件相同，则 ignore 掉
        lower_relative_path = to_unicode(relative_path.lower())
        should_ignore = False
        if file_version:
            remote_file_version = get_value_from_data(lower_files_info_on_server.get(lower_relative_path), 'version')
            if not remote_file_version:
                remote_file_version = get_value_from_data(lower_files_info_on_server.get(lower_relative_path), 'hash')
            if remote_file_version == file_version:
                #if settings.DEBUG:
                #    print('has same file on server already for %s' % relative_path)
                should_ignore = True
            self.ipfs_files[relative_path] = dict(hash=file_version, size=file_size, real_size=file_real_size)

        is_dir = os.path.isdir(filepath)
        if is_dir:
            if lower_relative_path in lower_folders_info_on_server:
                #if settings.DEBUG:
                #   print('has same folder on server already for %s' % relative_path)
                should_ignore = True
        if should_ignore:
            # ignore 的进行保存，避免下次 loop 继续被找到
            after_synced(filepath, root=self.root, app_name=self.app_name_for_sync)
        else:
            sync_compiler_worker = FarBoxSyncCompilerWorker(
                server_node=self.server_node,
                root=self.root,
                filepath=filepath,
                is_deleted=False,
                is_dir=is_dir,
                private_key=self.private_key,
                should_encrypt_file=self.should_encrypt_file,
                ipfs_key = ipfs_key,
                auto_clean_bucket=self.auto_clean_bucket,

                files_info=self.files_info,
            )
            sync_status = sync_compiler_worker.sync()
            self.record_sync_log(filepath=filepath, sync_status=sync_status, is_deleted=False)
            if sync_status and sync_status.get('code') == 200:
                synced = True
                after_synced(filepath, root=self.root, app_name=self.app_name_for_sync)

                if settings.DEBUG:
                    print("synced (to) %s" % filepath)

                if should_store_files_info:
                    self.store_files_info()
            elif not sync_status:
                # 没有 status 返回， 认为属于 ignore 的一种
                after_synced(filepath, root=self.root, app_name=self.app_name_for_sync)

        return synced



    def sync_for_deleted_files(self):
        # 处理删除了的文件
        synced = False
        filepaths_to_delete_data = sync_find_files_to_delete(self.root, app_name=self.app_name_for_sync, as_dict=True)
        for filepath_to_delete_data in filepaths_to_delete_data:
            filepath_to_delete = filepath_to_delete_data['filepath']
            is_dir = filepath_to_delete_data.get('is_dir', False)
            relative_path = get_relative_path(filepath_to_delete, root=self.root)
            ipfs_to_delete = self.ipfs_files.pop(relative_path, None)
            if isinstance(ipfs_to_delete, dict):
                ipfs_hash_to_delete = ipfs_to_delete.get('hash')
            else:
                ipfs_hash_to_delete = ipfs_to_delete
            self.remove_file_from_ipfs(ipfs_hash_to_delete)

            # is_deleted=True, send md5 value as version
            md5_value = filepath_to_delete_data.get('md5')

            compiler_sync_worker = FarBoxSyncCompilerWorker(
                server_node=self.server_node,
                root=self.root,
                filepath=filepath_to_delete,
                is_deleted=True,
                is_dir=is_dir,
                private_key=self.private_key,
                should_encrypt_file=self.should_encrypt_file,
                ipfs_key=ipfs_hash_to_delete,
                version = md5_value,
                auto_clean_bucket=self.auto_clean_bucket,

                files_info=self.files_info
            )
            sync_status = compiler_sync_worker.sync()
            self.record_sync_log(filepath=filepath_to_delete, sync_status=sync_status, is_deleted=True)
            if sync_status and sync_status.get('code')==200:
                synced = True
                # at last, mark status as synced
                after_sync_deleted(filepath_to_delete, root=self.root, app_name=self.app_name_for_sync)

                if settings.DEBUG:
                    print("sync_deleted %s" % filepath_to_delete)

        # files on server, but no in local side, clean the configs_for_files
        # should run after self.sync_for_updated_files, to get self.files_info_on_server
        files_info_on_server = get_value_from_data(self.files_info_on_server, 'message.files') or {}
        for relative_path in files_info_on_server.keys():
            abs_filepath = join(self.root, relative_path)
            if not os.path.isfile(abs_filepath):
                self.ipfs_files.pop(relative_path, None)
                synced = True

        return synced


    def check_remote(self):
        # 确保 bucket 存在，以及能联网
        reply = send_message(
            node = self.server_node,
            private_key = self.private_key,
            action='check',
            message=''
        )
        if reply and reply.get('code') == 200:
            return True
        else:
            return False


    def sync(self):
        is_remote_ok = self.check_remote()
        if not is_remote_ok:
            self.do_record_sync_log('check_remote failed, network error?')
            return False

        synced_for_deleted = self.sync_for_deleted_files() # 先处理删除的
        synced_for_updated = self.sync_for_updated_files()

        # 文件 相关的信息，进行保存
        self.store_files_info()

        changed = synced_for_updated or synced_for_deleted
        return changed

    def store_files_info(self):
        files_info_content = json_dumps(self.files_info, indent=4)
        write_file(self.files_info_filepath, files_info_content)




def should_sync_file_for_sync_folder_simply(relative_path, extra_func=None):
    # must return True or False, else will checked by`should_sync` func in detact.py
    relative_path_without_dot = relative_path.lstrip('.')
    ext = os.path.splitext(relative_path)[-1].lower().strip('.')
    if ext in ['py', 'pyc']:
        return False
    if is_a_hidden_path(relative_path):
        return False
    if relative_path_without_dot in ['template', 'configs',]:
        return False
    if relative_path_without_dot.startswith('template/') or relative_path_without_dot.startswith('configs/'):
        return False
    if relative_path.startswith('_data/visits/'): # 原来 Bitcron 下记录每日访问的数据
        return False
    elif relative_path.startswith('_data/email_status/'): # 原 Bitcron 邮件发送的状态记录
        return False
    elif relative_path.startswith('_cache/'): # 原来 Bitcron site 的缓存数据
        return False
    if relative_path in ['_cache']:
        return False

    if '_sync_ignore_' in relative_path:
        return False

    # at last
    if extra_func:
        return extra_func(relative_path)



def sync_folder_simply(node, root, private_key, should_encrypt_file=False,
                       app_name_for_sync=None, auto_clean_bucket=True,
                       exclude_rpath_func=None,):
    app_name_for_sync = app_name_for_sync or 'farbox_bucket'
    should_sync_file_func = should_sync_file_for_sync_folder_simply
    if exclude_rpath_func:
        should_sync_file_func = curry(should_sync_file_for_sync_folder_simply, extra_func=exclude_rpath_func)
    worker = FarBoxBucketSyncWorker(server_node=node, root=root, private_key=private_key,
                                    should_encrypt_file=should_encrypt_file, app_name_for_sync=app_name_for_sync,
                                    should_sync_file_func = should_sync_file_func,
                                    auto_clean_bucket= auto_clean_bucket,
                                    )
    changed = worker.sync()
    return changed



def sync_file_simply(filepath, node, root, private_key, should_encrypt_file=False, app_name_for_sync=None, auto_clean_bucket=True,):
    if not os.path.isfile(filepath):
        return False# ignore
    # 要确保 filepath 的 parent 已经记录了，不然，会导致 parent 不会被同步上去
    parent_folder = os.path.dirname(filepath)
    app_name_for_sync = app_name_for_sync or 'farbox_bucket'
    parent_folder_sync_data_filepath = get_sync_data_filepath(root=root, filepath=parent_folder, app_name=app_name_for_sync)
    if not os.path.isfile(parent_folder_sync_data_filepath):
        return False
    worker = FarBoxBucketSyncWorker(server_node=node, root=root, private_key=private_key,
                                    should_encrypt_file=should_encrypt_file, app_name_for_sync=app_name_for_sync,
                                    should_sync_file_func=should_sync_file_for_sync_folder_simply,
                                    auto_clean_bucket=auto_clean_bucket,
                                    )
    worker.sync_one_file(filepath, re_check=True, should_store_files_info=True)
    return True

