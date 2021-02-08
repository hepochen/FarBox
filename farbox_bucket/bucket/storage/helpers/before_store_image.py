# coding: utf8
from farbox_bucket.utils.image.utils import get_im, get_im_size
from farbox_bucket.utils.image.exif import Exif
from farbox_bucket.utils.date import get_image_date
from farbox_bucket.bucket.utils import get_bucket_utc_offset
from farbox_bucket.utils.date import date_to_timestamp

# 在图片存储之前，解析图片的信息，包括旋转相关的逻辑


def do_get_image_info_from_raw_content(raw_content):
    info = {}
    im = get_im(raw_content)
    if not im:
        return info
    exif_obj = Exif(im)
    exif = exif_obj.data  # 获得exif信息，并且会自动旋转图片
    info['exif'] = exif
    info['degrees'] = exif_obj.degrees  # 旋转角度多少才能正回来
    # 从exif中取日期
    utc_offset = get_bucket_utc_offset()
    image_date = get_image_date(exif, None, utc_offset)
    if image_date:
        info["date"] = image_date
        sort_value = date_to_timestamp(image_date, is_utc=True)
        info["_order"] = sort_value # 要处理图片的排序
    im_size = get_im_size(im)
    image_width, image_height = im_size
    if image_width and image_height:
        info['image_width'] = image_width
        info['image_height'] = image_height
    return info


def get_image_info_from_raw_content(raw_content):
    try:
        return do_get_image_info_from_raw_content(raw_content)
    except:
        return {}
