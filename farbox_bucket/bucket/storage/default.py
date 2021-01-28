# coding: utf8
from farbox_bucket.bucket.clouds.storage.qcloud import qcloud_is_valid
from .local_file_system import LocalStorage
from .qcloud_storage import QCloudStorage


def get_default_storage():
    if qcloud_is_valid:
        return QCloudStorage()
    else:
        return LocalStorage()


storage = get_default_storage()