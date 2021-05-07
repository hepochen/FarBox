#coding: utf8
from farbox_bucket.utils import string_types, smart_unicode, smart_str
from farbox_bucket.utils.path import get_just_name
from farbox_bucket.utils.date import utc_date_parse, date_to_timestamp
import datetime
import re
import unidecode
import os
import time


def get_meta_value(key, metadata=None, default=None):
    if not isinstance(metadata, dict) or not metadata:
        return default
    if key in metadata:
        value = metadata.get(key)
        if value is None:
            value = default
    else:
        value = default
    if isinstance(value, string_types):
        value = value.strip()

    # 根据default的值，自动格式化得到的value
    if default is not None and not isinstance(value, string_types) and value is not None:
        value = type(default)(value)  # 变量格式化

    return value



def get_file_timestamp(relative_path=None, metadata=None, abs_filepath=None, utc_offset=None):
    # 主要是获取 post 的date信息
    # relative_path 是相对于 root 的 path
    if abs_filepath and not metadata:
        if os.path.isfile(abs_filepath):
            return os.path.getmtime(abs_filepath)
        else:
            return time.time()

    name_from_path = get_just_name(relative_path)
    try:
        metadata_date = metadata.get('date')
        if isinstance(metadata_date, datetime.datetime):
            # 先转成 str 形式，这样能最终获得 utc 的时间戳
            date_s = metadata_date.strftime('%Y-%m-%d %H:%M:%S')
        else:
            date_s = smart_str(get_meta_value(metadata=metadata, key='date', default='')) # 先从meta中获取, 格式化之后，可以自动调整时差
        if date_s:
            date_s = date_s.strip()
        if date_s and re.match('\d{4}\.\d+\.\d+$', date_s):
            # # 2018.3.19  这种日期形式的 转为 xxxx-xx-xx
            date_s = date_s.replace('.', '-')
        if not date_s:
            # 兼容 '2012-12-12 12-12 or 2012-12-12 12-12-12 这种格式'
            if re.match(r'^\d+-\d+-\d+ \d+-\d+(-\d+)?$', name_from_path):
                part1, part2 = name_from_path.split(' ', 1)
                try:
                    s = '%s %s' % (part1, part2.replace('-', ':'))
                    date = utc_date_parse(s, utc_offset=utc_offset)
                    return date
                except:
                    pass
            # 从文件名中获取 2012-1?2-1?2, date模式
            date_search = re.search('/?([123]\d{3}-\d{1,2}-\d{1,2})[^/]*', relative_path)
            if date_search: # 可以从文件的路径中取， 兼容jekyll
                date_s = date_search.groups()[0]
        date = utc_date_parse(date_s, utc_offset=utc_offset)
    except (ValueError, TypeError):
        return time.time()
    timestamp = date_to_timestamp(date)
    if not timestamp:
        timestamp = time.time()
    return timestamp




def split_title_and_position(title):
    position_c = re.search(r'^\d+(\.\d+)? ', title)
    if position_c:
        position = position_c.group()
        new_title = title.replace(position, '', 1)
        title = new_title.lstrip(' ')
    else:
        position = None
    if position:
        position = position.strip()
        if '.' in position:
            position = float(position)
        else:
            position = int(position)
    return title.strip(), position




def slugify(value, must_lower=True, auto=False):
    # auto=True 表示是自动生成的
    value= smart_unicode(value)
    value = unidecode.unidecode(value).strip()
    if must_lower:
        value = value.lower()
    value = re.sub(r'[ &~,"\':*+?#{}()<>\[\]]', '-', value).strip('-')  # 去掉非法的url字符
    value = re.sub(r'-+', '-', value)  # 替换连续的 --的或者-/
    value = value.replace('-/', '/')
    if auto: # 去掉可能的序号, 这样自动生成的 url 美观一点
        value = re.sub(r'^\d{1,2}(\.\d+)? ', '', value).strip() or value
        value = value.strip('-_')
    value = value.strip('/') # 头尾不能包含 /
    return value





def unique_list(data):
    # 类似 set 功能，但是保留原来的次序
    new_data = []
    for row in data:
        if row not in new_data:
            new_data.append(row)
    return new_data


def string_to_list(value):
    if not value:
        return []
    if isinstance(value, string_types) and value:
        if ',' in value:
            ls = value.split(',')
        elif u'，' in value:
            ls = value.split(u'，')
        else:
            ls = value.split(' ')
        ls = [item.strip() for item in ls if item]
        return unique_list(ls)
    elif type(value) in [list, tuple]:
        value = unique_list(value)
        return [smart_unicode(row).strip() for row in value if row]
    else:
        return [smart_unicode(value)]




def get_images_from_html(content, relative_to_site=False):
    raw_images = re.findall("""<\s*img.*?src=['"]([^'"]+).*?>""", content, flags=re.I)
    images = []
    for image_src in raw_images:
        if image_src in images:
            continue
        if relative_to_site and ('://' in image_src or image_src.startswith('//')):
            continue
        images.append(image_src)
    return images

