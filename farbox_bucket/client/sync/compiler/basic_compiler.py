#coding: utf8
import os, time
from farbox_bucket import version as farbox_version
from farbox_bucket.utils import md5_for_file, get_md5, smart_str
from farbox_bucket.utils.path import same_slash, read_file
from farbox_bucket.utils.functional import cached_property
from farbox_bucket.utils.gzip_content import gzip_content
from farbox_bucket.client.sync.compiler.utils import get_meta_value as _get_meta_value
from farbox_bucket.client.sync.compiler.utils import split_title_and_position
from farbox_bucket.utils.ipfs_utils import get_ipfs_hash_from_filepath


class BasicSyncCompiler(object):
    def __init__(self, relative_path, abs_filepath=None,
                 private_key=None, should_encrypt_file=False,
                 is_deleted=False,  is_dir=None, ipfs_key=None, doc_type=None, version=None,
                 raw_content = None, files_info=None,
                 real_relative_path = None,
                 utc_offset = None,
                 ):
        if raw_content: # 直接传入内容， abs_filepath 直接无效
            abs_filepath = None

        # 外部存储所有 files 的一个数据对象
        self.files_info_is_updated = False
        self.files_info = files_info

        self.real_relative_path = real_relative_path
        self.relative_path = same_slash(relative_path).lstrip('/')
        self.path = self.relative_path
        self.abs_filepath = abs_filepath
        self.is_deleted = is_deleted
        self._is_dir = is_dir
        self._ipfs_key = ipfs_key
        self._doc_type = doc_type
        self.private_key = private_key # 除了往服务器中提交数据之外，也是加密文件用到的的 key
        self.should_encrypt_file = should_encrypt_file
        self.should_ignore_current_file = False

        self._raw_content = raw_content
        self._raw_byte_content = smart_str(raw_content or '')

        self.version = version

        self.utc_offset = utc_offset

    @cached_property
    def lower_path(self):
        return self.relative_path.lower()

    @cached_property
    def metadata(self):
        return {}

    def get_meta_value(self, key, default=None):
        return _get_meta_value(key=key, metadata=self.metadata, default=default)


    @cached_property
    def file_version(self):
        # if is_deleted = True, will not get the file version, only get it by self.version
        if self._raw_content:
            return get_md5(self._raw_byte_content)
        if self.is_dir:
            version = None
        elif self.abs_filepath and os.path.isfile(self.abs_filepath):
            version = md5_for_file(self.abs_filepath)
        else:
            version = None
        return version

    @cached_property
    def file_size(self):
        if self._raw_content:
            return len(self._raw_byte_content)
        elif self.is_dir:
            return 0
        elif self.abs_filepath and os.path.isfile(self.abs_filepath):
            return os.path.getsize(self.abs_filepath)
        else:
            return 0


    @cached_property
    def is_dir(self):
        if self._raw_content:
            return False
        if self._is_dir is not None:
            return self._is_dir
        else:
            return os.path.isdir(self.abs_filepath)

    @cached_property
    def slash_number(self):
        return self.path.strip('/').count('/')

    @cached_property
    def title(self):
        path_parts = os.path.split(self.path)
        if len(path_parts) <= 1:
            filename = self.path
        else:
            filename = path_parts[1]
        if self.is_dir:
            title = filename
        else:
            title = filename.rsplit('.', 1)[0].strip()
        return title

    @cached_property
    def filename(self):  # 区分大小写的
        return os.path.split(self.path)[1]

    @cached_property
    def name(self):  # just name, without .ext
        return os.path.splitext(self.filename)[0]


    @cached_property
    def title(self):
        title, position = split_title_and_position(self.name)
        return title

    @cached_property
    def position(self):  # 根据文件名获得的position，支持浮点数
        title, position = split_title_and_position(self.name)
        return position



    @cached_property
    def ipfs_key(self):
        # hash on ipfs
        if self._raw_content or self.is_dir:
            return None
        if self._ipfs_key: # 已经传入，就不特殊获取了
            return self._ipfs_key
        if self.abs_filepath and os.path.isfile(self.abs_filepath):
            if self.should_encrypt_file:
                ipfs_hash = get_ipfs_hash_from_filepath(self.abs_filepath, encrypt_key=self.private_key)
            else:
                ipfs_hash = get_ipfs_hash_from_filepath(self.abs_filepath)
            return ipfs_hash
        else:
            return None

    @cached_property
    def raw_content(self):
        if self._raw_content:
            return self._raw_content
        elif self.is_dir:
            return ''

        # todo 这里如何加密的问题需要处理
        if self.abs_filepath and os.path.isfile(self.abs_filepath):
            return read_file(self.abs_filepath)
        else:
            return ''

    @cached_property
    def gb64_raw_content(self):
        # gzip and base64
        if self.raw_content:
            return gzip_content(self.raw_content, base64=True)
        else:
            return ''


    @cached_property
    def basic_compiled_data(self):
        if self.is_dir:
            _type = 'folder'
        else:
            _type = self._doc_type or 'file'
        data = dict(
            path = self.relative_path,
            #url_path = self.relative_path.lower(),
            version = self.file_version or self.version,
            size = self.file_size,
            is_dir = self.is_dir,
            is_deleted = self.is_deleted,
            title = self.title,
            slash_number = self.relative_path.count('/'),
            _ipfs = self.ipfs_key,
            _is_encrypted = self.should_encrypt_file,
            _type = _type,
            type = _type,
            timestamp = int(time.time()),
            _v = farbox_version,  # FarBox Bucket Package version
        )
        if not self.abs_filepath:
            data['mtime'] = time.time()
        elif not self.is_deleted and os.path.isfile(self.abs_filepath):
            mtime = os.path.getmtime(self.abs_filepath)
            data['mtime'] = mtime
        return data



    def get_compiled_data(self):
        # 子类需要处理的
        return {}


    def update_files_info(self, data):
        return


    @cached_property
    def compiled_data(self):
        data = self.basic_compiled_data
        if self.is_deleted:
            self.update_files_info(data) # 用于 update_files_info
            return data
        extra_data = self.get_compiled_data()
        if extra_data is None: # 认为当前 compile 失败了
            return {}
        data.update(extra_data)
        self.update_files_info(data)  # 用于 update_files_info
        return data


    @cached_property
    def ipfs_compiled_data(self):
        # 通用的做法，处置为 ipfs 上的逻辑
        data = self.basic_compiled_data
        return data


