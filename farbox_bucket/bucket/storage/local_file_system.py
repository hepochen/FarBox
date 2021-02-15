#coding: utf8
import os, shutil
from farbox_bucket.settings import DEBUG, MAX_FILE_SIZE
from farbox_bucket.utils import string_types
from farbox_bucket.utils.mime import guess_type
from farbox_bucket.utils.path import write_file
from farbox_bucket.bucket.record.utils import get_file_id_from_record
from farbox_bucket.bucket.storage.helpers.before_store_image import get_image_info_from_raw_content
from .base import Storage



def get_server_side_storage_filepath_root():
    storage_root = os.environ.get('STORAGE_ROOT') or '/mt/web/data/file_storage'
    return storage_root


def get_server_side_storage_folder(bucket, sub_root='origin', sub_folder=''):
    storage_folder = get_server_side_storage_filepath_root()
    if sub_root:
        storage_folder = os.path.join(storage_folder, sub_root)
    storage_folder = os.path.join(storage_folder, bucket)
    if sub_folder:
        storage_folder = os.path.join(storage_folder, sub_folder)
    return storage_folder


def get_server_side_storage_filepath(bucket, file_id=None, version=None, sub_root='origin', sub_folder='', auto_split_name=True):
    # 一般不使用 sub_folder， 在 sub_root=='cache' 的情况下有用到， 用于区分 图片类型-width-height 作为一个 space
    storage_folder = get_server_side_storage_folder(bucket, sub_root=sub_root, sub_folder=sub_folder)
    storage_key = file_id or version
    if not isinstance(storage_key, string_types) or not storage_key:
        return
    if auto_split_name:
        if len(storage_key) < 10:
            filepath = os.path.join(storage_folder, storage_key)
        else:
            filepath = os.path.join(storage_folder, storage_key[:5], storage_key[5:])
    else:
        filepath = os.path.join(storage_folder, storage_key)
    return filepath




class LocalStorage(Storage):
    def get_filepath_from_record(self, bucket, record_data):
        file_id = get_file_id_from_record(record_data)
        if file_id:
            filepath = get_server_side_storage_filepath(file_id=file_id, bucket=bucket)
            return filepath
        else:
            return None

    ############ API starts ########
    def when_record_deleted(self, bucket, record_data):
        filepath = self.get_filepath_from_record(bucket, record_data)
        if filepath and os.path.isfile(filepath):
            try: os.remove(filepath)
            except: pass
        self.update_bucket_file_size_when_deleted(bucket, record_data)

    def should_upload_file_by_client(self, bucket, record_data):
        filepath = self.get_filepath_from_record(bucket=bucket, record_data=record_data)
        if filepath and os.path.isfile(filepath):
            return False
        else:
            return True

    def accept_upload_file_from_client(self, bucket, record_data, get_raw_content_func=None):
        # return ok, failed, existed
        if not self.should_upload_file_by_client(bucket, record_data):
            return "failed"
        filepath = self.get_filepath_from_record(bucket=bucket, record_data=record_data)
        if not filepath:
            return "failed"
        if not get_raw_content_func:
            return "failed"
        if not os.path.isfile(filepath):
            if hasattr(get_raw_content_func, "__call__"):
                raw_content = get_raw_content_func()
            else:
                raw_content = get_raw_content_func
            if not raw_content or not isinstance(raw_content, string_types):
                return "failed"
            if len(raw_content) > MAX_FILE_SIZE:
                return "failed"
            if DEBUG:
                relative_path = record_data.get("path") or ""
                print("store %s to local" % relative_path)
            write_file(filepath, raw_content)

            file_size = len(raw_content)
            image_info = None
            if guess_type(filepath).startswith("image/"):
                image_info = get_image_info_from_raw_content(raw_content)
            self.update_record_when_file_stored(bucket, record_data, file_size=file_size, image_info=image_info) # update the record
            return "ok"
        else:
            try:
                file_size = os.path.getsize(filepath) or 0
            except:
                file_size = 0
            self.update_record_when_file_stored(bucket, record_data, file_size=file_size)  # try to update the record
            return "existed"

    def get_local_filepath(self, bucket, record_data):
        filepath = self.get_filepath_from_record(bucket=bucket, record_data=record_data)
        return filepath

    def exists(self, bucket, record_data):
        filepath = self.get_filepath_from_record(bucket=bucket, record_data=record_data)
        if filepath:
            return os.path.isfile(filepath)
        else:
            return False

    def get_raw_content(self, bucket, record_data):
        filepath = self.get_filepath_from_record(bucket=bucket, record_data=record_data)
        if os.path.isfile(filepath):
            with open(filepath, "rb") as f:
                return f.read()
        else:
            return None

    ############ API ends ########