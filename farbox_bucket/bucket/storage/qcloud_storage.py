#coding: utf8
import os, time
from farbox_bucket.settings import DEBUG, MAX_FILE_SIZE
from farbox_bucket.utils import string_types, smart_str, get_md5
from farbox_bucket.utils.mime import guess_type
from farbox_bucket.clouds.qcloud import sign_qcloud_url

from farbox_bucket.bucket.record.utils import get_file_id_from_record
from farbox_bucket.bucket.clouds.storage.qcloud import delete_file_on_qcloud_for_bucket, has_file_on_qcloud_for_bucket, \
    upload_file_to_qcloud_for_bucket, get_file_on_qcloud_for_bucket, QCLOUD_URL, QCLOUD_CDN_TOKEN
from farbox_bucket.bucket.storage.helpers.before_store_image import get_image_info_from_raw_content

from .base import Storage


class QCloudStorage(Storage):

    def get_filepath_from_record(self, bucket, record_data):
        file_id = get_file_id_from_record(record_data)
        if file_id:
            filepath = file_id
            #filepath = "%s/%s" % (bucket, file_id)
            return filepath
        else:
            return None


    def when_record_deleted(self, bucket, record_data):
        filepath = self.get_filepath_from_record(bucket, record_data)
        if filepath:
            delete_file_on_qcloud_for_bucket(bucket, filepath)
        self.update_bucket_file_size_when_deleted(bucket, record_data)

    def should_upload_file_by_client(self, bucket, record_data):
        filepath = self.get_filepath_from_record(bucket, record_data)
        if filepath:
            if has_file_on_qcloud_for_bucket(bucket, filepath):
                if not record_data.get("_file_stored"):
                    # 不需要上传，但是又没有标记，进行一次标记
                    self.update_record_when_file_stored(bucket, record_data)
                return False
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
        if hasattr(get_raw_content_func, "__call__"):
            raw_content = get_raw_content_func()
        else:
            raw_content = get_raw_content_func

        if len(raw_content) > MAX_FILE_SIZE:
            return "failed"

        if not self.exists(bucket, record_data):
            if not raw_content or not isinstance(raw_content, string_types):
                return "failed"
            # qcloud_cos.cos_common.maplist
            content_type = guess_type(record_data.get("path"))
            relative_path = record_data.get("path") or ""
            filename = os.path.split(relative_path)[-1]
            headers = dict()
            if filename:
                headers["ContentDisposition"] = smart_str('attachment;filename="%s"' % relative_path)
            if DEBUG:
                print("upload %s to qcloud" % relative_path)
            uploaded = upload_file_to_qcloud_for_bucket(bucket, filepath, raw_content, content_type=content_type, **headers)
            if uploaded:
                file_size = len(raw_content)
                image_info = {}
                if guess_type(relative_path).startswith("image/"):
                    image_info = get_image_info_from_raw_content(raw_content)
                self.update_record_when_file_stored(bucket, record_data, file_size=file_size, image_info=image_info)
                return "ok"
            else:
                return "failed"
        else:
            if raw_content and isinstance(raw_content, string_types):
                file_size = len(raw_content)
            else:
                file_size = 0
            self.update_record_when_file_stored(bucket, record_data, file_size=file_size)  # try to update the record
            return "existed"

    def get_url(self, bucket, record_data):
        filepath = self.get_filepath_from_record(bucket=bucket, record_data=record_data)
        # the relative path
        if filepath and QCLOUD_URL:
            url_path = "/%s/%s" % (bucket, filepath)
            if QCLOUD_CDN_TOKEN:
                # 10000秒的容差, about 3 hours, 相当于 3 个小时左右的跳转 URL 是固定的，方便缓存的逻辑
                return sign_qcloud_url(QCLOUD_URL, qcloud_token=QCLOUD_CDN_TOKEN, url_path=url_path)
            else:
                return "%s%s" % (QCLOUD_URL, url_path)
        else:
            return ""

    def exists(self, bucket, record_data):
        filepath = self.get_filepath_from_record(bucket=bucket, record_data=record_data)
        if filepath:
            return has_file_on_qcloud_for_bucket(bucket, filepath)
        return False

    def get_raw_content(self, bucket, record_data):
        filepath = self.get_filepath_from_record(bucket=bucket, record_data=record_data)
        if filepath:
            return get_file_on_qcloud_for_bucket(bucket=bucket, relative_path=filepath)
        else:
            return None
