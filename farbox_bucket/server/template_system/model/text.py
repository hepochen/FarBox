# coding: utf8
from __future__ import absolute_import
import re
from farbox_markdown.meta import extract_metadata
from farbox_bucket.utils import smart_unicode, get_value_from_data, to_int, to_float, is_on
from farbox_bucket.utils.functional import cached_property
from farbox_bucket.utils.html import linebreaks, html_to_text, limit as _limit, html_escape
from farbox_bucket.bucket.record.utils import get_type_from_record
from farbox_bucket.bucket.utils import get_bucket_site_configs

import HTMLParser
unescape = HTMLParser.HTMLParser().unescape

HTML_C = re.compile(r'</?[^<]+?>')


class Text(object):
    def __init__(self, core, attr=None, parent=None):
        self.parent = parent # text 字段所在的父data，比如post
        self.attr = attr # 该字段被调用的名称
        if not isinstance(core, unicode):
            core = smart_unicode(core)
        self.core = core

        self.is_post_content = False
        # 对 post 类型做的特别处理
        if self.parent and isinstance(self.parent, dict):
            if get_type_from_record(self.parent) == "post":
                self.is_post_content = True

    def __nonzero__(self):
        # 判断 boolean 用的
        if self.core:
            return True
        else:
            return False

    def __eq__(self, other):
        return other == self.core


    def __contains__(self, item):
        if not isinstance(item, (str, unicode)):
            item = smart_unicode(item)
        return item in self.core


    def _get_slice_content(self):
        if self.parent and self.attr=='content' and 'raw_content' in self.parent:
            content_to_slice = self.plain_text
        else:
            content_to_slice = self.core
        return content_to_slice


    def __getitem__(self, length):
        # 截取部分内容的
        if isinstance(length, int):
            content_to_slice = self._get_slice_content()
            return linebreaks(content_to_slice[:length], self.post_path)
        return self.core

    def __call__(self, length): # 同上， 截取部分内容的
        return self.__getitem__(length)


    def __getslice__(self, i, j):
        # 也是截取内容，但是可以指定开始、结束的位置
        content_to_slice = self._get_slice_content()
        return content_to_slice[i: j]


    def __repr__(self):
        return self._auto_content

    def __unicode__(self):
        return self._auto_content

    def __add__(self, other):
        # 对相加的特殊处理
        if other is None:
            other = ''
        return '%s%s' % (self.core, other)


    def count(self, key):
        return self.core.count(key)


    @cached_property
    def int(self):
        # '123'.int  or '123'.int('98')
        return to_int(self.core)


    @cached_property
    def float(self):
        # 类似 int 的用法
        return to_float(self.core)


    @cached_property
    def escaped(self):
        return html_escape(self.core)

    @cached_property
    def plain(self):
        return self.plain_text

    @cached_property
    def clean_text(self):
        # 平文本, 即使原来是 html 类型的，也会转为普通文本; 如果有raw_content, 则取raw_content(去除了metadata声明的部分)
        if self.parent and isinstance(self.parent, dict) and 'raw_content' in self.parent:
            raw_content = self.parent['raw_content'] or ''
            clean_content, metadata = extract_metadata(raw_content) # 去除头部可能的 meta 声明的敏感信息
            return clean_content
        else:
            return html_to_text(self.core)

    @cached_property
    def plain_text(self):
        # 平文本, 即使原来是 html 类型的，也会转为普通文本
        return html_to_text(self.core)


    @cached_property
    def plain_html(self):
        # 仅仅处理图片 & 换行的 html
        return  linebreaks(self.plain_text, post_path=self.post_path, render_markdown_image=True)


    @cached_property
    def site_configs(self):
        return get_bucket_site_configs()


    @cached_property
    def _toc_content(self):
        # 主要是 post 的TOC内容
        if not self.parent or not isinstance(self.parent, dict):
            return ''
        toc_content = self.parent.get('toc', '')
        if toc_content:
            return "<div class='toc'>%s</div>" % unescape(toc_content)
        else:
            return ''

    @cached_property
    def site_is_plain_text_type(self):
        if self.site_configs.get('post_content_type') == 'plaintext':
            return True
        return False

    @cached_property
    def _show_toc(self):
        # 只有post，并且post以markdown格式显示的，才有__show_toc这个属性
        if self.is_post_content and self.parent and not self.site_is_plain_text_type:
            # post未设定，走site.configs # post已设定，走post.metadata
            # 默认是post自行定义
            show_toc = get_value_from_data(self.parent, 'metadata.toc', default=self.site_configs.get('show_post_toc'))
            return is_on(show_toc)
        # 默认返回None，表示否
        return False


    @cached_property
    def _content(self):
        if self.attr in ['content',] and self.is_post_content and self.parent and self.parent.get('raw_content') and self.site_is_plain_text_type:
            # post 作为 普通的文本作为解析
            core_content = linebreaks(self.clean_text, post_path=self.post_path, render_markdown_image=True)
            # 增加一个wrap，做一个 class 的外部表示
            core_content = '<div class="plain_content">\n%s\n</div>' % core_content
        else:
            core_content = self.core
        return core_content


    @cached_property
    def _auto_content(self):
        # 主要是直接调用时候的处理，比如 site.title  post.content(这个可能有TOC 或者什么的)
        if self._show_toc and self._toc_content:
            return self._toc_content + self._content
        else:
            return self._content


    @cached_property
    def opening(self):
        # 获取摘要
        opening_parts = re.split(r'<!-- *more *-->', self.core, 1, flags=re.I)
        if len(opening_parts) == 2:
            return opening_parts[0]
        else:
            # 没有分割，就返回空值
            return ''

    @cached_property
    def post_path(self):
        # 日志的路径
        if self.parent and self.parent.get('path') and self.is_post_content:
            return self.parent.get('path')

    def limit(self, length=None, mark='......', keep_images=True, words=None, remove_a=False, keep_a_html=False, ignore_first_tag_name='blockquote'):
        result = _limit(content=self.core, length=length, mark=mark,
                        keep_images=keep_images, words=words, post_path=self.post_path,
                        remove_a=remove_a, keep_a_html=keep_a_html, ignore_first_tag_name=ignore_first_tag_name)
        return result

    # 基本函数的调用 ends
