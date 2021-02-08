# coding: utf8
import os
import gevent
import requests
from farbox_bucket.utils import smart_str, get_md5
from farbox_bucket.utils.url import get_url_path
from farbox_bucket.bucket.utils import has_bucket
from farbox_bucket.bucket.record.get.path_related import has_record_by_path
from farbox_bucket.server.helpers.file_manager import sync_file_by_server_side


def do_download_from_internet_and_sync(bucket, path, url, timeout=10):
    # 下载行为， 这里要获得site，因为如果是异步的话，g.site是无效的
    if not has_bucket(bucket):
        return
    try:
        response = requests.get(url, timeout=timeout, verify=False)
        if response.status_code > 300:
            return  # ignore
        response_content = smart_str(response.content)
        if not response_content:
            return
        sync_file_by_server_side(bucket=bucket, relative_path=path, content=response_content) # 进行同步
        return True
    except:
        pass



def download_from_internet_and_sync(bucket, url, folder_to_save='/_data/downloads', path=None, timeout=10, force=False, async=True):
    # 从互联上下载内容
    if not has_bucket(bucket):
        return ""
    if not path: # 自动生成doc_path, 以url为md5作为filename
        url_path = get_url_path(url)
        ext = os.path.splitext(url_path)[-1]
        url_md5 = get_md5(url)
        filename = url_md5 + ext
        path = '/%s/%s' % (folder_to_save.strip('/'), filename)
    if not force:
        # 非强制的情况下，如果文件已经存在，就不下载了
        if has_record_by_path(bucket, path):
            return path
    if async:
        gevent.spawn(do_download_from_internet_and_sync, bucket, path, url=url, timeout=timeout)
    else:
        do_download_from_internet_and_sync(bucket, path, url, timeout=timeout)
    return path
