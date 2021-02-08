# coding: utf8
from __future__ import absolute_import
from farbox_bucket.utils.html import linebreaks, html_to_text, limit as _limit, html_escape
from farbox_bucket.utils.date import utc_date_parse as date_parse
from farbox_bucket.utils import UnicodeWithAttrs, smart_unicode, is_str, count_words, to_int
from farbox_bucket.server.template_system.model.date import Date



def date(obj): # 转为日期格式
    try:
        return Date(date_parse(obj))
    except:
        return obj


def length(obj):
    return len(obj)


def words(obj):
    if isinstance(obj, (str, unicode)):
        obj = smart_unicode(obj)
        if len(obj) > 100000:
            return -1 # 超过10w字节, 不能处理了
        return count_words(obj)
    else:
        return 0


def small_thumbnail(obj):
    # todo 还没有处理小型的图片缩略图
    return obj


def escaped(obj):
    # 确保 html 的标签进行转义
    return html_escape(obj)

def plain_html(obj):
    # 先将 html 转为文本，再分行
    return linebreaks(html_to_text(obj))

def to_html(obj):
    # 单纯 html 分行
    return linebreaks(obj)

def to_html_with_images(obj):
    return linebreaks(obj, render_markdown_image=True)

def plain_text(obj):
    # 就是 html 转为 text
    return html_to_text(obj)


def plain(obj):
    # 就是 html 转为 text
    return html_to_text(obj)


def limit(obj, length=None, mark='......', keep_images=True, words=None, remove_a=False, keep_a_html=False, ignore_first_tag_name='blockquote'):
    return _limit(obj, length, mark, keep_images, words, remove_a=remove_a, keep_a_html=keep_a_html, ignore_first_tag_name=ignore_first_tag_name)

def resize(obj, *args, **kwargs):
    # compatibility for Bitcron
    width = to_int(kwargs.get("width", None), default_if_fail=None)
    if width is not None:
        if width <= 800 and width > 300:
            return obj + "?size=m"
    return obj

def has(obj, to_check, just_in=False):
    if isinstance(to_check, (tuple, list)): # 给的是一个list，只要其中一个元素满足就可以了
        for sub_to_check in to_check[:100]: # 最多检测100项
            if isinstance(sub_to_check, (unicode, str)) and has(obj, sub_to_check, just_in=just_in):
                return True

    if not isinstance(obj, (unicode, str)):
        return False
    if not isinstance(to_check, (unicode, str)):
        return False
    to_check = to_check.strip().lower()
    obj = obj.strip().lower()
    to_check_start = to_check.strip()+' '
    to_check_end = ' ' + to_check.strip()
    if just_in:
        return to_check in obj
    elif is_str(to_check):
        if obj == to_check or obj.startswith(to_check_start) or obj.endswith(to_check_end):
            return True
        else:
            return False
    else: # 中文的，没有空格
        return to_check in obj

