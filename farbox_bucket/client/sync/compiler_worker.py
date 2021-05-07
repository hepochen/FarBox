#coding: utf8
import os
from farbox_bucket.settings import MAX_RECORD_SIZE, DEBUG
from farbox_bucket.utils import is_a_markdown_file
from farbox_bucket.utils.data import json_loads, json_dumps
from farbox_bucket.utils.path import get_relative_path, is_sub_path, get_just_name
from farbox_bucket.utils.functional import cached_property
from farbox_bucket.client.message import send_message
from farbox_bucket.client.sync.compiler.post_compiler import PostSyncCompiler
from farbox_bucket.client.sync.compiler.file_compiler import FileSyncCompiler
from farbox_bucket.client.sync.compiler.folder_compiler import FolderSyncCompiler
from farbox_bucket.client.sync.compiler.visits_compiler import VisitsSyncCompiler
from farbox_bucket.client.sync.compiler.comments_compiler import CommentsSyncCompiler
from farbox_bucket.utils.mime import guess_type
from farbox_bucket.utils.encrypt.key_encrypt import get_md5_for_key



FILE_TYPE_FILENAMES = ['robots.txt', 'robot.txt']

VISITS_FILEPATHS = ['_data/visits.csv']


def is_a_image_file(filepath):
    mimetype = guess_type(filepath) or ''
    if mimetype.startswith('image/'):
        return True
    else:
        return False


class FarBoxSyncCompilerWorker(object):
    def __init__(self, server_node, root, filepath,
                    private_key=None, should_encrypt_file=False,
                    is_dir=False, is_deleted=False, ipfs_key=None,
                    version=None, auto_clean_bucket=True,
                    relative_path=None, real_relative_path=None,raw_content=None,
                    files_info=None, utc_offset=None,
                 ):
        self.files_info = files_info
        self.utc_offset = utc_offset

        self.server_node = server_node
        self.root = root
        self.filepath = filepath
        self.private_key = private_key
        self.should_encrypt_file = should_encrypt_file
        self.is_dir = is_dir
        self.is_deleted = is_deleted
        self.ipfs_key = ipfs_key
        self.version = version
        self.auto_clean_bucket = auto_clean_bucket

        # 主要是 Markdown 文档编译，针对 FarBox Page 时候用的
        self.real_relative_path = real_relative_path

        # 如果没有指定 relative_path， 是需要从 root & filepath 中获得的
        # filepath 是用于获得文件内容的，如果有指定了 raw_content，那就是 raw_content 优先
        self._raw_content = raw_content
        if relative_path:
            self.relative_path = relative_path
        else:
            if not is_sub_path(self.filepath, parent_path=self.root):
                self.relative_path = ''
            else:
                self.relative_path = get_relative_path(self.filepath, root=self.root)

        self.lower_relative_path = self.relative_path.lower()

    @cached_property
    def private_key_md5(self):
        if self.private_key:
            return get_md5_for_key(self.private_key)
        else:
            return None


    @property
    def should_md_doc_hit_folder_compiler(self):
        if not self.filepath:
            return False
        if not os.path.isfile(self.filepath):
            return False
        if not is_a_markdown_file(self.filepath):
            return False
        just_name = get_just_name(self.filepath)
        if just_name == 'index':
            return True
        else:
            return False


    def pre_data_for_sync(self, data):
        if data and isinstance(data, dict):
            if self.auto_clean_bucket:
                data['_auto_clean_bucket'] = True
            doc_type = data.get('_type')
            if doc_type in ['visits', 'comments']:
                # visits & comments 是强制要进行 clean 的， 不然数据会无限冗余下去
                data['_auto_clean_bucket'] = True


    def json_dumps(self, data):
        self.pre_data_for_sync(data)
        return json_dumps(data)

    @cached_property
    def json_data_for_sync(self):
        if not self.relative_path:
            return # ignore
        if self.filepath and not os.path.exists(self.filepath) and not self.is_deleted:
            return # ignore too

        # 这些都是 BasicSyncCompiler 接收的参数
        kwargs = dict(
            relative_path = self.relative_path,
            real_relative_path = self.real_relative_path,
            abs_filepath = self.filepath,
            private_key = self.private_key,
            should_encrypt_file = self.should_encrypt_file,
            is_dir = self.is_dir,
            is_deleted = self.is_deleted,
            ipfs_key = self.ipfs_key,
            version = self.version,

            raw_content = self._raw_content,
            files_info = self.files_info,
            utc_offset = self.utc_offset,
        )

        matched_compiler = None
        is_markdown = is_a_markdown_file(self.relative_path)
        if self._raw_content:
            is_file = True
        elif self.filepath:
            is_file = os.path.isfile(self.filepath)
        elif self.is_dir:
            is_file = False
        else:
            is_file = True
        if self.is_dir:
            matched_compiler = FolderSyncCompiler(**kwargs)
        elif is_markdown and self.relative_path not in FILE_TYPE_FILENAMES:
            matched_compiler = PostSyncCompiler(**kwargs)
        elif is_file and self.relative_path in VISITS_FILEPATHS:
            matched_compiler = VisitsSyncCompiler(**kwargs)
        elif is_file and self.lower_relative_path.startswith('_comments/'):
            matched_compiler = CommentsSyncCompiler(**kwargs)

        if matched_compiler:
            matched_data = matched_compiler.compiled_data
            doc_type = matched_data.get('_type')
            # 这里会调用 compile 相关获取数据的逻辑，如果 compiler.should_ignore_current_file， 则返回 {}, 相当于不同步
            if matched_compiler.should_ignore_current_file:
                return {}
            if matched_data:
                matched_json_data = self.json_dumps(matched_data)
                if len(matched_json_data) < MAX_RECORD_SIZE:
                    return matched_json_data
                else:
                    # 如果 size 超了，会后面走 file 类型的逻辑，作为通用 record
                    if doc_type in ['visits', 'comments']:
                        # 这些类型，不作为普通 file 类型处理，如果超过 300 kb，就是无效
                        # 由于转化数据的存在，实际上 100kb 左右的size
                        return {}

        # 上面类型匹配失败或者 size 太大，作为普通的 record 处理
        common_file_compiler = FileSyncCompiler(**kwargs)
        compiled_data = common_file_compiler.compiled_data
        if compiled_data:
            compiled_json_data = self.json_dumps(compiled_data)
            if len(compiled_json_data) < MAX_RECORD_SIZE:
                return compiled_json_data

        data = common_file_compiler.basic_compiled_data
        compiled_json_data = self.json_dumps(data)
        return compiled_json_data



    def send_message(self, action, message, file_to_post=None, timeout=None):
        reply = send_message(
            node = self.server_node,
            private_key = self.private_key,
            action = action,
            message = message,
            file_to_post = file_to_post,
            timeout = timeout,
        )
        return reply



    def sync(self):
        # one record only, push to server  now
        # return sync_status
        json_data = self.json_data_for_sync
        if not json_data:
            return None # ignore

        py_data = json_loads(json_data)

        sync_status = self.send_message(
            action='create',
            message=json_data
        )

        # 上传文件
        if py_data.get('_type') in ['file', 'image']:
            raw_file_data = py_data.get('raw_content')
            if not raw_file_data:
                # 直接上传文件, 如果 version 一样，或者 size 超了，都会返回 no 的结果
                reply = self.send_message(action='should_upload_file', message=json_data)
                if reply.get('message') == 'yes' and os.path.isfile(self.filepath):
                    file_size = os.path.getsize(self.filepath)

                    request_timeout = 120
                    if file_size:
                        file_mb = int(file_size/1024./1024)
                        if file_mb > 2:
                            request_timeout = file_mb * 60 # 1mb 就是多 1 分钟的 timeout
                        request_timeout = min(request_timeout, 30*60) # 不能超过 30 分钟

                    with open(self.filepath, 'rb') as f:
                        sync_status = self.send_message(
                            action = 'upload_file',
                            message = json_data,
                            file_to_post = f,
                            timeout = request_timeout,
                        )

        if DEBUG:
            info = 'is_deleted=%s, sync %s, sync_status: %s' % (self.is_deleted, self.relative_path, sync_status)
            print(info)

        return sync_status




def get_compiler_data_directly(relative_path, content=None, is_deleted=False, is_dir=False,
                               real_relative_path=None, utc_offset=None):
    if not relative_path:
        return
    if content and len(content) > MAX_RECORD_SIZE:
        # 避免不必要的内存占用，此时的 content 必然不会存储在 raw_content 这个字段中
        content = None
    compiler_worker = FarBoxSyncCompilerWorker(server_node=None, root=None, filepath=None,
                                               relative_path=relative_path, raw_content=content,
                                               is_deleted = is_deleted, is_dir = is_dir,
                                               real_relative_path=real_relative_path,
                                               utc_offset=utc_offset)
    json_data = compiler_worker.json_data_for_sync
    if json_data:
        data = json_loads(json_data)
        return data