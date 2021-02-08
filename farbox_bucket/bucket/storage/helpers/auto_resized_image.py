# coding: utf8
from __future__ import absolute_import
import os, re
from flask import request
from farbox_bucket.utils import string_types
from farbox_bucket.utils.image.resize import resize_image, can_resize_by_system
from farbox_bucket.utils.image.utils import get_im
from farbox_bucket.utils import to_int
from farbox_bucket.bucket.record.update import update_record
from farbox_bucket.bucket.record.utils import get_file_id_from_record
from farbox_bucket.bucket.record.get.path_related import get_record_by_path
from farbox_bucket.bucket.utils import get_bucket_site_configs

from farbox_bucket.server.utils.site_resource import get_site_config

# 这里其实有个隐患，就是原图太大，存在处理上的内存压力

def get_response_for_resized_image(bucket, record, storage):
    from farbox_bucket.server.helpers.file_manager import sync_file_by_server_side
    if not record or not isinstance(record, dict):
        return

    if record.get("_get_im_failed"):
        return
    #if not is_doc_modified(record, date_field='mtime'): #todo ????
    #   return get_304_response()

    if request.args.get('origin') in ['true']:
        return # ignore
    relative_path = record.get('path')
    if not relative_path:
        return
    file_id = get_file_id_from_record(record)
    if not file_id:
        return
    ext = os.path.splitext(relative_path)[-1].strip('.').lower()
    if ext not in ['png', 'jpg', 'jpeg', 'bmp', 'png']:
        return
    if not can_resize_by_system():
        return
    site_settings = get_bucket_site_configs(bucket)
    image_max_width = to_int(site_settings.get('image_max_width'), default_if_fail=None)

    size_from_request = request.values.get("size")
    if size_from_request == "m":
        image_max_width = 600

    if not isinstance(image_max_width, int) or image_max_width<100:
        image_max_width = None
    image_max_height = to_int(site_settings.get('image_max_height'), default_if_fail=None)
    if not isinstance(image_max_height, int) or image_max_height<100:
        image_max_height = None
    if not image_max_height and not image_max_width:
        return

    # 处理 image_max_type 允许的值
    image_max_type = (get_site_config('image_max_type') or 'webp-jpg').lower().strip()
    if not isinstance(image_max_type, string_types):
        image_max_type = 'webp-jpg'
    if not re.match("[a-z-]+$", image_max_type):
        image_max_type = "jpg"

    if "webp" in image_max_type:
        request_client_accept = request.headers.get("Accept") or ""
        if "image/webp" not in request_client_accept:
            # webp 浏览器不支持的情况下
            image_max_type = "png" if ext == "png" else "jpg"

    if image_max_type == 'webp-jpg':
        mimetype = 'image/webp'
    else:
        if '/' not in image_max_type:
            mimetype = 'image/%s' % image_max_type
        else:
            mimetype = image_max_type
        if mimetype == 'image/jpg':
            mimetype = 'image/jpeg'

    if "webp" not in mimetype:
        # 非 webp，并且文件中能读取到 size 的，判断是否需要进行缩略图的处理
        image_width = record.get("image_width")
        image_height = record.get("image_height")
        if image_width and image_height:
            if image_max_width and image_width < image_max_width:
                return
            if image_max_height and image_height < image_max_height:
                return
    if "webp" in image_max_type:
        ext = "webp"

    cache_image_filepath = "_cache/images/%s/%s-%s-%s.%s" % (file_id, image_max_type, image_max_width, image_max_height, ext)
    cache_image_record = get_record_by_path(bucket=bucket, path=cache_image_filepath)


    if cache_image_record:
        # 已经存在了
        return storage.as_web_response(bucket=bucket, record=cache_image_record, mimetype=mimetype, try_resized_image=False)
    else:
        # todo 这里应该增加一个 time-block，避免潜在的攻击存在
        # 构建一个缩略图
        raw_content = storage.get_raw_content(bucket=bucket, record_data=record)
        if not raw_content: return
        try: im = get_im(raw_content)
        except: im = None
        if not im:
            # 标识，下次就不会尝试了
            update_record(bucket, record_id=record.get("_id"), _get_im_failed=True)
            return
        degrees = to_int(record.get("degrees"), default_if_fail=0)
        if image_max_type == 'webp-jpg':
            #resized_jpg_content = resize_image(im, width=image_max_width, height=image_max_height, image_type='jpg')
            #resized_jpg_im = get_im(resized_jpg_content)
            resized_im_content = resize_image(im, width=image_max_width, height=image_max_height, image_type='webp', degrees=degrees)
            if not resized_im_content:
                update_record(bucket, record_id=record.get("_id"), _get_im_failed=True)
                return
            #del im, resized_im_content # resized_jpg_im,
        else:
            resized_im_content = resize_image(im, width=image_max_width, height=image_max_height, image_type=image_max_type, degrees=degrees)
        cache_image_record = sync_file_by_server_side(
            bucket = bucket,
            relative_path = cache_image_filepath,
            content = resized_im_content,
            is_dir = False,
            is_deleted = False,
            return_record = True
        )
        if cache_image_record:
            return storage.as_web_response(bucket=bucket, record=cache_image_record, mimetype=mimetype, try_resized_image=False)


