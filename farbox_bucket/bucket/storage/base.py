# coding: utf8
import os, io
from flask import send_file
from gevent import spawn
from farbox_bucket.utils import str_type, to_bytes
from farbox_bucket.utils.objectid import is_object_id
from farbox_bucket.utils.mime import guess_type
from farbox_bucket.utils.gzip_content import ungzip_content
from farbox_bucket.utils.image.utils import fast_get_image_size
from farbox_bucket.bucket.record.update import update_record
from farbox_bucket.bucket.record.get.path_related import get_record_id_by_path
from farbox_bucket.server.utils.response import set_304_response_for_doc, p_redirect
from farbox_bucket.bucket.usage.bucket_usage_utils import increase_file_size_for_bucket, decrease_file_size_for_bucket, \
    increase_bandwidth_for_bucket
from .helpers.auto_resized_image import get_response_for_resized_image

class Storage(object):
    def __init__(self):
        pass

    def update_record_when_file_stored(self, bucket, record_data, file_size=None, image_info=None):
        # 原则上，我们是不允许对 record 进行修改的，因为文件分开了存储，做一个妥协性的对应
        # 主要是 accept_upload_file_from_client 上调用后，要再调用本函数
        if not isinstance(record_data, dict):
            return
        record_id = record_data.get("_id")
        if not record_id:
            record_id = get_record_id_by_path(bucket, path=record_data.get("path"))
        if not is_object_id(record_id):
            return
        if record_data.get("_file_stored"):
            return

        # 走 update_record 的逻辑
        kwargs_to_update = {"_file_stored": True}
        if file_size is not None:
            kwargs_to_update["file_size"] = file_size
        if image_info and isinstance(image_info, dict):
            image_info.pop("_id", None) # in case, try remove _id
            kwargs_to_update.update(image_info)
        update_record(bucket=bucket, record_id=record_id, **kwargs_to_update)
        file_size = kwargs_to_update.get("file_size")
        increase_file_size_for_bucket(bucket, file_size)

    def update_bucket_file_size_when_deleted(self, bucket, record_data):
        if isinstance(record_data, dict):
            file_size = record_data.get("file_size") or record_data.get("size")
            if file_size:
                decrease_file_size_for_bucket(bucket, file_size)

    def update_bucket_bandwidth(self, bucket, record_data):
        if isinstance(record_data, dict):
            file_size = record_data.get("file_size")
            if file_size:
                increase_bandwidth_for_bucket(bucket, file_size)


    def get_image_size_from_raw_content(self, raw_content):
        if isinstance(raw_content, str_type):
            return fast_get_image_size(raw_content)
        else:
            return 0,0

    def is_responsable_for_web(self, bucket, record):
        file_stored = record.get("_file_stored")
        if not file_stored:
            return False
        local_filepath = self.get_local_filepath(bucket, record)
        if local_filepath:
            if os.path.isfile(local_filepath):
                return True
        elif self.get_url(bucket, record):
            return True
        return False

    def as_web_response(self, bucket, record, mimetype="", try_resized_image=True):
        # 只处理存储在外部（包括本地），但不在 database 中的数据
        file_stored = record.get("_file_stored")
        if not file_stored:
            return
        relative_path = record.get('path')
        if not relative_path:
            return  # ignore
        local_filepath = self.get_local_filepath(bucket, record)

        mimetype = mimetype or guess_type(relative_path) or 'application/octet-stream'

        # 处理缩略图的对应
        if try_resized_image and mimetype.startswith("image"):
            resized_image_response =  get_response_for_resized_image(bucket, record, self)
            if resized_image_response:
                return resized_image_response

        if local_filepath:
            if os.path.isfile(local_filepath):
                response = send_file(local_filepath, mimetype=mimetype)
                spawn(self.update_bucket_bandwidth, bucket, record)
                set_304_response_for_doc(response=response, doc=record, date_field='mtime')
                return response
            else:
                return
        else:
            file_url = self.get_url(bucket, record)
            if file_url:
                spawn(self.update_bucket_bandwidth, bucket, record)
                return p_redirect(file_url)
            else:
                return


    def get_download_response_for_record(self, bucket, record_data, try_resized_image=False):
        # 同步回去的 response
        # 如果是 Web 端给普通访客的，则会根据需要自动提供缩略图的逻辑支持
        raw_content = record_data.get('raw_content') or record_data.get('content') or ''
        if raw_content and record_data.get('_zipped'):
            try:
                raw_content = ungzip_content(raw_content, base64=True)
            except:
                pass
        mime_type = guess_type(record_data.get("path", "")) or "application/octet-stream"
        if raw_content:
            raw_content = to_bytes(raw_content)
            return send_file(io.BytesIO(raw_content), mimetype=mime_type)
        else:
            file_response = self.as_web_response(bucket, record_data, try_resized_image=try_resized_image)
            return file_response # 可能是 None


    ########### others starts ###########
    def when_record_deleted(self, bucket, record_data):
        # 一般来说，是不允许 delete record，最多最多也只有 replace，这里因为存储了静态文件，所以有这个对应
        # delete the file
        pass

    def should_upload_file_by_client(self, bucket, record_data):
        return True

    def accept_upload_file_from_client(self, bucket, record_data, get_raw_content_func=None):
        # return ok, failed, existed
        return 'ok'

    def get_local_filepath(self, bucket, record_data):
        # if the static file is stored on server
        return ""

    def get_url(self, bucket, record_data):
        # if stored on a Cloud, return the url
        return ""


    def get_raw_content(self, bucket, record_data):
        # get the raw content from local or a Cloud
        return ""


    def exists(self, bucket, record_data):
        # like is_file
        return False



